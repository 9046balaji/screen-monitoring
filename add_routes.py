import re
import sys

routes = '''
import uuid
from datetime import datetime, timedelta

@app.route('/api/timetable', methods=['GET'])
def list_timetables():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM weekly_timetable WHERE user_id = ?', ('local',))
        tables = [dict(row) for row in c.fetchall()]
        
        for t in tables:
            c.execute('SELECT * FROM weekly_timetable_slots WHERE timetable_id = ? ORDER BY day_of_week, start_time', (t['id'],))
            t['slots'] = [dict(row) for row in c.fetchall()]
            
        conn.close()
        return jsonify(tables)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/timetable', methods=['POST'])
def create_timetable():
    try:
        data = request.json
        t_id = uuid.uuid4().hex[:8]
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO weekly_timetable (id, name, timezone) VALUES (?, ?, ?)',
            (t_id, data.get('name', 'My Timetable'), data.get('timezone', 'UTC')))
        conn.commit()
        conn.close()
        return jsonify(id=t_id, status="created")
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/timetable/<t_id>', methods=['PUT', 'DELETE'])
def modify_timetable(t_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        if request.method == 'DELETE':
            c.execute('DELETE FROM weekly_timetable_slots WHERE timetable_id = ?', (t_id,))
            c.execute('DELETE FROM weekly_timetable WHERE id = ?', (t_id,))
            conn.commit()
            conn.close()
            return jsonify(status="deleted")
        else:
            data = request.json
            c.execute('UPDATE weekly_timetable SET name = ?, timezone = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (data.get('name'), data.get('timezone'), t_id))
            conn.commit()
            conn.close()
            return jsonify(status="updated")
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/timetable/<t_id>/slot', methods=['POST'])
def create_slot(t_id):
    try:
        data = request.json
        s_id = uuid.uuid4().hex[:8]
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(\'''
            INSERT INTO weekly_timetable_slots 
            (id, timetable_id, day_of_week, start_time, end_time, title, description, category, focus_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        \''', (
            s_id, t_id, data.get('day_of_week'), data.get('start_time'), data.get('end_time'),
            data.get('title'), data.get('description', ''), data.get('category'), bool(data.get('focus_mode', False))
        ))
        conn.commit()
        conn.close()
        return jsonify(id=s_id, status="created")
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/timetable/slot/<s_id>', methods=['PUT', 'DELETE'])
def modify_slot(s_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        if request.method == 'DELETE':
            c.execute('DELETE FROM weekly_timetable_slots WHERE id = ?', (s_id,))
            conn.commit()
            conn.close()
            return jsonify(status="deleted")
        else:
            data = request.json
            c.execute(\'''
                UPDATE weekly_timetable_slots SET 
                day_of_week = ?, start_time = ?, end_time = ?, title = ?, 
                description = ?, category = ?, focus_mode = ? 
                WHERE id = ?
            \''', (
                data.get('day_of_week'), data.get('start_time'), data.get('end_time'),
                data.get('title'), data.get('description', ''), data.get('category'), 
                bool(data.get('focus_mode', False)), s_id
            ))
            conn.commit()
            conn.close()
            return jsonify(status="updated")
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/timetable/<t_id>/generate-daily', methods=['POST'])
def generate_daily_tasks(t_id):
    try:
        target_date = request.args.get('date') # YYYY-MM-DD
        if not target_date:
            return jsonify(error="date query param is required"), 400
            
        dt = datetime.strptime(target_date, '%Y-%m-%d')
        # python weekday: 0=Mon, 6=Sun
        day_of_week = dt.weekday()
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM weekly_timetable_slots WHERE timetable_id = ? AND day_of_week = ?', (t_id, day_of_week))
        slots = [dict(row) for row in c.fetchall()]
        
        generated = []
        for s in slots:
            # Check if this slot was already generated for this date
            c.execute('SELECT 1 FROM daily_tasks WHERE date = ? AND slot_id = ?', (target_date, s['id']))
            if c.fetchone():
                continue
            
            task_id = uuid.uuid4().hex[:8]
            planned_start = f"{target_date}T{s['start_time']}:00"
            planned_end = f"{target_date}T{s['end_time']}:00"
            
            # calculate planned duration
            start_dt = datetime.strptime(planned_start, '%Y-%m-%dT%H:%M:%S')
            end_dt = datetime.strptime(planned_end, '%Y-%m-%dT%H:%M:%S')
            dur = int((end_dt - start_dt).total_seconds() / 60)
            
            meta = '{"auto_focus": true}' if s['focus_mode'] else '{}'
            
            c.execute(\'''
                INSERT INTO daily_tasks 
                (id, date, slot_id, planned_start, planned_end, title, description, category, duration_planned_minutes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            \''', (
                task_id, target_date, s['id'], planned_start, planned_end, 
                s['title'], s['description'], s['category'], dur, meta
            ))
            generated.append({
                "id": task_id, "date": target_date, "title": s['title'], "planned_start": planned_start, "planned_end": planned_end
            })
            
        conn.commit()
        conn.close()
        return jsonify(generated)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/dailytasks', methods=['GET'])
def list_daily_tasks():
    try:
        target_date = request.args.get('date')
        if not target_date:
            return jsonify(error="date query param is required"), 400
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM daily_tasks WHERE date = ? ORDER BY planned_start', (target_date,))
        tasks = [dict(row) for row in c.fetchall()]
        for t in tasks:
            if t.get('metadata'):
                import json
                try: t['metadata'] = json.loads(t['metadata'])
                except: pass
        conn.close()
        return jsonify(tasks)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/dailytasks/<task_id>/start', methods=['POST'])
def start_daily_task(task_id):
    try:
        now_ts = datetime.utcnow().isoformat()
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('UPDATE daily_tasks SET status = "running", actual_start = ? WHERE id = ?', (now_ts, task_id))
        
        # Check if we need to auto start focus mode
        c.execute('SELECT metadata, duration_planned_minutes, title FROM daily_tasks WHERE id = ?', (task_id,))
        task = dict(c.fetchone())
        metadata = task.get('metadata', "{}")
        import json
        try: meta_dict = json.loads(metadata)
        except: meta_dict = {}
        
        if meta_dict.get('auto_focus'):
            c.execute('INSERT INTO focus_sessions (id, commitment_id, start_ts, duration_minutes, status) VALUES (?, ?, ?, ?, ?)',
              (uuid.uuid4().hex[:8], 'task_'+task_id, now_ts, task.get('duration_planned_minutes', 30), 'scheduled'))
              
        conn.commit()
        conn.close()
        return jsonify(id=task_id, status="running", actual_start=now_ts)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/dailytasks/<task_id>/complete', methods=['POST'])
def complete_daily_task(task_id):
    try:
        now_dt = datetime.utcnow()
        now_ts = now_dt.isoformat()
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('SELECT actual_start FROM daily_tasks WHERE id = ?', (task_id,))
        row = c.fetchone()
        actual_start_ts = row['actual_start'] if row and row['actual_start'] else now_ts
        start_dt = datetime.fromisoformat(actual_start_ts)
        dur = int((now_dt - start_dt).total_seconds() / 60)
        
        c.execute('UPDATE daily_tasks SET status = "completed", actual_end = ?, duration_actual_minutes = ? WHERE id = ?', 
                  (now_ts, dur, task_id))
        conn.commit()
        conn.close()
        return jsonify(id=task_id, status="completed", actual_end=now_ts, duration_actual_minutes=dur)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/dailytasks/<task_id>/skip', methods=['POST'])
def skip_daily_task(task_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('UPDATE daily_tasks SET status = "skipped" WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()
        return jsonify(id=task_id, status="skipped")
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/planner/adherence', methods=['POST', 'GET'])
def planner_adherence():
    try:
        target_date = request.args.get('date')
        if not target_date:
            return jsonify(error="date param required"), 400
            
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('SELECT * FROM daily_tasks WHERE date = ?', (target_date,))
        tasks = [dict(row) for row in c.fetchall()]
        
        planned_tot = sum([t['duration_planned_minutes'] or 0 for t in tasks])
        actual_tot = sum([t['duration_actual_minutes'] or 0 for t in tasks])
        sched_count = len(tasks)
        comp_count = len([t for t in tasks if t['status'] == 'completed'])
        
        score = 0
        if sched_count > 0:
            tc_ratio = comp_count / sched_count
            ta_ratio = min(actual_tot / max(planned_tot, 1), 1)
            score = 100 * (0.6 * tc_ratio + 0.4 * ta_ratio)
            
        rep_id = uuid.uuid4().hex[:8]
        c.execute(\'''
            INSERT INTO adherence_reports 
            (id, date, planned_total_minutes, actual_total_minutes, completed_tasks, scheduled_tasks, adherence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        \''', (rep_id, target_date, planned_tot, actual_tot, comp_count, sched_count, score))
        
        conn.commit()
        conn.close()
        
        return jsonify(
            planned_total_minutes=planned_tot,
            actual_total_minutes=actual_tot,
            completed_tasks=comp_count,
            scheduled_tasks=sched_count,
            adherence_score=round(score, 1)
        )
    except Exception as e:
        return jsonify(error=str(e)), 500
'''

with open('app.py', 'a', encoding='utf-8') as f:
    f.write(routes)
print('Done!')
