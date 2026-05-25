import time
import threading
import psutil
import win32process
import win32gui

from src.cryotask.core.process_manager import ProcessManager, get_active_window_pid
from src.cryotask.utils.constants import EXCLUDED_PROCESSES, CRITICAL_SYSTEM_PROCESSES
from src.cryotask.persistence.storage import (
    load_suspended_state, load_pinned_apps, load_scheduled_actions,
    save_scheduled_actions, add_periodic_trim, remove_periodic_trim,
    toggle_pinned_app, load_presets, save_presets
)

class CryoEngine:
    def __init__(self):
        self.safe_mode = True
        self.scheduler_running = False
        self.scheduler_thread = None
        
        self.pinned_apps = set(load_pinned_apps())
        self.suspended_apps = set(load_suspended_state())
        
        # Cache for process PIDs and details to prevent redundant psutil scans
        self.process_cache = {}
        self.cache_lock = threading.Lock()
        
    def start_scheduler(self):
        if self.scheduler_running:
            return
        self.scheduler_running = True
        self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self.scheduler_thread.start()
        
    def stop_scheduler(self):
        self.scheduler_running = False
        
    def get_system_stats(self):
        sys_mem = psutil.virtual_memory()
        # Non-blocking CPU percent
        sys_cpu = psutil.cpu_percent(interval=None) 
        total_procs = len(psutil.pids())
        
        return {
            'mem_used_gb': round(sys_mem.used / 1073741824, 2),
            'mem_total_gb': round(sys_mem.total / 1073741824, 2),
            'mem_percent': sys_mem.percent,
            'cpu_percent': sys_cpu,
            'total_processes': total_procs
        }
        
    def get_process_list(self, query="", safe_mode=True):
        self.safe_mode = safe_mode
        visible_pids = ProcessManager.get_visible_windows_info()
        visible_pid_set = set(visible_pids.keys())
        
        from collections import defaultdict
        groups = defaultdict(lambda: {'mem': 0, 'cpu': 0.0, 'count': 0, 'status': 'Running', 'has_window': False, 'pids': []})
        
        # Load fresh state
        self.pinned_apps = set(load_pinned_apps())
        self.suspended_apps = set(load_suspended_state())
        scheduled_apps = self.get_scheduled_apps()
        
        # Single pass iteration
        for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'status', 'cpu_percent']):
            try:
                pid = proc.info['pid']
                name = proc.info['name']
                name_lower = name.lower()
                
                if name_lower in EXCLUDED_PROCESSES:
                    continue
                    
                mem_info = proc.info['memory_info']
                mem = getattr(mem_info, 'private', mem_info.rss)
                cpu = proc.info.get('cpu_percent', 0.0) or 0.0
                
                g = groups[name]
                g['mem'] += mem
                g['cpu'] += cpu
                g['count'] += 1
                g['pids'].append(pid)
                
                if pid in visible_pid_set:
                    g['has_window'] = True
                    
                # Mark status as suspended if any process/thread indicates suspended or saved state
                if proc.info['status'] == 'suspended' or name in self.suspended_apps:
                    g['status'] = 'Suspended'
                    
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        final_list = []
        for name, data in groups.items():
            name_lower = name.lower()
            
            # Safe Mode filters
            if safe_mode:
                if not data['has_window']:
                    continue
                if name_lower in CRITICAL_SYSTEM_PROCESSES:
                    continue
            
            is_pinned = name in self.pinned_apps
            has_schedule = name in scheduled_apps
            is_critical = name_lower in CRITICAL_SYSTEM_PROCESSES
            
            total_mem_mb = round(data['mem'] / (1024 * 1024), 1)
            total_cpu = round(data['cpu'], 1)
            
            final_list.append({
                "name": name,
                "status": data['status'],
                "memory": total_mem_mb,
                "count": data['count'],
                "cpu": total_cpu,
                "is_critical": is_critical,
                "is_pinned": is_pinned,
                "has_schedule": has_schedule
            })
            
        # Sort pinned items first, then by memory descending
        final_list.sort(key=lambda x: (x['is_pinned'], x['memory']), reverse=True)
        
        # Apply search query
        if query:
            query_lower = query.lower()
            final_list = [p for p in final_list if query_lower in p['name'].lower()]
            
        return final_list[:100]  # Limit to top 100 for render performance

    def toggle_suspend(self, app_name, suspend_action):
        success = ProcessManager.toggle_group_state(app_name, suspend_action)
        if success:
            if suspend_action:
                self.suspended_apps.add(app_name)
            else:
                self.suspended_apps.discard(app_name)
        return success
        
    def trim_process(self, app_name):
        return ProcessManager.trim_group(app_name)
        
    def toggle_pin(self, app_name):
        is_pinned = toggle_pinned_app(app_name)
        if is_pinned:
            self.pinned_apps.add(app_name)
        else:
            self.pinned_apps.discard(app_name)
        return is_pinned
        
    def get_scheduled_apps(self):
        data = load_scheduled_actions()
        scheduled = set()
        for app_name, config in data.get("periodic_trim", {}).items():
            if config.get("enabled", False):
                scheduled.add(app_name)
        if data.get("ram_threshold", {}).get("enabled", False):
            for app_name in data["ram_threshold"].get("apps", []):
                scheduled.add(app_name)
        return scheduled

    def get_rules(self):
        return load_scheduled_actions()
        
    def save_rules(self, rules_data):
        save_scheduled_actions(rules_data)
        
    def get_presets(self):
        return load_presets()
        
    def save_presets(self, presets_data):
        save_presets(presets_data)
        
    def apply_preset(self, name):
        presets = load_presets()
        if name not in presets:
            return {"success": False, "message": f"Preset '{name}' not found."}
            
        apps = presets[name]
        targeted = 0
        success_count = 0
        
        # Get active processes to check running status
        running_names = {p.info['name'] for p in psutil.process_iter(['name'])}
        
        for app_name, action in apps.items():
            if app_name not in running_names:
                continue
            targeted += 1
            try:
                if action == "Trim":
                    self.trim_process(app_name)
                    success_count += 1
                elif action == "Suspend":
                    if self.toggle_suspend(app_name, True):
                        success_count += 1
                elif action == "Trim & Suspend":
                    self.trim_process(app_name)
                    if self.toggle_suspend(app_name, True):
                        success_count += 1
            except Exception as e:
                print(f"Error applying preset for {app_name}: {e}")
                
        return {
            "success": True,
            "message": f"Preset applied successfully.",
            "targeted": targeted,
            "success_count": success_count
        }

    def _scheduler_loop(self):
        """Background thread executing scheduled tasks"""
        while self.scheduler_running:
            try:
                current_time = time.time()
                data = load_scheduled_actions()
                
                # 1. Periodic Trims
                for app_name, config in data.get("periodic_trim", {}).items():
                    if not config.get("enabled", False):
                        continue
                    interval_seconds = config.get("interval", 15) * 60
                    last_run = config.get("last_run", 0)
                    
                    if current_time - last_run >= interval_seconds:
                        self.trim_process(app_name)
                        data["periodic_trim"][app_name]["last_run"] = current_time
                        save_scheduled_actions(data)
                
                # 2. RAM Threshold Auto-Suspend with Foreground App Protection
                ram_config = data.get("ram_threshold", {})
                if ram_config.get("enabled", False):
                    threshold = ram_config.get("threshold", 80)
                    ram_percent = psutil.virtual_memory().percent
                    
                    if ram_percent > threshold:
                        foreground_pid = get_active_window_pid()
                        foreground_name = None
                        
                        if foreground_pid:
                            try:
                                foreground_name = psutil.Process(foreground_pid).name()
                            except:
                                pass
                                
                        for app_name in ram_config.get("apps", []):
                            # Skip if this is the active foreground app
                            if foreground_name and foreground_name.lower() == app_name.lower():
                                continue
                                
                            # Toggle suspension
                            self.toggle_suspend(app_name, True)
                            
            except Exception as e:
                print(f"Error in scheduler loop: {e}")
                
            # Sleep for 10 seconds before next check
            time.sleep(10)
