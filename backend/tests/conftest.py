import os, tempfile
from pathlib import Path

TEST_DB=Path(tempfile.gettempdir())/'otp_enterprise_rc_tests.db'
if TEST_DB.exists(): TEST_DB.unlink()
os.environ['DATABASE_URL']=f'sqlite:///{TEST_DB}'
os.environ['DEMO_MODE']='true'
os.environ['ENVIRONMENT']='test'
os.environ['JWT_SECRET']='test-secret-with-sufficient-entropy-123456'
os.environ['N8N_INTEGRATION_KEY']='test-integration-key'

import pytest
from fastapi.testclient import TestClient
from app.db import Base, engine
from app.main import app

@pytest.fixture(scope='session',autouse=True)
def schema():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)
    if TEST_DB.exists(): TEST_DB.unlink()

@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture()
def analyst_token(client):
    r=client.post('/api/v1/auth/login',data={'username':'analyst@otp.local','password':'Demo-Analyst-2026!'})
    assert r.status_code==200
    return r.json()['access_token']

@pytest.fixture()
def manager_token(client):
    r=client.post('/api/v1/auth/login',data={'username':'manager@otp.local','password':'Demo-Manager-2026!'})
    assert r.status_code==200
    return r.json()['access_token']

@pytest.fixture()
def finance_token(client):
    r=client.post('/api/v1/auth/login',data={'username':'finance@otp.local','password':'Demo-Finance-2026!'})
    assert r.status_code==200
    return r.json()['access_token']

@pytest.fixture()
def director_token(client):
    r=client.post('/api/v1/auth/login',data={'username':'tax.director@otp.local','password':'Demo-Director-2026!'})
    assert r.status_code==200
    return r.json()['access_token']

@pytest.fixture()
def local_finance_token(client):
    r=client.post('/api/v1/auth/login',data={'username':'local.finance@otp.local','password':'Demo-LocalFinance-2026!'})
    assert r.status_code==200
    return r.json()['access_token']

@pytest.fixture()
def admin_token(client):
    r=client.post('/api/v1/auth/login',data={'username':'demo.admin@otp.local','password':'Demo-OTP-2026!'})
    assert r.status_code==200
    return r.json()['access_token']

@pytest.fixture()
def data_steward_token(client):
    r=client.post('/api/v1/auth/login',data={'username':'data.steward@otp.local','password':'Demo-DataSteward-2026!'})
    assert r.status_code==200
    return r.json()['access_token']
