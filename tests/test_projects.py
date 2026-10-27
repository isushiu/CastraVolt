from uuid import uuid4

from fastapi.testclient import TestClient

from test_accounts import account_settings, client, post, register_verified
from castravolt.main import create_app


def write(client, method, path, data=None):
    csrf = client.get('/api/v1/auth/csrf').json()['csrf_token']
    return client.request(method, '/api/v1' + path, json=data,
                          headers={'Origin': 'http://localhost:5173', 'X-CSRF-Token': csrf})


def login(client, settings):
    register_verified(client, settings)
    assert post(client, 'login', {'email': 'planner@example.com', 'password': 'Long-password-2026!'}).status_code == 200


def test_internal_login_and_registration_disabled(client, account_settings):
    internal = account_settings.model_copy(update={'internal_access': True})
    with TestClient(create_app(internal)) as browser:
        assert post(browser, 'login', {'id': 'admin', 'password': 'wrong'}).status_code == 401
        assert post(browser, 'login', {'id': 'admin', 'password': '\u00e9'}).status_code == 401
        response = post(browser, 'login', {'id': 'admin', 'password': '123'})
        assert response.status_code == 200
        user_id = response.json()['user']['id']
        assert post(browser, 'register', {'name': 'Someone', 'email': 'new@example.com', 'password': 'Long-password-2026!'}).status_code == 404
        assert post(browser, 'forgot-password', {'email': 'admin@castravolt.local'}).status_code == 404
        post(browser, 'logout')
        assert post(browser, 'login', {'id': 'admin', 'password': '123'}).json()['user']['id'] == user_id


def test_project_site_crud_persists_and_cascades(client, account_settings):
    login(client, account_settings)
    project = write(client, 'POST', '/projects', {'name': 'KL pilot', 'description': 'New sites'} )
    assert project.status_code == 201
    pid = project.json()['id']
    assert client.get('/api/v1/projects').json()[0]['id'] == pid
    assert write(client, 'PATCH', f'/projects/{pid}', {'name': 'City pilot'}).json()['name'] == 'City pilot'
    site = write(client, 'POST', f'/projects/{pid}/sites', {'name': 'Office entrance', 'latitude': 3.14, 'longitude': 101.69, 'category': 'Office'})
    assert site.status_code == 201
    sid = site.json()['id']
    assert site.json()['state'] == 'W.P. KUALA LUMPUR'
    assert client.get(f'/api/v1/sites/{sid}/predictions').json() == []
    assert write(client, 'PATCH', f'/sites/{sid}', {'name': 'North entrance'}).json()['name'] == 'North entrance'
    assert client.get(f'/api/v1/projects/{pid}/sites').json()[0]['name'] == 'North entrance'
    with TestClient(create_app(account_settings)) as reopened:
        reopened.cookies.update(client.cookies)
        assert reopened.get(f'/api/v1/sites/{sid}').json()['name'] == 'North entrance'
    assert write(client, 'DELETE', f'/projects/{pid}').status_code == 204
    assert client.get(f'/api/v1/sites/{sid}').status_code == 404


def test_ownership_and_unauthenticated_access(client, account_settings):
    assert client.get('/api/v1/projects').status_code == 401
    login(client, account_settings)
    pid = write(client, 'POST', '/projects', {'name': 'Private project'}).json()['id']
    sid = write(client, 'POST', f'/projects/{pid}/sites', {'name': 'Private site', 'latitude': 3.0738, 'longitude': 101.5183, 'category': 'Unknown'}).json()['id']
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from castravolt.account_models import User
    from castravolt.auth import hasher, now
    from castravolt.project_models import Prediction
    engine = create_engine(account_settings.database_url)
    with Session(engine) as db:
        db.add(User(name='Other', email='other@example.com', password_hash=hasher.hash('Long-password-2026!'), verified_at=now(), created_at=now()))
        owner_id=client.get('/api/v1/auth/me').json()['id']
        from uuid import UUID
        record=Prediction(site_id=UUID(sid),requester_id=UUID(owner_id),input_snapshot={'latitude':3,'longitude':101,'category':'Unknown'},
                          raw_estimate=3.5,displayed_total=4,model_version='test-fixture',extraction_rule_version='fixture',
                          poi_timestamp=now(),adoption_reference_year=2025,adoption_value=560,rounding_policy='half-up',created_at=now())
        db.add(record)
        db.commit()
        prediction_id=str(record.id)
    engine.dispose()
    assert write(client,'PATCH',f'/sites/{sid}',{'latitude':3.1579,'longitude':101.7116}).status_code==200
    saved=client.get(f'/api/v1/predictions/{prediction_id}').json()
    assert saved['input_snapshot']['latitude']==3
    assert len(client.get(f'/api/v1/sites/{sid}/predictions').json())==1
    assert write(client,'PATCH',f'/predictions/{prediction_id}',{'displayed_total':99}).status_code==405
    with TestClient(create_app(account_settings)) as other:
        assert post(other, 'login', {'email': 'other@example.com', 'password': 'Long-password-2026!'}).status_code == 200
        assert other.get('/api/v1/projects').json() == []
        for path in [f'/projects/{pid}', f'/projects/{pid}/sites', f'/sites/{sid}', f'/sites/{sid}/predictions', f'/predictions/{prediction_id}', f'/predictions/{uuid4()}']:
            assert other.get('/api/v1' + path).status_code == 404
        for path in [f'/projects/{pid}', f'/sites/{sid}']:
            assert write(other, 'PATCH', path, {'name': 'Stolen'}).status_code == 404
            assert write(other, 'DELETE', path).status_code == 404
        assert write(other, 'POST', f'/projects/{pid}/sites', {'name': 'Intrusion', 'latitude': 3.0738, 'longitude': 101.5183, 'category': 'Office'}).status_code == 404


def test_validation_and_csrf(client, account_settings):
    login(client, account_settings)
    assert write(client, 'POST', '/projects', {'name': '   '}).status_code == 422
    pid = write(client, 'POST', '/projects', {'name': 'Validation'}).json()['id']
    assert client.post('/api/v1/projects', json={'name': 'No CSRF'}).status_code == 403
    for fields in [{'latitude': 91}, {'longitude': -181}, {'category': 'Invented'}, {'state': 'SELANGOR'}]:
        data = {'name': 'Site', 'latitude': 3.0738, 'longitude': 101.5183, 'category': 'Office', **fields}
        assert write(client, 'POST', f'/projects/{pid}/sites', data).status_code == 422
    assert write(client, 'PATCH', f'/projects/{pid}', {'name': None}).status_code == 422
    sid = write(client, 'POST', f'/projects/{pid}/sites', {'name': 'Remove me', 'latitude': 3.0738, 'longitude': 101.5183, 'category': 'Office'}).json()['id']
    assert write(client, 'DELETE', f'/sites/{sid}').status_code == 204
    assert client.get(f'/api/v1/sites/{sid}').status_code == 404
