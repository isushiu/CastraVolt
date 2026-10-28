from uuid import uuid4
from test_accounts import account_settings,client
from test_feature_api import make_site
from test_projects import write


def request_data(client,sid,key=None):
    return {'idempotency_key':key or str(uuid4()),'site_updated_at':client.get(f'/api/v1/sites/{sid}').json()['updated_at'],
        'acknowledge_model_limitations':True}


def test_real_experimental_prediction_is_saved_and_retries_are_idempotent(client,account_settings):
    client.app.state.settings.poi_source='local'
    sid=make_site(client,account_settings);data=request_data(client,sid)
    result=write(client,'POST',f'/sites/{sid}/predictions',data)
    assert result.status_code==201,result.text
    record=result.json()
    assert record['experimental'] is True
    assert record['input_snapshot']['poi']['radius_metres']==1000
    assert 'adoption' not in record['input_snapshot']
    assert record['adoption_reference_year'] is None and record['adoption_value'] is None
    assert record['model_version'].startswith('rf-poi-category-80-cv10-1km-')
    assert record['displayed_total']==max(1,int(__import__('math').floor(record['raw_estimate']+.5)))
    assert len(record['input_snapshot']['features'])==9
    assert record['input_snapshot']['validation']['poi_parity_verified'] is True
    assert write(client,'POST',f'/sites/{sid}/predictions',data).json()['id']==record['id']
    assert len(client.get(f'/api/v1/sites/{sid}/predictions').json())==1
    assert write(client,'PATCH',f'/sites/{sid}',{'name':'Edited later'}).status_code==200
    assert client.get(f'/api/v1/predictions/{record["id"]}').json()['input_snapshot']['site']['name']=='KLCC'
    changed=request_data(client,sid,key=data['idempotency_key'])
    assert write(client,'POST',f'/sites/{sid}/predictions',changed).status_code==409


def test_experimental_ack_and_current_site_revision_required(client,account_settings):
    client.app.state.settings.poi_source='local'
    sid=make_site(client,account_settings);data=request_data(client,sid)
    assert client.post(f'/api/v1/sites/{sid}/predictions',json=data).status_code==403
    assert write(client,'POST',f'/sites/{sid}/predictions',{**data,'acknowledge_model_limitations':False}).status_code==409
    write(client,'PATCH',f'/sites/{sid}',{'category':'Office'})
    assert write(client,'POST',f'/sites/{sid}/predictions',data).status_code==409


def test_concurrent_retries_create_one_history_record(client,account_settings):
    from concurrent.futures import ThreadPoolExecutor
    from fastapi.testclient import TestClient
    from castravolt.main import create_app
    account_settings.poi_source='local'
    sid=make_site(client,account_settings);data=request_data(client,sid)
    def estimate(_):
        with TestClient(create_app(account_settings)) as browser:
            browser.cookies.update(client.cookies)
            response=write(browser,'POST',f'/sites/{sid}/predictions',data)
            assert response.status_code==201,response.text
            return response.json()['id']
    with ThreadPoolExecutor(max_workers=2) as pool:ids=list(pool.map(estimate,[1,2]))
    assert ids[0]==ids[1]
    assert len(client.get(f'/api/v1/sites/{sid}/predictions').json())==1


def test_nonfinite_model_output_is_not_saved(client,account_settings):
    from types import SimpleNamespace
    account_settings.poi_source='local';sid=make_site(client,account_settings)
    client.app.state.prediction_model=SimpleNamespace(**client.app.state.prediction_model.__dict__,predict=lambda values:float('nan'))
    assert write(client,'POST',f'/sites/{sid}/predictions',request_data(client,sid)).status_code==503
    assert client.get(f'/api/v1/sites/{sid}/predictions').json()==[]


def test_production_refuses_unverified_poi_inference(client,account_settings):
    sid=make_site(client,account_settings);data=request_data(client,sid)
    account_settings.environment='production'
    try:assert write(client,'POST',f'/sites/{sid}/predictions',data).status_code==409
    finally:account_settings.environment='development'


