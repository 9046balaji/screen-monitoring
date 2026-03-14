import psutil
import json
import os
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from plyer import notification
from datetime import datetime
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.database import get_db_connection

LIMITS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'app_limits.json')

# Track which warnings already shown this session
_warned = set()
_break_active = False
_doomscroll_warned = set()

def load_limits():
    """Load user-defined app time limits in seconds"""
    if os.path.exists(LIMITS_PATH):
        with open(LIMITS_PATH) as f:
            return json.load(f)
    return {}

def save_limits(limits):
    os.makedirs(os.path.dirname(LIMITS_PATH), exist_ok=True)
    with open(LIMITS_PATH, 'w') as f:
        json.dump(limits, f, indent=2)

def send_warning(app_name, seconds_used, limit_seconds):
    # Use ceil or float precision so it doesn't say "0 mins" for 48 seconds
    mins_used_str = f"{seconds_used / 60:.1f}".rstrip('0').rstrip('.')
    mins_limit_str = f"{limit_seconds / 60:.1f}".rstrip('0').rstrip('.')
    try:
        notification.notify(
            title=f'⚠️ DigiWell Warning — {app_name}',
            message=f'You have used {app_name} for {mins_used_str} mins. Limit is {mins_limit_str} mins. App will close soon.',
            app_name='DigiWell',
            timeout=8
        )
    except Exception as e:
        print(f"Failed to send warning notification for {app_name}: {e}")

def force_close_app(app_name, process_name):
    """Kill all processes matching the process name"""
    closed = 0
    base_name = process_name.lower().replace('.exe', '')
    
    for proc in psutil.process_iter(['name', 'pid']):
        try:
            p_name = proc.info['name'].lower()
            if p_name == process_name.lower() or p_name.startswith(f"{base_name}.") or p_name == f"{base_name}.exe":
                proc.kill()
                closed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError, TypeError):
            pass

    if closed > 0:
        try:
            notification.notify(
                title=f'🚫 DigiWell — {app_name} Closed',
                message=f'Your time limit for {app_name} has been reached. Take a break!',
                app_name='DigiWell',
                timeout=10
            )
        except Exception as e:
            print(f"Failed to send closing notification for {app_name}: {e}")
    return closed > 0

def show_break_screen(duration_seconds=60, message="Time's up! Take a break. 👀"):
    """Show a full-screen overlay that blocks usage for duration_seconds"""
    global _break_active
    if _break_active:
        return
    _break_active = True

    def _run():
        global _break_active
        root = tk.Tk()
        root.attributes('-fullscreen', True)
        root.attributes('-topmost', True)
        root.attributes('-alpha', 0.95)
        root.configure(bg='#0F172A')
        root.overrideredirect(True)

        # Countdown variable
        # remaining = tk.IntVar(value=duration_seconds)

        # Fonts
        big_font   = tkfont.Font(family='Segoe UI', size=64, weight='bold')
        mid_font   = tkfont.Font(family='Segoe UI', size=24)
        small_font = tkfont.Font(family='Segoe UI', size=16)

        # Layout
        frame = tk.Frame(root, bg='#0F172A')
        frame.place(relx=0.5, rely=0.5, anchor='center')

        tk.Label(frame, text='🧠', font=tkfont.Font(size=80), bg='#0F172A').pack(pady=(0,10))
        tk.Label(frame, text='DigiWell — Break Time', font=mid_font, fg='#6366F1', bg='#0F172A').pack()
        tk.Label(frame, text=message, font=small_font, fg='#94A3B8', bg='#0F172A').pack(pady=10)

        timer_label = tk.Label(frame, text=f'{duration_seconds}s', font=big_font, fg='#F8FAFC', bg='#0F172A')
        timer_label.pack(pady=20)

        tip_label = tk.Label(frame, text='Look at something 20 feet away for 20 seconds 👀',
                             font=small_font, fg='#10B981', bg='#0F172A')
        tip_label.pack()

        progress_frame = tk.Frame(frame, bg='#1E293B', width=400, height=8)
        progress_frame.pack(pady=20)
        progress_bar = tk.Frame(progress_frame, bg='#6366F1', height=8)
        progress_bar.place(x=0, y=0, width=400)

        def countdown(val):
            if val <= 0:
                root.destroy()
                global _break_active
                _break_active = False
                return
            timer_label.config(text=f'{val}s')
            # Update progress bar
            pct = val / duration_seconds
            progress_bar.place(x=0, y=0, width=int(400 * pct))
            # Color change as time runs out
            color = '#10B981' if pct > 0.5 else '#F59E0B' if pct > 0.2 else '#EF4444'
            timer_label.config(fg=color)
            root.after(1000, countdown, val - 1)

        countdown(duration_seconds)
        root.mainloop()
        _break_active = False

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

