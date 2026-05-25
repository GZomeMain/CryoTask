import os
import json

STATE_FILE = "suspended_apps.json"
SCHEDULE_FILE = "scheduled_actions.json"
PRESETS_FILE = "presets.json"

# --- State Management ---
def load_suspended_state():
    if not os.path.exists(STATE_FILE): return []
    try:
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get("suspended", [])
    except: return []

def save_suspended_state(app_name, is_suspended):
    current_list = load_suspended_state()
    if is_suspended:
        if app_name not in current_list: current_list.append(app_name)
    else:
        if app_name in current_list: current_list.remove(app_name)
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({"suspended": current_list, "pinned": load_pinned_apps()}, f)
    except: pass

def load_pinned_apps():
    """Load pinned/favorite apps from file"""
    if not os.path.exists(STATE_FILE): return []
    try:
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get("pinned", [])
    except: return []

def save_pinned_apps(pinned_list):
    """Save pinned apps to file"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({"suspended": load_suspended_state(), "pinned": pinned_list}, f)
    except: pass

def toggle_pinned_app(app_name):
    """Toggle pin status for an app, returns new status"""
    pinned = load_pinned_apps()
    if app_name in pinned:
        pinned.remove(app_name)
        is_pinned = False
    else:
        pinned.append(app_name)
        is_pinned = True
    save_pinned_apps(pinned)
    return is_pinned

# --- Scheduled Actions ---
def load_scheduled_actions():
    """Load scheduled actions from file"""
    if not os.path.exists(SCHEDULE_FILE):
        return {"periodic_trim": {}, "ram_threshold": {"enabled": False, "threshold": 80, "apps": []}}
    try:
        with open(SCHEDULE_FILE, 'r') as f:
            data = json.load(f)
            # Ensure structure exists
            if "periodic_trim" not in data:
                data["periodic_trim"] = {}
            if "ram_threshold" not in data:
                data["ram_threshold"] = {"enabled": False, "threshold": 80, "apps": []}
            return data
    except:
        return {"periodic_trim": {}, "ram_threshold": {"enabled": False, "threshold": 80, "apps": []}}

def save_scheduled_actions(data):
    """Save scheduled actions to file"""
    try:
        with open(SCHEDULE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except: pass

def add_periodic_trim(app_name, interval_minutes):
    """Add a periodic trim schedule for an app"""
    data = load_scheduled_actions()
    data["periodic_trim"][app_name] = {
        "interval": interval_minutes,
        "enabled": True,
        "last_run": 0
    }
    save_scheduled_actions(data)

def remove_periodic_trim(app_name):
    """Remove periodic trim schedule for an app"""
    data = load_scheduled_actions()
    if app_name in data["periodic_trim"]:
        del data["periodic_trim"][app_name]
        save_scheduled_actions(data)

def toggle_periodic_trim(app_name, enabled):
    """Enable/disable periodic trim for an app"""
    data = load_scheduled_actions()
    if app_name in data["periodic_trim"]:
        data["periodic_trim"][app_name]["enabled"] = enabled
        save_scheduled_actions(data)

def set_ram_threshold(threshold, apps, enabled=True):
    """Set RAM threshold auto-suspend rule"""
    data = load_scheduled_actions()
    data["ram_threshold"] = {
        "enabled": enabled,
        "threshold": threshold,
        "apps": apps
    }
    save_scheduled_actions(data)

# --- Presets Management ---
def load_presets():
    """Load user presets from file"""
    if not os.path.exists(PRESETS_FILE):
        return {}
    try:
        with open(PRESETS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_presets(data):
    """Save presets to file"""
    try:
        with open(PRESETS_FILE, 'w') as f:
            json.dump(data, f, indent=4)
    except:
        pass

def get_apps_with_schedules():
    """Get set of app names that have any scheduled action"""
    data = load_scheduled_actions()
    scheduled_apps = set()
    
    # Apps with periodic trim
    for app_name, config in data.get("periodic_trim", {}).items():
        if config.get("enabled", False):
            scheduled_apps.add(app_name)
    
    # Apps in RAM threshold list
    if data.get("ram_threshold", {}).get("enabled", False):
        for app_name in data["ram_threshold"].get("apps", []):
            scheduled_apps.add(app_name)
    
    return scheduled_apps
