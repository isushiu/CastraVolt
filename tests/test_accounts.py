import os
import re
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from castravolt.config import Settings
from castravolt.main import create_app


@pytest.fixture(scope='module')
def account_settings(tmp_path_factory):
    original = Settings()
    assert original.database_url, 'Configure local PostgreSQL to run account integration tests'
    url = make_url(original.database_url)
    name = 'castravolt_test_' + uuid4().hex[:16]
    admin = create_engine(url.set(database='postgres'),isolation_level='AUTOCOMMIT')
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    test_url = url.set(database=name).render_as_string(hide_password=False)
    try:
        result = subprocess.run([sys.executable,'-m','alembic','upgrade','head'],
            env={**os.environ,'CASTRAVOLT_DATABASE_URL':test_url},capture_output=True,text=True)
        assert result.returncode == 0, result.stderr
        yield Settings(database_url=test_url,mail_directory=str(tmp_path_factory.mktemp('mail')),
                       frontend_url='http://localhost:5173',auth_rate_limit=1000)
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        admin.dispose()


@pytest.fixture
def client(account_settings):
    engine = create_engine(account_settings.database_url)
    with engine.begin() as connection:
        connection.execute(text('TRUNCATE account_tokens, sessions, users, auth_rate_limits CASCADE'))
    engine.dispose()
    for path in Path(account_settings.mail_directory).glob('*.eml'): path.unlink()
    with TestClient(create_app(account_settings)) as c:
        yield c


def post(client,path,data=None,token=None):
    token = token or client.get('/api/v1/auth/csrf').json()['csrf_token']
    return client.post('/api/v1/auth/'+path,json=data or {},
                       headers={'Origin':'http://localhost:5173','X-CSRF-Token':token})


def mail_token(settings,kind):
    from email import policy
    from email.parser import Parser
    for path in sorted(Path(settings.mail_directory).glob('*.eml'),key=lambda p:p.stat().st_mtime_ns,reverse=True):
        content = Parser(policy=policy.default).parsestr(path.read_text()).get_content()
        if kind in content: return re.search(r'token=([A-Za-z0-9_-]+)',content).group(1)
    raise AssertionError('Expected email not delivered to development inbox')


def register_verified(client,settings):
    assert post(client,'register',{'name':'Afina','email':'Planner@example.com','password':'Long-password-2026!'}).status_code==202
    token=mail_token(settings,'verify-email')
    assert post(client,'verify-email',{'token':token}).status_code==200


def test_verified_login_session_logout_and_cookie_security(client,account_settings):
    register_verified(client,account_settings)
    response=post(client,'login',{'email':'planner@EXAMPLE.com','password':'Long-password-2026!'})
    assert response.status_code==200
    assert response.json()['user']['email']=='planner@example.com'
    assert 'httponly' in response.headers['set-cookie'].lower()
    assert client.get('/api/v1/auth/me').status_code==200
    assert post(client,'logout').status_code==200
    assert client.get('/api/v1/auth/me').status_code==401


def test_csrf_required_and_untrusted_origin_rejected(client):
    assert client.post('/api/v1/auth/login',json={}).status_code==403
    token=client.get('/api/v1/auth/csrf').json()['csrf_token']
    response=client.post('/api/v1/auth/login',json={'email':'a@example.com','password':'abc'},
          headers={'Origin':'https://evil.example','X-CSRF-Token':token})
    assert response.status_code==403


def test_reset_is_single_use_and_revokes_all_sessions(client,account_settings):
    register_verified(client,account_settings)
    assert post(client,'login',{'email':'planner@example.com','password':'Long-password-2026!'}).status_code==200
    assert post(client,'forgot-password',{'email':'planner@example.com'}).status_code==202
    token=mail_token(account_settings,'reset-password')
    assert post(client,'reset-password',{'token':token,'password':'New-password-2026!'}).status_code==200
    assert client.get('/api/v1/auth/me').status_code==401
    assert post(client,'reset-password',{'token':token,'password':'Another-password-2026!'}).status_code==400
    assert post(client,'login',{'email':'planner@example.com','password':'Long-password-2026!'}).status_code==401
    assert post(client,'login',{'email':'planner@example.com','password':'New-password-2026!'}).status_code==200


def test_unverified_login_duplicate_registration_and_unknown_reset_are_generic(client,account_settings):
    data={'name':'Afina','email':'planner@example.com','password':'Long-password-2026!'}
    first=post(client,'register',data)
    assert post(client,'register',data).json()==first.json()
    assert post(client,'login',data).status_code==401
    assert post(client,'forgot-password',{'email':'unknown@example.com'}).json()==post(client,'forgot-password',{'email':'planner@example.com'}).json()


def test_expired_verification_and_session_are_rejected(client,account_settings):
    from datetime import datetime,timezone,timedelta
    post(client,'register',{'name':'Afina','email':'planner@example.com','password':'Long-password-2026!'})
    token=mail_token(account_settings,'verify-email')
    engine=create_engine(account_settings.database_url)
    with engine.begin() as conn:
        conn.execute(text('UPDATE account_tokens SET expires_at=:past'),{'past':datetime.now(timezone.utc)-timedelta(days=1)})
    assert post(client,'verify-email',{'token':token}).status_code==400
    assert post(client,'resend-verification',{'email':'planner@example.com'}).status_code==202
    token=mail_token(account_settings,'verify-email')
    assert post(client,'verify-email',{'token':token}).status_code==200
    assert post(client,'verify-email',{'token':token}).status_code==400
    post(client,'login',{'email':'planner@example.com','password':'Long-password-2026!'})
    with engine.begin() as conn:
        conn.execute(text('UPDATE sessions SET expires_at=:past'),{'past':datetime.now(timezone.utc)-timedelta(days=1)})
    assert client.get('/api/v1/auth/me').status_code==401
    engine.dispose()


def test_rate_limit_and_stored_secrets(client,account_settings):
    from castravolt.auth import digest
    register_verified(client,account_settings)
    response=post(client,'login',{'email':'planner@example.com','password':'Long-password-2026!'})
    raw_session=client.cookies.get('castravolt_session')
    engine=create_engine(account_settings.database_url)
    with engine.connect() as conn:
        stored=conn.execute(text('SELECT token_hash,csrf_hash FROM sessions')).one()
        assert stored.token_hash==digest(raw_session) and stored.token_hash!=raw_session
        assert stored.csrf_hash==digest(response.json()['csrf_token'])
        assert conn.execute(text('SELECT password_hash FROM users')).scalar().startswith('$argon2id$')
    engine.dispose()
    low=account_settings.model_copy(update={'auth_rate_limit':1})
    with TestClient(create_app(low)) as limited:
        first=post(limited,'forgot-password',{'email':'absent@example.com'})
        assert first.status_code==202
        assert post(limited,'forgot-password',{'email':'absent@example.com'}).status_code==429


def test_concurrent_token_consumption_allows_one_success(client,account_settings):
    from concurrent.futures import ThreadPoolExecutor
    post(client,'register',{'name':'Afina','email':'planner@example.com','password':'Long-password-2026!'})
    token=mail_token(account_settings,'verify-email')
    def consume(_):
        with TestClient(create_app(account_settings)) as browser:
            return post(browser,'verify-email',{'token':token}).status_code
    with ThreadPoolExecutor(max_workers=2) as workers:
        assert sorted(workers.map(consume,[1,2]))==[200,400]
