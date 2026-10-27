from test_accounts import account_settings, client, post
from test_projects import login, write
from test_features import payload,element


def make_site(client,settings):
    login(client,settings)
    pid=write(client,'POST','/projects',{'name':'Features'}).json()['id']
    return write(client,'POST',f'/projects/{pid}/sites',{'name':'KLCC','latitude':3.1579,'longitude':101.7116,'category':'Shopping Mall'}).json()['id']


def test_owned_context_cached_with_ten_features(client,account_settings,monkeypatch):
    from castravolt import features
    sid=make_site(client,account_settings);calls=[]
    def fetch(*args):calls.append(1);return payload([element('node',1,{'shop':'mall'})])
    monkeypatch.setattr(features,'fetch_overpass',fetch)
    response=write(client,'POST',f'/sites/{sid}/features')
    assert response.status_code==200,response.text
    body=response.json();assert len(body['features'])==10
    assert 'state_ev_registrations' not in body['features']
    assert 'adoption' not in body
    assert body['features']['nearby_mall_count']==1
    assert body['radius_metres']==1000 and body['inference_eligible'] is False
    assert write(client,'POST',f'/sites/{sid}/features').json()['cache_hit'] is True
    assert len(calls)==1
    from sqlalchemy import select,func
    from sqlalchemy.orm import Session
    from castravolt.account_models import AuthRateLimit
    from castravolt.auth import digest
    with Session(client.app.state.engine) as db:
        remaining=db.scalar(select(func.extract('epoch',AuthRateLimit.expires_at-func.clock_timestamp())).where(AuthRateLimit.key==digest('overpass:global')))
        assert remaining<=2  # Completion does not leave a fixed 35-second busy period.
    assert client.get(f'/api/v1/sites/{sid}/predictions').json()==[]
    post(client,'logout')
    assert write(client,'POST',f'/sites/{sid}/features').status_code==401


def test_provider_failure_is_not_cached_as_zero(client,account_settings,monkeypatch):
    from castravolt import features
    sid=make_site(client,account_settings)
    monkeypatch.setattr(features,'fetch_overpass',lambda *args: payload([])|{'remark':'runtime error'})
    result=write(client,'POST',f'/sites/{sid}/features')
    assert result.status_code==503
    from sqlalchemy import select
    from sqlalchemy.orm import Session
    from castravolt.feature_models import PoiCache
    with Session(client.app.state.engine) as db: assert db.scalars(select(PoiCache)).all()==[]


def test_stale_site_rejected_after_provider_call(client,account_settings,monkeypatch):
    from castravolt import features
    from castravolt.project_models import Site
    from castravolt.auth import now
    from sqlalchemy.orm import Session
    from uuid import UUID
    sid=make_site(client,account_settings)
    def fetch(*args):
        with Session(client.app.state.engine) as db:
            record=db.get(Site,UUID(sid));record.category='Office';record.updated_at=now();db.commit()
        return payload([])
    monkeypatch.setattr(features,'fetch_overpass',fetch)
    assert write(client,'POST',f'/sites/{sid}/features').status_code==409


def test_foreign_site_cannot_trigger_provider_work(client,account_settings,monkeypatch):
    from castravolt import features
    from castravolt.account_models import User
    from castravolt.auth import hasher,now
    from sqlalchemy.orm import Session
    from fastapi.testclient import TestClient
    from castravolt.main import create_app
    sid=make_site(client,account_settings)
    with Session(client.app.state.engine) as db:
        db.add(User(name='Other',email='other@example.com',password_hash=hasher.hash('Long-password-2026!'),created_at=now(),verified_at=now()));db.commit()
    def forbidden(*args):raise AssertionError('Foreign lookup reached provider')
    monkeypatch.setattr(features,'fetch_overpass',forbidden)
    with TestClient(create_app(account_settings)) as other:
        post(other,'login',{'email':'other@example.com','password':'Long-password-2026!'})
        assert write(other,'POST',f'/sites/{sid}/features').status_code==404


def test_timeout_has_actionable_message_and_shorter_retry_wait(client,account_settings,monkeypatch):
    from castravolt import features
    sid=make_site(client,account_settings)
    def timeout(*args):raise TimeoutError('Sensitive network details')
    monkeypatch.setattr(features,'fetch_overpass',timeout)
    response=write(client,'POST',f'/sites/{sid}/features')
    assert response.status_code==504
    assert response.headers['retry-after']=='10'
    assert 'timed out' in response.json()['error']['message']
    assert 'Sensitive' not in response.text
    again=write(client,'POST',f'/sites/{sid}/features')
    assert again.status_code==429
    assert 1<=int(again.headers['retry-after'])<=10
    assert '35 seconds' not in again.text


def test_provider_certificate_and_overload_errors_are_distinguished(client,account_settings,monkeypatch):
    import ssl
    from urllib.error import URLError
    from castravolt import features
    sid=make_site(client,account_settings)
    def invalid_cert(*args):raise URLError(ssl.SSLCertVerificationError('certificate has expired'))
    monkeypatch.setattr(features,'fetch_overpass',invalid_cert)
    response=write(client,'POST',f'/sites/{sid}/features')
    assert response.status_code==503
    assert 'secure connection' in response.json()['error']['message']


def test_local_context_uses_genuine_snapshot_without_remote_calls(client,account_settings,monkeypatch):
    from castravolt import features
    from fastapi.testclient import TestClient
    from castravolt.main import create_app
    sid=make_site(client,account_settings)
    def remote_forbidden(*args):raise AssertionError('Local lookup must not contact Overpass')
    monkeypatch.setattr(features,'fetch_overpass',remote_forbidden)
    with TestClient(create_app(account_settings.model_copy(update={'poi_source':'local'}))) as local:
        local.cookies.update(client.cookies)
        response=write(local,'POST',f'/sites/{sid}/features')
        assert response.status_code==200,response.text
        data=response.json()
        assert data['features']['nearby_mall_count']>0
        assert data['provenance']['provider']=='Local Geofabrik OSM snapshot'
        assert data['provenance']['source_snapshot_sha256']
        assert data['inference_eligible'] is True
        assert write(local,'POST',f'/sites/{sid}/features').json()['cache_hit'] is True
