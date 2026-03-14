import os
import shutil
import platform
import subprocess
import json

HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts" if platform.system() == "Windows" else "/etc/hosts"
REDIRECT_IP = "127.0.0.1"
BACKUP_PATH = HOSTS_PATH + ".backup"
MARKER_START = "# --- FOCUS MODE START ---"
MARKER_END = "# --- FOCUS MODE END ---"

def is_admin():
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            return os.geteuid() == 0
    except:
        return False

def backup_hosts():
    if not os.path.exists(BACKUP_PATH) and os.path.exists(HOSTS_PATH):
        try:
            shutil.copy2(HOSTS_PATH, BACKUP_PATH)
        except Exception as e:
            print(f"Failed to backup hosts file: {e}")

def restore_hosts():
    if os.path.exists(BACKUP_PATH):
        try:
            shutil.copy2(BACKUP_PATH, HOSTS_PATH)
        except Exception as e:
            print(f"Failed to restore hosts file: {e}")

def flush_dns():
    try:
        if platform.system() == "Windows":
            subprocess.run(["ipconfig", "/flushdns"], capture_output=True)
    except Exception as e:
        print(f"Failed to flush DNS: {e}")

def block_websites(domains):
    if not is_admin():
        print("Warning: Admin privileges required to modify hosts file.")
        
    backup_hosts()
    
    try:
        with open(HOSTS_PATH, 'r') as file:
            content = file.read()
            
        if MARKER_START in content:
            unblock_websites()
            with open(HOSTS_PATH, 'r') as file:
                content = file.read()
                
        block_text = f"\\n{MARKER_START}\\n"
        for domain in domains:
            block_text += f"{REDIRECT_IP} {domain}\\n"
            if not domain.startswith("www."):
                block_text += f"{REDIRECT_IP} www.{domain}\\n"
                block_text += f"{REDIRECT_IP} m.{domain}\\n"
        block_text += f"{MARKER_END}\\n"
        
        with open(HOSTS_PATH, 'a') as file:
            file.write(block_text)
            
        flush_dns()
        return True
    except Exception as e:
        print(f"Error blocking websites: {e}")
        return False

def unblock_websites():
    if not is_admin():
        print("Warning: Admin privileges required to modify hosts file.")
        
    try:
        with open(HOSTS_PATH, 'r') as file:
            lines = file.readlines()
            
        new_lines = []
        in_block = False
        
        for line in lines:
            if line.strip() == MARKER_START:
                in_block = True
            elif line.strip() == MARKER_END:
                in_block = False
            elif not in_block:
                new_lines.append(line)
                
        with open(HOSTS_PATH, 'w') as file:
            file.writelines(new_lines)
            
        flush_dns()
        return True
    except Exception as e:
        print(f"Error unblocking websites: {e}")
        return False

def get_blocked_list_from_config(categories=None):
    config_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'blocked_sites.json')
    try:
        with open(config_path, 'r') as f:
            data = json.load(f)
            
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
    except Exception as e:
        print(f"Error reading blocked sites config: {e}")
        return []
