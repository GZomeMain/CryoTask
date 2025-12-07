"""
App Suspender & RAM Optimizer
Style: "Card View" (Image 2 Reference)
- Large rows (72px)
- Status Dots
- Purple/Blue Buttons
Author: GZome
License: MIT
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import win32api
import win32process
import win32con
import win32gui
import psutil
import threading
import ctypes
import sys
import os
import json
from collections import defaultdict

# --- High DPI Fix ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# --- Persistence Files ---
STATE_FILE = "suspended_apps.json"
SCHEDULE_FILE = "scheduled_actions.json"

# --- Excluded Processes ---
# These processes are always hidden from the app list to prevent
# accidentally suspending CryoTask itself or its dependencies.
# Add any helper processes here that should never appear.
EXCLUDED_PROCESSES = frozenset([
    # CryoTask & Python (self-protection)
    "python.exe",
    "pythonw.exe", 
    "python3.exe",
    "cryotask.exe",
    
    # Common Python IDEs/tools (if running from dev environment)
    "code.exe",          # VS Code
    "pycharm64.exe",     # PyCharm
    "idle.exe",          # Python IDLE
    
    # Windows Host Processes (low-level, dangerous to suspend)
    "wininit.exe",
    "csrss.exe",
    "smss.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
])

# --- Localization Strings ---
# All user-visible text is stored here for easy translation/theming.
# To translate, duplicate this dict with translated values.
class Strings:
    # App Info
    APP_TITLE = "CryoTask - Process Manager & RAM Optimizer"
    APP_NAME = "⚡ CryoTask"
    APP_SUBTITLE = "Process Manager"
    
    # Buttons
    BTN_REFRESH = "⟳ Refresh"
    BTN_REFRESH_SCANNING = "⏳ Scanning..."
    BTN_SUSPEND = "⏸ Suspend"
    BTN_RESUME = "▶ Resume"
    BTN_TRIM = "⚡ Trim"
    BTN_TRIM_WORKING = "Working..."
    BTN_TRIM_DONE = "✓ Done"
    BTN_SAFE_MODE = "🛡️ Safe Mode"
    BTN_ADVANCED_MODE = "⚠️ Advanced"
    BTN_SAVE = "Save"
    BTN_CANCEL = "Cancel"
    BTN_REMOVE_ALL = "Remove All"
    BTN_REMOVE_ALL = "Remove All"
    
    # Status Messages
    STATUS_READY = "● Ready"
    STATUS_SCANNING = "● Scanning processes..."
    STATUS_NO_APPS = "● No applications found"
    STATUS_SHOWING = "● Showing {count} of {total} applications"
    STATUS_NO_RESULTS = "● No results for '{query}'"
    STATUS_APPS_FOUND = "● {count} app{'s' if count != 1 else ''} ({mode})"
    
    # Labels
    LABEL_SYSTEM_MEMORY = "System Memory"
    LABEL_CPU_USAGE = "CPU Usage"
    LABEL_PROCESSES = "Processes"
    LABEL_SEARCH = "🔍 Search applications..."
    LABEL_TOTAL_MEMORY = "Total Memory: {gb} GB"
    LABEL_PROCESS = "process"
    LABEL_PROCESSES_PLURAL = "processes"
    
    # Schedule Dialog
    SCHEDULE_TITLE = "⏰ Schedule for {app_name}..."
    SCHEDULE_PERIODIC_TRIM = "⚡ Periodic Trim"
    SCHEDULE_TRIM_EVERY = "Trim every"
    SCHEDULE_MINUTES = "minutes"
    SCHEDULE_TIP = "💡 Periodic trim helps keep memory usage low\nwithout stopping the application."
    SCHEDULE_INDICATOR = "🕐 Scheduled"
    
    # Warnings/Dialogs
    WARN_SYSTEM_PROCESS = "⚠️ System"
    WARN_ADVANCED_TITLE = "⚠️ Enable Advanced Mode?"
    WARN_ADVANCED_MSG = """Advanced Mode allows you to see and manage ALL processes, including system processes.

⚠️ WARNING:
• Suspending critical system processes may crash your PC
• Some processes are essential for Windows to function
• Only use this if you know what you're doing

Do you want to enable Advanced Mode?"""
    WARN_ADMIN_TITLE = "Permission"
    WARN_ADMIN_MSG = "Restart as Administrator?"
    
    # Memory Display
    MEM_SAVED = "Saved: {mb} MB"
    MEM_FORMAT = "💾 {mb} MB"
    
    # Info Dialog
    INFO_TITLE = "About CryoTask"
    INFO_GITHUB_BTN = "View on GitHub"
    INFO_DESC = """⚡ CryoTask

A powerful process manager and RAM optimizer.

