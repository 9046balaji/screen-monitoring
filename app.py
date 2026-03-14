from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import time
import requests
from sklearn.ensemble import IsolationForest
import os
from pydantic import BaseModel, ValidationError
from typing import Any, Optional
from collections import defaultdict

from database.database import init_db, get_db_connection
from database.migrations import apply_migrations
from services.analytics_service import AnalyticsService
from services.weekly_analytics_service import WeeklyAnalyticsService

app = Flask(__name__)
# Allow local dev frontends (Vite/React) to access the API.
CORS(app, origins=["http://localhost:5173", "http://localhost:3000"])

# Ensure DB is initialized
init_db()
apply_migrations()

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
analytics_service = AnalyticsService()
weekly_analytics_service = WeeklyAnalyticsService()

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
MOOD_JOURNAL_PATH = os.path.join(DATA_DIR, "mood_journal.json")
FOCUS_SESSION_PATH = os.path.join(DATA_DIR, "focus_session.json")
BLOCKED_SITES_PATH = os.path.join(DATA_DIR, "blocked_sites.json")

PRODUCTIVE_CATEGORY_LABELS = {"development", "productivity", "office", "education", "work", "utility", "study"}
DISTRACTING_CATEGORY_LABELS = {"entertainment", "social", "social media", "games", "video"}

CHATBOT_CONTEXT_TTL_SECONDS = 20
_chatbot_context_cache = {
    'data': None,
    'expires_at': 0.0,
}


def _load_json(path: str, fallback):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return fallback


def _truncate_text(value: str, max_chars: int = 16000) -> str:
    text = value or ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n... [truncated]"


def _safe_json_preview(value: Any, max_chars: int = 3500):
    try:
        dumped = json.dumps(value, ensure_ascii=True)
    except Exception:
        dumped = str(value)
    return _truncate_text(dumped, max_chars=max_chars)


