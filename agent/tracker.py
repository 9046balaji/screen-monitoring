import psutil
import win32gui
import win32process
import json
import time
import os
from datetime import datetime, date
from collections import defaultdict
import sqlite3

# Import database connection from root dir
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.database import get_db_connection

# Map process names to friendly app names
APP_NAME_MAP = {
    'chrome.exe':        'Google Chrome',
    'firefox.exe':       'Firefox',
    'msedge.exe':        'Microsoft Edge',
    'Code.exe':          'VS Code',
    'slack.exe':         'Slack',
    'discord.exe':       'Discord',
    'spotify.exe':       'Spotify',
    'WhatsApp.exe':      'WhatsApp',
    'Telegram.exe':      'Telegram',
    'notepad.exe':       'Notepad',
    'explorer.exe':      'File Explorer',
    'WINWORD.EXE':       'Microsoft Word',
    'EXCEL.EXE':         'Microsoft Excel',
    'POWERPNT.EXE':      'PowerPoint',
    'zoom.exe':          'Zoom',
    'Teams.exe':         'Microsoft Teams',
    'vlc.exe':           'VLC',
    'photoshop.exe':     'Photoshop',
    'devenv.exe':        'Visual Studio',
    'pycharm64.exe':     'PyCharm',
    'idea64.exe':        'IntelliJ IDEA',
    'obs64.exe':         'OBS Studio',
    'steam.exe':         'Steam',
}

# Risk categories for ML integration
APP_RISK_MAP = {
    'Google Chrome': 'medium', 'Firefox': 'medium', 'Microsoft Edge': 'medium',
    'Discord': 'high', 'Slack': 'low', 'WhatsApp': 'medium', 'Telegram': 'medium',
    'Spotify': 'low', 'Steam': 'high', 'VS Code': 'low', 'PyCharm': 'low',
    'Microsoft Word': 'low', 'Microsoft Excel': 'low', 'Zoom': 'low',
    'VLC': 'medium',
}

# App categories
APP_CATEGORY_MAP = {
    'Google Chrome': 'Browser',   'Firefox': 'Browser',   'Microsoft Edge': 'Browser',
    'Discord': 'Social',          'WhatsApp': 'Social',   'Telegram': 'Social',
    'Slack': 'Productivity',      'Zoom': 'Productivity', 'Microsoft Teams': 'Productivity',
    'VS Code': 'Development',     'PyCharm': 'Development', 'IntelliJ IDEA': 'Development',
    'Microsoft Word': 'Office',   'Microsoft Excel': 'Office', 'PowerPoint': 'Office',
    'Spotify': 'Entertainment',   'VLC': 'Entertainment', 'Steam': 'Gaming',
    'OBS Studio': 'Creative',     'Photoshop': 'Creative',
}

def get_active_app():
    """Returns (process_name, friendly_name, window_title)"""
    try:
        hwnd = win32gui.GetForegroundWindow()
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = psutil.Process(pid)
        proc_name = proc.name()
        friendly = APP_NAME_MAP.get(proc_name, proc_name.replace('.exe', ''))
        title = win32gui.GetWindowText(hwnd)
        return proc_name, friendly, title
    except Exception:
        return None, 'Unknown', ''

def update_log_db(date_str, hour_str, friendly, proc_name, category, risk):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Update usage_logs
    c.execute('''
        INSERT INTO usage_logs (date, friendly_name, process_name, category, risk, seconds, last_seen)
        VALUES (?, ?, ?, ?, ?, 1, ?)
        ON CONFLICT(date, friendly_name) DO UPDATE SET
        seconds = seconds + 1,
        last_seen = excluded.last_seen
    ''', (date_str, friendly, proc_name, category, risk, datetime.now().isoformat()))
    
    # Update hourly_logs
    c.execute('''
        INSERT INTO hourly_logs (date, hour_str, seconds)
        VALUES (?, ?, 1)
        ON CONFLICT(date, hour_str) DO UPDATE SET
        seconds = seconds + 1
    ''', (date_str, hour_str))
    
    conn.commit()
    
    # Get total seconds for the app to pass to enforcer
    c.execute('SELECT seconds FROM usage_logs WHERE date = ? AND friendly_name = ?', (date_str, friendly))
    row = c.fetchone()
    app_seconds = row['seconds'] if row else 1
    
    conn.close()
    return app_seconds

def run_tracker():
    print("✅ DigiWell Tracker started — monitoring app usage...")
    while True:
        proc_name, friendly, title = get_active_app()
        today = str(date.today())
        hour_key = datetime.now().strftime('%H:00')

        if friendly and friendly != 'Unknown':
            category = APP_CATEGORY_MAP.get(friendly, 'Other')
            risk = APP_RISK_MAP.get(friendly, 'medium')
            
            app_seconds = update_log_db(today, hour_key, friendly, proc_name, category, risk)

            # Check limits — import here to avoid circular
            try:
                from enforcer import check_and_enforce
                check_and_enforce(friendly, proc_name, app_seconds, category)
            except ImportError:
                pass # enforcer will be created next
            except Exception as e:
                print(f"Error enforcing limits for {friendly}: {e}")

        time.sleep(1)

if __name__ == '__main__':
    run_tracker()
