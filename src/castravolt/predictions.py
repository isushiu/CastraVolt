from datetime import datetime
from uuid import UUID
import hashlib,json

from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,ConfigDict
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from castravolt.account_models import User
from castravolt.auth import csrf,current_user,current_session,database,now,throttle
from castravolt.features import prepare_features
from castravolt.inference import display_count
from castravolt.project_models import Prediction
from castravolt.projects import PredictionResult,owned_site

router=APIRouter(prefix='/api/v1/sites',tags=['Predictions'])


class PredictionInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    idempotency_key:UUID
    site_updated_at:datetime
    acknowledge_model_limitations:bool=False


def existing(db,site_id,key,fingerprint):
    result=db.scalar(select(Prediction).where(Prediction.site_id==site_id,Prediction.idempotency_key==key))
    if result and result.input_snapshot.get('request_fingerprint')!=fingerprint:
        raise HTTPException(409,'This request key was already used for different inputs. Start a new estimate.')
    return result


@router.post('/{site_id}/predictions',response_model=PredictionResult,status_code=201,dependencies=[Depends(csrf)])
def predict(site_id:UUID,data:PredictionInput,request:Request,user:User=Depends(current_user),db:Session=Depends(database)):
    site=owned_site(db,user,site_id)
    fingerprint=hashlib.sha256(json.dumps({'site_id':str(site_id),'revision':data.site_updated_at.isoformat(),
        'ack':data.acknowledge_model_limitations},sort_keys=True).encode()).hexdigest()
    key=str(data.idempotency_key)
    replay=existing(db,site_id,key,fingerprint)
    if replay:return replay
    if site.updated_at!=data.site_updated_at:raise HTTPException(409,'This site changed. Save the current selection before estimating.')
    if not data.acknowledge_model_limitations or request.app.state.settings.environment!='development':
        raise HTTPException(409,'Acknowledge the model limitations to generate a research estimate in development.')
    model=getattr(request.app.state,'prediction_model',None)
    if model is None:raise HTTPException(503,'The verified model is unavailable. Run setup and restore the trusted model artifact, then restart.')
    throttle(request,db,'prediction',str(user.id))
    context=prepare_features(site_id,request,user,db)
    if not context.inference_eligible:raise HTTPException(409,context.limitation)
    if context.site_updated_at!=data.site_updated_at:raise HTTPException(409,'Site changed while preparing inputs. Save and try again.')
    values=context.features.model_dump();db.commit()
    try:raw=model.predict(values);rounded=display_count(raw)
    except Exception:raise HTTPException(503,'The model could not produce a finite estimate. No result was saved.') from None
    if not current_session(request,db):raise HTTPException(401,'Please sign in to continue.')
    db.expire_all();current=owned_site(db,user,site_id,lock=True)
    replay=existing(db,site_id,key,fingerprint)
    if replay:return replay
    if current.updated_at!=data.site_updated_at:raise HTTPException(409,'Site changed during estimation. Save the current selection and retry.')
    snapshot={'request_fingerprint':fingerprint,'site':{'name':current.name,'latitude':current.latitude,'longitude':current.longitude,
        'address':current.address,'category':current.category,'state':values['state'],'updated_at':current.updated_at.isoformat()},
        'features':values,'poi':{'radius_metres':context.radius_metres,'rule_version':context.extraction_rule_version,
        'rule_sha256':context.rule_sha256,'provenance':context.provenance.model_dump(),'extracted_at':context.extracted_at.isoformat()},
        'model':{'version':model.version,'sha256':model.sha256},
        'validation':{'poi_parity_verified':True,'status':'research_prototype','capacity_validated':False,
                      'acknowledged':True,'warning':context.limitation}}
    record=Prediction(site_id=site_id,requester_id=user.id,input_snapshot=snapshot,raw_estimate=raw,displayed_total=rounded,
        model_version=model.version,extraction_rule_version=context.extraction_rule_version,poi_timestamp=context.extracted_at,
        adoption_reference_year=None,adoption_value=None,
        rounding_policy='nearest_half_up_minimum_1',idempotency_key=key,created_at=now())
    try:db.add(record);db.commit()
    except IntegrityError:
        db.rollback();replay=existing(db,site_id,key,fingerprint)
        if replay:return replay
        raise HTTPException(409,'This site or request changed. Refresh before retrying.') from None
    return record
