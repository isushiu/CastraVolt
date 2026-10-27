import copy
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import pytest
from pydantic import SecretStr
from sqlalchemy import delete
from sqlalchemy.orm import Session
from test_accounts import account_settings,client,post
from test_projects import login,write


@pytest.fixture(autouse=True)
def clean_summary_cache(client):
    from castravolt.trend_models import TrendSummary
    with Session(client.app.state.engine) as db:db.execute(delete(TrendSummary));db.commit()
    client.app.state.settings.groq_api_key=SecretStr('')


def body(client):
    data=client.get('/api/v1/trends').json()
    return {'filters':data['filters'],'source_version':data['source_version']}


def test_dashboard_authenticated_reconciled_and_validated(client,account_settings):
    assert client.get('/api/v1/trends').status_code==401
    login(client,account_settings)
    data=client.get('/api/v1/trends').json()
    assert data['total']==6401 and len(data['months'])==66
    assert data['summary_enabled'] is False
    assert client.get('/api/v1/trends?years=2026&start_month=2026-10').json()['total'] is None
    assert client.get('/api/v1/trends?states=JOHOR').status_code==422
    assert client.get('/api/v1/trends?comparison_mode=year_over_year&start_month=2026-01').status_code==422


def test_summary_disabled_and_csrf_and_stale_version(client,account_settings):
    login(client,account_settings);data=body(client)
    assert client.post('/api/v1/trends/summary',json=data).status_code==403
    assert write(client,'POST','/trends/summary',data).status_code==503
    assert write(client,'POST','/trends/summary',{**data,'source_version':'0'*64}).status_code==409


def test_generated_summary_cached_across_sessions_and_filter_changes(client,account_settings,monkeypatch):
    from castravolt import trend_summaries as summaries
    login(client,account_settings);data=body(client);calls=[]
    account_settings.groq_api_key=SecretStr('test-secret-never-returned')
    def provider(settings,facts):
        calls.append(copy.deepcopy(facts));return 'Registrations vary by state and month. The latest year is incomplete.'
    monkeypatch.setattr(summaries,'generate_text',provider)
    first=write(client,'POST','/trends/summary',data)
    assert first.status_code==200,first.text
    assert first.json()['cache_hit'] is False
    assert 'test-secret' not in first.text
    assert write(client,'POST','/trends/summary',data).json()['cache_hit'] is True
    dashboard=client.get('/api/v1/trends').json()
    assert dashboard['summary']['cache_hit'] is True
    assert len(calls)==1
    assert set(calls[0])=={'source_version','filters','scope','coverage','months','metrics','total','average_per_month','peak'}
    assert not any('maker' in str(x) or 'password' in str(x) for x in calls[0])
    # Canonical filter order shares the cache identity; dataset/model/prompt changes do not.
    changed=copy.deepcopy(data);changed['filters']['years']=[2026,2025,2024]
    assert write(client,'POST','/trends/summary',changed).json()['cache_hit'] is True
    base=summaries.summary_key(data['source_version'],summaries.TrendFilters(**data['filters']),account_settings)
    assert base!=summaries.summary_key('a'*64,summaries.TrendFilters(**data['filters']),account_settings)
    changed['filters']['years']=[2026]
    assert base!=summaries.summary_key(data['source_version'],summaries.TrendFilters(**changed['filters']),account_settings)
    monkeypatch.setattr(summaries,'PROMPT_VERSION','changed-prompt')
    assert base!=summaries.summary_key(data['source_version'],summaries.TrendFilters(**data['filters']),account_settings)
    monkeypatch.setattr(summaries,'PROMPT_VERSION','monthly-facts-v1')
    account_settings.groq_model='other-model'
    try:assert base!=summaries.summary_key(data['source_version'],summaries.TrendFilters(**data['filters']),account_settings)
    finally:account_settings.groq_model='openai/gpt-oss-20b'


def test_provider_failure_has_no_fabricated_or_ready_summary(client,account_settings,monkeypatch):
    from castravolt import trend_summaries as summaries
    login(client,account_settings);data=body(client);account_settings.groq_api_key=SecretStr('test')
    def broken(*args):raise RuntimeError('secret-provider-body')
    monkeypatch.setattr(summaries,'generate_text',broken)
    failed=write(client,'POST','/trends/summary',data)
    assert failed.status_code==503 and 'secret-provider-body' not in failed.text
    assert client.get('/api/v1/trends').json()['summary'] is None
    assert write(client,'POST','/trends/summary',data).status_code==429


def test_same_summary_concurrent_calls_invoke_provider_once(client,account_settings,monkeypatch):
    from castravolt import trend_summaries as summaries
    from fastapi.testclient import TestClient
    from castravolt.main import create_app
    login(client,account_settings);data=body(client);account_settings.groq_api_key=SecretStr('test')
    entered=Event();release=Event();calls=[]
    def provider(*args):calls.append(1);entered.set();assert release.wait(10);return 'Only filtered monthly registrations are described.'
    monkeypatch.setattr(summaries,'generate_text',provider)
    def first():
        with TestClient(create_app(account_settings)) as other:
            other.cookies.update(client.cookies)
            return write(other,'POST','/trends/summary',data)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future=pool.submit(first)
        try:
            assert entered.wait(10)
            duplicate=write(client,'POST','/trends/summary',data)
            assert duplicate.status_code==429
        finally:release.set()
        assert future.result().status_code==200
    assert calls==[1]
    assert write(client,'POST','/trends/summary',data).json()['cache_hit'] is True


def test_reimport_is_idempotent_and_new_versions_do_not_mix_months(client,account_settings):
    from castravolt.trends_data import packaged_snapshot,identity
    from castravolt.trends import publish_snapshot
    from castravolt.trend_models import RegistrationMonth,RegistrationVersion
    from sqlalchemy import select,func
    login(client,account_settings)
    original=packaged_snapshot()
    with Session(client.app.state.engine) as db:
        publish_snapshot(db,original);publish_snapshot(db,original);db.commit()
        assert db.scalar(select(func.count()).select_from(RegistrationMonth).where(RegistrationMonth.version_id==original['version']))==66
        revised=copy.deepcopy(original);revised['sources'][0]['sha256']='f'*64;revised['version']=identity(revised)
        publish_snapshot(db,revised);db.commit()
        assert db.scalar(select(func.count()).select_from(RegistrationVersion).where(RegistrationVersion.active.is_(True)))==1
    try:
        dashboard=client.get('/api/v1/trends').json()
        assert dashboard['source_version']==revised['version'] and dashboard['total']==6401
        assert write(client,'POST','/trends/summary',{'filters':dashboard['filters'],'source_version':original['version']}).status_code==409
    finally:
        with Session(client.app.state.engine) as db:publish_snapshot(db,original);db.commit()
