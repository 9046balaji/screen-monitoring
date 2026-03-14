import json
import os
import platform
import shutil
import subprocess
from datetime import datetime

SYSTEM = platform.system()
DEFAULT_HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts" if SYSTEM == "Windows" else "/etc/hosts"
HOSTS_PATH = os.environ.get("DIGIWELL_HOSTS_PATH", DEFAULT_HOSTS_PATH)
REDIRECT_IP = "127.0.0.1"
MARKER_START = "# --- DIGIWELL FOCUS MODE START ---"
MARKER_END = "# --- DIGIWELL FOCUS MODE END ---"

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
BACKUP_PATH = os.path.join(DATA_DIR, "hosts_backup.txt")
STATE_PATH = os.path.join(DATA_DIR, "focus_hosts_state.json")
FOCUS_PATH = os.path.join(DATA_DIR, "focus_session.json")


def is_admin():
    try:
        if SYSTEM == "Windows":
            import ctypes
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        return os.geteuid() == 0
    except Exception:
        return False


def flush_dns():
    if SYSTEM != "Windows":
        return True
    try:
        subprocess.run(
            ["ipconfig", "/flushdns"],
            capture_output=True,
            text=True,
            check=False,
        )
        return True
    except Exception as exc:
        print(f"Failed to flush DNS: {exc}")
        return False


def _safe_read(path):
    with open(path, "r", encoding="utf-8", errors="ignore") as file:
        return file.read()


def _safe_write(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as file:
        file.write(content)


def _load_focus_session_active():
    if not os.path.exists(FOCUS_PATH):
        return False
    try:
        with open(FOCUS_PATH, "r", encoding="utf-8") as file:
            payload = json.load(file)
        return bool(payload.get("active"))
    except Exception:
        return False


def _read_state():
    if not os.path.exists(STATE_PATH):
        return {}
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def _write_state(payload):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def _clear_state():
    if os.path.exists(STATE_PATH):
        try:
            os.remove(STATE_PATH)
        except Exception:
            pass


def _normalize_domain(domain):
    if not domain:
        return ""
    d = domain.strip().lower()
    d = d.replace("http://", "").replace("https://", "")
    if "/" in d:
        d = d.split("/", 1)[0]
    return d.strip(".")


def _expand_domains(domains):
    expanded = set()
    aliases = {
        "youtube.com": ["youtube.com", "www.youtube.com", "m.youtube.com", "youtube-nocookie.com", "www.youtube-nocookie.com"],
        "instagram.com": ["instagram.com", "www.instagram.com"],
    }

    for raw_domain in domains or []:
        domain = _normalize_domain(raw_domain)
        if not domain:
            continue

        if domain in aliases:
            expanded.update(aliases[domain])
        else:
            expanded.add(domain)
            if not domain.startswith("www."):
                expanded.add(f"www.{domain}")
            if not domain.startswith("m."):
                expanded.add(f"m.{domain}")

    return sorted(expanded)


def _remove_focus_section(content):
    lines = content.splitlines()
    result = []
    in_focus_block = False

    for line in lines:
        stripped = line.strip()
        if stripped == MARKER_START:
            in_focus_block = True
            continue
        if stripped == MARKER_END:
            in_focus_block = False
            continue
        if not in_focus_block:
            result.append(line)

    cleaned = "\n".join(result).rstrip() + "\n"
    return cleaned


def _build_focus_block(domains):
    block_lines = [MARKER_START]
    for domain in domains:
        block_lines.append(f"{REDIRECT_IP} {domain}")
    block_lines.append(MARKER_END)
    return "\n".join(block_lines) + "\n"


def _ensure_backup_exists():
    if os.path.exists(BACKUP_PATH):
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    shutil.copy2(HOSTS_PATH, BACKUP_PATH)


def _restore_backup():
    if not os.path.exists(BACKUP_PATH):
        return False
    shutil.copy2(BACKUP_PATH, HOSTS_PATH)
    return True


def recover_hosts_if_needed():
    """Restore hosts if focus markers were left behind after an unclean shutdown."""
    if SYSTEM != "Windows" or not os.path.exists(HOSTS_PATH):
        return {"recovered": False}

    try:
        content = _safe_read(HOSTS_PATH)
    except Exception:
        return {"recovered": False}

    has_focus_markers = MARKER_START in content and MARKER_END in content
    if not has_focus_markers:
        return {"recovered": False}

    state = _read_state()
    session_active = _load_focus_session_active()

    if state.get("blocked") and session_active:
        return {"recovered": False}

    try:
        if _restore_backup():
            flush_dns()
            _clear_state()
            return {"recovered": True, "method": "backup_restore"}

        cleaned = _remove_focus_section(content)
        _safe_write(HOSTS_PATH, cleaned)
        flush_dns()
        _clear_state()
        return {"recovered": True, "method": "marker_cleanup"}
    except Exception as exc:
        return {"recovered": False, "error": str(exc)}


def block_websites(domains):
    if SYSTEM != "Windows":
        return {"success": False, "reason": "unsupported_os", "message": "System-level hosts blocking is only supported on Windows in this build."}
    if not is_admin():
        return {"success": False, "reason": "admin_required", "message": "Administrator privileges are required to edit the Windows hosts file."}

    expanded_domains = _expand_domains(domains)
    if not expanded_domains:
        return {"success": False, "reason": "no_domains", "message": "No valid domains provided for blocking."}

    try:
        _ensure_backup_exists()
        current_content = _safe_read(HOSTS_PATH)
        cleaned_content = _remove_focus_section(current_content)
        focus_block = _build_focus_block(expanded_domains)

        new_content = cleaned_content.rstrip() + "\n\n" + focus_block
        _safe_write(HOSTS_PATH, new_content)

        _write_state({
            "blocked": True,
            "domains": expanded_domains,
            "hosts_path": HOSTS_PATH,
            "backup_path": BACKUP_PATH,
            "updated_at": datetime.utcnow().isoformat(),
        })
        flush_dns()
        return {"success": True, "blocked_domains": expanded_domains}
    except Exception as exc:
        try:
            _restore_backup()
            flush_dns()
        except Exception:
            pass
        return {"success": False, "reason": "write_failed", "message": str(exc)}


def unblock_websites(domains=None):
    if SYSTEM != "Windows":
        return {"success": False, "reason": "unsupported_os", "message": "System-level hosts blocking is only supported on Windows in this build."}
    if not is_admin():
        return {"success": False, "reason": "admin_required", "message": "Administrator privileges are required to edit the Windows hosts file."}

    try:
        # Use backup-first restore to guarantee original hosts content comes back.
        restored = _restore_backup()
        if not restored:
            content = _safe_read(HOSTS_PATH)
            cleaned = _remove_focus_section(content)
            _safe_write(HOSTS_PATH, cleaned)

        flush_dns()
        _clear_state()
        return {"success": True}
    except Exception as exc:
        return {"success": False, "reason": "write_failed", "message": str(exc)}


def get_blocked_list_from_config(categories=None):
    config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'blocked_sites.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

        if not categories:
            domains = []
            for cat_domains in data.values():
                domains.extend(cat_domains)
            return domains

        domains = []
        for cat in categories:
            if cat in data:
                domains.extend(data[cat])
        return domains
    except Exception as exc:
        print(f"Error reading blocked sites config: {exc}")
        return []
