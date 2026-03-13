import pytest
from app import app
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_relapse_risk_prediction(client):
    response = client.get('/api/predictions/relapse-risk?user_id=test_user')
    
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'risk' in data
    assert 'top_features' in data
    assert type(data['risk']) == float
    assert len(data['top_features']) > 0
    assert data['risk'] == 0.85 # per mock model output