"""Optional Groq prose, keyed to immutable public aggregates. No raw vehicle data."""
from datetime import timedelta
import hashlib,json,math
from urllib.request import Request as UrlRequest,urlopen
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Request
from pydantic import BaseModel,ConfigDict,Field
from sqlalchemy import select,update,func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session
from castravolt.auth import csrf,current_user,database,now,digest,current_session
from castravolt.account_models import AuthRateLimit
from castravolt.network import tls_context
from castravolt.trend_models import TrendSummary
from castravolt.trends import TrendFilters,active_snapshot,calculate_dashboard

router=APIRouter(prefix='/api/v1/trends',tags=['Registration explanations'])
PROMPT_VERSION='monthly-facts-v1'
SYSTEM_PROMPT=("Explain the supplied public monthly new electric motokar registration statistics for a planner in clear English. "
    "Return one short paragraph of 3 sentences, at most 130 words. Only describe supplied facts. "
    "Do not invent counts, causes, forecasts, charging demand, fleet ownership or charger recommendations. "
    "Use per-year matching-period growth only when available; never compare incomplete years as full years. "
    "Mention incomplete coverage and excluded Rakan Niaga when applicable. No markdown, reasoning or HTML.")


class SummaryInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    filters:TrendFilters
    source_version:str=Field(pattern=r'^[a-f0-9]{64}$')


def summary_key(version,filters,settings):
    value={'source_version':version,'filters':filters.model_dump(),'model':settings.groq_model,'prompt_version':PROMPT_VERSION}
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def result(row,cache_hit):
    return {'text':row.content,'model':row.model,'prompt_version':row.prompt_version,'source_version':row.version_id,'generated_at':row.created_at.isoformat(),'cache_hit':cache_hit}


def cached_summary(db,settings,data):
    row=db.get(TrendSummary,summary_key(data['source_version'],TrendFilters(**data['filters']),settings))
    return result(row,True) if row and row.status=='ready' else None


def generate_text(settings,facts):
    payload={'model':settings.groq_model,'messages':[{'role':'system','content':SYSTEM_PROMPT},{'role':'user','content':json.dumps(facts,separators=(',',':'))}],
             'temperature':0.2,'max_completion_tokens':1000}
    if settings.groq_model.startswith('openai/gpt-oss-'):payload['reasoning_effort']='low'
    request=UrlRequest('https://api.groq.com/openai/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+settings.groq_api_key.get_secret_value(),'Content-Type':'application/json','Accept':'application/json','User-Agent':'CastraVolt/0.1'},method='POST')
    with urlopen(request,timeout=settings.groq_timeout_seconds,context=tls_context()) as response:
        raw=response.read(65537)
        if len(raw)>65536:raise ValueError('Provider response too large')
    data=json.loads(raw)
    choice=data['choices'][0]
    if choice.get('finish_reason')!='stop':raise ValueError('Incomplete summary')
    value=choice['message']['content']
    if not isinstance(value,str) or not value.strip() or len(value)>3000:raise ValueError('Invalid summary')
    return value.strip()


@router.post('/summary',dependencies=[Depends(csrf)])
def summarise(data:SummaryInput,request:Request,user=Depends(current_user),db:Session=Depends(database)):
    settings=request.app.state.settings
    snapshot=active_snapshot(db)
    if snapshot['version']!=data.source_version:raise HTTPException(409,'The registration dataset changed. Refresh the dashboard before generating a summary.')
    dashboard=calculate_dashboard(snapshot,data.filters)
    if not dashboard['months']:raise HTTPException(422,'Choose a period with covered registration data.')
    key=summary_key(snapshot['version'],data.filters,settings)
    cached=db.get(TrendSummary,key)
    if cached and cached.status=='ready':return result(cached,True)
    if not settings.groq_api_key.get_secret_value().strip():raise HTTPException(503,'AI summaries are not configured. Add the Groq key to the backend environment and restart. Charts and calculated statistics remain available.')
    if cached and cached.lease_until>now():raise HTTPException(429,'This summary is being prepared or waiting after a failed attempt. Try again shortly.',headers={'Retry-After':str(max(1,min(30,math.ceil((cached.lease_until-now()).total_seconds()))))})
    # Reserve each identity across workers before calling a paid provider.
    token=str(uuid4())
    claim=insert(TrendSummary).values(key=key,version_id=snapshot['version'],model=settings.groq_model,prompt_version=PROMPT_VERSION,filters=data.filters.model_dump(),status='pending',content=None,lease_token=token,lease_until=func.clock_timestamp()+timedelta(seconds=120),created_at=now())
    claim=claim.on_conflict_do_update(index_elements=['key'],set_={'status':'pending','lease_token':token,'lease_until':func.clock_timestamp()+timedelta(seconds=120),'content':None},where=(TrendSummary.status!='ready')&(TrendSummary.lease_until<=func.clock_timestamp())).returning(TrendSummary.key)
    if not db.scalar(claim):
        db.rollback();raise HTTPException(429,'This summary is already being prepared. Try again shortly.',headers={'Retry-After':'5'})
    # Small independent per-planner guard on new generations; cached reads bypass it.
    rate_key=digest('trend-summary:'+str(user.id))
    guard=insert(AuthRateLimit).values(key=rate_key,count=1,expires_at=func.clock_timestamp()+timedelta(seconds=15))
    guard=guard.on_conflict_do_update(index_elements=['key'],set_={'count':1,'expires_at':func.clock_timestamp()+timedelta(seconds=15)},where=AuthRateLimit.expires_at<=func.clock_timestamp()).returning(AuthRateLimit.key)
    if not db.scalar(guard):
        db.rollback();raise HTTPException(429,'Please wait a moment before generating a different summary.',headers={'Retry-After':'15'})
    db.commit()
    facts={k:dashboard[k] for k in ['source_version','filters','scope','coverage','months','metrics','total','average_per_month','peak']}
    try:
        content=generate_text(settings,facts)
        if not isinstance(content,str) or not content.strip() or len(content)>3000:raise ValueError()
    except Exception:
        # Never expose provider error bodies, headers or credentials to callers/logs.
        db.execute(update(TrendSummary).where(TrendSummary.key==key,TrendSummary.lease_token==token).values(status='failed',content=None,lease_until=now()+timedelta(seconds=30)));db.commit()
        raise HTTPException(503,'The AI summary service is unavailable. Your charts and calculated statistics are unaffected. Try again shortly.',headers={'Retry-After':'30'}) from None
    if not current_session(request,db):raise HTTPException(401,'Please sign in to continue.')
    db.execute(update(TrendSummary).where(TrendSummary.key==key,TrendSummary.lease_token==token).values(status='ready',content=content.strip(),created_at=now(),lease_until=now()))
    db.commit();db.expire_all()
    row=db.get(TrendSummary,key)
    if row.status!='ready':raise HTTPException(409,'Summary generation changed. Refresh before retrying.')
    return result(row,False)