def check_doomscrolling(app_name, category, seconds_used):
    """Detect doomscrolling based on time of day and app category."""
    now = datetime.now()
    hour = now.hour
    
    # Doomscrolling rules: Late night (23:00 - 05:00), Social Media, long consecutive use 
    is_late_night = hour >= 23 or hour < 5
    is_social = category == 'Social'
    is_long_use = seconds_used > 600  # 10 minutes session
    
    if is_late_night and is_social and is_long_use:
        # Prevent spamming interventions
        warn_key = f"{app_name}_{now.date()}_{hour}"
        if warn_key not in _doomscroll_warned:
            _doomscroll_warned.add(warn_key)
            
            # Log intervention to database
            conn = get_db_connection()
            c = conn.cursor()
            c.execute('''
                INSERT INTO interventions (timestamp, app_name, reason, status)
                VALUES (?, ?, ?, ?)
            ''', (now.isoformat(), app_name, 'Late night doomscrolling detected', 'pending'))
            conn.commit()
            conn.close()
            
            try:
                notification.notify(
                    title='🌙 Doomscroll Warning',
                    message=f'You\'ve been scrolling {app_name} late at night. Consider resting your eyes.',
                    app_name='DigiWell',
                    timeout=10
                )
            except Exception as e:
                pass


def get_active_window_text():
    import sys
    if sys.platform == "win32":
        try:
            import win32gui
            hwnd = win32gui.GetForegroundWindow()
            if hwnd:
                return win32gui.GetWindowText(hwnd).lower()
        except:
            pass
    return ""

def focus_violation_event(domain):
    try:
        notification.notify(
            title='🚫 Focus Violation',
            message='🚫 This website is blocked during Focus Mode.',
            app_name='DigiWell',
            timeout=5
        )
        show_break_screen(duration_seconds=10, message=f"🚫 This website is blocked during Focus Mode.\\n({domain})")
    except:
        pass

def poll_focus_sessions():
    """Poll DB for scheduled focus sessions and start them via focus_mode"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        now_ts = datetime.utcnow().isoformat()
        
        c.execute('''
            SELECT id, duration_minutes FROM focus_sessions
            WHERE status = 'scheduled' AND start_ts <= ?
        ''', (now_ts,))
        rows = c.fetchall()
        
        for row in rows:
            # Mark as running
            c.execute('UPDATE focus_sessions SET status = "running" WHERE id = ?', (row['id'],))
            conn.commit()
            
            # Start focus session using existing logic
            try:
                from focus_mode import start_focus_session
                start_focus_session(duration_minutes=row['duration_minutes'], session_name="Commitment Focus")
            except Exception as e:
                print(f"Failed to start focus mode: {e}")
                
        conn.close()
    except Exception as e:
        print(f"Failed to poll focus sessions: {e}")

_last_poll = 0
def check_and_enforce(app_name, process_name, seconds_used, category='Other'):
    """Called every second by tracker — checks limits and enforces"""
    global _last_poll
    now = time.time()
    if now - _last_poll > 5:  # Every 5 seconds
        poll_focus_sessions()
        _last_poll = now
        
    check_doomscrolling(app_name, category, seconds_used)
    limits = load_limits()
    if app_name not in limits:
        return

    limit = limits[app_name]
    limit_seconds = limit.get('limit_seconds', 3600)
    mode = limit.get('mode', 'warn')  # warn / close / break / all

    warn_at = limit_seconds - 60 if limit_seconds > 300 else int(limit_seconds * 0.8)

    # Warning
    if seconds_used >= warn_at and app_name not in _warned:
        _warned.add(app_name)
        send_warning(app_name, seconds_used, limit_seconds)

    # Enforce at 100%
    if seconds_used >= limit_seconds:
        if mode in ('close', 'all'):
            force_close_app(app_name, process_name)
        if mode in ('break', 'all'):
            show_break_screen(
                duration_seconds=60,
                message=f'{app_name} limit reached. Rest your eyes!'
            )
        # Reset warning flag so it can warn again next session
        _warned.discard(app_name)
