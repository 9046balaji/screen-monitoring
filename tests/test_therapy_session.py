import pytest
from app import app
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_therapy_session(client):
    # Create session
    res1 = client.post('/api/therapy/session', json={"user_id": "test_user"})
    assert res1.status_code == 201
    data1 = json.loads(res1.data)
    session_id = data1.get('session_id')
    assert session_id is not None
    assert len(data1.get('messages')) > 0
    
    # Respond
    res2 = client.post(f'/api/therapy/session/{session_id}/respond', json={
        "message": "I feel like I'm scrolling too much."
    })
    
    assert res2.status_code == 200
    data2 = json.loads(res2.data)
    assert 'agent_reply' in data2
    assert len(data2.get('messages')) > 1
