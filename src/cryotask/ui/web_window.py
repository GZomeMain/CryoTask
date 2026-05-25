import os
import sys
import threading
import webview
import pystray
from PIL import Image

from src.cryotask.core.engine import CryoEngine
from src.cryotask.utils.helpers import resource_path

# Global reference to engine and window for thread callbacks
engine = None
window = None
tray_icon = None
force_exit = False

class WebWindowAPI:
    def __init__(self):
        global engine
        self.engine = engine
        
    def get_system_stats(self):
        try:
            return self.engine.get_system_stats()
        except Exception as e:
            return {"error": str(e)}
            
    def get_processes(self, query="", safe_mode=True):
        try:
            return self.engine.get_process_list(query, safe_mode)
        except Exception as e:
            return {"error": str(e)}
            
    def toggle_suspend(self, app_name, suspend_action):
        try:
            res = self.engine.toggle_suspend(app_name, suspend_action)
            return {"success": res}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def trim_process(self, app_name):
        try:
            new_mem = self.engine.trim_process(app_name)
            return {"success": True, "new_memory": new_mem}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def toggle_pin(self, app_name):
        try:
            res = self.engine.toggle_pin(app_name)
            return {"success": True, "is_pinned": res}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def get_rules(self):
        try:
            return self.engine.get_rules()
        except Exception as e:
            return {"error": str(e)}
            
    def save_rules(self, rules_data):
        try:
            self.engine.save_rules(rules_data)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def get_presets(self):
        try:
            return self.engine.get_presets()
        except Exception as e:
            return {"error": str(e)}
            
    def save_presets(self, presets_data):
        try:
            self.engine.save_presets(presets_data)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def apply_preset(self, preset_name):
        try:
            res = self.engine.apply_preset(preset_name)
            return res
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def minimize_to_tray(self):
        global window
        if window:
            window.hide()
        return {"success": True}
        
    def exit_app(self):
        exit_application()
        return {"success": True}


def setup_tray():
    global tray_icon, window
    icon_path = resource_path("assets/app_icon.ico")
    
    try:
        if os.path.exists(icon_path):
            image = Image.open(icon_path)
        else:
            image = Image.new('RGB', (64, 64), color=(32, 32, 32))
    except Exception:
        image = Image.new('RGB', (64, 64), color=(32, 32, 32))
        
    def on_restore(icon, item):
        if window:
            window.show()
            
    def on_exit(icon, item):
        exit_application()
        
    menu = pystray.Menu(
        pystray.MenuItem('Restore CryoTask', on_restore, default=True),
        pystray.MenuItem('Exit', on_exit)
    )
    
    tray_icon = pystray.Icon("CryoTask", image, "CryoTask", menu)
    tray_icon.run()


def exit_application():
    global force_exit, window, tray_icon, engine
    force_exit = True
    
    # Stop scheduler
    if engine:
        engine.stop_scheduler()
        
    # Stop tray
    if tray_icon:
        tray_icon.stop()
        
    # Destroy window
    if window:
        window.destroy()
        
    sys.exit(0)


def on_closing():
    global force_exit, window
    if not force_exit:
        window.hide()
        return False  # Prevent closing the window
    return True  # Allow closing


def launch_web_gui():
    global engine, window
    
    # Initialize Core Engine and Scheduler
    engine = CryoEngine()
    engine.start_scheduler()
    
    # Setup System Tray in background thread
    tray_thread = threading.Thread(target=setup_tray, daemon=True)
    tray_thread.start()
    
    # Determine frontend HTML path
    html_path = resource_path("src/cryotask/ui/web/index.html")
    
    # Create webview window
    api = WebWindowAPI()
    window = webview.create_window(
        title="CryoTask",
        url=html_path,
        js_api=api,
        width=1000,
        height=750,
        min_size=(800, 600),
        background_color='#1E1E1E'
    )
    
    window.events.closing += on_closing
    
    # Start webview loop
    webview.start()
