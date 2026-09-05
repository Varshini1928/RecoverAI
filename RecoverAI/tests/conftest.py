import os,sys
os.environ["DATABASE_URL"]="sqlite:///./data/test_recoverai.db"
sys.path.insert(0,os.path.join(os.path.dirname(__file__),"..","backend"))
import pytest
from fastapi.testclient import TestClient
from app.database import Base,SessionLocal,engine
from app.main import app
from app.models import RecoveryCase
@pytest.fixture(autouse=True)
def clean():
    Base.metadata.drop_all(engine);Base.metadata.create_all(engine);yield
@pytest.fixture
def db():
    d=SessionLocal();yield d;d.close()
@pytest.fixture
def client(): return TestClient(app)
@pytest.fixture
def auth(client):
    r=client.post('/api/auth/login',json={'username':'admin@recoverai.demo','password':'RecoverAI@2026'});return {'Authorization':'Bearer '+r.json()['access_token']}
@pytest.fixture
def make_case(db):
    def f(**kw):
        base=dict(merchant_id='m1',payment_id='p1',customer_reference='c1',failure_reason='technical_error',amount=1000,previous_attempts=0,customer_history_score=.8,customer_opted_out=False,status='pending',idempotency_key='key-1');base.update(kw);c=RecoveryCase(**base);db.add(c);db.commit();db.refresh(c);return c
    return f

