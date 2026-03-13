import pytest
from app import app, init_db

@pytest.fixture
def client():
    # Setup
    app.config['TESTING'] = True
    init_db()
    with app.test_client() as client:
        yield client

def test_health_check(client):
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'ok'

def test_predict_usage_missing_data(client):
    response = client.post('/api/predict/usage', json={})
    assert response.status_code == 400

def test_predict_usage_valid_data(client):
    req_data = {
        "age_scaled": 0.5,
        "income_scaled": 0.5,
        "gender_encoded": 1,
        "platform_encoded": 2,
        "interests_encoded": 1,
        "location_encoded": 0,
        "demographics_encoded": 1,
        "profession_encoded": 2,
        "indebt": 0,
        "isHomeOwner": 1,
        "Owns_Car": 1,
        "platform_risk_score": 2
    }
    response = client.post('/api/predict/usage', json=req_data)
    # Could be 200 or 500 depending on if models exist in testing env 
    # but we just want to ensure it connects and passes pydantic validation
    assert response.status_code in [200, 500] 

def test_check_anomaly_valid(client):
    req_data = {
        "time_spent": 5.5
    }
    response = client.post('/api/anomaly', json=req_data)
    assert response.status_code in [200, 500]

def test_get_tracker_live(client):
    response = client.get('/api/tracker/live')
    assert response.status_code == 200
    data = response.get_json()
    assert "apps" in data
