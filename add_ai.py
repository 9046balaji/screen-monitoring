import json

new_func = '''
def suggest_planner_changes(context):
    try:
        from openai import OpenAI
        import os
        import json
        client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
        
        prompt = f"""
        You are a schedule optimization coach. Given the user's data:
        {json.dumps(context, indent=2)}
        
        Provide 3 prioritized suggestions to improve adherence. Return purely in JSON format:
        [
          {{"severity": "high|medium|low", "action": "description of suggestion"}}
        ]
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print("LLM Suggestion Error:", e)
        return []
'''

with open('ai_service.py', 'a', encoding='utf-8') as f:
    f.write('\n' + new_func)
print('Done AI')
