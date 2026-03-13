import pytest
import json
import uuid
import os
import sys

# Ensure app can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from database.database import init_db

@pytest.fixture
def client():
    # Setup test DB or just use existing with initialization
    init_db()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_start_commitment_success(client):
    payload = {
        "user_id": "local",
        "title": "Start Today's Commitment",
        "description": "One hour screen-free block",
        "expected_duration_minutes": 60,
        "auto_start_focus": True,
        "reminder_interval_minutes": 20
    }
    response = client.post('/api/commitments/start', json=payload)
    assert response.status_code == 201
    data = response.get_json()
    assert 'commitment_id' in data
    assert data['status'] == 'active'
    assert data['focus_session_created'] == True

def test_start_commitment_missing_title(client):
    payload = {
        "user_id": "local",
        "expected_duration_minutes": 60,
    }
    response = client.post('/api/commitments/start', json=payload)
    assert response.status_code == 400

def test_start_commitment_negative_duration(client):
    payload = {
        "title": "Bad duration",
        "expected_duration_minutes": -10,
    }
    response = client.post('/api/commitments/start', json=payload)
    assert response.status_code == 400

def test_patch_commitment_complete(client):
    # First create one
    payload = {"title": "To be completed"}
    res = client.post('/api/commitments/start', json=payload)
    c_id = res.get_json()['commitment_id']
    
    # Complete it
    res_complete = client.post(f'/api/commitments/{c_id}/complete')
    assert res_complete.status_code == 200
    assert res_complete.get_json()['status'] == 'completed'
