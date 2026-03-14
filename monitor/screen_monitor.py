import time
import datetime
import uuid
import json
import sqlite3
import os
import sys

try:
    import psutil
except ImportError:
    psutil = None

# Platform specific imports mapping
if sys.platform == "win32":
    try:
        import win32gui
        import win32process
    except ImportError:
        win32gui = None
        win32process = None

# DB connection
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'data', 'digiwell.db')
CATEGORIES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'app_categories.json')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    return conn

def load_categories():
    if os.path.exists(CATEGORIES_PATH):
        with open(CATEGORIES_PATH, 'r') as f:
            return json.load(f)
    return {}

def get_active_window_process():
    if sys.platform == "win32" and win32gui and win32process and psutil:
        try:
            hwnd = win32gui.GetForegroundWindow()
            if hwnd == 0:
                return None
            
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if pid <= 0:
                return None
                
            title = win32gui.GetWindowText(hwnd)
            try:
                process = psutil.Process(pid)
                name = process.name()
                return {"app_name": name, "window_title": title, "pid": pid, "process": process}
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                return None
        except Exception:
            return None
    elif sys.platform == "darwin":
        # macOS specific logic placeholder
        return None
    elif sys.platform == "linux":
        # linux specific logic placeholder
        return None
    return None

def get_system_metrics(process):
    cpu = 0.0
    mem = 0.0
    if process:
        try:
            cpu = process.cpu_percent()
            mem = process.memory_info().rss / (1024 * 1024) # MB
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return cpu, mem

class ScreenMonitor:
    def __init__(self, poll_interval=5):
        self.poll_interval = poll_interval
        self.categories = load_categories()
        
        # Current active session
        self.current_app = None
        self.session_start = None
        self.current_window_title = None
        
        # Cumulative metrics for the session
        self.cpu_samples = []
        self.mem_samples = []
    
    def get_category(self, app_name):
        return self.categories.get(app_name.lower(), "uncategorized")

    def run(self):
        print(f"Starting ScreenMonitor (polling every {self.poll_interval}s)...")
        while True:
            active_info = get_active_window_process()
            
            if active_info:
                app_name = active_info["app_name"]
                window_title = active_info["window_title"]
                process = active_info.get("process")
                cpu, mem = get_system_metrics(process)
                
                # App changed or no current session
                if app_name != self.current_app:
                    # Log the previous session if any
                    self.end_session()
                    
                    # Start new session
                    self.current_app = app_name
                    self.current_window_title = window_title
                    self.session_start = datetime.datetime.now()
                    self.cpu_samples = [cpu]
                    self.mem_samples = [mem]
                else:
                    # Update metrics for current session
                    self.current_window_title = window_title # update if title changed
                    self.cpu_samples.append(cpu)
                    self.mem_samples.append(mem)
            else:
                # No active window, end session
                if self.current_app:
                    self.end_session()
            
            time.sleep(self.poll_interval)
            
    def end_session(self):
        if not self.current_app or not self.session_start:
            return
            
        now = datetime.datetime.now()
        duration = (now - self.session_start).total_seconds()
        
        # Only log short sessions if they represent an actual switch
        if duration >= 1:
            avg_cpu = sum(self.cpu_samples) / max(len(self.cpu_samples), 1)
            avg_mem = sum(self.mem_samples) / max(len(self.mem_samples), 1)
            category = self.get_category(self.current_app)
            
            self.log_usage(
                self.current_app,
                self.current_window_title,
                avg_cpu,
                avg_mem,
                int(duration),
                category
            )
            
        self.current_app = None
        self.session_start = None
        self.current_window_title = None
        self.cpu_samples = []
        self.mem_samples = []
            
    def log_usage(self, app_name, window_title, cpu, mem, duration, category):
        try:
            conn = get_db()
            cursor = conn.cursor()
            record_id = str(uuid.uuid4())
            ts = datetime.datetime.now().isoformat()
            
            cursor.execute('''
                INSERT INTO screen_usage (id, timestamp, app_name, window_title, cpu_usage, memory_usage, duration_seconds, category)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (record_id, ts, app_name, window_title, cpu, mem, duration, category))
            
            conn.commit()
            conn.close()
            print(f"Logged session: {app_name} | {duration}s | {category}")
        except Exception as e:
            print(f"Error logging usage: {e}")

if __name__ == "__main__":
    monitor = ScreenMonitor(poll_interval=5)
    try:
        monitor.run()
    except KeyboardInterrupt:
        monitor.end_session()
        print("ScreenMonitor stopped.")