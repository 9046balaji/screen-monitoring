import sys

code = \"\"\"
# ═══════════════════════════════════
# NEW: /api/addiction-heatmap
# ═══════════════════════════════════
@app.route('/api/addiction-heatmap', methods=['GET'])
def addiction_heatmap():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT date, hour_str, seconds 
            FROM hourly_logs
        ''')
        rows = c.fetchall()
        conn.close()

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        counts = {d: {h: 0 for h in range(24)} for d in days}
        
        has_data = False
        from datetime import datetime
        for r in rows:
            ds = r['date']
            hr_str = r['hour_str']
            secs = r['seconds']
            try:
                dt = datetime.strptime(ds, "%Y-%m-%d")
                day_idx = dt.weekday()
                d_name = days[day_idx]
                hr = int(hr_str.split(':')[0]) if ':' in hr_str else int(hr_str)
                counts[d_name][hr] += secs
                has_data = True
            except Exception:
                pass

        heatmap_data = []
        for d in days:
            for h in range(24):
                val = counts[d][h] // 60 # minutes
                
                # Risk assignment
                if val == 0:
                    risk = "None"
                elif val < 15:
                    risk = "Low"
                elif val < 30:
                    risk = "Medium"
                elif val < 60:
                    risk = "High"
                else:
                    risk = "Very High"
                    
                heatmap_data.append({
                    "day": d,
                    "hour": h,
                    "value": val,
                    "riskLevel": risk
                })
        
        return jsonify(heatmap_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

\"\"\"

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = "# ═══════════════════════════════════\n# FIX 14: Health check endpoint"
text = text.replace(target, code + target)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)

