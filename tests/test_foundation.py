from fastapi.testclient import TestClient

from castravolt.config import Settings
from castravolt.main import create_app


def test_liveness_and_request_id_without_database():
    with TestClient(create_app(Settings(database_url=None))) as client:
        response = client.get('/health/live')
        assert response.status_code == 200
        assert response.json()['status'] == 'alive'
        assert response.headers['x-request-id']


def test_readiness_fails_honestly_without_database():
    with TestClient(create_app(Settings(database_url=None))) as client:
        response = client.get('/health/ready')
        assert response.status_code == 503
        assert response.json()['database'] == 'not_configured'
        assert response.json()['scope'] == 'foundation'


def test_error_contract_hides_missing_routes_and_preserves_request_id():
    with TestClient(create_app(Settings(database_url=None))) as client:
        response = client.get('/api/v1/missing')
        assert response.status_code == 404
        assert response.json()['error']['code'] == 'http_404'
        assert response.json()['error']['request_id'] == response.headers['x-request-id']


def test_database_failure_has_no_credentials_in_response():
    config = Settings(database_url='postgresql+psycopg://secret:password@127.0.0.1:1/not_real')
    with TestClient(create_app(config)) as client:
        response = client.get('/health/ready')
        assert response.status_code == 503
        assert response.json()['database'] == 'unavailable'
        assert 'password' not in response.text


def test_reference_contract_and_exact_cors():
    app = create_app(Settings(database_url=None, cors_origins=['http://localhost:5173']))
    with TestClient(app) as client:
        info = client.get('/api/v1/system').json()
        assert info['stage'] == 'foundation'
        assert info['capabilities']['predictions'] is False
        allowed = client.options('/api/v1/system', headers={
            'Origin': 'http://localhost:5173', 'Access-Control-Request-Method': 'GET'})
        assert allowed.headers['access-control-allow-origin'] == 'http://localhost:5173'
        denied = client.options('/api/v1/system', headers={
            'Origin': 'https://unknown.example', 'Access-Control-Request-Method': 'GET'})
        assert 'access-control-allow-origin' not in denied.headers