def _get_sqlite_snapshot(conn, max_rows_per_table: int = 20):
    c = conn.cursor()
    c.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name ASC
        """
    )
    tables = [r['name'] for r in c.fetchall()]

    snapshot = {}
    for table in tables:
        try:
            c.execute(f'SELECT COUNT(*) AS cnt FROM "{table}"')
            row_count = int(c.fetchone()['cnt'] or 0)

            c.execute(f'SELECT * FROM "{table}" ORDER BY rowid DESC LIMIT ?', (max_rows_per_table,))
            rows = [dict(r) for r in c.fetchall()]
            rows.reverse()

            snapshot[table] = {
                'row_count': row_count,
                'recent_rows': rows,
            }
        except Exception as ex:
            snapshot[table] = {
                'error': f'Failed reading table: {ex}',
            }

    return snapshot


def _get_data_folder_snapshot(max_chars_per_json: int = 3500):
    files = []
    json_files = {}

    if not os.path.isdir(DATA_DIR):
        return {
            'files': files,
            'json_files': json_files,
        }

    for name in sorted(os.listdir(DATA_DIR)):
        path = os.path.join(DATA_DIR, name)
        if not os.path.isfile(path):
            continue

        info = {
            'name': name,
            'size_bytes': os.path.getsize(path),
        }
        files.append(info)

        lower = name.lower()
        if lower.endswith('.json'):
            parsed = _load_json(path, None)
            if parsed is None:
                json_files[name] = {'error': 'Could not parse JSON'}
            else:
                data_type = type(parsed).__name__
                item_count = len(parsed) if isinstance(parsed, (list, dict)) else 1
                json_files[name] = {
                    'type': data_type,
                    'item_count': item_count,
                    'content_preview': _safe_json_preview(parsed, max_chars=max_chars_per_json),
                }

    return {
        'files': files,
        'json_files': json_files,
    }


def _build_chatbot_data_context(force_refresh: bool = False):
    now = time.monotonic()
    cached_data = _chatbot_context_cache.get('data')
    if (not force_refresh) and cached_data is not None and now < float(_chatbot_context_cache.get('expires_at') or 0.0):
        return cached_data

    weekly_payload = _build_report_payload(period_days=7)
    monthly_payload = _build_report_payload(period_days=30)

    conn = get_db_connection()
    try:
        db_snapshot = _get_sqlite_snapshot(conn, max_rows_per_table=20)
    finally:
        conn.close()

    data_snapshot = _get_data_folder_snapshot(max_chars_per_json=3500)

    context = {
        'generated_at_utc': datetime.utcnow().isoformat(),
        'report_summaries': {
            'weekly': weekly_payload,
            'monthly': monthly_payload,
        },
        'database_snapshot': db_snapshot,
        'data_folder_snapshot': data_snapshot,
    }

    _chatbot_context_cache['data'] = context
    _chatbot_context_cache['expires_at'] = now + CHATBOT_CONTEXT_TTL_SECONDS
    return context


def _date_range(start_date, end_date):
    cur = start_date
    while cur <= end_date:
        yield cur
        cur += timedelta(days=1)


def _usage_rows_for_period(conn, start_date, end_date):
    c = conn.cursor()
    c.execute(
        '''
        SELECT date, app_name, SUM(duration_minutes) AS minutes
        FROM app_usage_logs
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY date, app_name
        ORDER BY date ASC
        ''',
        ('local', start_date.isoformat(), end_date.isoformat())
    )
    rows = c.fetchall()

    category_map = weekly_analytics_service._load_category_map()
    mapped_rows = []
    for r in rows:
        app = r['app_name']
        category = weekly_analytics_service._classify(app, category_map)
        mapped_rows.append({
            'date': r['date'],
            'app': weekly_analytics_service._norm_app_name(app),
            'minutes': int(round(float(r['minutes'] or 0))),
            'category': category,
        })

    # Fallback to usage_logs if app_usage_logs is empty for this window.
    if mapped_rows:
        return mapped_rows

    c.execute(
        '''
        SELECT date, friendly_name, category, SUM(seconds) AS total_seconds
        FROM usage_logs
        WHERE date BETWEEN ? AND ?
        GROUP BY date, friendly_name, category
        ORDER BY date ASC
        ''',
        (start_date.isoformat(), end_date.isoformat())
    )
    rows = c.fetchall()
    fallback_rows = []
    for r in rows:
        fallback_rows.append({
            'date': r['date'],
            'app': r['friendly_name'],
            'minutes': int(round(float(r['total_seconds'] or 0) / 60.0)),
            'category': (r['category'] or 'Other').title(),
        })
    return fallback_rows


def _compute_task_completion(conn, start_date, end_date):
    c = conn.cursor()
    planned_total = 0
    for d in _date_range(start_date, end_date):
        c.execute(
            'SELECT COUNT(*) AS cnt FROM weekly_tasks WHERE user_id = ? AND day_of_week = ?',
            ('local', d.weekday())
        )
        planned_total += int(c.fetchone()['cnt'])

    c.execute(
        '''
        SELECT COUNT(*) AS cnt
        FROM daily_task_status
        WHERE status = 'completed' AND date BETWEEN ? AND ?
        ''',
        (start_date.isoformat(), end_date.isoformat())
    )
    completed = int(c.fetchone()['cnt'])

    rate = round((completed / planned_total) * 100, 1) if planned_total > 0 else 0.0
    return {
        'planned_total': planned_total,
        'completed_total': completed,
        'completion_rate': rate,
    }


def _compute_streak_over_rows(rows):
    longest = 0
    current = 0
    for r in rows:
        if r.get('success'):
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def _get_mood_period_summary(conn, start_date, end_date):
    c = conn.cursor()
    c.execute(
        '''
        SELECT SUBSTR(date, 1, 10) AS d, AVG(mood_score) AS avg_mood, COUNT(*) AS cnt
        FROM mood_journal
        WHERE SUBSTR(date, 1, 10) BETWEEN ? AND ?
        GROUP BY SUBSTR(date, 1, 10)
        ORDER BY d ASC
        ''',
        (start_date.isoformat(), end_date.isoformat())
    )
    rows = c.fetchall()
    if rows:
        trend = [{'date': r['d'], 'avg_mood': round(float(r['avg_mood']), 2), 'entries': int(r['cnt'])} for r in rows]
        c.execute('SELECT COUNT(*) AS cnt, AVG(mood_score) AS avg_mood FROM mood_journal')
        all_row = c.fetchone()
        return {
            'total_entries': int(all_row['cnt'] or 0),
            'average_mood': round(float(all_row['avg_mood']), 2) if all_row['avg_mood'] is not None else 0.0,
            'trend': trend,
        }

    file_rows = _load_json(MOOD_JOURNAL_PATH, [])
    parsed = []
    for item in file_rows:
        try:
            d = str(item.get('date', ''))[:10]
            score = float(item.get('mood_score', 0) or 0)
            if d:
                parsed.append((d, score))
        except Exception:
            continue

    by_day = defaultdict(list)
    for d, score in parsed:
        if start_date.isoformat() <= d <= end_date.isoformat():
            by_day[d].append(score)

    trend = []
    for d in sorted(by_day.keys()):
        vals = by_day[d]
        trend.append({'date': d, 'avg_mood': round(sum(vals) / len(vals), 2), 'entries': len(vals)})

    all_avg = round(sum(s for _, s in parsed) / len(parsed), 2) if parsed else 0.0
    return {
        'total_entries': len(parsed),
        'average_mood': all_avg,
        'trend': trend,
    }


def _focus_stats(conn, start_date, end_date):
    c = conn.cursor()
    c.execute(
        '''
        SELECT COUNT(*) AS cnt, COALESCE(SUM(duration_minutes), 0) AS total_min
        FROM focus_sessions
        WHERE DATE(start_ts) BETWEEN ? AND ?
        ''',
        (start_date.isoformat(), end_date.isoformat())
    )
    row = c.fetchone()
    period_sessions = int(row['cnt'] or 0)
    period_minutes = int(row['total_min'] or 0)

    c.execute('SELECT COUNT(*) AS cnt, COALESCE(SUM(duration_minutes), 0) AS total_min FROM focus_sessions')
    total_row = c.fetchone()
    total_sessions = int(total_row['cnt'] or 0)
    total_minutes = int(total_row['total_min'] or 0)

    blocked_conf = _load_json(BLOCKED_SITES_PATH, {})
    blocked_domains = set()
    if isinstance(blocked_conf, dict):
        for domains in blocked_conf.values():
            if isinstance(domains, list):
                blocked_domains.update(str(d).strip().lower() for d in domains if d)

    session_data = _load_json(FOCUS_SESSION_PATH, {})
    if isinstance(session_data, dict):
        for d in session_data.get('blocked_domains', []):
            blocked_domains.add(str(d).strip().lower())

    return {
        'period_sessions': period_sessions,
        'period_minutes': period_minutes,
        'period_hours': round(period_minutes / 60.0, 2),
        'total_sessions': total_sessions,
        'total_hours': round(total_minutes / 60.0, 2),
        'websites_blocked': len(blocked_domains),
    }


def _app_usage_stats(usage_rows):
    app_totals = defaultdict(int)
    cat_totals = defaultdict(int)
    productive_apps = defaultdict(int)
    distracting_apps = defaultdict(int)

    for r in usage_rows:
        app = r['app']
        mins = int(r['minutes'] or 0)
        cat = (r.get('category') or 'Other').title()
        norm_cat = cat.lower()

        app_totals[app] += mins
        cat_totals[cat] += mins

        if norm_cat in PRODUCTIVE_CATEGORY_LABELS:
            productive_apps[app] += mins
        if norm_cat in DISTRACTING_CATEGORY_LABELS:
            distracting_apps[app] += mins

    total_minutes = sum(app_totals.values())
    entertainment_minutes = sum(v for k, v in cat_totals.items() if k.lower() in DISTRACTING_CATEGORY_LABELS)
    entertainment_pct = round((entertainment_minutes / total_minutes) * 100, 1) if total_minutes else 0.0

    top_apps = sorted(app_totals.items(), key=lambda x: x[1], reverse=True)
    top_categories = sorted(cat_totals.items(), key=lambda x: x[1], reverse=True)

    return {
        'total_minutes': total_minutes,
        'total_hours': round(total_minutes / 60.0, 2),
        'entertainment_pct': entertainment_pct,
        'most_used_app': top_apps[0][0] if top_apps else 'N/A',
        'most_productive_app': sorted(productive_apps.items(), key=lambda x: x[1], reverse=True)[0][0] if productive_apps else 'N/A',
        'most_distracting_app': sorted(distracting_apps.items(), key=lambda x: x[1], reverse=True)[0][0] if distracting_apps else 'N/A',
        'top_apps': [
            {'app': app, 'minutes': mins, 'hours': round(mins / 60.0, 2)}
            for app, mins in top_apps[:7]
        ],
        'category_breakdown': [
            {
                'category': cat,
                'minutes': mins,
                'hours': round(mins / 60.0, 2),
                'percentage': round((mins / total_minutes) * 100, 2) if total_minutes else 0.0,
            }
            for cat, mins in top_categories
        ],
    }


def _productivity_score_v2(focus_hours, task_completion_rate, entertainment_pct, average_mood):
    focus_component = max(0.0, min(100.0, (focus_hours / 10.0) * 100.0))
    task_component = max(0.0, min(100.0, float(task_completion_rate or 0.0)))
    low_entertainment_usage = max(0.0, min(100.0, 100.0 - float(entertainment_pct or 0.0)))
    mood_component = max(0.0, min(100.0, float(average_mood or 0.0) * 20.0))

    score = (
        focus_component * 0.4
        + task_component * 0.3
        + low_entertainment_usage * 0.2
        + mood_component * 0.1
    )

    return {
        'score': round(max(0.0, min(100.0, score)), 1),
        'components': {
            'focus_hours': round(float(focus_hours or 0.0), 2),
            'focus_component': round(focus_component, 1),
            'task_completion_rate': round(task_component, 1),
            'low_entertainment_usage': round(low_entertainment_usage, 1),
            'mood_score_component': round(mood_component, 1),
        }
    }


def _day_screen_series(usage_rows, start_date, end_date):
    day_totals = defaultdict(int)
    for r in usage_rows:
        day_totals[r['date']] += int(r['minutes'] or 0)
    return [
        {
            'date': d.isoformat(),
            'day': d.strftime('%a'),
            'minutes': int(day_totals.get(d.isoformat(), 0)),
            'hours': round(day_totals.get(d.isoformat(), 0) / 60.0, 2),
        }
        for d in _date_range(start_date, end_date)
    ]


def _task_day_series(conn, start_date, end_date):
    c = conn.cursor()
    rows = []
    for d in _date_range(start_date, end_date):
        date_str = d.isoformat()
        dow = d.weekday()
        c.execute('SELECT COUNT(*) AS cnt FROM weekly_tasks WHERE user_id = ? AND day_of_week = ?', ('local', dow))
        planned = int(c.fetchone()['cnt'])

        c.execute(
            '''
            SELECT COUNT(*) AS cnt
            FROM daily_task_status dts
            JOIN weekly_tasks wt ON wt.id = dts.task_id
            WHERE wt.user_id = ? AND wt.day_of_week = ? AND dts.date = ? AND dts.status = 'completed'
            ''',
            ('local', dow, date_str)
        )
        completed = int(c.fetchone()['cnt'])

        rows.append({
            'date': date_str,
            'day': d.strftime('%a'),
            'planned': planned,
            'completed': completed,
            'completion_rate': round((completed / planned) * 100, 1) if planned > 0 else 0.0,
        })
    return rows


def _best_task_window(conn, start_date, end_date):
    c = conn.cursor()
    c.execute(
        '''
        SELECT SUBSTR(wt.start_time, 1, 2) AS hour_block, COUNT(*) AS completed_count
        FROM daily_task_status dts
        JOIN weekly_tasks wt ON wt.id = dts.task_id
        WHERE dts.status = 'completed' AND dts.date BETWEEN ? AND ?
        GROUP BY hour_block
        ORDER BY completed_count DESC
        LIMIT 1
        ''',
        (start_date.isoformat(), end_date.isoformat())
    )
    row = c.fetchone()
    if not row or not row['hour_block']:
        return None
    h = int(row['hour_block'])
    return f"{h:02d}:00-{(h + 3) % 24:02d}:00"


def _generate_ai_insights(screen_series, app_stats, task_window, task_stats, mood_summary, productivity_score):
    insights = []
    insights.append(
        f"You spent {app_stats['entertainment_pct']}% of your screen time on entertainment/social apps this period."
    )

    if task_window:
        insights.append(f"You complete most tasks between {task_window}.")

    low_days = [d for d in screen_series if d['hours'] < 4.0]
    high_days = [d for d in screen_series if d['hours'] >= 4.0]
    if low_days and high_days:
        low_avg = sum(d['hours'] for d in low_days) / len(low_days)
        high_avg = sum(d['hours'] for d in high_days) / len(high_days)
        if low_avg < high_avg:
            insights.append("Your productivity increases when daily screen time is below 4 hours.")

    if float(mood_summary.get('average_mood', 0) or 0) < 3.0:
        insights.append("Mood scores dipped below neutral. Add shorter focus blocks and a recovery break in the evening.")

    insights.append(
        f"Current productivity score is {productivity_score['score']}/100 with task completion at {task_stats['completion_rate']}%."
    )
    return insights


def _build_report_payload(period_days=7):
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=period_days - 1)
    conn = get_db_connection()
    try:
        usage_rows = _usage_rows_for_period(conn, start_date, end_date)
        app_stats = _app_usage_stats(usage_rows)
        task_stats = _compute_task_completion(conn, start_date, end_date)
        focus_stats = _focus_stats(conn, start_date, end_date)
        mood_summary = _get_mood_period_summary(conn, start_date, end_date)
        screen_series = _day_screen_series(usage_rows, start_date, end_date)
        task_series = _task_day_series(conn, start_date, end_date)
        task_window = _best_task_window(conn, start_date, end_date)
        heatmap = analytics_service.get_heatmap(user_id='local', days=min(period_days, 31))

        c = conn.cursor()
        c.execute(
            'SELECT COUNT(*) AS cnt FROM therapy_sessions WHERE DATE(started_at) BETWEEN ? AND ?',
            (start_date.isoformat(), end_date.isoformat())
        )
        therapy_sessions = int(c.fetchone()['cnt'] or 0)

        c.execute(
            'SELECT COUNT(*) AS cnt FROM therapy_sessions'
        )
        therapy_total = int(c.fetchone()['cnt'] or 0)

        productivity = _productivity_score_v2(
            focus_hours=focus_stats['period_hours'],
            task_completion_rate=task_stats['completion_rate'],
            entertainment_pct=app_stats['entertainment_pct'],
            average_mood=mood_summary['average_mood'],
        )

        insights = _generate_ai_insights(
            screen_series=screen_series,
            app_stats=app_stats,
            task_window=task_window,
            task_stats=task_stats,
            mood_summary=mood_summary,
            productivity_score=productivity,
        )

        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': period_days,
            },
            'totals': {
                'screen_time_minutes': app_stats['total_minutes'],
                'screen_time_hours': app_stats['total_hours'],
                'focus_hours': focus_stats['period_hours'],
                'focus_sessions': focus_stats['period_sessions'],
                'task_completion_rate': task_stats['completion_rate'],
                'therapy_sessions': therapy_sessions,
            },
            'usage': {
                'most_used_apps': app_stats['top_apps'][:5],
                'category_breakdown': app_stats['category_breakdown'],
                'most_used_app': app_stats['most_used_app'],
                'most_productive_app': app_stats['most_productive_app'],
                'most_distracting_app': app_stats['most_distracting_app'],
            },
            'mood': {
                'summary': {
                    'total_entries': mood_summary['total_entries'],
                    'average_mood_score': mood_summary['average_mood'],
                },
                'trend': mood_summary['trend'],
            },
            'planner': {
                'tasks_completed': task_stats['completed_total'],
                'tasks_planned': task_stats['planned_total'],
                'daily_completion': task_series,
                'best_task_window': task_window,
            },
            'focus_mode': {
                'total_focus_sessions': focus_stats['total_sessions'],
                'focus_hours_this_period': focus_stats['period_hours'],
                'focus_hours_total': focus_stats['total_hours'],
                'websites_blocked': focus_stats['websites_blocked'],
            },
            'cbt_activity': {
                'sessions_this_period': therapy_sessions,
                'sessions_total': therapy_total,
            },
            'productivity_score': productivity,
            'ai_insights': insights,
            'charts': {
                'screen_time_series': screen_series,
                'app_usage_pie': app_stats['category_breakdown'],
                'productivity_heatmap': heatmap,
                'task_completion_series': task_series,
                'mood_trend': mood_summary['trend'],
            }
        }
    finally:
        conn.close()

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
        return jsonify(analytics_service.get_heatmap(user_id='local', days=7))
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
# Analytics Endpoints (real usage pipeline)
# ═══════════════════════════════════
@app.route('/api/analytics/daily', methods=['GET'])
def analytics_daily():
    try:
        data = analytics_service.get_daily_usage(user_id='local')
        data['battery'] = analytics_service.get_battery_usage_summary()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analytics/weekly', methods=['GET'])
def weekly_analytics():
    try:
        weekly = analytics_service.get_weekly_usage(user_id='local', days=7)
        apps = analytics_service.get_weekly_app_usage(user_id='local', days=7)
        total_screen_time = sum(int(a.get('minutes', 0)) for a in apps)
        weekly['apps'] = apps
        weekly['total_screen_time'] = total_screen_time
        return jsonify(weekly)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analytics/heatmap', methods=['GET'])
def analytics_heatmap():
    try:
        return jsonify(analytics_service.get_heatmap(user_id='local', days=7))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analytics/top-apps', methods=['GET'])
def analytics_top_apps():
    try:
        return jsonify(analytics_service.get_top_apps(user_id='local', days=7, limit=5))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analytics/ai-insights', methods=['GET'])
def analytics_ai_insights():
    try:
        return jsonify(analytics_service.get_ai_insights(user_id='local'))
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/analytics/weekly-app-usage', methods=['GET'])
def analytics_weekly_app_usage():
    try:
        return jsonify(weekly_analytics_service.get_weekly_app_usage_report(user_id='local'))
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
    from reporter import generate_daily_report, generate_weekly_report, generate_structured_report_pdf
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
            session_name=data.get('session_name', 'Focus Session'),
            block_categories=data.get('block_categories', ['social', 'video', 'entertainment'])
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


@app.route('/api/profile/summary', methods=['GET'])
def profile_summary():
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=6)

        conn = get_db_connection()
        c = conn.cursor()

        usage_rows = _usage_rows_for_period(conn, start_date, end_date)
        app_stats = _app_usage_stats(usage_rows)
        task_stats = _compute_task_completion(conn, start_date, end_date)
        focus_stats = _focus_stats(conn, start_date, end_date)
        mood_summary = _get_mood_period_summary(conn, start_date, end_date)
        screen_series = _day_screen_series(usage_rows, start_date, end_date)
        task_series = _task_day_series(conn, start_date, end_date)

        streak_window = _compute_streak(conn, end_date, 90)
        longest_streak = _compute_streak_over_rows(streak_window.get('days', []))

        c.execute('SELECT COUNT(*) AS cnt FROM weekly_tasks WHERE user_id = ?', ('local',))
        total_tasks_created = int(c.fetchone()['cnt'] or 0)

        c.execute('SELECT COUNT(*) AS cnt FROM therapy_sessions')
        cbt_total = int(c.fetchone()['cnt'] or 0)

        c.execute(
            '''
            SELECT MIN(dt) AS first_day
            FROM (
                SELECT MIN(date) AS dt FROM app_usage_logs
                UNION ALL
                SELECT MIN(SUBSTR(date, 1, 10)) AS dt FROM mood_journal
                UNION ALL
                SELECT MIN(SUBSTR(created_at, 1, 10)) AS dt FROM weekly_tasks
            )
            WHERE dt IS NOT NULL
            '''
        )
        join_row = c.fetchone()
        join_date = join_row['first_day'] if join_row and join_row['first_day'] else end_date.isoformat()

        conn.close()

        productivity = _productivity_score_v2(
            focus_hours=focus_stats['period_hours'],
            task_completion_rate=task_stats['completion_rate'],
            entertainment_pct=app_stats['entertainment_pct'],
            average_mood=mood_summary['average_mood'],
        )

        achievements = [
            {
                'id': 'digital_detox_starter',
                'title': 'Digital Detox Starter',
                'description': 'Complete 5 focus sessions',
                'target': 5,
                'progress': focus_stats['total_sessions'],
                'unlocked': focus_stats['total_sessions'] >= 5,
            },
            {
                'id': 'consistency_master',
                'title': 'Consistency Master',
                'description': 'Reach a 7-day streak',
                'target': 7,
                'progress': streak_window.get('current_streak', 0),
                'unlocked': streak_window.get('current_streak', 0) >= 7,
            },
            {
                'id': 'deep_work_champion',
                'title': 'Deep Work Champion',
                'description': 'Log 10 focus hours',
                'target': 10,
                'progress': focus_stats['total_hours'],
                'unlocked': focus_stats['total_hours'] >= 10,
            },
            {
                'id': 'balanced_mind',
                'title': 'Balanced Mind',
                'description': 'Write 5 mood journal entries',
                'target': 5,
                'progress': mood_summary['total_entries'],
                'unlocked': mood_summary['total_entries'] >= 5,
            },
        ]

        return jsonify({
            'user_info': {
                'name': request.args.get('name', 'Arjun Reddy'),
                'email': request.args.get('email', 'arjun.reddy@digiwell.app'),
                'join_date': join_date,
                'profile_picture': request.args.get('profile_picture', 'https://ui-avatars.com/api/?name=Arjun+Reddy&background=0F172A&color=ffffff'),
            },
            'productivity_summary': {
                'average_daily_screen_time_hours': round(app_stats['total_hours'] / 7.0, 2),
                'weekly_productivity_score': productivity['score'],
                'total_focus_hours': focus_stats['total_hours'],
            },
            'streak_statistics': {
                'current_streak': streak_window.get('current_streak', 0),
                'longest_streak': longest_streak,
                'total_successful_days': streak_window.get('monthly_success_days', 0),
            },
            'task_completion_stats': {
                'total_tasks_created': total_tasks_created,
                'tasks_completed_this_week': task_stats['completed_total'],
                'weekly_completion_percentage': task_stats['completion_rate'],
            },
            'focus_mode_stats': {
                'total_focus_sessions': focus_stats['total_sessions'],
                'websites_blocked': focus_stats['websites_blocked'],
                'focus_hours_this_week': focus_stats['period_hours'],
            },
            'mood_journal_summary': {
                'total_journal_entries': mood_summary['total_entries'],
                'average_mood_score': mood_summary['average_mood'],
                'mood_trend_graph': mood_summary['trend'],
            },
            'app_usage_summary': {
                'most_used_app': app_stats['most_used_app'],
                'most_productive_app': app_stats['most_productive_app'],
                'most_distracting_app': app_stats['most_distracting_app'],
            },
            'achievements': achievements,
            'cbt_activity': {
                'total_sessions': cbt_total,
            },
            'charts': {
                'weekly_screen_time_graph': screen_series,
                'task_completion_graph': task_series,
                'mood_trend_line_chart': mood_summary['trend'],
            },
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/weekly', methods=['GET'])
def weekly_report():
    try:
        fmt = (request.args.get('format') or 'json').strip().lower()
        if fmt == 'pdf':
            payload = _build_report_payload(period_days=7)
            payload['report_type'] = 'weekly'
            result = generate_structured_report_pdf(payload, period='weekly')
            if 'error' in result:
                return jsonify(result), 400
            return send_file(result['filepath'], as_attachment=True,
                             download_name=result['filename'], mimetype='application/pdf')

        payload = _build_report_payload(period_days=7)
        payload['report_type'] = 'weekly'
        if request.args.get('download') == '1':
            filename = f"digiwell_weekly_report_{datetime.utcnow().strftime('%Y%m%d')}.json"
            response = app.response_class(
                response=json.dumps(payload, indent=2),
                mimetype='application/json'
            )
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response
        return jsonify(payload)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/api/reports/monthly', methods=['GET'])
def monthly_report():
    try:
        fmt = (request.args.get('format') or 'json').strip().lower()
        payload = _build_report_payload(period_days=30)
        payload['report_type'] = 'monthly'
        conn = get_db_connection()
        streak_data = _compute_streak(conn, datetime.utcnow().date(), 90)
        conn.close()
        payload['monthly_summary'] = {
            'total_productivity_hours': payload['totals']['focus_hours'],
            'average_daily_screen_time_hours': round(payload['totals']['screen_time_hours'] / 30.0, 2),
            'longest_streak': _compute_streak_over_rows(streak_data.get('days', [])),
            'app_usage_trends': payload['charts']['screen_time_series'],
        }

        if fmt == 'pdf':
            result = generate_structured_report_pdf(payload, period='monthly')
            if 'error' in result:
                return jsonify(result), 400
            return send_file(result['filepath'], as_attachment=True,
                             download_name=result['filename'], mimetype='application/pdf')

        if request.args.get('download') == '1':
            filename = f"digiwell_monthly_report_{datetime.utcnow().strftime('%Y%m%d')}.json"
            response = app.response_class(
                response=json.dumps(payload, indent=2),
                mimetype='application/json'
            )
            response.headers['Content-Disposition'] = f'attachment; filename={filename}'
            return response

        return jsonify(payload)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/productivity-score', methods=['GET'])
def reports_productivity_score():
    try:
        period = (request.args.get('period') or 'weekly').strip().lower()
        days = 30 if period == 'monthly' else 7
        payload = _build_report_payload(period_days=days)
        return jsonify({
            'period': period,
            'formula': '( focus_hours * 0.4 ) + ( task_completion_rate * 0.3 ) + ( low_entertainment_usage * 0.2 ) + ( mood_score * 0.1 )',
            'score': payload['productivity_score']['score'],
            'components': payload['productivity_score']['components'],
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Ollama AI Chatbot ─────────────────────────────────

@app.route('/api/chat', methods=['POST'])
def digiwell_chat():
    try:
        data = request.get_json(silent=True) or {}
        user_message = str(data.get('message', '')).strip()
        if not user_message:
            return jsonify({"error": "Missing 'message' in request body"}), 400

        force_refresh = bool(data.get('refresh_context', False))
        chat_context = _build_chatbot_data_context(force_refresh=force_refresh)
        context_json = _truncate_text(json.dumps(chat_context, ensure_ascii=True, indent=2), max_chars=16000)

        system_prompt = f"""
