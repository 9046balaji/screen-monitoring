import json
import os
import pickle
import requests
from cachetools import cached, TTLCache

# In-memory LRU cache for predictions (max 100 items, ttl 30s)
prediction_cache = TTLCache(maxsize=100, ttl=30)

# Production model loading at startup
import __main__
if not hasattr(__main__, 'MockModel'):
    class MockModel:
        def __init__(self):
            self.type = "random_forest_mock"
            self.feature_importances = {"Late night (pm)": 0.4, "Recent negative mood": 0.35, "Long unused focus mode": 0.25}
        def predict(self, features):
            return 0.85
    __main__.MockModel = MockModel

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
    Returns AI analysis for a journal entry using Ollama.
    """
    import json
    import requests

    prompt = f"""
    You are a cognitive behavioral therapy assistant. Analyze the user's journal entry.
    Journal entry: "{text}"
    
    Return a pure JSON object in exactly this format with no other text (no markdown blocks like ```json):
    {{
        "primary_emotion": "Primary emotion felt (e.g., Anxious, Frustrated, Calm)",
        "cognitive_distortions": ["List of distortions if any, e.g., All-or-Nothing Thinking"],
        "reframe": "A compassionate sentence reframing their negative thoughts.",
        "micro_task": {{
            "type": "breathing|stretching|focus",
            "duration_minutes": 1,
            "instruction": "A simple 1-2 minute task to help them process."
        }}
    }}
    """
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": "gemma3:1b", "prompt": prompt, "stream": False},
            timeout=30
        )
        response.raise_for_status()
        text_resp = response.json().get("response", "{}")
        
        # Simple extraction of JSON if markdown is returned
        import re
        match = re.search(r'\{.*\}', text_resp, re.DOTALL)
        if match:
            text_resp = match.group(0)
            
        return json.loads(text_resp)
    except Exception as e:
        print("analyze_journal Ollama Error:", e)
        # Fallback response
        return {
            "primary_emotion": "Unknown",
            "cognitive_distortions": [],
            "reframe": "I notice you are reflecting on your day. Take a moment to breathe and reset.",
            "micro_task": {
                "type": "breathing",
                "duration_minutes": 1,
                "instruction": "Take 5 deep breaths to center yourself."
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

def coach_agent_step(user_message: str, chat_history: list = None, screen_time_mins: int = 0) -> str:
    """
    Process a message in the Life Coach session using web search context.
    """
    search_query = f"Life coaching advice for productivity and wellness: {user_message}"
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=2))
            if results:
                search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
            else:
                search_context = "Focus on small positive habits."
    except Exception as e:
        search_context = f"Could not perform search: {e}"
        
    history_len = len(chat_history) if chat_history else 0
    formatted_history = ""
    if chat_history:
        for msg in chat_history[-4:]:  # Keep last 4 messages
            role = "Coach" if msg["role"] == "assistant" else "User"
            # Coach history can come in either shape depending on sender.
            text = msg.get("text", msg.get("content", ""))
            formatted_history += f"{role}: {text}\n"

    # 3. Construct the robust LLM Prompt
    llm_system_prompt = f"""
You are an empowering, motivational Life Coach AI.
The user is working on managing their screen time and digital habits.
Their current screen time this hour is {screen_time_mins} minutes.

Recent Conversation History:
{formatted_history}

Current User Message: "{user_message}"

Relevant Real-time Web Advice:
{search_context}

Instructions:
1. Encourage the user.
2. Acknowledge their screen time context.
3. Suggest a tip based on the Web Advice.
"""

    prompt_payload = {
        "model": "gemma3:1b",
        "prompt": llm_system_prompt,
        "stream": False
    }

    try:
        response = requests.post("http://localhost:11434/api/generate", json=prompt_payload, timeout=30)
        response.raise_for_status()
        reply_text = response.json().get("response", "I could not generate a response at this time.")
    except Exception as e:
        print("Ollama Error in coach_agent_step:", e)
        # Fallback response
        if results:
            extracted_insight = results[0]['body'][:150] + "..."
        else:
            extracted_insight = "mindfulness and building slow momentum."
            
        reply_text = (
            f"Right now I see you've used {screen_time_mins} mins of screen time this hour. "
            f"Based on what you just said, here's an idea: \"{extracted_insight}\" "
            f"Let's break the cycle and take a 5 minute reset loop right away. You've got this! (Failed to reach Ollama AI)"
        )

    return reply_text


def suggest_planner_changes(context):
    try:
        import json
        import urllib.request
        
        prompt = f"""
        You are a schedule optimization coach. Given the user's data:
        {json.dumps(context, indent=2)}
        
        Provide 3 prioritized suggestions to improve adherence. Return purely in JSON format:
        [
          {{"severity": "high" | "medium" | "low", "action": "description of suggestion"}}
        ]
        """
        
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=json.dumps({"model": "gemma3:1b", "prompt": prompt, "stream": False}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode())
            text = result.get("response", "[]")
            
            # Simple heuristic to extract JSON array if there's markdown formatting
            import re
            match = re.search(r'\[.*\]', text, re.DOTALL)
            if match:
                text = match.group(0)
            
            return json.loads(text)
    except Exception as e:
        print("LLM Suggestion Error (Ollama):", e)
        return []
