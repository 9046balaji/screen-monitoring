import json
from datetime import datetime

def generate_suggestions(target_date, db_connection):
    c = db_connection.cursor()
    c.execute('SELECT * FROM adherence_reports WHERE date = ?', (target_date,))
    rep = c.fetchone()
    
    c.execute('SELECT * FROM daily_tasks WHERE date = ?', (target_date,))
    tasks = [dict(row) for row in c.fetchall()]
    
    suggestions = []
    
    # Rule 1: task completion low
    if rep:
        rep_dict = dict(rep)
        if rep_dict['scheduled_tasks'] > 0:
            ratio = rep_dict['completed_tasks'] / rep_dict['scheduled_tasks']
            if ratio < 0.5:
                suggestions.append({
                    "severity": "high",
                    "action": "Consider moving evening tasks to morning, as your completion rate was below 50% today."
                })
    
    # Rule 2: actual time >> planned time
    overrun_tasks = [t for t in tasks if t['duration_actual_minutes'] and t['duration_planned_minutes'] and t['duration_actual_minutes'] > t['duration_planned_minutes'] * 1.5]
    if overrun_tasks:
        suggestions.append({
            "severity": "medium",
            "action": f"Task '{overrun_tasks[0]['title']}' took significantly longer than planned. Recommend adding buffer time or splitting it into sub-tasks."
        })
        
    # Default suggestion if none triggered but adhrerence exists
    if len(suggestions) == 0 and rep:
        suggestions.append({
            "severity": "low",
            "action": "Great job sticking to your planned tasks! Keep maintaining realistic goals."
        })
        
    return suggestions
