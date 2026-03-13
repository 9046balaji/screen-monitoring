import json

# Mock AI Service wrapper for deterministic outputs

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

def predict_relapse(features: dict) -> dict:
    """
    Returns a mock risk prediction of doomscrolling/relapse.
    """
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
