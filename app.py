from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import json
import numpy as np
import pandas as pd
from datetime import datetime
import requests
from sklearn.ensemble import IsolationForest
import os
from pydantic import BaseModel, ValidationError
from typing import Optional

from database.database import init_db, get_db_connection

app = Flask(__name__)
# Allow local dev frontends (Vite/React) to access the API.
CORS(app, origins=["http://localhost:5173", "http://localhost:3000"])

# Ensure DB is initialized
init_db()

# ═══════════════════════════════════
# FIX 7: Move ML logic into an InferenceService class
# ═══════════════════════════════════
class InferenceService:
    def __init__(self):
        self.usage_clf = None
        self.mental_clf = None
        self.productivity_reg = None
        self.segmentation = None
        self.scaler = None
        self.encoders = None
        self.persona_map = {}
        self.model_report = {}
        self.anomaly_detector = None
        self.load_models()

    def load_models(self):
        try:
            self.usage_clf = joblib.load('models/usage_classifier.pkl')
            self.mental_clf = joblib.load('models/mental_health_classifier.pkl')
            self.productivity_reg = joblib.load('models/productivity_regressor.pkl')
            self.segmentation = joblib.load('models/user_segmentation.pkl')
            self.scaler = joblib.load('models/scaler.pkl')
            self.encoders = joblib.load('models/encoders.pkl')
            with open('models/persona_map.json') as f:
                self.persona_map = json.load(f)
            with open('models/model_report.json') as f:
                self.model_report = json.load(f)
                
            # Quick Anomaly Detection Setup
            df_anomaly = pd.read_csv('data/dummy_data.csv')
            if 'time_spent' in df_anomaly.columns:
                self.anomaly_detector = IsolationForest(contamination=0.05, random_state=42)
                self.anomaly_detector.fit(df_anomaly[['time_spent']])
                
            print("All models loaded successfully (including Anomaly Detector)")
        except Exception as e:
            print(f"Model loading error: {e}")

inference_service = InferenceService()

# ═══════════════════════════════════
# Pydantic Schemas
# ═══════════════════════════════════
class UsagePredictSchema(BaseModel):
    age_scaled: float = 0
    income_scaled: float = 0
    gender_encoded: int = 0
    platform_encoded: int = 0
    interests_encoded: int = 0
    location_encoded: int = 0
    demographics_encoded: int = 0
    profession_encoded: int = 0
    indebt: int = 0
    isHomeOwner: int = 0
    Owns_Car: int = 0
    platform_risk_score: int = 1

class MentalHealthPredictSchema(BaseModel):
    distraction_score: int = 3
    concentration_score: int = 3
    depression_score: int = 3
    interest_fluctuation: int = 3
    sleep_issues_score: int = 3
    purposeless_usage: int = 3
    distracted_when_busy: int = 3
    restlessness_score: int = 3
    worries_score: int = 3
    comparison_score: int = 3
    comparison_feeling: int = 3
    validation_seeking: int = 3
    avg_daily_usage: float = 2.5
    age: int = 21

class UserSegmentSchema(BaseModel):
    time_spent: float = 4
    age: float = 25
    income: float = 30000
    platform_risk_score: float = 2

class ProductivityPredictSchema(BaseModel):
    hours_studied: int = 15
    attendance: int = 80
    sleep_hours: int = 7
    previous_scores: int = 70
    tutoring_sessions: int = 1
    physical_activity: int = 3
    parental_involvement_encoded: int = 1
    access_to_resources_encoded: int = 1
    extracurricular_encoded: int = 0
    motivation_encoded: int = 1
    internet_access_encoded: int = 1
    family_income_encoded: int = 1
    teacher_quality_encoded: int = 1
    school_type_encoded: int = 0
    peer_influence_encoded: int = 1
    learning_disabilities_encoded: int = 0
    parental_education_encoded: int = 1
    distance_encoded: int = 1
    gender_encoded: int = 0

class RecommendationSchema(BaseModel):
    persona: str = 'Balanced Professional'

class AnomalySchema(BaseModel):
    time_spent: float = 0


# ═══════════════════════════════════
# Feature 5: Productivity AI (Focus Productivity Score)
# ═══════════════════════════════════
@app.route('/api/productivity-score', methods=['GET'])
def get_productivity_score():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 1. Ratio of deep work vs distracted apps
    # Categories that imply deep work: 'Productivity', 'Education', 'Utility', 'Development'
    # Categories that imply distraction: 'Social', 'Entertainment', 'Games', 'Social Media'
    c.execute("SELECT category, SUM(seconds) as total_sec FROM usage_logs GROUP BY category")
    rows = c.fetchall()
    
    deep_work_sec = 0
    distracted_sec = 0
    
    deep_work_categories = ['Productivity', 'Education', 'Utility', 'Development', 'Work']
    distracted_categories = ['Social', 'Entertainment', 'Games', 'Social Media', 'Video']
    
    for r in rows:
        cat = r['category']
        sec = r['total_sec']
        if not cat: continue
        if any(dw_cat.lower() in cat.lower() for dw_cat in deep_work_categories):
            deep_work_sec += sec
        elif any(dt_cat.lower() in cat.lower() for dt_cat in distracted_categories):
            distracted_sec += sec
            
    total_focused_ratio = 0
    if (deep_work_sec + distracted_sec) > 0:
        total_focused_ratio = deep_work_sec / (deep_work_sec + distracted_sec)
        
    productivity_score = round(total_focused_ratio * 100)
    
    # 2. Best Focus Window based on history (hour with most total usage or highest ratio? 
    # Let's say we find hour with least distracted usage or most deep work. 
    # For simplicity, if we don't have app categories per hour in hourly_logs, 
    # let's assume we approximate or look at hourly_logs. 
    # Since hourly_logs just has date, hour_str, seconds, we can just find the hour with highest usage.
    # Alternatively, parse hour_str.
    c.execute("""
        SELECT hour_str, SUM(seconds) as sec
        FROM hourly_logs
        GROUP BY hour_str
        ORDER BY sec DESC
        LIMIT 1
    """)
    best_hour_row = c.fetchone()
    best_focus_window = best_hour_row['hour_str'] if best_hour_row else "09:00"
    
    conn.close()
    
    return jsonify({
        "productivity_score": productivity_score,
        "deep_work_minutes": round(deep_work_sec / 60),
        "distracted_minutes": round(distracted_sec / 60),
        "best_focus_window": best_focus_window
    })


# ═══════════════════════════════════
# Feature 8: Burnout Prediction (ML + heuristic)
# ═══════════════════════════════════
class BurnoutPredictSchema(BaseModel):
    screen_time_hours: float
    mood_score: float  # 1 to 10 scale (where 10 is excellent, 1 is terrible)
    sleep_hours: float