Features:
⏸ Suspend: Freezes apps to free up CPU resources.
⚡ Trim: Compresses app memory to free up RAM.
🛡️ Safe Mode: Hides critical system processes.
⭐ Pin: Keep favorite apps at the top.
⏰ Schedule: Auto-trim or suspend apps.
"""
    INFO_GITHUB_URL = "https://github.com/GZomeMain/CryoTask"
    INFO_AUTHOR = "Author: GZome"
    INFO_YOUTUBE = "YT: www.youtube.com/@GZome"
    INFO_YOUTUBE_URL = "https://www.youtube.com/@GZome"

# --- Resource Helper ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

# --- Theme Configuration ---
# --- Theme Configuration ---
class ModernTheme:
    BG_ROOT = "#121212"       # Material Dark Background
    BG_CONTAINER = "#181818"  # Slightly lighter
    BG_CARD = "#1E1E1E"       # Material Surface (Elevation 1)
    BG_CARD_HOVER = "#2A2A2A" # Surface Hover (Elevation 2)
    BG_SEARCH = "#252525"     # Search bar background (Elevation 2)
    
    TEXT_MAIN = "#F5F5F5"     # High Emphasis
    TEXT_SUB = "#A0A0A0"      # Medium Emphasis
    TEXT_DIM = "#606060"      # Disabled
    
    # Button Colors - Softer Material Tones
    BTN_TRIM = "#7C3AED"      # Soft Purple
    BTN_TRIM_HOVER = "#8B5CF6"
    BTN_SUSPEND = "#2563EB"   # Soft Blue
    BTN_SUSPEND_HOVER = "#3B82F6"
    BTN_SECONDARY = "#333333" # Neutral Surface
    BTN_SECONDARY_HOVER = "#404040"
    
    # Status Dots
    DOT_RUNNING = "#10B981"   # Emerald Green
    DOT_FROZEN = "#F59E0B"    # Amber
    DOT_PULSE = "#6EE7B7"     
    
    # Accent colors
    ACCENT_BLUE = "#38BDF8"   # Sky Blue
    ACCENT_PURPLE = "#A78BFA" # Soft Purple
    
    # Border/separator - Minimal/None
    BORDER_COLOR = "#2A2A2A"  # Very subtle if needed
    
    # Corner Radii
    RADIUS_CARD = 20
    RADIUS_BTN = 20  # Pill shape
    
    FONTS = {
        "header": ("Segoe UI", 24, "bold"),
        "title": ("Segoe UI", 15, "bold"), 
        "sub": ("Segoe UI", 12),
        "btn": ("Segoe UI", 12, "bold"),
        "status": ("Segoe UI", 10)
    }

# --- Critical System Processes Deny List ---
# These processes should NEVER be suspended as they are essential for Windows operation
CRITICAL_SYSTEM_PROCESSES = frozenset([
    # Windows Core
    "system", "system idle process", "registry", "smss.exe", "csrss.exe", 
    "wininit.exe", "services.exe", "lsass.exe", "lsaiso.exe", "svchost.exe",
    "winlogon.exe", "dwm.exe", "fontdrvhost.exe", "sihost.exe", "taskhostw.exe",
    
    # Windows Shell & Explorer
    "explorer.exe", "searchui.exe", "searchapp.exe", "startmenuexperiencehost.exe",
    "shellexperiencehost.exe", "runtimebroker.exe", "applicationframehost.exe",
    
    # Security & Antivirus
    "securityhealthservice.exe", "securityhealthsystray.exe", "msmpeng.exe",
    "nissrv.exe", "msseces.exe", "windowsdefender.exe", "smartscreen.exe",
    
    # Windows Update & Maintenance  
    "trustedinstaller.exe", "tiworker.exe", "wuauclt.exe", "musnotification.exe",
    
    # Networking
    "netsh.exe", "ipconfig.exe", "dnscache.exe", "nlasvc.exe",
    
    # Audio & Display
    "audiodg.exe", "audiosrv.exe", "ctfmon.exe",
    
    # Hardware & Drivers
    "wudfhost.exe", "dashost.exe", "wmiprvse.exe", "dllhost.exe",
    "conhost.exe", "spoolsv.exe",
    
    # Microsoft Services
    "searchindexer.exe", "searchprotocolhost.exe", "settingsynchost.exe",
    "backgroundtaskhost.exe", "systemsettings.exe",
    
    # Development Tools (to protect CryoTask itself)
    "python.exe", "pythonw.exe", "python3.exe", "cryotask.exe",
    
    # Critical Background Services
    "wbengine.exe", "vssvc.exe", "msiexec.exe", "dism.exe",
    "taskmgr.exe", "perfmon.exe", "mmc.exe", "regedit.exe",
    
    # Graphics & Display
    "igfxem.exe", "igfxhk.exe", "igfxtray.exe",  # Intel Graphics
    "nvdisplay.container.exe", "nvidia share.exe",  # NVIDIA
    "amdow.exe", "radeonsoft.exe",  # AMD
    
    # Memory & Disk
    "memorycompression", "vds.exe", "defrag.exe",
])

# --- Low Level Windows API ---
psapi = ctypes.WinDLL('psapi.dll')
kernel32 = ctypes.WinDLL('kernel32.dll')
PROCESS_SET_QUOTA = 0x0100
PROCESS_QUERY_INFORMATION = 0x0400

def is_admin():
    try: return ctypes.windll.shell32.IsUserAnAdmin()
    except: return False

def run_as_admin():
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

def trim_pid(pid):
    try:
        handle = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
        if not handle: return False
        result = psapi.EmptyWorkingSet(handle)
        kernel32.CloseHandle(handle)
        return bool(result)
    except: return False

def get_process_group_memory(proc_name):
    """Get total memory for a process group - optimized with single iteration"""
    total_mem = 0
    try:
        for p in psutil.process_iter(['name', 'memory_info']):
            try:
                if p.info['name'] == proc_name:
                    total_mem += p.info['memory_info'].rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except: pass
    return round(total_mem / (1024 * 1024), 1)

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
SCHEDULE_FILE = "scheduled_actions.json"

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

# --- UI Components ---

class ProcessCard(ctk.CTkFrame):
    # Class-level cache for reusable strings
    _PROCESS_TEXT = "process"
    _PROCESSES_TEXT = "processes"
    
    def __init__(self, master, process_data, suspend_callback, trim_callback, refresh_callback=None, schedule_callback=None, pin_callback=None, *args, **kwargs):
        # Larger Height: 80px for cleaner look
        super().__init__(master, corner_radius=ModernTheme.RADIUS_CARD, fg_color=ModernTheme.BG_CARD, 
                         height=80, border_width=0, # border_color removed for cleaner look
                         *args, **kwargs)
        self.pack_propagate(False) 
        
        self.proc_name = process_data['name']
        self.proc_name_lower = self.proc_name.lower()  # Cache lowercase for filtering
        self.is_suspended = (process_data['status'] == "Suspended")
        self.suspend_callback = suspend_callback
        self.trim_callback = trim_callback
        self.refresh_callback = refresh_callback  # Callback to refresh list after trim
        self.schedule_callback = schedule_callback  # Callback to open schedule dialog
        self.pin_callback = pin_callback  # Callback to toggle pin status
        self.memory_mb = process_data['memory']
        self.process_count = process_data['count']
        self.cpu_percent = process_data.get('cpu', 0.0)
        self.is_critical = process_data.get('is_critical', False)  # Critical system process
        self.has_schedule = process_data.get('has_schedule', False)  # Has scheduled action
        self.is_pinned = process_data.get('is_pinned', False)  # Pinned/favorite status
        self.is_trimmed = False  # Track if recently trimmed
        self._trim_reset_job = None  # Track the reset timer

        # Hover effect binding (Use specific events and direct callbacks)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        # Bind children but exclude buttons/interactive elements to avoid conflict
        for child in self.winfo_children():
            if not isinstance(child, (ctk.CTkButton, ctk.CTkEntry, ctk.CTkCheckBox, ctk.CTkSwitch)):
                child.bind("<Enter>", self._on_enter)
                child.bind("<Leave>", self._on_leave)

        # --- Layout ---

        # 1. Status Dot with glow effect (Left)
        self.dot_container = ctk.CTkFrame(self, fg_color="transparent", width=50)
        self.dot_container.pack(side="left", fill="y", padx=(20, 10))
        
        self.status_dot = ctk.CTkFrame(self.dot_container, width=14, height=14, corner_radius=7,
                                      border_width=2, border_color=ModernTheme.BG_CARD)
        self.status_dot.place(relx=0.5, rely=0.5, anchor="center")

        # 2. Text Info (Left, after dot)
        self.text_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.text_frame.pack(side="left", fill="both", expand=True, pady=14)

        self.name_label = ctk.CTkLabel(self.text_frame, text=self.proc_name, 
                                     font=ModernTheme.FONTS["title"], 
                                     text_color=ModernTheme.TEXT_MAIN, anchor="w")
        self.name_label.pack(anchor="w")
        
        # Memory bar visualization
        self.info_frame = ctk.CTkFrame(self.text_frame, fg_color="transparent")
        self.info_frame.pack(anchor="w", fill="x", pady=(4, 0))
        
        count_text = f"{self.process_count} process{'es' if self.process_count > 1 else ''}"
        cpu_text = f"CPU: {self.cpu_percent:.1f}%" if self.cpu_percent > 0 else ""
        detail_parts = [f"💾 {self.memory_mb} MB", count_text]
        if cpu_text:
            detail_parts.append(cpu_text)
        
        self.detail_label = ctk.CTkLabel(self.info_frame, 
                                       text=f"  •  ".join(detail_parts), 
                                       font=ModernTheme.FONTS["sub"], 
                                       text_color=ModernTheme.TEXT_SUB, anchor="w")
        self.detail_label.pack(side="left")
        
        # Remove the small progress bar - not needed for Task Manager match
        # Memory usage indicator (small progress bar)
        # self.mem_bar = ctk.CTkProgressBar(self.info_frame, width=100, height=4, corner_radius=2,
        #                                   fg_color="#1a1a1a", progress_color=ModernTheme.ACCENT_BLUE)
        # self.mem_bar.pack(side="left", padx=(10, 0))
        # # Normalize memory (assuming max 2000 MB for visualization, adjust as needed)
        # mem_ratio = min(self.memory_mb / 2000, 1.0)
        # self.mem_bar.set(mem_ratio)

        # 3. Actions (Right)
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.pack(side="right", padx=20, fill="y")
        
        # Suspend Button (Blue) - Pill Shape
        self.suspend_btn = ctk.CTkButton(self.actions_frame, text="⏸ Suspend", width=110, height=38,
                                      fg_color=ModernTheme.BTN_SUSPEND, hover_color=ModernTheme.BTN_SUSPEND_HOVER,
                                      font=ModernTheme.FONTS["btn"], corner_radius=ModernTheme.RADIUS_BTN,
                                      border_width=0, command=self.on_suspend)
        self.suspend_btn.pack(side="right", padx=(0, 8))

        # Trim Button (Purple) - Pill Shape
        self.trim_btn = ctk.CTkButton(self.actions_frame, text="⚡ Trim", width=110, height=38,
                                    fg_color=ModernTheme.BTN_TRIM, hover_color=ModernTheme.BTN_TRIM_HOVER,
                                    font=ModernTheme.FONTS["btn"], corner_radius=ModernTheme.RADIUS_BTN,
                                    border_width=0, command=self.on_trim_click)
        self.trim_btn.pack(side="right", padx=(8, 0))
        
        # Schedule Button (Clock icon) - Shows cyan if scheduled
        schedule_color = ModernTheme.ACCENT_BLUE if self.has_schedule else ModernTheme.BTN_SECONDARY
        schedule_hover = "#0891B2" if self.has_schedule else ModernTheme.BTN_SECONDARY_HOVER
        self.schedule_btn = ctk.CTkButton(self.actions_frame, text="🕐", width=40, height=36,
                                         fg_color=schedule_color, hover_color=schedule_hover,
                                         font=("Segoe UI", 14), corner_radius=8,
                                         border_width=0, command=self.on_schedule_click)
        self.schedule_btn.pack(side="right", padx=(0, 8))
        
        # Pin/Star Button - Shows gold when pinned
        pin_color = "#D97706" if self.is_pinned else ModernTheme.BTN_SECONDARY  # Gold/Amber when pinned
        pin_hover = "#F59E0B" if self.is_pinned else ModernTheme.BTN_SECONDARY_HOVER
        pin_text = "⭐" if self.is_pinned else "☆"
        self.pin_btn = ctk.CTkButton(self.actions_frame, text=pin_text, width=40, height=36,
                                    fg_color=pin_color, hover_color=pin_hover,
                                    font=("Segoe UI", 14), corner_radius=8,
                                    border_width=0, command=self.on_pin_click)
        self.pin_btn.pack(side="right", padx=(0, 8))

        self.update_visual_state()
    
    def _on_enter(self, event=None):
        self.configure(fg_color=ModernTheme.BG_CARD_HOVER)
    
    def _on_leave(self, event=None):
        self.configure(fg_color=ModernTheme.BG_CARD)

    def update_visual_state(self):
        if self.is_suspended:
            # Suspended state - RED indicator
            self.status_dot.configure(fg_color="#EF4444", border_color="#EF4444")  # Red
            self.configure(border_width=2, border_color="#7F1D1D")  # Dark red border
            self.suspend_btn.configure(text="▶ Resume", fg_color="#374151", 
                                     hover_color="#4B5563")
            self.trim_btn.configure(state="disabled", fg_color="#2a2a2a", hover_color="#2a2a2a")
            self.name_label.configure(text_color="#FCA5A5")  # Light red text
            self.detail_label.configure(text_color=ModernTheme.TEXT_DIM)
        elif self.is_trimmed:
            # Trimmed state - GREEN indicator
            self.status_dot.configure(fg_color=ModernTheme.DOT_RUNNING, border_color=ModernTheme.DOT_RUNNING)
            self.configure(border_width=2, border_color="#166534")  # Dark green border
            self.suspend_btn.configure(text="⏸ Suspend", fg_color=ModernTheme.BTN_SUSPEND, 
                                     hover_color=ModernTheme.BTN_SUSPEND_HOVER)
            self.trim_btn.configure(state="normal", fg_color=ModernTheme.DOT_RUNNING, 
                                  hover_color="#34D399", text="✓ Done")
            self.name_label.configure(text_color="#86EFAC")  # Light green text
            self.detail_label.configure(text_color=ModernTheme.DOT_RUNNING)
        elif self.is_critical:
            # Critical system process - AMBER warning indicator
            self.status_dot.configure(fg_color="#F59E0B", border_color="#F59E0B")  # Amber
            self.configure(border_width=2, border_color="#92400E")  # Dark amber border
            self.suspend_btn.configure(text="⚠️ Suspend", fg_color="#B45309", 
                                     hover_color="#D97706")  # Warning orange
            self.trim_btn.configure(state="normal", fg_color=ModernTheme.BTN_TRIM, 
                                  hover_color=ModernTheme.BTN_TRIM_HOVER, text="⚡ Trim")
            self.name_label.configure(text_color="#FCD34D")  # Amber text
            self.detail_label.configure(text_color="#FBBF24")  # Lighter amber
        else:
            # Normal running state
            self.status_dot.configure(fg_color=ModernTheme.DOT_RUNNING, border_color=ModernTheme.DOT_RUNNING)
            self.configure(border_width=0, border_color=ModernTheme.BG_CARD)
            self.suspend_btn.configure(text="⏸ Suspend", fg_color=ModernTheme.BTN_SUSPEND, 
                                     hover_color=ModernTheme.BTN_SUSPEND_HOVER)
            self.trim_btn.configure(state="normal", fg_color=ModernTheme.BTN_TRIM, 
                                  hover_color=ModernTheme.BTN_TRIM_HOVER, text="⚡ Trim")
            self.name_label.configure(text_color=ModernTheme.TEXT_MAIN)
            self.detail_label.configure(text_color=ModernTheme.TEXT_SUB)

    def on_suspend(self):
        success = self.suspend_callback(self.proc_name, not self.is_suspended)
        if success:
            self.is_suspended = not self.is_suspended
            self.update_visual_state()

    def update_data(self, process_data):
        self.memory_mb = process_data['memory']
        self.process_count = process_data['count']
        self.cpu_percent = process_data.get('cpu', 0.0)
        new_status = process_data['status']
        new_is_critical = process_data.get('is_critical', False)
        new_has_schedule = process_data.get('has_schedule', False)
        
        # Check if visual state needs update
        status_changed = (self.is_suspended and new_status != "Suspended") or \
                        (not self.is_suspended and new_status == "Suspended")
        critical_changed = self.is_critical != new_is_critical
        schedule_changed = self.has_schedule != new_has_schedule
        
        self.is_critical = new_is_critical
        self.has_schedule = new_has_schedule
        
        # Check pinned status
        new_is_pinned = process_data.get('is_pinned', False)
        pinned_changed = self.is_pinned != new_is_pinned
        self.is_pinned = new_is_pinned
        
        if status_changed:
            self.is_suspended = (new_status == "Suspended")
            self.update_visual_state()
        elif critical_changed:
            self.update_visual_state()
        
        # Update schedule button color if changed
        if schedule_changed:
            schedule_color = ModernTheme.ACCENT_BLUE if self.has_schedule else ModernTheme.BTN_SECONDARY
            schedule_hover = "#0891B2" if self.has_schedule else ModernTheme.BTN_SECONDARY_HOVER
            self.schedule_btn.configure(fg_color=schedule_color, hover_color=schedule_hover)
        
        # Update pin button if changed
        if pinned_changed:
            pin_color = "#D97706" if self.is_pinned else ModernTheme.BTN_SECONDARY
            pin_hover = "#F59E0B" if self.is_pinned else ModernTheme.BTN_SECONDARY_HOVER
            pin_text = "⭐" if self.is_pinned else "☆"
            self.pin_btn.configure(text=pin_text, fg_color=pin_color, hover_color=pin_hover)
            
        # Update text
        count_text = f"{self.process_count} process{'es' if self.process_count > 1 else ''}"
        cpu_text = f"CPU: {self.cpu_percent:.1f}%" if self.cpu_percent > 0 else ""
        detail_parts = [f"💾 {self.memory_mb} MB", count_text]
        if cpu_text:
            detail_parts.append(cpu_text)
        
        # Add pinned indicator
        if self.is_pinned:
            detail_parts.append("⭐ Pinned")
        
        # Add warning for critical processes
        if self.is_critical:
            detail_parts.append("⚠️ System")
        
        # Add schedule indicator
        if self.has_schedule:
            detail_parts.append("🕐 Scheduled")
        
        # Check if we are currently showing a "Saved" message (trim result)
        if self.detail_label.cget("text_color") != ModernTheme.DOT_RUNNING:
            text_color = ModernTheme.TEXT_SUB
            if self.is_pinned:
                text_color = "#FBBF24"  # Gold for pinned
            elif self.is_critical:
                text_color = "#FBBF24"
            self.detail_label.configure(
                text=f"  •  ".join(detail_parts), 
                text_color=text_color
            )
    
    def on_schedule_click(self):
        """Open schedule dialog for this app"""
        if self.schedule_callback:
            self.schedule_callback(self.proc_name, self.has_schedule)
    
    def on_pin_click(self):
        """Toggle pin/favorite status for this app"""
        if self.pin_callback:
            new_status = self.pin_callback(self.proc_name)
            self.is_pinned = new_status
            
            # Update button appearance
            pin_color = "#D97706" if self.is_pinned else ModernTheme.BTN_SECONDARY
            pin_hover = "#F59E0B" if self.is_pinned else ModernTheme.BTN_SECONDARY_HOVER
            pin_text = "⭐" if self.is_pinned else "☆"
            self.pin_btn.configure(text=pin_text, fg_color=pin_color, hover_color=pin_hover)

    def on_trim_click(self):
        # Cancel any pending reset
        if self._trim_reset_job:
            self.after_cancel(self._trim_reset_job)
            self._trim_reset_job = None
            
        self.trim_btn.configure(text="Working...", fg_color="#444444", state="disabled")
        threading.Thread(target=self._trim_worker, daemon=True).start()

    def _trim_worker(self):
        new_total = self.trim_callback(self.proc_name)
        self.after(0, lambda: self._trim_finished(new_total))

    def _trim_finished(self, new_total):
        if new_total is not None:
            old_memory = self.memory_mb
            self.memory_mb = new_total
            
            # Update memory display with visual feedback
            count_text = f"{self.process_count} process{'es' if self.process_count > 1 else ''}"
            saved = round(old_memory - new_total, 1)
            
            if saved > 0:
                self.detail_label.configure(
                    text=f"� {new_total} MB  •  {count_text}  •  Saved: {saved} MB"
                )
            else:
                self.detail_label.configure(text=f"� {new_total} MB  •  {count_text}")
        
        # Set trimmed state and update visuals
        self.is_trimmed = True
        self.update_visual_state()
        
        # Reset to normal state after 2 seconds and trigger refresh
        def reset_trim_state():
            self.is_trimmed = False
            self._trim_reset_job = None
            if not self.is_suspended:
                self.update_visual_state()
            # Trigger a silent refresh to update all memory values
            if self.refresh_callback:
                self.refresh_callback()
        
        self._trim_reset_job = self.after(2000, reset_trim_state)

class AppSuspender(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CryoTask - Process Manager & RAM Optimizer")
        self.geometry("1000x750")
        self.minsize(800, 600)
        self.configure(fg_color=ModernTheme.BG_ROOT)
        
        # Set app icon (snowflake hexagon icon)
        try:
            icon_path = resource_path("assets/app_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass  # Icon loading is optional
        
        # Center window on screen
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        # Admin check
        if not is_admin():
            if messagebox.askyesno("Permission", "Restart as Administrator?"):
                run_as_admin()
                sys.exit()

        # Refresh state
        self.is_refreshing = False  # Prevent concurrent refreshes
        
        # Safe Mode: Only show user-facing apps, block critical processes
        self.safe_mode = True  # Default to safe mode
        
        self.setup_ui()
        
        # State for diff-based updates
        self.card_map = {} # name -> ProcessCard widget
        self.card_rows = [] # Ordered list of widgets
        
        # Scheduled actions cache
        self.scheduled_apps = get_apps_with_schedules()
        
        # Pinned apps cache
        self.pinned_apps = set(load_pinned_apps())
        
        self.refresh_list()
        
        # Start scheduler for periodic tasks
        self._start_scheduler()

    def setup_ui(self):
        # 1. Header Area - Enhanced
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=70)
        self.header_frame.pack(fill="x", padx=30, pady=(30, 15))

        # Title with icon
        title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(title_frame, text=Strings.APP_NAME, font=ModernTheme.FONTS["header"], 
                     text_color=ModernTheme.TEXT_MAIN).pack(side="left")
        
        subtitle = ctk.CTkLabel(title_frame, text=Strings.APP_SUBTITLE, 
                               font=ModernTheme.FONTS["sub"], 
                               text_color=ModernTheme.TEXT_SUB)
        subtitle.pack(side="left", padx=(12, 0))

        # Refresh button - Pill Shape
        self.refresh_btn = ctk.CTkButton(self.header_frame, text=Strings.BTN_REFRESH, width=110, height=38,
                                       fg_color=ModernTheme.BG_CARD, border_width=0, 
                                       text_color=ModernTheme.TEXT_MAIN, 
                                       hover_color=ModernTheme.BG_CARD_HOVER,
                                       font=ModernTheme.FONTS["btn"],
                                       corner_radius=ModernTheme.RADIUS_BTN,
                                       command=self.refresh_list)
        self.refresh_btn.pack(side="right")
        
        # Safe Mode Toggle Button - Pill Shape
        self.mode_btn = ctk.CTkButton(self.header_frame, text=Strings.BTN_SAFE_MODE, width=130, height=38,
                                     fg_color="#15803d",  # Soft Green
                                     hover_color="#166534",
                                     text_color=ModernTheme.TEXT_MAIN,
                                     font=ModernTheme.FONTS["btn"],
                                     corner_radius=ModernTheme.RADIUS_BTN,
                                     command=self.toggle_mode)
        self.mode_btn.pack(side="right", padx=(0, 12))
        
        # Info Button - Circle/Pill
        self.info_btn = ctk.CTkButton(self.header_frame, text="ℹ️", width=42, height=38,
                                     fg_color=ModernTheme.BG_CARD, border_width=0,
                                     text_color=ModernTheme.TEXT_MAIN,
                                     hover_color=ModernTheme.BG_CARD_HOVER,
                                     font=("Segoe UI", 16),
                                     corner_radius=ModernTheme.RADIUS_BTN,
                                     command=self.show_info_dialog)
        self.info_btn.pack(side="right", padx=(0, 12))
        
        # 1.5 System Memory Overview - Material Card
        self.system_overview = ctk.CTkFrame(self, fg_color=ModernTheme.BG_CARD, 
                                           corner_radius=ModernTheme.RADIUS_CARD, border_width=0, 
                                           height=90)
        self.system_overview.pack(fill="x", padx=30, pady=(0, 15))
        self.system_overview.pack_propagate(False)
        
        # System stats - horizontal layout
        stats_container = ctk.CTkFrame(self.system_overview, fg_color="transparent")
        stats_container.pack(expand=True, fill="both", padx=20, pady=15)
        
        # Memory stat
        mem_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        mem_frame.pack(side="left", expand=True, fill="both")
        
        ctk.CTkLabel(mem_frame, text=Strings.LABEL_SYSTEM_MEMORY, font=ModernTheme.FONTS["sub"], 
                    text_color=ModernTheme.TEXT_SUB).pack(anchor="w")
        self.sys_mem_label = ctk.CTkLabel(mem_frame, text="0 / 0 GB (0%)", 
                                         font=ModernTheme.FONTS["title"], 
                                         text_color=ModernTheme.TEXT_MAIN)
        self.sys_mem_label.pack(anchor="w", pady=(2, 0))
        
        # Memory progress bar
        self.sys_mem_bar = ctk.CTkProgressBar(mem_frame, width=200, height=6, corner_radius=3,
                                             fg_color="#1a1a1a", progress_color=ModernTheme.ACCENT_BLUE)
        self.sys_mem_bar.pack(anchor="w", pady=(6, 0))
        self.sys_mem_bar.set(0)
        
        # CPU stat
        cpu_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        cpu_frame.pack(side="left", expand=True, fill="both")
        
        ctk.CTkLabel(cpu_frame, text=Strings.LABEL_CPU_USAGE, font=ModernTheme.FONTS["sub"], 
                    text_color=ModernTheme.TEXT_SUB).pack(anchor="w")
        self.sys_cpu_label = ctk.CTkLabel(cpu_frame, text="0%", 
                                         font=ModernTheme.FONTS["title"], 
                                         text_color=ModernTheme.TEXT_MAIN)
        self.sys_cpu_label.pack(anchor="w", pady=(2, 0))
        
        # Processes count
        proc_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        proc_frame.pack(side="left", expand=True, fill="both")
        
        ctk.CTkLabel(proc_frame, text=Strings.LABEL_PROCESSES, font=ModernTheme.FONTS["sub"], 
                    text_color=ModernTheme.TEXT_SUB).pack(anchor="w")
        self.sys_proc_label = ctk.CTkLabel(proc_frame, text="0", 
                                          font=ModernTheme.FONTS["title"], 
                                          text_color=ModernTheme.TEXT_MAIN)
        self.sys_proc_label.pack(anchor="w", pady=(2, 0))

        # 2. Search Bar - Enhanced with icon
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=30, pady=(0, 15))
        
        # Search container with pill shape
        search_container = ctk.CTkFrame(self.search_frame, fg_color=ModernTheme.BG_SEARCH, 
                                       corner_radius=ModernTheme.RADIUS_BTN, border_width=0)
        search_container.pack(fill="x")
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_list)
        
        # Search icon label
        search_icon = ctk.CTkLabel(search_container, text="🔍", font=("Segoe UI", 14))
        search_icon.pack(side="left", padx=(15, 8))
        
        self.search_entry = ctk.CTkEntry(search_container, placeholder_text="Search processes by name...", 
                                       height=42, corner_radius=0, border_width=0,
                                       fg_color="transparent", 
                                       text_color=ModernTheme.TEXT_MAIN, 
                                       placeholder_text_color=ModernTheme.TEXT_DIM,
                                       font=ModernTheme.FONTS["sub"], 
                                       textvariable=self.search_var)
        self.search_entry.pack(side="left", fill="both", expand=True, padx=(0, 15))

        # 3. Scrollable List Area - Enhanced
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=30, pady=(0, 15))
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.container, fg_color="transparent",
                                                   corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True)
        
        # Enable smooth and faster scrolling
        self._setup_smooth_scroll()

        # 4. Status Bar - Enhanced
        status_frame = ctk.CTkFrame(self, fg_color=ModernTheme.BG_CONTAINER, height=35)
        status_frame.pack(side="bottom", fill="x", padx=0, pady=0)
        status_frame.pack_propagate(False)
        
        self.status_bar = ctk.CTkLabel(status_frame, text="● Ready", 
                                     font=ModernTheme.FONTS["status"], 
                                     text_color=ModernTheme.TEXT_SUB)
        self.status_bar.pack(side="left", padx=30, pady=8)
        
        # Subtle GitHub Button embedded in footer
        def open_github():
            import webbrowser
            webbrowser.open(Strings.INFO_GITHUB_URL)

        self.github_footer_btn = ctk.CTkButton(status_frame, text="GitHub", width=60, height=20,
                                             font=("Cascadia Mono", 12),
                                             fg_color="#2c2c2c",
                                             hover_color=ModernTheme.BG_CARD_HOVER,
                                             text_color=ModernTheme.TEXT_DIM,
                                             command=open_github)
        self.github_footer_btn.pack(side="right", padx=(0, 30))
        
        # Memory summary (will be updated)
        self.memory_summary = ctk.CTkLabel(status_frame, text="", 
                                         font=ModernTheme.FONTS["status"], 
                                         text_color=ModernTheme.TEXT_SUB)
        self.memory_summary.pack(side="right", padx=30, pady=8)
    
    def _setup_smooth_scroll(self):
        """Setup smooth animated scrolling"""
        self._scroll_animation_running = False
        self._target_scroll = 0
        self._current_scroll = 0
        
        def _on_mousewheel(event):
            # Calculate target scroll position
            scroll_amount = int(-1 * (event.delta / 120) * 15)  # Balanced scroll distance
            
            # Get current scroll position
            canvas = self.scroll_frame._parent_canvas
            scroll_region = canvas.cget("scrollregion").split()
            if len(scroll_region) == 4:
                total_height = float(scroll_region[3])
                if total_height > 0:
                    current_pos = canvas.yview()[0] * total_height
                    self._target_scroll = current_pos + (scroll_amount * 8)  # Multiply for pixel-based scrolling
                    
                    # Start smooth animation if not already running
                    if not self._scroll_animation_running:
                        self._current_scroll = current_pos
                        self._animate_scroll()
        
        def _animate_scroll_step():
            """Single step of scroll animation"""
            canvas = self.scroll_frame._parent_canvas
            scroll_region = canvas.cget("scrollregion").split()
            if len(scroll_region) != 4:
                self._scroll_animation_running = False
                return
                
            total_height = float(scroll_region[3])
            if total_height == 0:
                self._scroll_animation_running = False
                return
            
            # Smooth interpolation (ease-out)
            diff = self._target_scroll - self._current_scroll
            
            if abs(diff) < 1:
                # Close enough, stop animation
                self._scroll_animation_running = False
                return
            
            # Adaptive Animation: Adjust speed based on load
            card_count = len(self.card_rows)
            
            # Base values
            speed_factor = 0.25 # Movement per frame (0.25 = 25% of distance)
            frame_delay = 16    # Target ~60 FPS
            
            # If under heavy load (many cards), reduce overhead
            if card_count > 50:
                speed_factor = 0.45  # Move faster (fewer frames needed)
                frame_delay = 25     # Lower FPS (~40 FPS) to reduce CPU load
            elif card_count > 25:
                speed_factor = 0.35
            
            # Move towards target (smooth deceleration)
            step = diff * speed_factor
            self._current_scroll += step
            
            # Update canvas scroll position
            new_fraction = self._current_scroll / total_height
            canvas.yview_moveto(max(0, min(1, new_fraction)))
            
            # Continue animation
            self.after(frame_delay, _animate_scroll_step)
        
        self._animate_scroll = lambda: (
            setattr(self, '_scroll_animation_running', True),
            _animate_scroll_step()
        )
        
        # Bind to the canvas inside the scrollable frame
        self.scroll_frame._parent_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Store binding so we can clean up later if needed
        self._mousewheel_binding = _on_mousewheel
    
    def toggle_mode(self):
        """Toggle between Safe Mode and Advanced Mode"""
        if self.safe_mode:
            # Switching to Advanced Mode - show warning
            result = messagebox.askyesno(
                Strings.WARN_ADVANCED_TITLE,
                Strings.WARN_ADVANCED_MSG,
                icon='warning'
            )
            if result:
                self.safe_mode = False
                self.auto_refresh_interval = 5000  # Slower refresh in Advanced Mode
                self.mode_btn.configure(
                    text=Strings.BTN_ADVANCED_MODE,
                    fg_color="#991B1B",  # Red for danger
                    hover_color="#B91C1C"
                )
                # Clear existing cards when switching modes
                for card in list(self.card_map.values()):
                    card.destroy()
                self.card_map.clear()
                self.card_rows.clear()
                self.refresh_list()
        else:
            # Switching back to Safe Mode
            self.safe_mode = True
            self.auto_refresh_interval = 3000  # Faster refresh in Safe Mode
            self.mode_btn.configure(
                text=Strings.BTN_SAFE_MODE,
                fg_color="#166534",  # Green for safe
                hover_color="#15803d"
            )
            # Clear existing cards when switching modes
            for card in list(self.card_map.values()):
                card.destroy()
            self.card_map.clear()
            self.card_rows.clear()
            self.refresh_list()

            self.card_rows.clear()
            self.refresh_list()

    def get_visible_windows_info(self):
        visible_map = {}
        def enum_window_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                visible_map[pid] = True
        try: win32gui.EnumWindows(enum_window_callback, None)
        except: pass
        return visible_map

    def toggle_pin_status(self, app_name):
        return toggle_pinned_app(app_name)

    def toggle_group_state(self, proc_name, suspend):
        success = False
        try:
            save_suspended_state(proc_name, suspend)
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] == proc_name:
                    try:
                        p = psutil.Process(proc.info['pid'])
                        if suspend: p.suspend()
                        else: p.resume()
                        success = True
                    except: pass
        except: pass
        return success

    def trim_group(self, proc_name):
        try:
            for proc in psutil.process_iter(['name', 'pid']):
                if proc.info['name'] == proc_name:
                    trim_pid(proc.info['pid'])
        except: pass
        return int(get_process_group_memory(proc_name))

    def _start_scheduler(self):
        def loop():
            while True:
                time.sleep(60)
                self._check_tasks()
        threading.Thread(target=loop, daemon=True).start()
        
    def _check_tasks(self):
        try:
            data = load_scheduled_actions()
            now = time.time()
            changed = False
            for app, conf in data.get("periodic_trim", {}).items():
                if conf.get("enabled"):
                    if now - conf.get("last_run", 0) >= conf.get("interval", 15) * 60:
                        self.trim_group(app)
                        conf["last_run"] = now
                        changed = True
            if changed: save_scheduled_actions(data)
        except: pass

    def open_schedule_dialog(self, app_name, has_schedule):
        dialog = ctk.CTkToplevel(self)
        dialog.title(Strings.SCHEDULE_TITLE.format(app_name=app_name))
        dialog.geometry("420x350")
        dialog.configure(fg_color=ModernTheme.BG_ROOT)
        try: dialog.attributes('-topmost', True)
        except: pass
        
        # Center dialog
        dialog.update_idletasks()
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - (210)
            y = self.winfo_y() + (self.winfo_height() // 2) - (175)
            dialog.geometry(f"+{x}+{y}")
        except: pass

        ctk.CTkLabel(dialog, text=Strings.SCHEDULE_TITLE.format(app_name=app_name), 
                    font=ModernTheme.FONTS["title"], text_color=ModernTheme.TEXT_MAIN).pack(pady=20)
        
        trim_frame = ctk.CTkFrame(dialog, fg_color=ModernTheme.BG_CARD, corner_radius=12)
        trim_frame.pack(fill="x", padx=20, pady=10)
        
        trim_data = load_scheduled_actions().get("periodic_trim", {}).get(app_name, {})
        trim_enabled = ctk.BooleanVar(value=trim_data.get("enabled", False))
        
        ctk.CTkSwitch(trim_frame, text=Strings.SCHEDULE_PERIODIC_TRIM, variable=trim_enabled,
                     font=ModernTheme.FONTS["sub"], text_color=ModernTheme.TEXT_MAIN,
                     progress_color=ModernTheme.BTN_TRIM).pack(anchor="w", padx=15, pady=15)
                     
        settings_frame = ctk.CTkFrame(trim_frame, fg_color="transparent")
        settings_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        interval_var = ctk.StringVar(value=str(trim_data.get("interval", 15)))
        ctk.CTkLabel(settings_frame, text=Strings.SCHEDULE_TRIM_EVERY, font=ModernTheme.FONTS["sub"], text_color=ModernTheme.TEXT_SUB).pack(side="left")
        ctk.CTkEntry(settings_frame, width=50, textvariable=interval_var, fg_color=ModernTheme.BG_SEARCH, border_width=0).pack(side="left", padx=10)
        ctk.CTkLabel(settings_frame, text=Strings.SCHEDULE_MINUTES, font=ModernTheme.FONTS["sub"], text_color=ModernTheme.TEXT_SUB).pack(side="left")
        
        def save():
            try: interval = int(interval_var.get())
            except: interval = 15
            if trim_enabled.get(): add_periodic_trim(app_name, interval)
            else: remove_periodic_trim(app_name)
            self.scheduled_apps = get_apps_with_schedules()
            self.refresh_list(silent=True)
            dialog.destroy()
            
        def remove():
            remove_periodic_trim(app_name)
            self.scheduled_apps = get_apps_with_schedules()
            self.refresh_list(silent=True)
            dialog.destroy()

        btn_row = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_row.pack(pady=20)
        ctk.CTkButton(btn_row, text=Strings.BTN_SAVE, command=save, width=100, fg_color=ModernTheme.ACCENT_BLUE, hover_color="#0891B2").pack(side="left", padx=5)
        if has_schedule:
            ctk.CTkButton(btn_row, text=Strings.BTN_REMOVE_ALL, command=remove, fg_color="#991b1b", hover_color="#7f1d1d", width=100).pack(side="left", padx=5)

    def refresh_list(self, silent=False, visible_only=False):
        # Prevent concurrent refreshes
        if self.is_refreshing:
            return
            
        self.is_refreshing = True
        
        if not silent:
            self.refresh_btn.configure(state="disabled", text="⏳ Scanning...")
            self.status_bar.configure(text="● Scanning processes...", text_color=ModernTheme.ACCENT_BLUE)
        
        threading.Thread(target=self._scan_process_thread, daemon=True, args=(silent, visible_only)).start()
    
    def _check_window_focus(self):
        """Check if this window currently has focus"""
        try:
            # Get the window handle using the window title
            window_title = self.title()
            hwnd = win32gui.FindWindow(None, window_title)
            
            if hwnd != 0:
                focused_hwnd = win32gui.GetForegroundWindow()
                # Check if our window has focus or if focused window is a child
                if hwnd == focused_hwnd:
                    return True
                # Check if focused window is a child of our window
                try:
                    parent = win32gui.GetParent(focused_hwnd)
                    while parent != 0:
                        if parent == hwnd:
                            return True
                        parent = win32gui.GetParent(parent)
                except:
                    pass
        except Exception:
            pass
        
        # Fallback: use tkinter's focus check
        try:
            return self.focus_get() is not None
        except:
            # If all else fails, assume focused (safer for auto-refresh)
            return True

    def _scan_process_thread(self, silent=False, visible_only=False):
        final_list = []
        visible_pids = self.get_visible_windows_info()
        visible_pid_set = set(visible_pids.keys())  # Convert to set for O(1) lookup
        
        process_groups = defaultdict(lambda: {'mem': 0, 'count': 0, 'status': 'Running', 'cpu': 0.0, 'has_window': False})
        
        # Cache suspended state once (avoid repeated file reads)
        suspended_apps_history = set(load_suspended_state())  # Convert to set for O(1) lookup
        
        # Get current mode
        safe_mode = self.safe_mode
        
        # If visible_only mode, get the list of currently displayed process names
        existing_card_names = set(self.card_map.keys()) if visible_only else set()
        
        # Get system stats
        sys_mem = psutil.virtual_memory()
        sys_cpu = psutil.cpu_percent(interval=0.1)
        total_processes = 0
        
        # Track which process names have visible windows
        visible_process_names = set()

        try:
            # Single pass through all processes
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'status', 'cpu_percent']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    name_lower = name.lower()
                    
                    # Skip excluded processes (CryoTask itself, IDEs, system processes)
                    if name_lower in EXCLUDED_PROCESSES:
                        continue
                    
                    # In visible_only mode, skip processes we're not already showing
                    if visible_only and name not in existing_card_names:
                        continue
                    
                    mem = proc.info['memory_info'].rss
                    cpu = proc.info.get('cpu_percent', 0.0) or 0.0
                    
                    process_groups[name]['mem'] += mem
                    process_groups[name]['cpu'] += cpu
                    process_groups[name]['count'] += 1
                    total_processes += 1
                    
                    # Check if this PID has a visible window
                    if pid in visible_pid_set:
                        visible_process_names.add(name)
                        process_groups[name]['has_window'] = True
                    
                    # Check suspended status
                    if proc.info['status'] == 'suspended':
                        process_groups[name]['status'] = 'Suspended'
                    elif name in suspended_apps_history:
                        process_groups[name]['status'] = 'Suspended'
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Build final list based on mode
            if visible_only:
                # Visible-only mode: Only update existing cards
                process_names_to_show = existing_card_names
            elif safe_mode:
                # Safe Mode: Only show processes with visible windows (user-facing apps)
                process_names_to_show = visible_process_names
            else:
                # Advanced Mode: Show all processes (including background ones)
                process_names_to_show = set(process_groups.keys())
            
            for name in process_names_to_show:
                name_lower = name.lower()
                
                # In Safe Mode, skip critical system processes entirely
                if safe_mode and not visible_only and name_lower in CRITICAL_SYSTEM_PROCESSES:
                    continue
                
                # Skip if no data collected (process ended)
                if name not in process_groups:
                    continue
                
                group_data = process_groups[name]
                total_mem_mb = round(group_data['mem'] / 1048576, 1)  # 1024*1024 = 1048576
                total_cpu = round(group_data['cpu'], 1)
                
                # Mark if this is a critical process (for UI warning)
                is_critical = name_lower in CRITICAL_SYSTEM_PROCESSES
                
                final_list.append({
                    "name": name,
                    "status": group_data['status'],
                    "memory": total_mem_mb,
                    "count": group_data['count'],
                    "cpu": total_cpu,
                    "is_critical": is_critical,
                    "has_window": group_data['has_window']
                })
                
        except Exception as e: 
            print(e)
        
        # Sort by memory and limit to top 75 processes for performance (only for full refresh)
        final_list.sort(key=lambda x: x['memory'], reverse=True)
        if not visible_only and len(final_list) > 75:
            final_list = final_list[:75]

        # Pass system stats along with process list
        system_stats = {
            'mem_used_gb': round(sys_mem.used / 1073741824, 1),  # 1024**3 = 1073741824
            'mem_total_gb': round(sys_mem.total / 1073741824, 1),
            'mem_percent': sys_mem.percent,
            'cpu_percent': sys_cpu,
            'total_processes': total_processes
        }
        
        self.after(0, lambda: self._update_ui_list(final_list, system_stats, silent, visible_only))

    def _update_ui_list(self, data, system_stats, silent=False, visible_only=False):
        try:
            self._update_ui_list_safe(data, system_stats, silent, visible_only)
        except Exception as e:
            import traceback
            err = traceback.format_exc()
            try: messagebox.showerror("Error", f"Update Error: {err}")
            except: print(err)

    def _update_ui_list_safe(self, data, system_stats, silent=False, visible_only=False):
        # Sort data: Pinned first (Descending), then Memory (Descending)
        # We add 'is_pinned' to data for sorting if not present
        for p in data:
            p['is_pinned'] = p['name'] in self.pinned_apps
            
        data.sort(key=lambda x: (x['is_pinned'], x['memory']), reverse=True)
        total_memory = sum(p['memory'] for p in data)
        
        # Update system overview (always update this)
        self.sys_mem_label.configure(
            text=f"{system_stats['mem_used_gb']} / {system_stats['mem_total_gb']} GB ({system_stats['mem_percent']:.0f}%)"
        )
        self.sys_mem_bar.set(system_stats['mem_percent'] / 100)
        self.sys_cpu_label.configure(text=f"{system_stats['cpu_percent']:.1f}%")
        self.sys_proc_label.configure(text=f"{system_stats['total_processes']} total")
        
        # Update color of memory bar based on usage
        if system_stats['mem_percent'] > 80:
            self.sys_mem_bar.configure(progress_color="#EF4444")  # Red
        elif system_stats['mem_percent'] > 60:
            self.sys_mem_bar.configure(progress_color="#F59E0B")  # Amber
        else:
            self.sys_mem_bar.configure(progress_color=ModernTheme.ACCENT_BLUE)
        
        # In visible_only mode, just update existing cards data without creating/removing
        if visible_only:
            data_map = {p['name']: p for p in data}
            for name, card in self.card_map.items():
                if name in data_map:
                    card.update_data(data_map[name])
            self.is_refreshing = False
            return
        
        current_names = set(item['name'] for item in data)
        
        # 1. Remove old cards - batch the destruction
        cards_to_remove = [name for name in self.card_map.keys() if name not in current_names]
        for name in cards_to_remove:
            self.card_map[name].pack_forget()  # Unpack first
        for name in cards_to_remove:
            self.card_map[name].destroy()
            del self.card_map[name]
        
        # 2. Update existing and create new cards
        self.card_rows = []
        new_cards = []  # Batch new card creation
        
        for p_data in data:
            name = p_data['name']
            # Add schedule status to process data
            p_data['has_schedule'] = name in self.scheduled_apps
            
            if name in self.card_map:
                card = self.card_map[name]
                card.update_data(p_data)
            else:
                card = ProcessCard(self.scroll_frame, p_data, self.toggle_group_state, self.trim_group, 
                                  refresh_callback=lambda: self.refresh_list(silent=True),
                                  schedule_callback=self.open_schedule_dialog,
                                  pin_callback=self.toggle_pin_status)
                self.card_map[name] = card
                new_cards.append(card)
            
            self.card_rows.append(card)
        
        # Reset refresh state
        self.is_refreshing = False
        
        if not silent:
            self.refresh_btn.configure(state="normal", text="⟳ Refresh")
        
        # Enhanced status with memory info
        total_shown = len(data)
        if total_shown > 0:
            total_gb = round(total_memory / 1024, 2)
            mode_indicator = "Safe" if self.safe_mode else "Advanced"
            self.status_bar.configure(
                text=f"● {total_shown} app{'s' if total_shown != 1 else ''} ({mode_indicator})", 
                text_color=ModernTheme.TEXT_SUB
            )
            self.memory_summary.configure(
                text=f"Total Memory: {total_gb} GB",
                text_color=ModernTheme.ACCENT_BLUE
            )
        else:
            self.status_bar.configure(text="● No applications found", text_color=ModernTheme.TEXT_DIM)
            self.memory_summary.configure(text="")
        
        self.filter_list()

    def filter_list(self, *args):
        query = self.search_var.get().lower()
        visible_count = 0
        cards = self.card_rows
        
        if not query:
            # No filter - show all cards efficiently
            for card in cards:
                card.pack(fill="x", pady=8)
            visible_count = len(cards)
        else:
            # Filter with cached lowercase name
            for card in cards:
                if query in card.proc_name_lower:
                    card.pack(fill="x", pady=8)
                    visible_count += 1
                else:
                    card.pack_forget()
        
        # Update status when filtering
        if query:
            if visible_count > 0:
                self.status_bar.configure(
                    text=f"● Showing {visible_count} of {len(cards)} applications",
                    text_color=ModernTheme.TEXT_SUB
                )
            else:
                self.status_bar.configure(
                    text=f"● No results for '{query}'",
                    text_color=ModernTheme.TEXT_DIM
                )

    def trim_group(self, process_name):
        for p in psutil.process_iter(['pid', 'name']):
            if p.info['name'] == process_name:
                trim_pid(p.info['pid'])
        return get_process_group_memory(process_name)

    def toggle_group_state(self, process_name, suspend_action):
        save_suspended_state(process_name, suspend_action)
        for p in psutil.process_iter(['pid', 'name']):
            if p.info['name'] == process_name:
                try:
                    pid = p.info['pid']
                    proc = psutil.Process(pid)
                    ACCESS = win32con.PROCESS_SUSPEND_RESUME | win32con.PROCESS_QUERY_INFORMATION
                    handle = win32api.OpenProcess(ACCESS, False, pid)
                    threads = proc.threads()
                    for t in threads:
                        t_handle = win32api.OpenThread(win32con.THREAD_SUSPEND_RESUME, False, t.id)
                        if t_handle:
                            if suspend_action: win32process.SuspendThread(t_handle)
                            else:
                                while True:
                                    if win32process.ResumeThread(t_handle) <= 1: break
                            win32api.CloseHandle(t_handle)
                    win32api.CloseHandle(handle)
                except: pass
        return True 

    def toggle_pin_status(self, process_name):
        """Toggle pinned status for an app"""
        new_status = toggle_pinned_app(process_name)
        if new_status:
            self.pinned_apps.add(process_name)
        else:
            if process_name in self.pinned_apps: self.pinned_apps.remove(process_name)
        
        # Trigger immediate refresh to re-sort list
        self.refresh_list(silent=True)
        return new_status 
    
    # --- Scheduled Actions ---
    
    def _start_scheduler(self):
        """Start the scheduler for periodic tasks"""
        self._scheduler_job = self.after(60000, self._run_scheduled_tasks)  # Check every 60 seconds
    
    def _run_scheduled_tasks(self):
        """Execute any scheduled tasks that are due"""
        import time
        current_time = time.time()
        data = load_scheduled_actions()
        tasks_ran = False
        
        # Check periodic trim tasks
        for app_name, config in data.get("periodic_trim", {}).items():
            if not config.get("enabled", False):
                continue
            
            interval_seconds = config.get("interval", 15) * 60  # Convert minutes to seconds
            last_run = config.get("last_run", 0)
            
            if current_time - last_run >= interval_seconds:
                # Time to trim!
                self.trim_group(app_name)
                data["periodic_trim"][app_name]["last_run"] = current_time
                tasks_ran = True
        
        # Check RAM threshold (auto-suspend when RAM > threshold)
        ram_config = data.get("ram_threshold", {})
        if ram_config.get("enabled", False):
            threshold = ram_config.get("threshold", 80)
            ram_percent = psutil.virtual_memory().percent
            
            if ram_percent > threshold:
                # RAM is high - suspend configured apps
                for app_name in ram_config.get("apps", []):
                    if app_name in self.card_map:
                        card = self.card_map[app_name]
                        if not card.is_suspended:
                            self.toggle_group_state(app_name, True)
                            tasks_ran = True
        
        # Save updated last_run times
        if tasks_ran:
            save_scheduled_actions(data)
            self.refresh_list(silent=True)
        
        # Schedule next check
        self._scheduler_job = self.after(60000, self._run_scheduled_tasks)
    
    def open_schedule_dialog(self, app_name, has_schedule):
        """Open dialog to configure scheduled actions for an app"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Schedule Actions - {app_name}")
        dialog.geometry("450x350")
        dialog.configure(fg_color=ModernTheme.BG_ROOT)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - (225)
        y = self.winfo_y() + (self.winfo_height() // 2) - (175)
        dialog.geometry(f"+{x}+{y}")
        
        # Load current settings
        data = load_scheduled_actions()
        current_trim = data.get("periodic_trim", {}).get(app_name, {})
        
        # Title
        ctk.CTkLabel(dialog, text=f"⏰ Schedule for {app_name[:25]}...", 
                    font=ModernTheme.FONTS["title"],
                    text_color=ModernTheme.TEXT_MAIN).pack(pady=(20, 10))
        
        # --- Periodic Trim Section ---
        trim_frame = ctk.CTkFrame(dialog, fg_color=ModernTheme.BG_CARD, corner_radius=12)
        trim_frame.pack(fill="x", padx=20, pady=10)
        
        trim_header = ctk.CTkFrame(trim_frame, fg_color="transparent")
        trim_header.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(trim_header, text="⚡ Periodic Trim", 
                    font=ModernTheme.FONTS["title"],
                    text_color=ModernTheme.ACCENT_PURPLE).pack(side="left")
        
        trim_enabled = ctk.BooleanVar(value=current_trim.get("enabled", False))
        trim_switch = ctk.CTkSwitch(trim_header, text="", variable=trim_enabled,
                                   onvalue=True, offvalue=False,
                                   progress_color=ModernTheme.ACCENT_PURPLE)
        trim_switch.pack(side="right")
        
        trim_settings = ctk.CTkFrame(trim_frame, fg_color="transparent")
        trim_settings.pack(fill="x", padx=15, pady=(5, 15))
        
        ctk.CTkLabel(trim_settings, text="Trim every", 
                    font=ModernTheme.FONTS["sub"],
                    text_color=ModernTheme.TEXT_SUB).pack(side="left")
        
        interval_var = ctk.StringVar(value=str(current_trim.get("interval", 15)))
        interval_entry = ctk.CTkEntry(trim_settings, width=60, height=32,
                                     textvariable=interval_var,
                                     fg_color=ModernTheme.BG_SEARCH,
                                     border_color=ModernTheme.BORDER_COLOR)
        interval_entry.pack(side="left", padx=10)
        
        ctk.CTkLabel(trim_settings, text="minutes", 
                    font=ModernTheme.FONTS["sub"],
                    text_color=ModernTheme.TEXT_SUB).pack(side="left")
        
        # Info text
        ctk.CTkLabel(dialog, text="💡 Periodic trim helps keep memory usage low\nwithout stopping the application.",
                    font=ModernTheme.FONTS["sub"],
                    text_color=ModernTheme.TEXT_DIM,
                    justify="center").pack(pady=10)
        
        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=20)
        
        def save_settings():
            try:
                interval = int(interval_var.get())
                if interval < 1:
                    interval = 1
            except:
                interval = 15
            
            if trim_enabled.get():
                add_periodic_trim(app_name, interval)
            else:
                remove_periodic_trim(app_name)
            
            # Update cache
            self.scheduled_apps = get_apps_with_schedules()
            self.refresh_list(silent=True)
            dialog.destroy()
        
        def remove_all():
            remove_periodic_trim(app_name)
            self.scheduled_apps = get_apps_with_schedules()
            self.refresh_list(silent=True)
            dialog.destroy()
        
        ctk.CTkButton(btn_frame, text="Save", width=100, height=36,
                     fg_color=ModernTheme.ACCENT_BLUE, hover_color="#0891B2",
                     font=ModernTheme.FONTS["btn"],
                     command=save_settings).pack(side="right", padx=(10, 0))
        
        if has_schedule:
            ctk.CTkButton(btn_frame, text="Remove All", width=100, height=36,
                         fg_color="#991B1B", hover_color="#B91C1C",
                         font=ModernTheme.FONTS["btn"],
                         command=remove_all).pack(side="right")
        
        ctk.CTkButton(btn_frame, text="Cancel", width=100, height=36,
                     fg_color=ModernTheme.BTN_SECONDARY,
                     hover_color=ModernTheme.BTN_SECONDARY_HOVER,
                     font=ModernTheme.FONTS["btn"],
                     command=dialog.destroy).pack(side="left")

    def show_info_dialog(self):
        """Open info/about dialog"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("About")
        dialog.geometry("500x600")
        dialog.configure(fg_color=ModernTheme.BG_ROOT)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - (250)
            y = self.winfo_y() + (self.winfo_height() // 2) - (300)
            dialog.geometry(f"+{x}+{y}")
        except:
            pass
        
        # Main Container
        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 1. Big Icon (Centered)
        icon_label = ctk.CTkLabel(container, text="⚡", font=("Segoe UI Emoji", 64))
        icon_label.pack(pady=(10, 0))
        
        # 2. App Title (Centered)
        title_label = ctk.CTkLabel(container, text="CryoTask", 
                                  font=("Segoe UI", 28, "bold"), 
                                  text_color=ModernTheme.TEXT_MAIN)
        title_label.pack(pady=(0, 5))
        
        # 3. Subtitle (Centered)
        sub_label = ctk.CTkLabel(container, text="Process Manager & RAM Optimizer", 
                                font=("Segoe UI", 14), 
                                text_color=ModernTheme.TEXT_SUB)
        sub_label.pack(pady=(0, 20))

        # Separator
        ctk.CTkFrame(container, height=1, fg_color=ModernTheme.BORDER_COLOR).pack(fill="x", padx=40, pady=(0, 20))
        
        # 4. Features Section (Card)
        
        # 4. Features Section (Card)
        features_frame = ctk.CTkFrame(container, fg_color=ModernTheme.BG_CARD, corner_radius=12, border_width=1, border_color=ModernTheme.BORDER_COLOR)
        features_frame.pack(fill="x", pady=10, padx=10)
        
        # Configure grid columns
        features_frame.grid_columnconfigure(0, minsize=50)   # Icon (Increased width for centering)
        features_frame.grid_columnconfigure(1, weight=0, minsize=90) # Name
        features_frame.grid_columnconfigure(2, weight=1)     # Description
        
        features = [
            ("⏸", "Suspend", "Freezes apps to free up CPU."),
            ("⚡", "Trim", "Compresses app memory to free RAM."),
            ("🛡️", "Safe Mode", "Protects critical system processes."),
            ("⭐", "Pin", "Keep favorite apps at the top."),
            ("⏰", "Schedule", "Auto-trim or suspend apps.")
        ]
        
        for i, (icon, name, desc) in enumerate(features):
            # Icon
            # Icon - Centered in column 0
            ctk.CTkLabel(features_frame, text=icon, font=("Segoe UI Emoji", 18)).grid(row=i*2, column=0, pady=8, padx=0, sticky="ew")
            
            # Name
            ctk.CTkLabel(features_frame, text=name, font=("Segoe UI", 14, "bold"), 
                        text_color=ModernTheme.TEXT_MAIN, anchor="w").grid(row=i*2, column=1, sticky="w", pady=8)
            
            # Description
            ctk.CTkLabel(features_frame, text=desc, font=("Segoe UI", 13), 
                        text_color=ModernTheme.TEXT_SUB, anchor="w").grid(row=i*2, column=2, sticky="ew", padx=(10, 15), pady=8)
            
            # Separator line (except for last item) - spanned across columns
            if i < len(features) - 1:
                sep = ctk.CTkFrame(features_frame, height=1, fg_color=ModernTheme.BORDER_COLOR)
                sep.grid(row=i*2+1, column=0, columnspan=3, sticky="ew", padx=10)

        # 5. Footer Section (Author + Buttons)
        footer_frame = ctk.CTkFrame(container, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", pady=20)
        
        # Author Details
        author_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        author_frame.pack(fill="x", pady=(0, 15))
        
        ctk.CTkLabel(author_frame, text=Strings.INFO_AUTHOR, 
                    font=("Segoe UI", 14, "bold"), text_color=ModernTheme.TEXT_MAIN).pack()
                    
        def open_youtube(event=None):
            import webbrowser
            webbrowser.open(Strings.INFO_YOUTUBE_URL)
            
        yt_label = ctk.CTkLabel(author_frame, text=Strings.INFO_YOUTUBE, 
                               font=("Segoe UI", 13), text_color="#3b82f6", cursor="hand2")
        yt_label.pack()
        yt_label.bind("<Button-1>", open_youtube)

        # Buttons
        btn_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        def open_github():
            import webbrowser
            webbrowser.open(Strings.INFO_GITHUB_URL)
            
        # Unified button width
        btn_width = 140
        
        # Center container for buttons
        center_btn_container = ctk.CTkFrame(btn_frame, fg_color="transparent")
        center_btn_container.pack(expand=True)
            
        ctk.CTkButton(center_btn_container, text="Close", width=btn_width, height=36,
                     fg_color=ModernTheme.BTN_SECONDARY,
                     hover_color=ModernTheme.BTN_SECONDARY_HOVER,
                     font=ModernTheme.FONTS["btn"],
                     command=dialog.destroy).pack(side="left", padx=10)

if __name__ == "__main__":
    app = AppSuspender()
    app.mainloop()
