import sqlite3
from datetime import date
import os
import json

DB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'digiwell.db')

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            friendly_name TEXT NOT NULL,
            process_name TEXT,
            category TEXT,
            risk TEXT,
            seconds INTEGER NOT NULL,
            last_seen TEXT,
            UNIQUE(date, friendly_name)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS hourly_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            hour_str TEXT NOT NULL,
            seconds INTEGER NOT NULL,
            UNIQUE(date, hour_str)
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS interventions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            app_name TEXT NOT NULL,
            reason TEXT NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS doom_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            timestamp TEXT NOT NULL,
            risk REAL,
            action_taken TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS wellness_score (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            date TEXT NOT NULL,
            score INTEGER,
            components TEXT,
            UNIQUE(user_id, date)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS detox_challenge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            day INTEGER NOT NULL,
            task TEXT NOT NULL,
            completed BOOLEAN DEFAULT 0,
            date_completed TEXT,
            UNIQUE(user_id, day)
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS commitments (
          id TEXT PRIMARY KEY,
          user_id TEXT NOT NULL,
          challenge_id TEXT,
          title TEXT NOT NULL,
          description TEXT,
          start_ts DATETIME NOT NULL,
          end_ts DATETIME,
          expected_duration_minutes INT,
          auto_start_focus BOOLEAN DEFAULT 0,
          reminder_interval_minutes INT,
          status TEXT DEFAULT 'active',
          metadata JSON,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS focus_sessions (
          id TEXT PRIMARY KEY,
          commitment_id TEXT,
          start_ts DATETIME,
          duration_minutes INT,
          status TEXT DEFAULT 'scheduled'
        )
    ''')

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()