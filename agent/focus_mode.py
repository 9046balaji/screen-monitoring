import psutil
import json
import os
import time
import threading
import atexit
from plyer import notification
from datetime import datetime, timedelta

from website_blocker import (
    block_websites,
    unblock_websites,
    get_blocked_list_from_config,
    recover_hosts_if_needed,
)
from enforcer import focus_violation_event, get_active_window_text

FOCUS_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'focus_session.json')

# Default list of distracting apps to block during focus
DEFAULT_BLOCK_LIST = [
    'discord.exe', 'slack.exe', 'WhatsApp.exe', 'Telegram.exe',
    'steam.exe', 'spotify.exe', 'chrome.exe', 'firefox.exe'
]

_focus_active = False
_focus_thread = None

# Recover stale hosts entries from any previous unclean shutdown.
recover_hosts_if_needed()


def _cleanup_hosts_on_exit():
    session = _load_session()
    if session.get("active"):
        unblock_websites(session.get("blocked_domains", []))


atexit.register(_cleanup_hosts_on_exit)

def start_focus_session(duration_minutes=25, block_list=None, session_name="Focus Session", block_categories=None):
    global _focus_active, _focus_thread
    if _focus_active:
        return {"status": "already_running"}

    block = block_list or DEFAULT_BLOCK_LIST
    categories = block_categories if block_categories is not None else ["social", "video", "entertainment"]
    end_time = datetime.now() + timedelta(minutes=duration_minutes)

    session = {
        "active": True,
        "session_name": session_name,
        "duration_minutes": duration_minutes,
        "started_at": datetime.now().isoformat(),
        "ends_at": end_time.isoformat(),
        "block_list": block,
        "block_categories": categories,
        "apps_killed": [],
        "blocked_domains": [],
        "website_blocking": {
            "enforced": False,
            "reason": "pending"
        }
    }
    _save_session(session)
    _focus_active = True

    blocked_domains = get_blocked_list_from_config(categories)
    block_result = block_websites(blocked_domains)
    session["blocked_domains"] = block_result.get("blocked_domains", blocked_domains)
    session["website_blocking"] = {
        "enforced": bool(block_result.get("success")),
        "reason": block_result.get("reason"),
        "message": block_result.get("message")
    }
    _save_session(session)

    notification.notify(
        title=f'🎯 Focus Mode ON — {session_name}',
        message=f'Staying focused for {duration_minutes} minutes. Distracting apps will be closed.',
        app_name='DigiWell',
        timeout=5
    )

    def _enforce_focus():
        global _focus_active
        while _focus_active and datetime.now() < end_time:
            block_bases = [b.lower().replace('.exe', '') for b in block]
            
            # Check window titles for blocked domains
            active_title = get_active_window_text()
            for domain in session.get("blocked_domains", []):
                if domain in active_title:
                    focus_violation_event(domain)
                    break # trigger once per cycle

            for proc in psutil.process_iter(['name', 'pid']):
                try:
                    p_name = proc.info['name'].lower()
                    
                    should_kill = False
                    if p_name in [b.lower() for b in block] or any(p_name.startswith(f"{b_base}.") or p_name == f"{b_base}.exe" for b_base in block_bases):
                        should_kill = True

                    if should_kill:
                        try:
                            proc.kill()
                            if proc.info['name'] not in session['apps_killed']:
                                session['apps_killed'].append(proc.info['name'])
                                _save_session(session)
                                
                            notification.notify(
                                title=f'🚫 DigiWell Focus Mode',
                                message=f'{proc.info["name"]} was closed — stay focused!',
                                app_name='DigiWell',
                                timeout=4
                            )
                        except:
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied, KeyError, TypeError):
                    pass
            time.sleep(3)

        # Session ended
        _focus_active = False
        session['active'] = False
        _save_session(session)
        unblock_websites(session.get("blocked_domains", []))
        notification.notify(
            title='✅ Focus Session Complete!',
            message=f'Great work! {session_name} is done. Take a 5-minute break.',
            app_name='DigiWell',
            timeout=10
        )

    _focus_thread = threading.Thread(target=_enforce_focus, daemon=True)
    _focus_thread.start()
    return {
        "status": "started",
        "ends_at": end_time.isoformat(),
        "website_blocking": session.get("website_blocking", {"enforced": False})
    }

def stop_focus_session():
    global _focus_active
    _focus_active = False
    session = _load_session()
    session['active'] = False
    _save_session(session)
    unblock_websites(session.get("blocked_domains", []))
    notification.notify(
        title='Focus Mode Ended',
        message='You ended your focus session early.',
        app_name='DigiWell',
        timeout=5
    )
    return {"status": "stopped"}

def get_focus_status():
    return _load_session()

def _save_session(session):
    os.makedirs(os.path.dirname(FOCUS_PATH), exist_ok=True)
    with open(FOCUS_PATH, 'w') as f:
        json.dump(session, f, indent=2)

def _load_session():
    if os.path.exists(FOCUS_PATH):
        with open(FOCUS_PATH) as f:
            return json.load(f)
    return {"active": False}
