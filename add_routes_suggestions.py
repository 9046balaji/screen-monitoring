import re

routes = '''
from planner_suggestions import generate_suggestions

@app.route('/api/planner/suggestions', methods=['GET'])
def get_planner_suggestions():
    try:
        target_date = request.args.get('date')
        if not target_date:
            return jsonify(error="date param required"), 400
            
        conn = get_db_connection()
        suggestions = generate_suggestions(target_date, conn)
        conn.close()
        
        return jsonify(suggestions)
    except Exception as e:
        return jsonify(error=str(e)), 500
'''

with open('app.py', 'a', encoding='utf-8') as f:
    f.write(routes)
print('Done Suggestions API!')