def test_site_edit_during_model_execution_is_not_saved(client,account_settings):
    from types import SimpleNamespace
    from sqlalchemy.orm import Session
    from castravolt.project_models import Site
    from castravolt.auth import now
    from uuid import UUID
    account_settings.poi_source='local';sid=make_site(client,account_settings)
    def edited(values):
        with Session(client.app.state.engine) as db:
            site=db.get(Site,UUID(sid));site.updated_at=now();site.category='Office';db.commit()
        return 3.5
    client.app.state.prediction_model=SimpleNamespace(**client.app.state.prediction_model.__dict__,predict=edited)
    assert write(client,'POST',f'/sites/{sid}/predictions',request_data(client,sid)).status_code==409
    assert client.get(f'/api/v1/sites/{sid}/predictions').json()==[]


def test_foreign_account_cannot_predict_a_site(client,account_settings):
    from test_accounts import post
    from castravolt.account_models import User
    from castravolt.auth import hasher,now
    from sqlalchemy.orm import Session
    from fastapi.testclient import TestClient
    from castravolt.main import create_app
    account_settings.poi_source='local';sid=make_site(client,account_settings);data=request_data(client,sid)
    with Session(client.app.state.engine) as db:
        db.add(User(name='Other',email='other@example.com',password_hash=hasher.hash('Long-password-2026!'),created_at=now(),verified_at=now()));db.commit()
    with TestClient(create_app(account_settings)) as other:
        post(other,'login',{'email':'other@example.com','password':'Long-password-2026!'})
        assert write(other,'POST',f'/sites/{sid}/predictions',data).status_code==404


def test_session_revocation_during_prediction_prevents_saving(client,account_settings):
    from types import SimpleNamespace
    from sqlalchemy import update,select
    from sqlalchemy.orm import Session
    from castravolt.account_models import AccountSession
    from castravolt.project_models import Prediction
    from castravolt.auth import now
    account_settings.poi_source='local';sid=make_site(client,account_settings)
    def revoked(values):
        with Session(client.app.state.engine) as db:
            db.execute(update(AccountSession).values(revoked_at=now()));db.commit()
        return 3.5
    client.app.state.prediction_model=SimpleNamespace(**client.app.state.prediction_model.__dict__,predict=revoked)
    assert write(client,'POST',f'/sites/{sid}/predictions',request_data(client,sid)).status_code==401
    with Session(client.app.state.engine) as db:assert db.scalars(select(Prediction)).all()==[]


def test_mismatched_snapshot_cannot_create_prediction(client,account_settings):
    from types import SimpleNamespace
    account_settings.poi_source='local';sid=make_site(client,account_settings)
    values={**client.app.state.prediction_model.__dict__,'snapshot_sha256':'different-snapshot'}
    client.app.state.prediction_model=SimpleNamespace(**values)
    response=write(client,'POST',f'/sites/{sid}/predictions',request_data(client,sid))
    assert response.status_code==409
    assert 'does not match' in response.text
    assert client.get(f'/api/v1/sites/{sid}/predictions').json()==[]


def test_legacy_adoption_history_remains_readable(client,account_settings):
    from sqlalchemy.orm import Session
    from castravolt.project_models import Prediction
    from uuid import UUID
    account_settings.poi_source='local';sid=make_site(client,account_settings)
    created=write(client,'POST',f'/sites/{sid}/predictions',request_data(client,sid)).json()
    with Session(client.app.state.engine) as db:
        record=db.get(Prediction,UUID(created['id']))
        record.adoption_reference_year=2025;record.adoption_value=560
        record.model_version='legacy-rf-3km'
        record.input_snapshot={'validation':{'poi_parity_verified':False},'adoption':{'year':2025,'registrations':560}}
        db.commit()
    result=client.get(f'/api/v1/predictions/{created["id"]}').json()
    assert result['adoption_reference_year']==2025 and result['adoption_value']==560
    assert result['model_version']=='legacy-rf-3km'
    assert result['input_snapshot']['adoption']['registrations']==560
