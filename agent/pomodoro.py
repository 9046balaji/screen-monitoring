import time
import threading
import json
import os
from plyer import notification
from datetime import datetime

POMODORO_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'pomodoro_state.json')

_pomodoro_thread = None
_pomodoro_running = False

DEFAULT_CONFIG = {
    "work_minutes": 25,
    "short_break_minutes": 5,
    "long_break_minutes": 15,
    "cycles_before_long_break": 4
}

def start_pomodoro(config=None):
    global _pomodoro_running, _pomodoro_thread
    if _pomodoro_running:
        return {"status": "already_running"}

    cfg = config or DEFAULT_CONFIG
    _pomodoro_running = True

    def _run():
        global _pomodoro_running
        cycle = 0
        total_cycles = cfg.get('cycles_before_long_break', 4)

        while _pomodoro_running:
            cycle += 1
            phase = "work"
            duration = cfg['work_minutes'] * 60

            _update_state({
                "running": True,
                "phase": phase,
                "cycle": cycle,
                "duration_seconds": duration,
                "remaining_seconds": duration,
                "started_at": datetime.now().isoformat()
            })

            notification.notify(
                title=f'🍅 Pomodoro #{cycle} — Work Time!',
                message=f'Focus for {cfg["work_minutes"]} minutes. You got this!',
                app_name='DigiWell', timeout=5
            )

            for remaining in range(duration, 0, -1):
                if not _pomodoro_running:
                    return
                _update_remaining(remaining)
                time.sleep(1)

            # Break phase
            is_long = (cycle % total_cycles == 0)
            break_duration = (cfg['long_break_minutes'] if is_long else cfg['short_break_minutes']) * 60
            break_label = "Long Break ☕" if is_long else "Short Break 🌿"

            _update_state({
                "running": True,
                "phase": "break",
                "cycle": cycle,
                "duration_seconds": break_duration,
                "remaining_seconds": break_duration,
                "started_at": datetime.now().isoformat()
            })

            notification.notify(
                title=f'✅ Pomodoro #{cycle} Done! {break_label}',
                message=f'Take a {cfg["long_break_minutes"] if is_long else cfg["short_break_minutes"]}-minute break.',
                app_name='DigiWell', timeout=8
            )

            from enforcer import show_break_screen
            show_break_screen(break_duration, f'{break_label} — Step away from the screen!')

            for remaining in range(break_duration, 0, -1):
                if not _pomodoro_running:
                    return
                _update_remaining(remaining)
                time.sleep(1)

        _update_state({"running": False, "phase": "idle"})

    _pomodoro_thread = threading.Thread(target=_run, daemon=True)
    _pomodoro_thread.start()
    return {"status": "started", "config": cfg}

def stop_pomodoro():
    global _pomodoro_running
    _pomodoro_running = False
    _update_state({"running": False, "phase": "idle"})
    return {"status": "stopped"}

def get_pomodoro_state():
    if os.path.exists(POMODORO_PATH):
        try:
            with open(POMODORO_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"running": False, "phase": "idle"}

def _update_state(state):
    os.makedirs(os.path.dirname(POMODORO_PATH), exist_ok=True)
    with open(POMODORO_PATH, 'w') as f:
        json.dump(state, f, indent=2)

def _update_remaining(remaining):
    state = get_pomodoro_state()
    state['remaining_seconds'] = remaining
    _update_state(state)
