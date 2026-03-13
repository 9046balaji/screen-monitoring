import json
import os
import pickle
from cachetools import cached, TTLCache

# In-memory LRU cache for predictions (max 100 items, ttl 30s)
prediction_cache = TTLCache(maxsize=100, ttl=30)

# Production model loading at startup
RELAPSE_MODEL = None
models_dir = os.path.join(os.path.dirname(__file__), 'models')
model_path = os.path.join(models_dir, 'relapse_model.pkl')

try:
    if os.path.exists(model_path):
        with open(model_path, 'rb') as f:
            RELAPSE_MODEL = pickle.load(f)
        print("Successfully loaded relapse_model.pkl at startup.")
except Exception as e:
    print(f"Warning: Could not load relapse_model.pkl: {e}")

def analyze_journal(text: str, context: dict = None) -> dict:
    """
    Returns mock analysis for a journal entry.
    """
    return {
        "primary_emotion": "Anxious",
        "cognitive_distortions": ["Catastrophizing", "All-or-Nothing Thinking"],
        "reframe": "I notice you are catastrophizing your screen time today. Missing one target doesn't ruin your entire progress. Let's try a small reset.",
        "micro_task": {
            "type": "breathing",
            "duration_minutes": 1,
            "instruction": "Take 5 deep breaths, focusing purely on inhaling for 4 seconds, holding for 4, and exhaling for 4."
        }
    }

@cached(prediction_cache)
def predict_relapse(features_json: str) -> dict:
    """
    Returns a mock risk prediction of doomscrolling/relapse.
    'features_json' is passed as string to make it hashable for the cache.
    """
    if RELAPSE_MODEL:
        # Features would be extracted here and passed to the model
        pass
        
    return {
        "risk": 0.85,  # High risk mock
        "top_features": ["Late night (pm)", "Recent negative mood", "Long unused focus mode"]
    }

def therapy_start() -> dict:
    """
    Initialize a therapy session.
    """
    return {
        "reply": "Hi! I see you're struggling with scrolling today. What exactly is keeping you stuck in the feed right now?"
    }

def therapy_agent_step(session_id: str, user_message: str) -> dict:
    """
    Process a message in the therapy session.
    """
    # Mocking a step that immediately suggests a commitment
    return {
        "reply": "It's normal to feel that way. I'd recommend a short break from the screen right now.",
        "ask_next": None,
        "suggested_commitment": {
            "title": "Short Detox",
            "duration_minutes": 15,
            "instructions": "Step away from the phone and stretch."
        }
    }
