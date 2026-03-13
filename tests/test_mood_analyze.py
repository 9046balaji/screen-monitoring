import pytest
from app import app
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_mood_analyze_and_save(client):
    response = client.post('/api/mood/analyze-and-save', json={
        "entry": "I feel incredibly terrible because I wasted 5 hours on tiktok.",
        "mood_score": 1,
        "user_id": "test_user"
    })
    
    assert response.status_code == 201
    data = json.loads(response.data)
    assert 'ai_primary_emotion' in data
    assert 'ai_distortion' in data
    assert 'ai_reframe' in data
    assert 'ai_microtask' in data
    assert data['ai_primary_emotion'] == "Anxious"  # Based on mock in ai_service.py
