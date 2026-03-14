import re

routes = '''
@app.route('/api/dailytasks/<task_id>', methods=['PATCH'])
def patch_daily_task(task_id):
    try:
        data = request.json
        conn = get_db_connection()
        c = conn.cursor()
        
        fields = []
        values = []
        for k in ['status', 'actual_start', 'actual_end', 'duration_actual_minutes', 'planned_start', 'planned_end']:
            if k in data:
                fields.append(f"{k} = ?")
                values.append(data[k])
                
        if fields:
            values.append(task_id)
            c.execute(f"UPDATE daily_tasks SET {', '.join(fields)} WHERE id = ?", tuple(values))
            conn.commit()
            
        conn.close()
        return jsonify(status="updated")
    except Exception as e:
        return jsonify(error=str(e)), 500
'''

with open('app.py', 'a', encoding='utf-8') as f:
    f.write(routes)
print('Done PATCH!')
