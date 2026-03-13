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

def therapy_agent_step(session_id: str, user_message: str, chat_history: list = None) -> dict:
    """
    Process a message in the therapy session, generating a robust LLM prompt
    using DuckDuckGo web search context and the user's conversational history.
    """
    # 1. Fetch relevant CBT or psychological coping mechanism from the web
    search_query = f"CBT cognitive behavioral therapy technique for: {user_message}"
    try:
        from ddgs import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(search_query, max_results=2))
            if results:
                search_context = "\n".join([f"- {r['title']}: {r['body']}" for r in results])
            else:
                search_context = "No specific findings."
    except Exception as e:
        search_context = f"Could not perform search: {e}"

    # 2. Reconstruct chat history for context
    history_len = len(chat_history) if chat_history else 0
    formatted_history = ""
    if chat_history:
        for msg in chat_history[-4:]:  # Keep last 4 messages to avoid token bloat
            role = "Therapist" if msg["role"] == "assistant" else "Patient"
            formatted_history += f"{role}: {msg['content']}\n"

    # 3. Construct the robust LLM Prompt
    llm_system_prompt = f"""
You are an empathetic, professional Cognitive Behavioral Therapist AI.
The user is struggling with digital addiction and excessive screen time.

Recent Conversation History:
{formatted_history}

Current Patient Message: "{user_message}"

Relevant Real-time Web Context (Therapy Techniques):
{search_context}

Instructions:
1. Validate the patient's feelings based on their message.
2. Incorporate a specific element from the Web Context as a practical coping mechanism.
3. Suggest a brief physical or mental break.
"""

    # In a production environment, you would invoke your LLM here:
    # response = openai.ChatCompletion.create(
    #     model="gpt-4",
    #     messages=[{"role": "system", "content": llm_system_prompt}]
    # )
    # agent_reply = response.choices[0].message.content

    # For the Hackathon / Demo, we generate an intelligent simulated answer based on the context:
    extracted_insight = results[0]['body'][:150] + "..." if 'results' in locals() and results else "mindfulness strategies."
    
    reply_text = (
        f"I can understand why you're feeling that way right now. "
        f"Interestingly, recent approaches suggest: \"{extracted_insight}\" "
        f"Let's apply that right now. How about we take a short break to reset your focus?"
    )

    return {
        "reply": reply_text,
        "ask_next": None,
        "suggested_commitment": {
            "title": "Guided Reset",
            "duration_minutes": 15,
            "instructions": "Put the device down, stand up, and practice the technique we just discussed."
        }
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
            # Note: Coach page uses 'text' while therapy uses 'content'
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

    # For the Hackathon / Demo, we generate an intelligent simulated answer based on the context:
    if results:
        extracted_insight = results[0]['body'][:150] + "..."
    else:
        extracted_insight = "mindfulness and building slow momentum."
        
    reply_text = (
        f"Right now I see you've used {screen_time_mins} mins of screen time this hour. "
        f"Based on what you just said, here's an idea: \"{extracted_insight}\" "
        f"Let's break the cycle and take a 5 minute reset loop right away. You've got this!"
    )
    return reply_text