@app.route('/api/predict/burnout', methods=['POST'])
def predict_burnout():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        try:
            req_data = BurnoutPredictSchema(**data)
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400

        # Heuristic combined risk:
        # High screen time increases risk (baseline 8 hours)
        screen_risk = min(req_data.screen_time_hours / 12.0, 1.0)
        
        # Low mood increases risk
        mood_risk = 1.0 - (req_data.mood_score / 10.0)
        
        # Poor sleep increases risk (baseline 8 hours needed)
        sleep_risk = max(0.0, (8.0 - req_data.sleep_hours) / 8.0)
        
        # Weighted combination
        burnout_risk_percentage = (screen_risk * 0.4 + mood_risk * 0.4 + sleep_risk * 0.2) * 100
        
        is_high_risk = burnout_risk_percentage > 70
        
        return jsonify({
            "burnout_risk_percentage": round(burnout_risk_percentage, 1),
            "is_high_risk": is_high_risk,
            "warning": "Burnout Risk Detected" if is_high_risk else "Burnout risk is manageable."
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════
# NEW: /api/addiction-heatmap
# ═══════════════════════════════════
@app.route('/api/addiction-heatmap', methods=['GET'])
def addiction_heatmap():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Query usage_logs for social/entertainment usage
        c.execute('''
            SELECT date, sum(seconds) as total_seconds 
            FROM usage_logs 
            WHERE category LIKE '%Social%' 
               OR category LIKE '%Entertainment%' 
               OR category LIKE '%Video%' 
            GROUP BY date
        ''')
        rows = c.fetchall()
        conn.close()

        days_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        
        if not rows:
            # Generate mock records if no database records
            import random
            heatmap_data = []
            for d in days_order:
                day_hours = []
                for h in range(24):
                    # Mock logic: higher risk in evenings and weekends
                    risk = "Low"
                    if d in ["Sat", "Sun"]:
                        if 10 <= h <= 23:
                            risk = random.choice(["Medium", "High", "Very High"])
                    else:
                        if 18 <= h <= 23:
                            risk = random.choice(["Medium", "High", "Very High"])
                        elif 12 <= h <= 13:
                            risk = "Medium"
                    
                    day_hours.append({
                        "hour": h,
                        "risk": risk
                    })
                heatmap_data.append({
                    "day": d,
                    "hours": day_hours
                })
            return jsonify(heatmap_data)

        # Process real records
        day_totals = {d: 0 for d in days_order}
        for r in rows:
            try:
                dt = datetime.strptime(r['date'], "%Y-%m-%d")
                d_name = days_order[dt.weekday()]
                day_totals[d_name] += r['total_seconds']
            except Exception:
                pass
                
        heatmap_data = []
        for d in days_order:
            day_hours = []
            total_secs = day_totals[d]
            total_hours_used = total_secs / 3600.0
            
            for h in range(24):
                # Distribute usage approximately based on typical patterns since we only have daily totals in usage_logs
                hour_fraction = 0
                if d in ["Sat", "Sun"]:
                    if 10 <= h <= 23: hour_fraction = 1.0 / 14.0
                else:
                    if 18 <= h <= 23: hour_fraction = 1.0 / 6.0
                    
                hour_usage = total_hours_used * hour_fraction
                
                if hour_usage == 0:
                    risk = "None"
                elif hour_usage < 0.25:
                    risk = "Low"
                elif hour_usage < 0.5:
                    risk = "Medium"
                elif hour_usage < 1.0:
                    risk = "High"
                else:
                    risk = "Very High"
                    
                day_hours.append({
                    "hour": h,
                    "risk": risk
                })
                
            heatmap_data.append({
                "day": d,
                "hours": day_hours
            })

        return jsonify(heatmap_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════
# FIX 14: Health check endpoint
# ═══════════════════════════════════
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "models_loaded": inference_service.usage_clf is not None,
        "timestamp": datetime.utcnow().isoformat()
    })

# ═══════════════════════════════════
# Feature 3: Habit Formation Engine (7 Day Detox Challenge)
# ═══════════════════════════════════
@app.route('/api/habits/challenge', methods=['GET', 'POST'])
def detox_challenge():
    conn = get_db_connection()
    c = conn.cursor()
    user_id = 'default_user'  # Hardcoded for now, as no auth

    if request.method == 'GET':
        # Default 7 tasks
        tasks = [
            "Reduce Instagram usage by 15 mins",
            "No screens 1 hour before bed",
            "Keep phone outside bedroom",
            "Grayscale mode for 4 hours",
            "Delete 1 distracting app",
            "Take 10-minute walk without phone",
            "Full day: Social media fasting!"
        ]
        
        # Ensure 7 tasks exist for user
        c.execute("SELECT COUNT(*) FROM detox_challenge WHERE user_id = ?", (user_id,))
        count = c.fetchone()[0]
        
        if count < 7:
            for day, task in enumerate(tasks, start=1):
                c.execute(
                    "INSERT OR IGNORE INTO detox_challenge (user_id, day, task, completed) VALUES (?, ?, ?, ?)",
                    (user_id, day, task, False)
                )
            conn.commit()
            
        c.execute("SELECT day, task, completed, date_completed FROM detox_challenge WHERE user_id = ? ORDER BY day ASC", (user_id,))
        rows = c.fetchall()
        
        result = []
        for r in rows:
            result.append({
                "day": r['day'],
                "task": r['task'],
                "completed": bool(r['completed']),
                "date_completed": r['date_completed']
            })
        conn.close()
        return jsonify(result)
        
    elif request.method == 'POST':
        data = request.get_json()
        day = data.get('day')
        completed = data.get('completed', True)
        date_completed = datetime.utcnow().isoformat() if completed else None
        
        if not day:
             return jsonify({"error": "Missing day"}), 400
             
        c.execute(
            "UPDATE detox_challenge SET completed = ?, date_completed = ? WHERE user_id = ? AND day = ?",
            (completed, date_completed, user_id, day)
        )
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "day": day, "completed": completed})