You are DigiWell, a digital wellness coach and planning assistant.

You have access to ALL available internal data in the JSON block below (database tables, analytics, mood, focus, tasks, usage, and data folder files).
Use this as the source of truth.

INTERNAL_DATA_CONTEXT_JSON:
{context_json}

Guidelines:
1. Ground every answer in the provided data context. If something is missing in context, say that clearly.
2. Be concise, warm, and specific. Max 4 sentences unless the user asks for deeper detail.
3. Do NOT recommend cutting productive tooling usage (development, study, work apps) unless the user explicitly asks.
4. Prioritize concrete action steps tied to the user's real usage patterns, focus sessions, mood trends, and task completion data.
"""

        full_prompt = f"{system_prompt}\n\nUser: {user_message}\nDigiWell:".strip()
        
        try:
            ollama_response = requests.post(
                "http://localhost:11434/api/generate", 
                json={
                    "model": "gemma3:1b",
                    "prompt": full_prompt, 
                    "stream": False
                },
                timeout=30
            )
            ollama_response.raise_for_status()
            reply = ollama_response.json().get("response", "I couldn't generate a response.")
        except requests.exceptions.RequestException as req_err:
            print(f"Ollama connection error: {req_err}")
            totals = chat_context.get('report_summaries', {}).get('weekly', {}).get('totals', {})
            weekly_hours = float(totals.get('screen_time_hours') or 0.0)
            reply = (
                "I'm having trouble connecting to my local AI brain (Ollama). "
                "Please ensure it's running locally on port 11434.\n\n"
                f"Fallback insight from your full data context: this week shows about {weekly_hours:.2f} hours of screen time. "
                "Try one focused 25-minute block right now and avoid your top distracting app during that block."
            )

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

from ai_service import analyze_journal, predict_relapse, coach_agent_step
import uuid

@app.route('/api/analytics', methods=['POST'])
def log_analytics():
    try:
        data = request.get_json()
        event_name = data.get('event_name')
        user_id = data.get('user_id', 'local')
        metadata = data.get('metadata', {})
        
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO analytics (event_name, user_id, metadata)
            VALUES (?, ?, ?)
        ''', (event_name, user_id, json.dumps(metadata)))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "logged"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
        user_message = data.get('message', '')
        chat_history = data.get('history', [])

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
        screen_time_mins = hr_seconds // 60

        response = coach_agent_step(user_message, chat_history, screen_time_mins)

        return jsonify({
            "response": response,
            "timestamp": datetime.utcnow().isoformat()
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


# ═══════════════════════════════════
# Desktop Screen Usage Monitoring APIs
# ═══════════════════════════════════
@app.route('/api/usage/daily', methods=['GET'])
def get_daily_usage():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # We define "daily" as today based on timestamp.
        # Alternatively we can extract the date from timestamp
        # and match today's date.
        today = datetime.now().strftime('%Y-%m-%d')
        
        c.execute('''
            SELECT 
                SUM(duration_seconds) as total_seconds,
                SUM(CASE WHEN category IN ('social', 'entertainment') THEN duration_seconds ELSE 0 END) as distracted_time,
                SUM(CASE WHEN category IN ('productivity', 'development', 'work') THEN duration_seconds ELSE 0 END) as productivity_time
            FROM screen_usage
            WHERE date(timestamp) = ?
        ''', (today,))
        
        row = c.fetchone()
        
        c.execute('''
            SELECT app_name, SUM(duration_seconds) as total_seconds
            FROM screen_usage
            WHERE date(timestamp) = ?
            GROUP BY app_name
            ORDER BY total_seconds DESC
            LIMIT 10
        ''', (today,))
        
        top_apps = [{"app_name": r["app_name"], "total_seconds": r["total_seconds"]} for r in c.fetchall()]
        
        c.execute("SELECT COUNT(*) as count FROM focus_sessions WHERE date(start_ts) = ?", (today,))
        focus_count = c.fetchone()["count"]
        
        conn.close()
        
        total = row["total_seconds"] or 0
        return jsonify({
            "total_screen_time_seconds": total,
            "social_media_time_seconds": row["distracted_time"] or 0,
            "productivity_time_seconds": row["productivity_time"] or 0,
            "focus_sessions_count": focus_count,
            "top_apps": top_apps
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/usage/hourly', methods=['GET'])
def get_hourly_usage():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        today = datetime.now().strftime('%Y-%m-%d')
        
        c.execute('''
            SELECT strftime('%H', timestamp) as hour, SUM(duration_seconds) as total_seconds
            FROM screen_usage
            WHERE date(timestamp) = ?
            GROUP BY hour
            ORDER BY hour ASC
        ''', (today,))
        
        hourly_data = [{"hour": int(r["hour"]), "total_seconds": r["total_seconds"]} for r in c.fetchall()]
        
        conn.close()
        return jsonify(hourly_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def start_screen_monitor_background():
    try:
        from agent.app_usage_tracker import AppUsageTracker
        import threading
        
        def run_monitor():
            tracker = AppUsageTracker(user_id='local', poll_seconds=5)
            tracker.run()
            
        monitor_thread = threading.Thread(target=run_monitor, daemon=True)
        monitor_thread.start()
        print("Started app usage tracker service in background")
    except Exception as e:
        print(f"Failed to start screen monitor: {e}")

# ── Weekly Timetable / Planner ────────────────────────────────────────

import uuid
from datetime import datetime, timedelta, date


def ensure_default_timetable(conn, c):
    # Try to reuse an existing timetable that has no slots yet.
    c.execute('''
        SELECT wt.id
        FROM weekly_timetable wt
        LEFT JOIN weekly_timetable_slots ws ON ws.timetable_id = wt.id
        WHERE wt.user_id = ?
        GROUP BY wt.id
        HAVING COUNT(ws.id) = 0
        ORDER BY wt.created_at DESC
        LIMIT 1
    ''', ('local',))
    empty_table = c.fetchone()

    if empty_table:
        timetable_id = empty_table['id']
        c.execute(
            'UPDATE weekly_timetable SET name = ?, timezone = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            ('Temporary Weekly Plan', 'UTC', timetable_id)
        )
    else:
        c.execute('SELECT COUNT(*) AS cnt FROM weekly_timetable WHERE user_id = ?', ('local',))
        row = c.fetchone()
        count = row['cnt'] if row else 0
        if count > 0:
            return

        timetable_id = uuid.uuid4().hex[:8]
        c.execute(
            'INSERT INTO weekly_timetable (id, user_id, name, timezone) VALUES (?, ?, ?, ?)',
            (timetable_id, 'local', 'Temporary Weekly Plan', 'UTC')
        )

    # One practical slot per weekday and a lighter weekend schedule.
    default_slots = [
        (0, '09:00', '10:00', 'Deep Work Sprint', 'Focused work block', 'deep_work', 1),
        (1, '18:00', '18:45', 'Exercise', 'Quick workout and stretch', 'exercise', 0),
        (2, '20:00', '20:30', 'Reading Session', 'Read or learn new topic', 'study', 0),
        (3, '09:00', '10:00', 'Project Work', 'Progress on key project', 'deep_work', 1),
        (4, '17:30', '18:00', 'Weekly Wrap-Up', 'Review wins and pending items', 'chores', 0),
        (5, '10:00', '11:00', 'Personal Growth', 'Skill-building time', 'study', 0),
        (6, '19:00', '19:30', 'Plan Next Week', 'Prepare schedule and priorities', 'chores', 0),
    ]

    for day_of_week, start_time, end_time, title, description, category, focus_mode in default_slots:
        c.execute(
            '''
            INSERT INTO weekly_timetable_slots
            (id, timetable_id, day_of_week, start_time, end_time, title, description, category, focus_mode)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                uuid.uuid4().hex[:8],
                timetable_id,
                day_of_week,
                start_time,
                end_time,
                title,
                description,
                category,
                focus_mode,
            )
        )

    conn.commit()

@app.route('/api/timetable', methods=['GET'])
def list_timetables():
    try:
        conn = get_db_connection()
        c = conn.cursor()
        ensure_default_timetable(conn, c)
        c.execute('SELECT * FROM weekly_timetable WHERE user_id = ?', ('local',))
        tables = [dict(row) for row in c.fetchall()]
        
        for t in tables:
            c.execute('SELECT * FROM weekly_timetable_slots WHERE timetable_id = ? ORDER BY day_of_week, start_time', (t['id'],))
            t['slots'] = [dict(row) for row in c.fetchall()]

        # Keep populated plans first so UI opens with a usable timetable.
        tables.sort(key=lambda t: len(t.get('slots', [])), reverse=True)
            
        conn.close()
        return jsonify(tables)
    except Exception as e:
        return jsonify(error=str(e)), 500

@app.route('/api/timetable', methods=['POST'])
def create_timetable():
    try:
        data = request.json or {}
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
        c.execute('''
            INSERT INTO weekly_timetable_slots 
            (id, timetable_id, day_of_week, start_time, end_time, title, description, category, focus_mode, completed, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            s_id, t_id, data.get('day_of_week'), data.get('start_time'), data.get('end_time'),
            data.get('title'), data.get('description', ''), data.get('category'), bool(data.get('focus_mode', False)),
            bool(data.get('completed', False)),
            datetime.utcnow().isoformat() if bool(data.get('completed', False)) else None
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
            completed = bool(data.get('completed', False))
            completed_at = data.get('completed_at')
            if completed and not completed_at:
                completed_at = datetime.utcnow().isoformat()
            if not completed:
                completed_at = None
            c.execute('''
                UPDATE weekly_timetable_slots SET 
                day_of_week = ?, start_time = ?, end_time = ?, title = ?, 
                description = ?, category = ?, focus_mode = ?, completed = ?, completed_at = ?
                WHERE id = ?
            ''', (
                data.get('day_of_week'), data.get('start_time'), data.get('end_time'),
                data.get('title'), data.get('description', ''), data.get('category'), 
                bool(data.get('focus_mode', False)), completed, completed_at, s_id
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
            
            c.execute('''
                INSERT INTO daily_tasks 
                (id, date, slot_id, planned_start, planned_end, title, description, category, duration_planned_minutes, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
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
        c.execute('''
            INSERT INTO adherence_reports 
            (id, date, planned_total_minutes, actual_total_minutes, completed_tasks, scheduled_tasks, adherence_score)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (rep_id, target_date, planned_tot, actual_tot, comp_count, sched_count, score))
        
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


# ── Weekly Planning + Daily Execution v2 ─────────────────────────────

VALID_TASK_CATEGORIES = {'Health', 'Study', 'Work', 'Mindfulness', 'Break'}
VALID_PRIORITIES = {'Low', 'Medium', 'High'}
VALID_DAILY_STATUS = {'pending', 'completed', 'skipped'}

DAY_NAME_TO_INT = {
    'Monday': 0,
    'Tuesday': 1,
    'Wednesday': 2,
    'Thursday': 3,
    'Friday': 4,
    'Saturday': 5,
    'Sunday': 6,
}

DEMO_WEEKLY_PLAN = [
    {
        'day_of_week': 'Monday',
        'tasks': [
            {'task_title': 'Morning Workout', 'start_time': '06:30', 'end_time': '07:00', 'category': 'Health', 'priority': 'High'},
            {'task_title': 'Study Machine Learning', 'start_time': '09:00', 'end_time': '11:00', 'category': 'Study', 'priority': 'High'},
            {'task_title': 'College Classes', 'start_time': '11:30', 'end_time': '15:30', 'category': 'Work', 'priority': 'High'},
            {'task_title': 'Project Development', 'start_time': '16:30', 'end_time': '18:00', 'category': 'Work', 'priority': 'Medium'},
            {'task_title': 'Meditation', 'start_time': '21:00', 'end_time': '21:15', 'category': 'Mindfulness', 'priority': 'Medium'},
        ],
    },
    {
        'day_of_week': 'Tuesday',
        'tasks': [
            {'task_title': 'Morning Run', 'start_time': '06:30', 'end_time': '07:00', 'category': 'Health', 'priority': 'High'},
            {'task_title': 'Deep Work Coding', 'start_time': '09:00', 'end_time': '11:30', 'category': 'Study', 'priority': 'High'},
            {'task_title': 'College Classes', 'start_time': '11:30', 'end_time': '15:30', 'category': 'Work', 'priority': 'High'},
            {'task_title': 'Hackathon Preparation', 'start_time': '17:00', 'end_time': '18:30', 'category': 'Study', 'priority': 'High'},
            {'task_title': 'Reading Book', 'start_time': '21:00', 'end_time': '21:30', 'category': 'Mindfulness', 'priority': 'Low'},
        ],
    },
    {
        'day_of_week': 'Wednesday',
        'tasks': [
            {'task_title': 'Stretching & Yoga', 'start_time': '06:30', 'end_time': '07:00', 'category': 'Health', 'priority': 'Medium'},
            {'task_title': 'AI Research Study', 'start_time': '09:00', 'end_time': '11:00', 'category': 'Study', 'priority': 'High'},
            {'task_title': 'College Classes', 'start_time': '11:30', 'end_time': '15:30', 'category': 'Work', 'priority': 'High'},
            {'task_title': 'Build Project Features', 'start_time': '16:30', 'end_time': '18:30', 'category': 'Work', 'priority': 'High'},
            {'task_title': 'Evening Walk', 'start_time': '20:30', 'end_time': '21:00', 'category': 'Health', 'priority': 'Low'},
        ],
    },
    {
        'day_of_week': 'Thursday',
        'tasks': [
            {'task_title': 'Morning Jog', 'start_time': '06:30', 'end_time': '07:00', 'category': 'Health', 'priority': 'Medium'},
            {'task_title': 'Practice Data Structures', 'start_time': '09:00', 'end_time': '11:00', 'category': 'Study', 'priority': 'High'},
            {'task_title': 'College Classes', 'start_time': '11:30', 'end_time': '15:30', 'category': 'Work', 'priority': 'High'},
            {'task_title': 'Work on CBT Feature', 'start_time': '16:30', 'end_time': '18:00', 'category': 'Work', 'priority': 'Medium'},
            {'task_title': 'Meditation', 'start_time': '21:00', 'end_time': '21:15', 'category': 'Mindfulness', 'priority': 'Medium'},
        ],
    },
    {
        'day_of_week': 'Friday',
        'tasks': [
            {'task_title': 'Morning Workout', 'start_time': '06:30', 'end_time': '07:00', 'category': 'Health', 'priority': 'High'},
            {'task_title': 'AI Model Experiment', 'start_time': '09:00', 'end_time': '11:30', 'category': 'Study', 'priority': 'High'},
            {'task_title': 'College Classes', 'start_time': '11:30', 'end_time': '15:30', 'category': 'Work', 'priority': 'High'},
            {'task_title': 'Hackathon Project Work', 'start_time': '16:30', 'end_time': '18:30', 'category': 'Work', 'priority': 'High'},
            {'task_title': 'Relax & Music', 'start_time': '21:00', 'end_time': '21:30', 'category': 'Break', 'priority': 'Low'},
        ],
    },
    {
        'day_of_week': 'Saturday',
        'tasks': [
            {'task_title': 'Morning Walk', 'start_time': '07:00', 'end_time': '07:30', 'category': 'Health', 'priority': 'Medium'},
            {'task_title': 'Side Project Development', 'start_time': '10:00', 'end_time': '12:00', 'category': 'Work', 'priority': 'High'},
            {'task_title': 'Learning New AI Concept', 'start_time': '14:00', 'end_time': '16:00', 'category': 'Study', 'priority': 'Medium'},
            {'task_title': 'Gym Session', 'start_time': '18:00', 'end_time': '19:00', 'category': 'Health', 'priority': 'High'},
            {'task_title': 'Movie / Relaxation', 'start_time': '21:00', 'end_time': '23:00', 'category': 'Break', 'priority': 'Low'},
        ],
    },
    {
        'day_of_week': 'Sunday',
        'tasks': [
            {'task_title': 'Late Morning Walk', 'start_time': '08:00', 'end_time': '08:30', 'category': 'Health', 'priority': 'Low'},
            {'task_title': 'Weekly Review & Planning', 'start_time': '10:00', 'end_time': '11:00', 'category': 'Work', 'priority': 'High'},
            {'task_title': 'Family / Social Time', 'start_time': '12:00', 'end_time': '14:00', 'category': 'Break', 'priority': 'Medium'},
            {'task_title': 'Read Personal Development Book', 'start_time': '17:00', 'end_time': '18:00', 'category': 'Mindfulness', 'priority': 'Medium'},
            {'task_title': 'Prepare Tasks for Next Week', 'start_time': '20:30', 'end_time': '21:00', 'category': 'Work', 'priority': 'Medium'},
        ],
    },
]


def _seed_demo_weekly_plan(conn, replace=False):
    c = conn.cursor()
    c.execute('SELECT COUNT(*) AS cnt FROM weekly_tasks WHERE user_id = ?', ('local',))
    existing = c.fetchone()['cnt']
    if existing > 0 and not replace:
        return 0

    if replace:
        c.execute('SELECT id FROM weekly_tasks WHERE user_id = ?', ('local',))
        task_ids = [row['id'] for row in c.fetchall()]
        if task_ids:
            marks = ','.join(['?'] * len(task_ids))
            c.execute(f'DELETE FROM daily_task_status WHERE task_id IN ({marks})', tuple(task_ids))
        c.execute('DELETE FROM weekly_tasks WHERE user_id = ?', ('local',))

    inserted = 0
    for day_bucket in DEMO_WEEKLY_PLAN:
        day = DAY_NAME_TO_INT.get(day_bucket['day_of_week'])
        if day is None:
            continue
        for idx, task in enumerate(day_bucket['tasks']):
            c.execute('''
                INSERT INTO weekly_tasks
                (id, user_id, day_of_week, task_title, task_description, start_time, end_time, category, priority, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                uuid.uuid4().hex[:8],
                'local',
                day,
                task.get('task_title', 'Untitled Task'),
                task.get('task_description', ''),
                task.get('start_time', '09:00'),
                task.get('end_time', '10:00'),
                task.get('category', 'Work'),
                task.get('priority', 'Medium'),
                idx,
            ))
            inserted += 1

    conn.commit()
    return inserted


def _clear_weekly_tasks(conn):
    c = conn.cursor()
    c.execute('SELECT id FROM weekly_tasks WHERE user_id = ?', ('local',))
    task_ids = [row['id'] for row in c.fetchall()]
    if task_ids:
        marks = ','.join(['?'] * len(task_ids))
        c.execute(f'DELETE FROM daily_task_status WHERE task_id IN ({marks})', tuple(task_ids))
    c.execute('DELETE FROM weekly_tasks WHERE user_id = ?', ('local',))


def _generate_smart_weekly_plan(conn, replace=True):
    c = conn.cursor()

    best_hour = 9
    c.execute('''
        SELECT CAST(SUBSTR(wt.start_time, 1, 2) AS INTEGER) AS hour_block, COUNT(*) AS completed_count
        FROM daily_task_status dts
        JOIN weekly_tasks wt ON wt.id = dts.task_id
        WHERE dts.status = 'completed'
        GROUP BY hour_block
        ORDER BY completed_count DESC
        LIMIT 1
    ''')
    row = c.fetchone()
    if row and row['hour_block'] is not None:
        best_hour = int(row['hour_block'])

    stress_day = 2  # Wednesday default
    c.execute('''
        SELECT CAST(strftime('%w', SUBSTR(date,1,10)) AS INTEGER) AS weekday, AVG(mood_score) AS avg_mood
        FROM mood_journal
        WHERE date IS NOT NULL
        GROUP BY weekday
        ORDER BY avg_mood ASC
        LIMIT 1
    ''')
    mood_row = c.fetchone()
    if mood_row and mood_row['weekday'] is not None:
        # sqlite: 0=Sun..6=Sat -> convert to python 0=Mon..6=Sun
        sqlite_day = int(mood_row['weekday'])
        stress_day = (sqlite_day + 6) % 7

    if replace:
        _clear_weekly_tasks(conn)
    else:
        c.execute('SELECT COUNT(*) AS cnt FROM weekly_tasks WHERE user_id = ?', ('local',))
        if c.fetchone()['cnt'] > 0:
            return 0

    def hhmm(h, m=0):
        return f"{h:02d}:{m:02d}"

    inserted = 0
    for day in range(7):
        is_stress_day = day == stress_day
        morning_start = best_hour

        tasks = [
            {
                'task_title': 'Morning Stretch' if not is_stress_day else 'Breathing + Stretch',
                'task_description': 'Start the day with movement and breath.',
                'start_time': hhmm(6, 30),
                'end_time': hhmm(7, 0),
                'category': 'Health',
                'priority': 'Medium' if is_stress_day else 'High',
            },
            {
                'task_title': 'Deep Work Sprint',
                'task_description': 'Focus block aligned to your productive window.',
                'start_time': hhmm(morning_start, 0),
                'end_time': hhmm(min(morning_start + 2, 23), 0),
                'category': 'Study',
                'priority': 'High',
            },
            {
                'task_title': 'Primary Work Block',
                'task_description': 'Main execution block for top priorities.',
                'start_time': hhmm(11, 30),
                'end_time': hhmm(15, 0),
                'category': 'Work',
                'priority': 'High',
            },
            {
                'task_title': 'Mindfulness Reset' if is_stress_day else 'Project Build Session',
                'task_description': 'Short reset or focused build based on stress trend.',
                'start_time': hhmm(17, 0),
                'end_time': hhmm(18, 0),
                'category': 'Mindfulness' if is_stress_day else 'Work',
                'priority': 'Medium',
            },
            {
                'task_title': 'Digital Detox Hour',
                'task_description': 'Offline wind-down to reduce late-night doomscrolling.',
                'start_time': hhmm(21, 0),
                'end_time': hhmm(22, 0),
                'category': 'Break',
                'priority': 'Low',
            },
        ]

        for idx, task in enumerate(tasks):
            c.execute('''
                INSERT INTO weekly_tasks
                (id, user_id, day_of_week, task_title, task_description, start_time, end_time, category, priority, sort_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                uuid.uuid4().hex[:8],
                'local',
                day,
                task['task_title'],
                task['task_description'],
                task['start_time'],
                task['end_time'],
                task['category'],
                task['priority'],
                idx,
            ))
            inserted += 1

    conn.commit()
    return inserted


def _parse_date_yyyy_mm_dd(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').date()


def _safe_date_from_query(param_name, default_date):
    val = request.args.get(param_name)
    if not val:
        return default_date
    return _parse_date_yyyy_mm_dd(val)


def _daterange(start_date, end_date):
    cur = start_date
    while cur <= end_date:
        yield cur
        cur += timedelta(days=1)


def _day_metrics(conn, target_date):
    date_str = target_date.strftime('%Y-%m-%d')
    dow = target_date.weekday()
    c = conn.cursor()

    c.execute('SELECT COUNT(*) AS cnt FROM weekly_tasks WHERE user_id = ? AND day_of_week = ?', ('local', dow))
    planned = c.fetchone()['cnt']

    c.execute('''
        SELECT COUNT(*) AS cnt
        FROM daily_task_status dts
        JOIN weekly_tasks wt ON wt.id = dts.task_id
        WHERE wt.user_id = ? AND wt.day_of_week = ? AND dts.date = ? AND dts.status = 'completed'
    ''', ('local', dow, date_str))
    completed = c.fetchone()['cnt']

    c.execute('''
        SELECT COUNT(*) AS cnt
        FROM daily_task_status dts
        JOIN weekly_tasks wt ON wt.id = dts.task_id
        WHERE wt.user_id = ? AND wt.day_of_week = ? AND dts.date = ? AND dts.status = 'skipped'
    ''', ('local', dow, date_str))
    skipped = c.fetchone()['cnt']

    execution_rate = round((completed / planned) * 100, 1) if planned > 0 else 0.0
    success = planned > 0 and (completed / planned) >= 0.7
    return {
        'date': date_str,
        'planned': planned,
        'completed': completed,
        'skipped': skipped,
        'execution_rate': execution_rate,
        'success': success,
    }


def _compute_streak(conn, end_date, days=30):
    start_date = end_date - timedelta(days=days - 1)
    day_rows = []
    for d in _daterange(start_date, end_date):
        day_rows.append(_day_metrics(conn, d))

    current_streak = 0
    for row in reversed(day_rows):
        if row['success']:
            current_streak += 1
        else:
            break

    weekly_success_days = sum(1 for r in day_rows[-7:] if r['success']) if day_rows else 0
    monthly_success_days = sum(1 for r in day_rows if r['success'])

    return {
        'current_streak': current_streak,
        'weekly_success_days': weekly_success_days,
        'monthly_success_days': monthly_success_days,
        'threshold_percent': 70,
        'days': day_rows,
    }


@app.route('/api/weekly-plan/tasks', methods=['GET'])
def list_weekly_plan_tasks():
    try:
        day_of_week = request.args.get('day_of_week')
        conn = get_db_connection()
        c = conn.cursor()
        _seed_demo_weekly_plan(conn, replace=False)
        if day_of_week is None:
            c.execute('''
                SELECT * FROM weekly_tasks
                WHERE user_id = ?
                ORDER BY day_of_week ASC, sort_order ASC, start_time ASC
            ''', ('local',))
        else:
            c.execute('''
                SELECT * FROM weekly_tasks
                WHERE user_id = ? AND day_of_week = ?
                ORDER BY sort_order ASC, start_time ASC
            ''', ('local', int(day_of_week)))

        tasks = [dict(r) for r in c.fetchall()]
        conn.close()
        return jsonify(tasks)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/weekly-plan/seed-demo', methods=['POST'])
def seed_demo_weekly_plan():
    try:
        data = request.json or {}
        replace = bool(data.get('replace', True))
        conn = get_db_connection()
        inserted = _seed_demo_weekly_plan(conn, replace=replace)
        conn.close()
        return jsonify(status='seeded', inserted=inserted, replace=replace)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/weekly-plan/generate-smart', methods=['POST'])
def generate_smart_weekly_plan():
    try:
        data = request.json or {}
        replace = bool(data.get('replace', True))
        conn = get_db_connection()
        inserted = _generate_smart_weekly_plan(conn, replace=replace)
        conn.close()
        return jsonify(status='generated', inserted=inserted, replace=replace)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/planner/habit-recommendations', methods=['GET'])
def get_habit_recommendations():
    try:
        conn = get_db_connection()
        c = conn.cursor()

        c.execute('SELECT AVG(seconds) AS avg_seconds FROM usage_logs')
        row = c.fetchone()
        avg_screen_hours = round((float(row['avg_seconds']) / 3600.0), 2) if row and row['avg_seconds'] is not None else 0.0

        c.execute('SELECT AVG(mood_score) AS avg_mood FROM mood_journal')
        mood_row = c.fetchone()
        avg_mood = round(float(mood_row['avg_mood']), 2) if mood_row and mood_row['avg_mood'] is not None else 3.5

        c.execute('''
            SELECT COUNT(*) AS skipped
            FROM daily_task_status
            WHERE status = 'skipped' AND date >= date('now', '-14 day')
        ''')
        skip_row = c.fetchone()
        skipped_recent = int(skip_row['skipped']) if skip_row else 0

        cards = []
        if avg_screen_hours > 5:
            cards.append({'title': 'Outdoor Walk', 'duration_minutes': 20, 'category': 'Health', 'reason': 'Screen time is high. Short outdoor movement improves recovery.'})
            cards.append({'title': 'Digital Detox Hour', 'duration_minutes': 60, 'category': 'Break', 'reason': 'Frequent late usage detected. Add an offline block in the evening.'})
        if avg_mood < 3:
            cards.append({'title': 'Breathing Exercise', 'duration_minutes': 5, 'category': 'Mindfulness', 'reason': 'Mood trend shows stress. Add a short regulation break.'})
            cards.append({'title': 'Evening Reflection', 'duration_minutes': 10, 'category': 'Mindfulness', 'reason': 'Journaling can stabilize mood and improve follow-through.'})
        if skipped_recent >= 5:
            cards.append({'title': 'Focus Sprint', 'duration_minutes': 25, 'category': 'Study', 'reason': 'Recent skipped tasks detected. Start with short, high-success focus blocks.'})

        if not cards:
            cards = [
                {'title': 'Morning Stretch', 'duration_minutes': 15, 'category': 'Health', 'reason': 'Build a reliable anchor habit each morning.'},
                {'title': 'Deep Work Block', 'duration_minutes': 90, 'category': 'Work', 'reason': 'Keep one protected high-value work block daily.'},
                {'title': 'Evening Reflection', 'duration_minutes': 10, 'category': 'Mindfulness', 'reason': 'Review wins and reset next-day priorities.'},
            ]

        conn.close()
        return jsonify(
            avg_screen_time_hours=avg_screen_hours,
            avg_mood=avg_mood,
            skipped_recent=skipped_recent,
            cards=cards,
        )
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/weekly-plan/tasks', methods=['POST'])
def create_weekly_plan_task():
    try:
        data = request.json or {}
        day_of_week = int(data.get('day_of_week', 0))
        category = data.get('category', 'Work')
        priority = data.get('priority', 'Medium')

        if category not in VALID_TASK_CATEGORIES:
            category = 'Work'
        if priority not in VALID_PRIORITIES:
            priority = 'Medium'

        conn = get_db_connection()
        c = conn.cursor()

        if 'sort_order' in data and data.get('sort_order') is not None:
            sort_order = int(data.get('sort_order'))
        else:
            c.execute('SELECT COALESCE(MAX(sort_order), -1) + 1 AS next_order FROM weekly_tasks WHERE user_id = ? AND day_of_week = ?', ('local', day_of_week))
            sort_order = c.fetchone()['next_order']

        task_id = uuid.uuid4().hex[:8]
        c.execute('''
            INSERT INTO weekly_tasks
            (id, user_id, day_of_week, task_title, task_description, start_time, end_time, category, priority, sort_order)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            task_id,
            'local',
            day_of_week,
            data.get('task_title', 'Untitled Task'),
            data.get('task_description', ''),
            data.get('start_time', '09:00'),
            data.get('end_time', '10:00'),
            category,
            priority,
            sort_order,
        ))
        conn.commit()
        conn.close()
        return jsonify(id=task_id, status='created')
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/weekly-plan/tasks/<task_id>', methods=['PUT', 'DELETE'])
def modify_weekly_plan_task(task_id):
    try:
        conn = get_db_connection()
        c = conn.cursor()
        if request.method == 'DELETE':
            c.execute('DELETE FROM daily_task_status WHERE task_id = ?', (task_id,))
            c.execute('DELETE FROM weekly_tasks WHERE id = ? AND user_id = ?', (task_id, 'local'))
            conn.commit()
            conn.close()
            return jsonify(status='deleted')

        data = request.json or {}
        category = data.get('category')
        if category not in VALID_TASK_CATEGORIES:
            category = 'Work'
        priority = data.get('priority')
        if priority not in VALID_PRIORITIES:
            priority = 'Medium'

        c.execute('''
            UPDATE weekly_tasks
            SET day_of_week = ?,
                task_title = ?,
                task_description = ?,
                start_time = ?,
                end_time = ?,
                category = ?,
                priority = ?,
                sort_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (
            int(data.get('day_of_week', 0)),
            data.get('task_title', 'Untitled Task'),
            data.get('task_description', ''),
            data.get('start_time', '09:00'),
            data.get('end_time', '10:00'),
            category,
            priority,
            int(data.get('sort_order', 0)),
            task_id,
            'local',
        ))
        conn.commit()
        conn.close()
        return jsonify(status='updated')
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/weekly-plan/tasks/reorder', methods=['POST'])
def reorder_weekly_plan_tasks():
    try:
        data = request.json or {}
        task_ids = data.get('task_ids', [])
        if not isinstance(task_ids, list):
            return jsonify(error='task_ids must be an array'), 400

        conn = get_db_connection()
        c = conn.cursor()
        for idx, task_id in enumerate(task_ids):
            c.execute('UPDATE weekly_tasks SET sort_order = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?', (idx, task_id, 'local'))
        conn.commit()
        conn.close()
        return jsonify(status='reordered')
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/daily-plan', methods=['GET'])
def get_daily_plan_v2():
    try:
        target_date = _safe_date_from_query('date', datetime.utcnow().date())
        date_str = target_date.strftime('%Y-%m-%d')
        day_of_week = target_date.weekday()

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            SELECT wt.*, COALESCE(dts.status, 'pending') AS status
            FROM weekly_tasks wt
            LEFT JOIN daily_task_status dts
              ON dts.task_id = wt.id AND dts.date = ?
            WHERE wt.user_id = ? AND wt.day_of_week = ?
            ORDER BY wt.sort_order ASC, wt.start_time ASC
        ''', (date_str, 'local', day_of_week))
        tasks = [dict(r) for r in c.fetchall()]

        completed = len([t for t in tasks if t['status'] == 'completed'])
        skipped = len([t for t in tasks if t['status'] == 'skipped'])
        pending = len([t for t in tasks if t['status'] == 'pending'])
        execution_rate = round((completed / len(tasks)) * 100, 1) if tasks else 0.0

        conn.close()
        return jsonify(
            date=date_str,
            day_of_week=day_of_week,
            tasks=tasks,
            summary={
                'planned': len(tasks),
                'completed': completed,
                'skipped': skipped,
                'pending': pending,
                'execution_rate': execution_rate,
            }
        )
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/daily-plan/status', methods=['POST'])
def set_daily_plan_status():
    try:
        data = request.json or {}
        task_id = data.get('task_id')
        if not task_id:
            return jsonify(error='task_id is required'), 400

        status = data.get('status', 'pending')
        if status not in VALID_DAILY_STATUS:
            return jsonify(error='invalid status'), 400

        target_date = data.get('date') or datetime.utcnow().strftime('%Y-%m-%d')
        _parse_date_yyyy_mm_dd(target_date)

        conn = get_db_connection()
        c = conn.cursor()
        row_id = uuid.uuid4().hex[:8]
        c.execute('''
            INSERT INTO daily_task_status (id, task_id, date, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(task_id, date)
            DO UPDATE SET status = excluded.status, updated_at = CURRENT_TIMESTAMP
        ''', (row_id, task_id, target_date, status))

        conn.commit()
        conn.close()
        return jsonify(status='updated', task_id=task_id, date=target_date, task_status=status)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/daily-plan/move-task', methods=['POST'])
def move_task_to_another_day():
    try:
        data = request.json or {}
        task_id = data.get('task_id')
        new_day_of_week = data.get('new_day_of_week')
        if task_id is None or new_day_of_week is None:
            return jsonify(error='task_id and new_day_of_week are required'), 400

        conn = get_db_connection()
        c = conn.cursor()
        c.execute('''
            UPDATE weekly_tasks
            SET day_of_week = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND user_id = ?
        ''', (int(new_day_of_week), task_id, 'local'))
        conn.commit()
        conn.close()
        return jsonify(status='moved')
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/planner/streak', methods=['GET'])
def get_planner_streak_v2():
    try:
        days = int(request.args.get('days', 30))
        days = max(1, min(days, 120))
        end_date = _safe_date_from_query('end_date', datetime.utcnow().date())

        conn = get_db_connection()
        streak = _compute_streak(conn, end_date, days)
        conn.close()
        return jsonify(streak)
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/planner/analysis', methods=['GET'])
def get_planner_analysis_v2():
    try:
        end_date = _safe_date_from_query('end_date', datetime.utcnow().date())
        start_date = _safe_date_from_query('start_date', end_date - timedelta(days=6))
        if start_date > end_date:
            start_date, end_date = end_date, start_date

        conn = get_db_connection()
        c = conn.cursor()

        day_breakdown = [_day_metrics(conn, d) for d in _daterange(start_date, end_date)]

        c.execute('''
            SELECT wt.task_title, COUNT(*) AS skip_count
            FROM daily_task_status dts
            JOIN weekly_tasks wt ON wt.id = dts.task_id
            WHERE dts.status = 'skipped' AND dts.date BETWEEN ? AND ?
            GROUP BY wt.id, wt.task_title
            ORDER BY skip_count DESC
            LIMIT 5
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        skipped_tasks = [dict(r) for r in c.fetchall()]

        c.execute('''
            SELECT SUBSTR(wt.start_time, 1, 2) AS hour_block, COUNT(*) AS completed_count
            FROM daily_task_status dts
            JOIN weekly_tasks wt ON wt.id = dts.task_id
            WHERE dts.status = 'completed' AND dts.date BETWEEN ? AND ?
            GROUP BY hour_block
            ORDER BY completed_count DESC
            LIMIT 1
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        productive_row = c.fetchone()
        most_productive_window = None
        if productive_row and productive_row['hour_block']:
            h = int(productive_row['hour_block'])
            most_productive_window = f"{h:02d}:00-{(h+1)%24:02d}:00"

        c.execute('''
            SELECT AVG(mood_score) AS avg_mood
            FROM mood_journal
            WHERE SUBSTR(date, 1, 10) BETWEEN ? AND ?
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        mood_row = c.fetchone()
        avg_mood = round(float(mood_row['avg_mood']), 2) if mood_row and mood_row['avg_mood'] is not None else None

        c.execute('''
            SELECT AVG(seconds) AS avg_seconds
            FROM usage_logs
            WHERE date BETWEEN ? AND ?
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        usage_row = c.fetchone()
        avg_screen_hours = round((float(usage_row['avg_seconds']) / 3600.0), 2) if usage_row and usage_row['avg_seconds'] is not None else None

        c.execute('''
            SELECT COUNT(*) AS therapy_sessions
            FROM therapy_sessions
            WHERE DATE(started_at) BETWEEN ? AND ?
        ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
        therapy_row = c.fetchone()
        therapy_sessions = therapy_row['therapy_sessions'] if therapy_row else 0

        planned_total = sum(d['planned'] for d in day_breakdown)
        completed_total = sum(d['completed'] for d in day_breakdown)
        execution_rate = round((completed_total / planned_total) * 100, 1) if planned_total > 0 else 0.0

        suggestions = []
        if planned_total > 0 and completed_total < (planned_total * 0.6):
            suggestions.append('You planned too many tasks versus completions. Try reducing daily planned load by 20-30%.')
        if avg_screen_hours is not None and avg_screen_hours > 4:
            suggestions.append('Your productivity tends to drop with higher screen time. Add an offline break before evening tasks.')
        if most_productive_window:
            suggestions.append(f'You complete most tasks around {most_productive_window}. Schedule deep work in that window.')
        if avg_mood is not None and avg_mood < 3:
            suggestions.append('Mood scores are low this week. Add mindfulness and recovery tasks in your weekly plan.')
        if therapy_sessions > 0:
            suggestions.append('Therapy engagement is active. Convert CBT micro-actions into short daily tasks for better follow-through.')

        if not suggestions:
            suggestions.append('Great consistency. Keep your current plan and increase one high-priority task next week.')

        conn.close()
        return jsonify(
            start_date=start_date.strftime('%Y-%m-%d'),
            end_date=end_date.strftime('%Y-%m-%d'),
            plan_vs_reality={
                'planned': planned_total,
                'completed': completed_total,
                'execution_rate': execution_rate,
            },
            day_breakdown=day_breakdown,
            skipped_tasks=skipped_tasks,
            most_productive_window=most_productive_window,
            avg_mood=avg_mood,
            avg_screen_time_hours=avg_screen_hours,
            therapy_sessions=therapy_sessions,
            suggestions=suggestions,
        )
    except Exception as e:
        return jsonify(error=str(e)), 500


@app.route('/api/planner/dashboard', methods=['GET'])
def get_planner_dashboard_v2():
    try:
        target_date = _safe_date_from_query('date', datetime.utcnow().date())
        conn = get_db_connection()
        today_metrics = _day_metrics(conn, target_date)
        streak = _compute_streak(conn, target_date, 30)

        week_start = target_date - timedelta(days=target_date.weekday())
        week_days = [_day_metrics(conn, week_start + timedelta(days=i)) for i in range(7)]

        conn.close()
        return jsonify(
            today=today_metrics,
            weekly_completion=week_days,
            streak={
                'current_streak': streak['current_streak'],
                'weekly_success_days': streak['weekly_success_days'],
                'monthly_success_days': streak['monthly_success_days'],
            }
        )
    except Exception as e:
        return jsonify(error=str(e)), 500


if __name__ == '__main__':
    start_screen_monitor_background()
    app.run(debug=True, port=5000)
