import os
import time
from datetime import datetime

import psutil
import win32gui
import win32process

import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from database.database import get_db_connection


POLL_SECONDS = 5

APP_FRIENDLY = {
    "chrome.exe": "Chrome",
    "msedge.exe": "Microsoft Edge",
    "firefox.exe": "Firefox",
    "code.exe": "VS Code",
    "code - insiders.exe": "VS Code Insiders",
    "discord.exe": "Discord",
    "spotify.exe": "Spotify",
    "teams.exe": "Microsoft Teams",
    "slack.exe": "Slack",
    "whatsapp.exe": "WhatsApp",
}


def _normalize_app_name(process_name: str, title: str) -> str:
    p = (process_name or "").lower()
    if p in APP_FRIENDLY:
        return APP_FRIENDLY[p]

    # Browser tab-aware naming for key apps.
    t = (title or "").lower()
    if "youtube" in t:
        return "YouTube"
    if "instagram" in t:
        return "Instagram"
    if "whatsapp" in t:
        return "WhatsApp"

    return (process_name or "Unknown").replace(".exe", "")


def get_active_window_info():
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return None

        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid <= 0:
            return None

        title = win32gui.GetWindowText(hwnd) or ""
        proc = psutil.Process(pid)
        process_name = proc.name()
        app_name = _normalize_app_name(process_name, title)

        return {
            "app": app_name,
            "window_title": title,
            "process_name": process_name,
            "pid": pid,
        }
    except Exception:
        return None


def save_usage_record(user_id: str, active: dict, start_dt: datetime, end_dt: datetime):
    if not active:
        return

    duration_min = max(1, int((end_dt - start_dt).total_seconds() // 60))

    conn = get_db_connection()
    c = conn.cursor()

    c.execute(
        """
        INSERT INTO app_usage_logs (
            user_id,
            app_name,
            window_title,
            process_name,
            start_time,
            end_time,
            duration_minutes,
            date
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            active.get("app", "Unknown"),
            active.get("window_title", ""),
            active.get("process_name", ""),
            start_dt.isoformat(),
            end_dt.isoformat(),
            duration_min,
            start_dt.date().isoformat(),
        ),
    )

    hour_bucket = start_dt.hour
    c.execute(
        """
        INSERT INTO hourly_activity_table (user_id, date, hour, activity_level)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, date, hour) DO UPDATE SET
            activity_level = activity_level + excluded.activity_level
        """,
        (user_id, start_dt.date().isoformat(), hour_bucket, duration_min),
    )

    conn.commit()
    conn.close()


class AppUsageTracker:
    def __init__(self, user_id: str = "local", poll_seconds: int = POLL_SECONDS):
        self.user_id = user_id
        self.poll_seconds = poll_seconds
        self.current_active = None
        self.current_start = None

    def _flush_current(self):
        if self.current_active and self.current_start:
            now = datetime.now()
            save_usage_record(self.user_id, self.current_active, self.current_start, now)
        self.current_active = None
        self.current_start = None

    def run(self):
        print(f"[AppUsageTracker] started with poll interval={self.poll_seconds}s")
        try:
            while True:
                active = get_active_window_info()
                now = datetime.now()

                if active is None:
                    self._flush_current()
                    time.sleep(self.poll_seconds)
                    continue

                # Active app switched -> close previous interval and start new.
                switched = (
                    self.current_active is None
                    or self.current_active.get("app") != active.get("app")
                    or self.current_active.get("window_title") != active.get("window_title")
                )

                if switched:
                    self._flush_current()
                    self.current_active = active
                    self.current_start = now

                time.sleep(self.poll_seconds)
        except KeyboardInterrupt:
            self._flush_current()
            print("[AppUsageTracker] stopped")
        except Exception as e:
            self._flush_current()
            print(f"[AppUsageTracker] crashed: {e}")


if __name__ == "__main__":
    tracker = AppUsageTracker(user_id="local", poll_seconds=POLL_SECONDS)
    tracker.run()