# ═══════════════════════════════════
# FIX 8: /api/predict/usage — real model inference
# ═══════════════════════════════════
@app.route('/api/predict/usage', methods=['POST'])
def predict_usage():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        try:
            req_data = UsagePredictSchema(**data)
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400

        # Features must match training order in train_models.py
        feature_names = [
            'age_scaled', 'income_scaled', 'gender_encoded', 'platform_encoded', 'interests_encoded',
            'location_encoded', 'demographics_encoded', 'profession_encoded',
            'indebt', 'isHomeOwner', 'Owns_Car', 'platform_risk_score'
        ]
        features = [
            req_data.age_scaled,
            req_data.income_scaled,
            req_data.gender_encoded,
            req_data.platform_encoded,
            req_data.interests_encoded,
            req_data.location_encoded,
            req_data.demographics_encoded,
            req_data.profession_encoded,
            req_data.indebt,
            req_data.isHomeOwner,
            req_data.Owns_Car,
            req_data.platform_risk_score,
        ]
        df_features = pd.DataFrame([features], columns=feature_names)

        pred_encoded = inference_service.usage_clf.predict(df_features)[0]
        probabilities = inference_service.usage_clf.predict_proba(df_features)[0]
        confidence = float(max(probabilities))

        # Decode prediction back to label
        label_encoder = inference_service.encoders.get('usage_category')
        if label_encoder is not None:
            prediction = label_encoder.inverse_transform([pred_encoded])[0]
        else:
            prediction = str(pred_encoded)

        return jsonify({
            "prediction": prediction,
            "confidence": round(confidence, 3),
            "model_used": inference_service.model_report.get('usage_classifier', {}).get('best_model', 'RandomForest'),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════
# FIX 9: /api/predict/mental_health — real model inference
# ═══════════════════════════════════
@app.route('/api/predict/mental_health', methods=['POST'])
def predict_mental_health():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        try:
            req_data = MentalHealthPredictSchema(**data)
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400

        # Features must match training column names and order for Model B
        col_age = '1. What is your age?'
        col_distracted_scale = '12. On a scale of 1 to 5, how easily distracted are you?'
        col_concentrate = '14. Do you find it difficult to concentrate on things?'
        col_depressed = '18. How often do you feel depressed or down?'
        col_interest = '19. On a scale of 1 to 5, how frequently does your interest in daily activities fluctuate?'
        col_sleep = '20. On a scale of 1 to 5, how often do you face issues regarding sleep?'
        col_purpose = '9. How often do you find yourself using Social media without a specific purpose?'
        col_distracted_busy = '10. How often do you get distracted by Social media when you are busy doing something?'
        col_restless = '11. Do you feel restless if you haven\'t used Social media in a while?'
        col_worries = '13. On a scale of 1 to 5, how much are you bothered by worries?'
        col_compare = '15. On a scale of 1-5, how often do you compare yourself to other successful people through the use of social media?'
        col_compare_feel = '16. Following the previous question, how do you feel about these comparisons, generally speaking?'
        col_validation = '17. How often do you look to seek validation from features of social media?'

        feature_names = [
            col_distracted_scale,
            col_concentrate,
            col_depressed,
            col_interest,
            col_sleep,
            col_purpose,
            col_distracted_busy,
            col_restless,
            col_worries,
            col_compare,
            col_compare_feel,
            col_validation,
            'usage_hours',
            col_age,
        ]

        feature_map = {
            col_distracted_scale: req_data.distraction_score,
            col_concentrate: req_data.concentration_score,
            col_depressed: req_data.depression_score,
            col_interest: req_data.interest_fluctuation,
            col_sleep: req_data.sleep_issues_score,
            col_purpose: req_data.purposeless_usage,
            col_distracted_busy: req_data.distracted_when_busy,
            col_restless: req_data.restlessness_score,
            col_worries: req_data.worries_score,
            col_compare: req_data.comparison_score,
            col_compare_feel: req_data.comparison_feeling,
            col_validation: req_data.validation_seeking,
            'usage_hours': req_data.avg_daily_usage,
            col_age: req_data.age,
        }

        df_features = pd.DataFrame([feature_map], columns=feature_names)

        pred_encoded = inference_service.mental_clf.predict(df_features)[0]
        probabilities = inference_service.mental_clf.predict_proba(df_features)[0]
        confidence = float(max(probabilities))

        label_encoder = inference_service.encoders.get('mental_health_risk')
        if label_encoder is not None:
            prediction = label_encoder.inverse_transform([pred_encoded])[0]
        else:
            prediction = str(pred_encoded)

        return jsonify({
            "prediction": prediction,
            "confidence": round(confidence, 3),
            "risk_score": int(round(confidence * 100)),
            "model_used": inference_service.model_report.get('mental_health_clf', {}).get('best_model', 'GradientBoosting'),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════
# FIX 10: /api/user/segment — real model inference (POST)
# ═══════════════════════════════════
@app.route('/api/user/segment', methods=['POST'])
def user_segment():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        try:
            req_data = UserSegmentSchema(**data)
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400

        # Clustering features: time_spent, age, income, platform_risk_score
        feature_names = ['time_spent', 'age', 'income', 'platform_risk_score']
        features = [
            req_data.time_spent,
            req_data.age,
            req_data.income,
            req_data.platform_risk_score,
        ]
        
        df_features = pd.DataFrame([features], columns=feature_names)

        scaled = inference_service.scaler.transform(df_features)
        cluster_id = int(inference_service.segmentation.predict(scaled)[0])
        persona_name = inference_service.persona_map.get(str(cluster_id), "Balanced Professional")

        persona_descriptions = {
            "Night Scroller": "Heavy usage after 10 PM. High sleep disruption risk.",
            "Social Addict": "3+ hours on social platforms daily. High mental health risk.",
            "Balanced Professional": "Controlled usage. Productivity-first behavior.",
            "Productive Learner": "Low social media. High study and focus hours.",
            "Weekend Binger": "Low weekday usage, significant spikes on weekends.",
        }

        risk_levels = {
            "Night Scroller": "High",
            "Social Addict": "High",
            "Weekend Binger": "Medium",
            "Balanced Professional": "Low",
            "Productive Learner": "Low",
        }

        return jsonify({
            "cluster_id": cluster_id,
            "persona": persona_name,
            "description": persona_descriptions.get(persona_name, ""),
            "risk": risk_levels.get(persona_name, "Medium"),
            "model_used": "KMeans",
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════
# FIX 11: /api/predict/productivity — new endpoint
# ═══════════════════════════════════
@app.route('/api/predict/productivity', methods=['POST'])
def predict_productivity():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400

        try:
            req_data = ProductivityPredictSchema(**data)
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400

        # Features must match StudentPerformanceFactors training columns
        feature_names = [
            'Hours_Studied',
            'Attendance',
            'Sleep_Hours',
            'Previous_Scores',
            'Tutoring_Sessions',
            'Physical_Activity',
            'Parental_Involvement_encoded',
            'Access_to_Resources_encoded',
            'Extracurricular_Activities_encoded',
            'Motivation_Level_encoded',
            'Internet_Access_encoded',
            'Family_Income_encoded',
            'Teacher_Quality_encoded',
            'School_Type_encoded',
            'Peer_Influence_encoded',
            'Learning_Disabilities_encoded',
            'Parental_Education_Level_encoded',
            'Distance_from_Home_encoded',
            'Gender_encoded',
        ]

        feature_map = {
            'Hours_Studied': req_data.hours_studied,
            'Attendance': req_data.attendance,
            'Sleep_Hours': req_data.sleep_hours,
            'Previous_Scores': req_data.previous_scores,
            'Tutoring_Sessions': req_data.tutoring_sessions,
            'Physical_Activity': req_data.physical_activity,
            'Parental_Involvement_encoded': req_data.parental_involvement_encoded,
            'Access_to_Resources_encoded': req_data.access_to_resources_encoded,
            'Extracurricular_Activities_encoded': req_data.extracurricular_encoded,
            'Motivation_Level_encoded': req_data.motivation_encoded,
            'Internet_Access_encoded': req_data.internet_access_encoded,
            'Family_Income_encoded': req_data.family_income_encoded,
            'Teacher_Quality_encoded': req_data.teacher_quality_encoded,
            'School_Type_encoded': req_data.school_type_encoded,
            'Peer_Influence_encoded': req_data.peer_influence_encoded,
            'Learning_Disabilities_encoded': req_data.learning_disabilities_encoded,
            'Parental_Education_Level_encoded': req_data.parental_education_encoded,
            'Distance_from_Home_encoded': req_data.distance_encoded,
            'Gender_encoded': req_data.gender_encoded,
        }

        df_features = pd.DataFrame([feature_map], columns=feature_names)

        predicted_score = float(inference_service.productivity_reg.predict(df_features)[0])
        predicted_score = max(0, min(100, round(predicted_score, 1)))

        return jsonify({
            "predicted_exam_score": predicted_score,
            "productivity_score": round(predicted_score / 100, 2),
            "model_used": inference_service.model_report.get('productivity_reg', {}).get('best_model', 'Ridge'),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════
# AI Doomscroll Predictor (Realtime)
# ═══════════════════════════════════
@app.route('/api/predict/realtime', methods=['POST'])
def predict_realtime_doomscroll():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    try:
        user_id = data.get("user_id", "default")
        events = data.get("last_events", [])
        hour_of_day = data.get("hour_of_day", datetime.now().hour)
        mood_score = data.get("mood_score", 5)

        # Basic heuristic model for demo: 
        # High social media usage late at night triggers high risk.
        risk = 0.2
        if hour_of_day >= 22 or hour_of_day <= 3:
            risk += 0.3
        
        social_duration = sum([e.get('duration', 0) for e in events if e.get('app', '').lower() in ['tiktok', 'instagram', 'twitter', 'reddit', 'youtube']])
        
        if social_duration > 900: # 15 minutes of social apps
            risk += 0.4
            
        if mood_score < 4:
            risk += 0.1

        risk = min(risk, 1.0)
        
        action = "none"
        if risk > 0.8:
            action = "start_focus"
        elif risk > 0.6:
            action = "suggest_break"

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('INSERT INTO doom_events (user_id, timestamp, risk, action_taken) VALUES (?, ?, ?, ?)',
                  (user_id, datetime.now().isoformat(), risk, action))
        conn.commit()
        conn.close()

        return jsonify({
            "risk": risk,
            "action": action,
            "confidence": 0.85,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════
# FIX 12: /api/analytics/weekly — new endpoint
# ═══════════════════════════════════
@app.route('/api/analytics/weekly', methods=['GET'])
def weekly_analytics():
    try:
        df = pd.read_csv('data/dummy_data.csv')
        stats = {
            "avg_daily_usage_hours": round(float(df['time_spent'].mean()), 2),
            "max_usage_hours": int(df['time_spent'].max()),
            "min_usage_hours": int(df['time_spent'].min()),
            "pct_excessive": round(float((df['time_spent'] >= 7).mean() * 100), 1),
            "pct_healthy": round(float((df['time_spent'] <= 3).mean() * 100), 1),
            "top_platform": df['platform'].mode()[0],
            "timestamp": datetime.utcnow().isoformat()
        }
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════
# FIX 13: /api/recommendations — new endpoint
# ═══════════════════════════════════
@app.route('/api/recommendations', methods=['POST'])
def recommendations():
    try:
        data = request.get_json()
        if data:
            try:
                req_data = RecommendationSchema(**data)
                persona = req_data.persona
            except ValidationError as e:
                persona = 'Balanced Professional'
        else:
            persona = 'Balanced Professional'

        tips_db = {
            "Night Scroller": [
                "Enable grayscale mode after 9 PM",
                "Set phone to Do Not Disturb at 10 PM",
                "Charge phone outside bedroom",
                "Use blue light filter after sunset",
            ],
            "Social Addict": [
                "Set a 2-hour daily social media limit",
                "Delete most-used app from home screen",
                "Schedule one social-media-free day per week",
                "Turn off all social media notifications",
            ],
            "Balanced Professional": [
                "Maintain your current usage — you're doing well",
                "Try a weekly digital detox Sunday",
                "Share your habits to help others",
            ],
            "Productive Learner": [
                "Great habits! Keep screen time low during study hours",
                "Reward focused study blocks with short screen breaks",
            ],
            "Weekend Binger": [
                "Plan offline weekend activities in advance",
                "Set a weekend screen time cap of 3 hours/day",
                "Use weekends for physical activity instead",
            ],
        }

        risk_levels = {
            "Night Scroller": "High",
            "Social Addict": "High",
            "Weekend Binger": "Medium",
            "Balanced Professional": "Low",
            "Productive Learner": "Low",
        }

        return jsonify({
            "persona": persona,
            "risk": risk_levels.get(persona, "Medium"),
            "recommendations": tips_db.get(persona, tips_db["Balanced Professional"]),
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════
# /api/model/report — existing, fixed error handling
# ═══════════════════════════════════
@app.route('/api/model/report', methods=['GET'])
def get_report():
    try:
        with open('models/model_report.json', 'r') as f:
            report = json.load(f)
        return jsonify(report)
    except FileNotFoundError:
        return jsonify({"error": "model_report.json not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════
# PART 2 — AGENT INTEGRATION ENDPOINTS
# ═══════════════════════════════════

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'agent'))
try:
    from enforcer import save_limits, load_limits
    from focus_mode import start_focus_session, stop_focus_session, get_focus_status
    from pomodoro import start_pomodoro, stop_pomodoro, get_pomodoro_state
    from reporter import generate_daily_report, generate_weekly_report
except ImportError as e:
    print(f"Warning: Could not import agent modules: {e}")
from flask import send_file
from datetime import date

USAGE_LOG_PATH = os.path.join(os.path.dirname(__file__), 'data', 'usage_log.json')

# ── App Tracking ──────────────────────────────────────

@app.route('/api/tracker/live', methods=['GET'])
def tracker_live():
    """Returns current live usage data from sqlite db"""
    try:
        today = str(date.today())
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('SELECT * FROM usage_logs WHERE date = ? ORDER BY seconds DESC', (today,))
        rows = c.fetchall()
        
        apps = {}
        total_seconds = 0
        for row in rows:
            apps[row['friendly_name']] = {
                'seconds': row['seconds'],
                'category': row['category'],
                'risk': row['risk'],
                'process_name': row['process_name'],
                'last_seen': row['last_seen']
            }
            total_seconds += row['seconds']
            
        conn.close()
        
        return jsonify({
            "date": today,
            "total_seconds": total_seconds,
            "apps": apps
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/interventions', methods=['GET'])
def get_interventions():
    """Retrieve doomscrolling interventions"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM interventions ORDER BY id DESC LIMIT 10')
        rows = c.fetchall()
        conn.close()
        
        interventions = []
        for r in rows:
            interventions.append({
                "id": r['id'],
                "timestamp": r['timestamp'],
                "app_name": r['app_name'],
                "reason": r['reason'],
                "status": r['status']
            })
        return jsonify(interventions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/interventions/<int:intervention_id>', methods=['POST'])
def resolve_intervention(intervention_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("UPDATE interventions SET status = 'resolved' WHERE id = ?", (intervention_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "resolved"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/wellness-score', methods=['GET'])
def wellness_score():
    """Calculate an addictive risk / wellness score from 0-100 based on usage"""
    try:
        today = str(date.today())
        conn = get_db_connection()
        c = conn.cursor()
        
        # Total usage today
        c.execute('SELECT category, seconds FROM usage_logs WHERE date = ?', (today,))
        rows = c.fetchall()
        conn.close()
        
        social_seconds = 0
        total_seconds = 0
        for r in rows:
            total_seconds += r['seconds']
            if r['category'] == 'Social':
                social_seconds += r['seconds']
                
        # Simple scoring logic: 
        # Base score 100
        # -10 for every hour of social media
        # -5 for every 2 hours of overall screen time
        score = 100
        social_hours = social_seconds / 3600.0
        total_hours = total_seconds / 3600.0
        
        score -= (social_hours * 10)
        score -= (total_hours / 2.0 * 5)
        
        score = max(0, min(100, int(score)))  # clamp 0-100
        
        # Calculate projection for "Digital Twin" (30-day outlook)
        # Mocking a basic linear degradation/improvement based on current score
        trend_slope = (score - 70) / 100.0  # If score > 70, trend is positive. Else negative.
        projected_score_30 = max(0, min(100, int(score + (trend_slope * 30))))

        # Save to DB
        conn = get_db_connection()
        c = conn.cursor()
        components_json = json.dumps({"social_hours": social_hours, "total_hours": total_hours})
        c.execute('''
            INSERT INTO wellness_score (user_id, date, score, components)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id, date) DO UPDATE SET score=excluded.score, components=excluded.components
        ''', ("default_user", today, score, components_json))
        conn.commit()

        # Fetch historical trend
        c.execute('SELECT date, score FROM wellness_score WHERE user_id = ? ORDER BY date ASC LIMIT 7', ("default_user",))
        history_rows = c.fetchall()
        conn.close()

        historical_trend = [{"date": r['date'], "score": r['score']} for r in history_rows]

        # Determine risk level
        if score > 80:
            risk = "Low"
        elif score > 50:
            risk = "Moderate"
        else:
            risk = "High"
            
        return jsonify({
            "score": score,
            "risk_level": risk,
            "social_hours": float(f"{social_hours:.2f}"),
            "total_hours": float(f"{total_hours:.2f}"),
            "projected_score_30_days": projected_score_30,
            "historical_trend": historical_trend
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── App Limits ────────────────────────────────────────

@app.route('/api/limits', methods=['GET'])
def get_limits():
    try:
        return jsonify(load_limits())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/limits', methods=['POST'])
def set_limit():
    """Set time limit for a specific app"""
    try:
        data = request.get_json()
        limits = load_limits()
        limits[data['app_name']] = {
            "limit_seconds": int(data.get('limit_seconds', 3600)),
            "mode": data.get('mode', 'all'),  # warn / close / break / all
            "created_at": datetime.utcnow().isoformat()
        }
        save_limits(limits)
        return jsonify({"status": "saved", "limits": limits})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/limits/<app_name>', methods=['DELETE'])
def delete_limit(app_name):
    try:
        limits = load_limits()
        limits.pop(app_name, None)
        save_limits(limits)
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Focus Mode ────────────────────────────────────────

@app.route('/api/focus/start', methods=['POST'])
def focus_start():
    try:
        data = request.get_json()
        result = start_focus_session(
            duration_minutes=data.get('duration_minutes', 25),
            block_list=data.get('block_list', None),
            session_name=data.get('session_name', 'Focus Session')
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/focus/stop', methods=['POST'])
def focus_stop():
    try:
        return jsonify(stop_focus_session())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/focus/status', methods=['GET'])
def focus_status():
    try:
        return jsonify(get_focus_status())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Pomodoro ──────────────────────────────────────────

@app.route('/api/pomodoro/start', methods=['POST'])
def pomodoro_start():
    try:
        config = request.get_json()
        return jsonify(start_pomodoro(config))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pomodoro/stop', methods=['POST'])
def pomodoro_stop():
    try:
        return jsonify(stop_pomodoro())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pomodoro/state', methods=['GET'])
def pomodoro_state():
    try:
        return jsonify(get_pomodoro_state())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Reports ───────────────────────────────────────────

@app.route('/api/reports/daily', methods=['GET'])
def daily_report():
    try:
        result = generate_daily_report()
        if 'error' in result:
            return jsonify(result), 400
        return send_file(result['filepath'], as_attachment=True,
                         download_name=result['filename'], mimetype='application/pdf')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/reports/weekly', methods=['GET'])
def weekly_report():
    try:
        result = generate_weekly_report()
        if 'error' in result:
            return jsonify(result), 400
        return send_file(result['filepath'], as_attachment=True,
                         download_name=result['filename'], mimetype='application/pdf')
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Ollama AI Chatbot ─────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def digiwell_chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        
        # Gather context from sqlite db
        today = str(date.today())
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('SELECT * FROM usage_logs WHERE date = ? ORDER BY seconds DESC', (today,))
        rows = c.fetchall()
        conn.close()
        
        total_seconds = sum(row['seconds'] for row in rows)
        total_hours = total_seconds / 3600.0
        app_count = len(rows)
        
        app_breakdown = "No data available."
        
        if rows:
            breakdown_lines = []
            for row in rows:
                app_hrs = row['seconds'] / 3600.0
                category = row['category'] or 'Unknown'
                breakdown_lines.append(f"- {row['friendly_name']}: {app_hrs:.2f} hrs (Category: {category})")
            app_breakdown = "\n".join(breakdown_lines)
                
        system_prompt = f"""
You are DigiWell, a digital wellness coach. Here is the user's real usage data for today:
Total screen time today: {total_hours:.2f} hrs across {app_count} apps.

App Breakdown:
{app_breakdown}

Guidelines:
1. Answer the user's questions specifically and tangibly based ONLY on the data above.
2. Be concise, warm, and specific. Max 3 sentences per response. 
3. Do NOT tell the user to reduce time on productive tools (like Development or VS Code). Encourage them instead.
4. Focus mini-goals on actual high-risk or time-wasting apps if any exist. Do not preach.
"""
        
        # Call local Ollama
        full_prompt = f"{system_prompt}\n\nUser: {user_message}\nDigiWell Planner:"
        
        try:
            ollama_response = requests.post(
                "http://localhost:11434/api/generate", 
                json={
                    "model": "gemma3:1b",
                    "prompt": full_prompt, 
                    "stream": False
                },
                timeout=15
            )
            ollama_response.raise_for_status()
            reply = ollama_response.json().get("response", "I couldn't generate a response.")
        except requests.exceptions.RequestException as req_err:
            print(f"Ollama connection error: {req_err}")
            reply = f"I'm having trouble connecting to my local AI brain (Ollama). Please ensure it's running locally on port 11434.\n\nSimulated response based on your {total_hours:.2f} hours of usage today: Consider taking a 15-minute screen-free break."

        return jsonify({"response": reply, "timestamp": datetime.utcnow().isoformat()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Anomaly Detection ─────────────────────────────────
@app.route('/api/anomaly', methods=['POST'])
def check_anomaly():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "No input data provided"}), 400
            
        try:
            req_data = AnomalySchema(**data)
            current_usage = req_data.time_spent
        except ValidationError as e:
            return jsonify({"error": e.errors()}), 400
        
        if inference_service.anomaly_detector is None:
            return jsonify({"is_anomaly": False, "message": "Model not loaded"})

        # -1 = anomaly, 1 = normal
        prediction = inference_service.anomaly_detector.predict([[current_usage]])[0]
        
        return jsonify({
            "is_anomaly": bool(prediction == -1),
            "score": int(prediction),
            "current_usage_hours": current_usage
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Mood Journal ──────────────────────────────────────
MOOD_JOURNAL_PATH = os.path.join(os.path.dirname(__file__), 'data', 'mood_journal.json')

from ai_service import analyze_journal, predict_relapse, therapy_start, therapy_agent_step
import uuid

@app.route('/api/therapy/session', methods=['POST'])
def create_therapy_session():
    try:
        user_id = request.json.get('user_id', 'default_user') if request.json else 'default_user'
        session_id = str(uuid.uuid4())
        
        initial_msg = therapy_start()
        messages = [{"role": "assistant", "content": initial_msg.get("reply", "Hello. Let's begin.")}]
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO therapy_sessions (id, user_id, messages, outcome)
            VALUES (?, ?, ?, ?)
        ''', (session_id, user_id, json.dumps(messages), json.dumps({})))
        conn.commit()
        conn.close()
        
        return jsonify({
            "session_id": session_id,
            "messages": messages
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/therapy/session/<session_id>/respond', methods=['POST'])
def therapy_respond(session_id):
    try:
        user_message = request.json.get('message', '')
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT messages FROM therapy_sessions WHERE id = ?', (session_id,))
        row = c.fetchone()
        if not row:
            return jsonify({'error': 'Session not found'}), 404
            
        messages = json.loads(row['messages']) if row['messages'] else []
        messages.append({"role": "user", "content": user_message})
        
        # Call AI service
        agent_reply = therapy_agent_step(session_id, user_message)
        
        messages.append({"role": "assistant", "content": agent_reply.get("reply", "")})
        
        c.execute('''
            UPDATE therapy_sessions 
            SET messages = ?, outcome = ?
            WHERE id = ?
        ''', (
            json.dumps(messages), 
            json.dumps(agent_reply.get("suggested_commitment", {})),
            session_id
        ))
        conn.commit()
        conn.close()
        
        return jsonify({
            "messages": messages,
            "agent_reply": agent_reply.get("reply", ""),
            "suggested_commitment": agent_reply.get("suggested_commitment", None)
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/predictions/relapse-risk', methods=['GET'])
def get_relapse_risk():
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # In reality, fetch recent features from DB
        features = {"user_id": user_id}
        features_json = json.dumps(features, sort_keys=True)
        
        # Predict using ai_service or loaded model
        result = predict_relapse(features_json)
        
        risk = result.get('risk', 0.0)
        top_features = result.get('top_features', [])
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO relapse_predictions (user_id, risk, features)
            VALUES (?, ?, ?)
        ''', (user_id, risk, json.dumps(top_features)))
        conn.commit()
        conn.close()
        
        return jsonify({
            "risk": risk,
            "top_features": top_features
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mood/analyze-and-save', methods=['POST'])
def analyze_and_save_mood():
    try:
        data = request.get_json()
        entry_text = data.get('entry', '')
        mood_score = data.get('mood_score', 3)
        user_id = data.get('user_id', 'default_user')
        
        polarity = 0.0
        
        ai_result = analyze_journal(entry_text)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO mood_journal 
            (user_id, date, entry, mood_score, polarity, ai_primary_emotion, ai_distortion, ai_reframe, ai_microtask)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            datetime.now().isoformat(),
            entry_text,
            mood_score,
            polarity,
            ai_result.get('primary_emotion'),
            json.dumps(ai_result.get('cognitive_distortions', [])),
            ai_result.get('reframe'),
            json.dumps(ai_result.get('micro_task', {}))
        ))
        conn.commit()
        new_id = c.lastrowid
        
        c.execute('SELECT * FROM mood_journal WHERE id = ?', (new_id,))
        row = dict(c.fetchone())
        conn.close()
        
        row['ai_distortion'] = json.loads(row['ai_distortion']) if row.get('ai_distortion') else []
        row['ai_microtask'] = json.loads(row['ai_microtask']) if row.get('ai_microtask') else {}
        
        return jsonify(row), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/mood', methods=['GET', 'POST'])
def mood_journal():
    try:
        # Ensure file exists
        if not os.path.exists(MOOD_JOURNAL_PATH):
            with open(MOOD_JOURNAL_PATH, 'w') as f:
                json.dump([], f)
                
        if request.method == 'GET':
            with open(MOOD_JOURNAL_PATH, 'r') as f:
                return jsonify(json.load(f))
                
        # POST - new entry
        data = request.get_json()
        entry_text = data.get('entry', '')
        mood_score = data.get('mood_score', 3) # 1-5 scale
        
        # Super basic lexical sentiment fallback if no NLP lib installed
        positive_words = ['great', 'good', 'happy', 'productive', 'focused', 'energized', 'calm', 'well']
        negative_words = ['bad', 'sad', 'tired', 'anxious', 'depressed', 'distracted', 'stressed', 'awful']
        
        words = entry_text.lower().split()
        pos_count = sum(1 for w in words if w in positive_words)
        neg_count = sum(1 for w in words if w in negative_words)
        
        polarity = 0.0
        if (pos_count + neg_count) > 0:
            polarity = (pos_count - neg_count) / (pos_count + neg_count)
            # scale based on explicit mood_score if provided
            polarity += (mood_score - 3) * 0.2
            polarity = max(-1.0, min(1.0, polarity)) # clamp -1 to 1
        else:
            polarity = (mood_score - 3) * 0.33 # Just use the numerical score
            
        new_entry = {
            "date": datetime.utcnow().isoformat(),
            "entry": entry_text,
            "mood_score": mood_score,
            "polarity": round(polarity, 2)
        }
        
        with open(MOOD_JOURNAL_PATH, 'r+') as f:
            journals = json.load(f)
            journals.append(new_entry)
            f.seek(0)
            json.dump(journals, f, indent=4)
            
        return jsonify({"status": "saved", "entry": new_entry})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Feature 7: AI Daily Reflection ─────────────────────
@app.route('/api/daily-reflection', methods=['GET'])
def get_daily_reflection():
    try:
        from datetime import date, timedelta
        conn = get_db_connection()
        c = conn.cursor()
        
        today_str = date.today().isoformat()
        yesterday_str = (date.today() - timedelta(days=1)).isoformat()
        
        c.execute("SELECT SUM(seconds) FROM usage_logs WHERE date=?", (today_str,))
        today_sec = c.fetchone()[0] or 0
        
        c.execute("SELECT SUM(seconds) FROM usage_logs WHERE date=?", (yesterday_str,))
        yesterday_sec = c.fetchone()[0] or 0
        
        today_hrs = today_sec / 3600.0
        yesterday_hrs = yesterday_sec / 3600.0
        
        diff = today_hrs - yesterday_hrs
        
        summary = ""
        if diff > 1:
            summary = "Your screen time is significantly higher today than yesterday. Consider taking a break."
        elif diff < -1:
            summary = "Great job! You've reduced your screen time today compared to yesterday."
        else:
            summary = "Your screen time is consistent with yesterday. Keep maintaining a balanced routine."
            
        reflection = {
            "today_hours": round(today_hrs, 2),
            "yesterday_hours": round(yesterday_hrs, 2),
            "difference_hours": round(abs(diff), 2),
            "trend": "up" if diff > 0 else "down",
            "summary": summary
        }
        return jsonify(reflection)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Feature 9: AI Personalized Focus Mode ──────────────
@app.route('/api/focus/recommend', methods=['GET'])
def focus_recommend():
    try:
        from datetime import date
        conn = get_db_connection()
        c = conn.cursor()
        
        # Determine top 3 distracting apps over the last 7 days
        c.execute('''
            SELECT friendly_name, SUM(seconds) as total_sec 
            FROM usage_logs 
            WHERE category IN ('Social', 'Entertainment', 'Games', 'Social Media')
            GROUP BY friendly_name 
            ORDER BY total_sec DESC 
            LIMIT 3
        ''')
        rows = c.fetchall()
        apps_to_block = [r['friendly_name'] for r in rows] if rows else ['YouTube', 'Instagram', 'TikTok']
        
        recommended_duration = 30 # Default 30 min focus
        # Suggest 45 mins if they spend > 4 hrs on distractions
        total_distract = sum(r['total_sec'] for r in rows) if rows else 0
        if total_distract > 4 * 3600:
            recommended_duration = 45 

        rec = {
            "recommended_duration_minutes": recommended_duration,
            "recommended_block_list": apps_to_block,
            "reasoning": "Based on your recent high usage of these apps, we recommend blocking them to minimize distractions."
        }
        return jsonify(rec)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Feature 10: AI Digital Twin Simulator ─────────────
@app.route('/api/predict/simulation', methods=['POST'])
def predict_simulation():
    try:
        data = request.get_json() or {}
        days_ahead = data.get('days', 30)
        daily_increment = data.get('current_daily_hours', 5.0)
        trend = data.get('trend_modifier', 1.05) # Assume 5% growth per period if no intervention
        
        simulated_future_hours = daily_increment * (trend ** (days_ahead / 7)) # compound weekly
        
        # Simple heuristics for projection
        productivity_drop = min(40, (simulated_future_hours - daily_increment) * 5) # 5% drop per extra hour
        sleep_drop = min(30, (simulated_future_hours - daily_increment) * 3) # 3% drop per extra hour
        mental_health_impact = "High Risk" if simulated_future_hours > 8 else "Moderate"
        
        proj = {
            "days_projected": days_ahead,
            "projected_daily_hours": round(simulated_future_hours, 2),
            "productivity_impact_percent": -round(max(0, productivity_drop), 1),
            "sleep_impact_percent": -round(max(0, sleep_drop), 1),
            "mental_health_forecast": mental_health_impact,
            "message": f"If current trends continue, your daily screen time will reach {round(simulated_future_hours, 1)} hrs. Productivity could drop by {round(max(0, productivity_drop), 1)}%."
        }
        return jsonify(proj)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ═══════════════════════════════════
# Feature 6: Browser Activity Tracking Extension
# ═══════════════════════════════════
class BrowserTrackerSchema(BaseModel):
    url: str
    domain: str
    duration_seconds: int

@app.route('/api/tracker/browser', methods=['POST'])
def track_browser_activity():
    try:
        data = request.json
        if not data or 'domain' not in data or 'duration_seconds' not in data:
            return jsonify({"error": "Invalid data", "details": "Requires domain and duration_seconds"}), 400
            
        domain = data['domain']
        duration = int(data['duration_seconds'])
        
        # Categorize domains heuristically for the demo
        category = "Web Browsing"
        if any(d in domain for d in ['youtube.com', 'netflix.com', 'twitch.tv']):
            category = "Entertainment"
        elif any(d in domain for d in ['facebook.com', 'instagram.com', 'twitter.com', 'reddit.com', 'tiktok.com']):
            category = "Social Media"
        elif any(d in domain for d in ['github.com', 'stackoverflow.com', 'docs.']):
            category = "Development"
        elif any(d in domain for d in ['gmail.com', 'notion.so', 'slack.com', 'calendar.google']):
            category = "Productivity"
            
        risk = "high" if category in ["Entertainment", "Social Media"] else "low"
            
        conn = get_db_connection()
        c = conn.cursor()
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        now_str = datetime.now().isoformat()
        
        # Insert or update daily usage logs
        c.execute('''
            INSERT INTO usage_logs (date, friendly_name, process_name, category, risk, seconds, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(date, friendly_name) DO UPDATE SET
            seconds = seconds + excluded.seconds,
            last_seen = excluded.last_seen
        ''', (date_str, domain, "Browser", category, risk, duration, now_str))
        
        # Insert or update hourly logs
        hour_str = datetime.now().strftime("%H:00")
        c.execute('''
            INSERT INTO hourly_logs (date, hour_str, seconds)
            VALUES (?, ?, ?)
            ON CONFLICT(date, hour_str) DO UPDATE SET
            seconds = seconds + excluded.seconds
        ''', (date_str, hour_str, duration))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success", "domain": domain, "added_seconds": duration})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── 1. Dopamine Loop Detector ──────────────────────────
@app.route('/api/dopamine-loop', methods=['GET'])
def get_dopamine_loop():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT friendly_name, category, last_seen
            FROM usage_logs
            WHERE category IN ('Social', 'Entertainment', 'Social Media', 'Video')
        ''')
        rows = c.fetchall()
        conn.close()
        
        now = datetime.now()
        recent_apps = []
        
        for row in rows:
            if row['last_seen']:
                try:
                    last_seen_dt = datetime.fromisoformat(row['last_seen'])
                    diff_mins = (now - last_seen_dt).total_seconds() / 60.0
                    if diff_mins <= 15 and diff_mins >= 0:
                        recent_apps.append(row['friendly_name'])
                except:
                    pass
                    
        detected = len(recent_apps) >= 3
        
        return jsonify({
            "detected": detected,
            "apps": recent_apps
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── 2. AI Life Coach ───────────────────────────────────
@app.route('/api/coach/chat', methods=['POST'])
def coach_chat_new():
    try:
        data = request.get_json()
        user_message = data.get('message', '').lower()
        
        conn = get_db_connection()
        c = conn.cursor()
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # Analyze the last hour from hourly_logs
        hour_str = datetime.now().strftime("%H:00")
        c.execute('SELECT seconds FROM hourly_logs WHERE date = ? AND hour_str = ?', (date_str, hour_str))
        hr_row = c.fetchone()
        
        c.execute('SELECT friendly_name, seconds, category FROM usage_logs WHERE date = ? ORDER BY seconds DESC', (date_str,))
        rows = c.fetchall()
        
        conn.close()
        
        hr_seconds = hr_row['seconds'] if hr_row else 0
        total_seconds = sum(r['seconds'] for r in rows)
        hours = total_seconds / 3600
        
        response = "I hear you. Let me help you stay on track."
        
        if any(word in user_message for word in ["hello", "hi", "hey"]):
            response = f"Hello! As your digital life coach, I see you've spent {hr_seconds//60} minutes on your devices this past hour. How can I support your goals?"
        elif any(word in user_message for word in ["help", "addict", "distract", "loop", "doom"]):
            if rows:
                top_app = rows[0]
                response = f"You've been active for {hr_seconds//60} mins this hour. I notice {top_app['friendly_name']} is highly used today. It's okay, building better habits takes time. Try setting a 15-minute focus timer right now."
            else:
                response = "Building focus takes time. Try breaking your tasks into manageable Pomodoro sessions."
        elif "how am i doing" in user_message or "status" in user_message:
            if hr_seconds < 1800:
                response = f"You are doing great! Only {hr_seconds//60} minutes of screen time this hour. Keep up the balanced lifestyle!"
            else:
                response = f"You've already spent {hr_seconds//60} minutes on screens this hour. It might be a good time for a quick screen-free break."
        else:
            response = f"That's a very valid point. Remember, moderation is key. You're currently at {hr_seconds//60} minutes of screen time this hour. I suggest drinking some water and looking at something 20 feet away."
            
        return jsonify({
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── 3. AI Screen Addiction Therapy ──────────────────────
@app.route('/api/therapy/plan', methods=['GET'])
def get_therapy_plan():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        date_str = datetime.now().strftime("%Y-%m-%d")
        c.execute('''
            SELECT category, SUM(seconds) as total_sec 
            FROM usage_logs 
            WHERE date = ?
            GROUP BY category 
            ORDER BY total_sec DESC
        ''', (date_str,))
        rows = c.fetchall()
        conn.close()
        
        top_cat = rows[0]['category'] if rows else "General"
        
        plan = []
        if top_cat in ["Social Media", "Social"]:
            plan = [
                {"step": 1, "title": "Awareness", "desc": "Notice your urge to open social media. Take a breath first."},
                {"step": 2, "title": "Delay", "desc": "Wait 5 minutes before checking apps like Instagram or TikTok."},
                {"step": 3, "title": "Replace", "desc": "Message a friend directly instead of scrolling through feeds."}
            ]
        elif top_cat in ["Entertainment", "Video"]:
            plan = [
                {"step": 1, "title": "Awareness", "desc": "Acknowledge when you start auto-playing the next video."},
                {"step": 2, "title": "Delay", "desc": "Pause the video and drink water before continuing."},
                {"step": 3, "title": "Replace", "desc": "Read a physical book or listen to a podcast instead."}
            ]
        else:
            plan = [
                {"step": 1, "title": "Awareness", "desc": "Keep track of how often you look at your screen without a specific goal."},
                {"step": 2, "title": "Delay", "desc": "Stand up and stretch before starting a new digital task."},
                {"step": 3, "title": "Replace", "desc": "Schedule one hour of completely screen-free time today."}
            ]
            
        return jsonify({
            "top_category": top_cat,
            "cbt_plan": plan
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── Commitments ─────────────────────────────────────────

import uuid

@app.route('/api/commitments/start', methods=['POST'])
def start_commitment():
    try:
        data = request.get_json()
        if not data or 'title' not in data:
            return jsonify({"error": "Missing title"}), 400
            
        commitment_id = str(uuid.uuid4())
        user_id = data.get('user_id', 'local')
        challenge_id = data.get('challenge_id')
        title = data.get('title')
        description = data.get('description')
        start_ts = data.get('start_ts', datetime.utcnow().isoformat())
        expected_duration_minutes = data.get('expected_duration_minutes', 60)
        
        if expected_duration_minutes < 0:
            return jsonify({"error": "Duration cannot be negative"}), 400
            
        auto_start_focus = bool(data.get('auto_start_focus', False))
        reminder_interval_minutes = data.get('reminder_interval_minutes')
        status = 'active'
        metadata = json.dumps(data.get('metadata', {}))
        
        # Calculate expected_end_ts if start_ts is now
        # Parse start_ts assuming standard iso format
        try:
            start_dt = datetime.fromisoformat(start_ts.replace('Z', '+00:00'))
            from datetime import timedelta
            end_dt = start_dt + timedelta(minutes=expected_duration_minutes)
            end_ts = end_dt.isoformat()
        except:
            end_ts = None
        
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO commitments (
                id, user_id, challenge_id, title, description, start_ts, end_ts,
                expected_duration_minutes, auto_start_focus, reminder_interval_minutes, status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            commitment_id, user_id, challenge_id, title, description, start_ts, end_ts,
            expected_duration_minutes, int(auto_start_focus), reminder_interval_minutes, status, metadata
        ))
        
        focus_session_created = False
        if auto_start_focus:
            session_id = str(uuid.uuid4())
            c.execute('''
                INSERT INTO focus_sessions (id, commitment_id, start_ts, duration_minutes, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (session_id, commitment_id, start_ts, expected_duration_minutes, 'scheduled'))
            focus_session_created = True
            
            # Write to JSON for agent compatibility
            focus_data = {
                "active": False,
                "session_name": title,
                "duration_minutes": expected_duration_minutes,
                "started_at": start_ts,
                "ends_at": end_ts,
                "block_list": ["discord.exe", "slack.exe", "WhatsApp.exe", "Telegram.exe", "steam.exe"],
                "apps_killed": []
            }
            try:
                with open(os.path.join(os.path.dirname(__file__), 'data', 'focus_session.json'), 'w') as f:
                    json.dump(focus_data, f)
            except Exception as e:
                print(f"Error writing focus_session.json: {e}")
                
        # Optional: track analytics event
        c.execute('''
            INSERT INTO interventions (timestamp, app_name, reason, status)
            VALUES (?, ?, ?, ?)
        ''', (datetime.utcnow().isoformat(), 'System', f'Started commitment: {title}', 'completed'))
            
        conn.commit()
        conn.close()
        
        return jsonify({
            "commitment_id": commitment_id,
            "status": status,
            "start_ts": start_ts,
            "expected_end_ts": end_ts,
            "focus_session_created": focus_session_created
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/commitments/<commitment_id>', methods=['GET'])
def get_commitment(commitment_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM commitments WHERE id = ?', (commitment_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Not found"}), 404
            
        return jsonify(dict(row))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/commitments', methods=['GET'])
def get_commitments():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM commitments ORDER BY start_ts DESC')
        rows = c.fetchall()
        conn.close()
        
        return jsonify([dict(r) for r in rows])
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/commitments/<commitment_id>', methods=['PATCH'])
def patch_commitment(commitment_id):
    try:
        data = request.get_json()
        status = data.get('status')
        end_ts = data.get('end_ts')
        
        updates = []
        params = []
        if status:
            updates.append("status = ?")
            params.append(status)
        if end_ts:
            updates.append("end_ts = ?")
            params.append(end_ts)
            
        if not updates:
            return jsonify({"error": "No valid fields to update"}), 400
            
        updates.append("updated_at = ?")
        params.append(datetime.utcnow().isoformat())
        params.append(commitment_id)
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute(f'UPDATE commitments SET {", ".join(updates)} WHERE id = ?', params)
        conn.commit()
        conn.close()
        
        return jsonify({"status": "updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/commitments/<commitment_id>/complete', methods=['POST'])
def complete_commitment(commitment_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        end_ts = datetime.utcnow().isoformat()
        c.execute('''
            UPDATE commitments SET status = 'completed', end_ts = ?, updated_at = ?
            WHERE id = ?
        ''', (end_ts, end_ts, commitment_id))
        
        # Mark focus session completed if it exists
        c.execute('''
            UPDATE focus_sessions SET status = 'completed' WHERE commitment_id = ?
        ''', (commitment_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({"status": "completed", "end_ts": end_ts})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
