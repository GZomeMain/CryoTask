# --- Theme Configuration ---
class ModernTheme:
    BG_ROOT = "#202020"       # Fluent UI Dark Background
    BG_CONTAINER = "#202020"  
    BG_CARD = "#2B2B2B"       # Fluent Surface
    BG_CARD_HOVER = "#323232" # Surface Hover
    BG_SEARCH = "#2D2D2D"     
    
    TEXT_MAIN = "#FFFFFF"     
    TEXT_SUB = "#CCCCCC"      
    TEXT_DIM = "#999999"      
    
    # Button Colors - Fluent Tones
    BTN_TRIM = "#744BCE"      # Soft Windows Purple
    BTN_TRIM_HOVER = "#8660D8"
    BTN_SUSPEND = "#005FB8"   # Windows Accent Blue
    BTN_SUSPEND_HOVER = "#0078D4"
    BTN_SECONDARY = "#3F3F3F" 
    BTN_SECONDARY_HOVER = "#4A4A4A"
    
    # Status Dots
    DOT_RUNNING = "#6CCB5F"   # Soft Green
    DOT_FROZEN = "#FCE100"    # Accent Amber
    DOT_PULSE = "#A0E395"     
    
    # Accent colors
    ACCENT_BLUE = "#0078D4"   
    ACCENT_PURPLE = "#744BCE" 
    
    # Border/separator
    BORDER_COLOR = "#3A3A3A"  
    
    # Corner Radii - Windows 11 Native (4px smaller, 8px larger)
    RADIUS_CARD = 8
    RADIUS_BTN = 4
    
    FONTS = {
        "header": ("Segoe UI", 24, "bold"),
        "title": ("Segoe UI", 14, "bold"), 
        "sub": ("Segoe UI", 12),
        "btn": ("Segoe UI", 12),
        "status": ("Segoe UI", 10)
    }

# --- Localization Strings ---
class Strings:
    # App Info
    APP_TITLE = "CryoTask"
    APP_NAME = "⚡ CryoTask"
    APP_SUBTITLE = ""
    
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

# --- Excluded Processes ---
EXCLUDED_PROCESSES = frozenset([
    "python.exe",
    "pythonw.exe", 
    "python3.exe",
    "cryotask.exe",
    "code.exe",
    "pycharm64.exe",
    "idle.exe",
    "wininit.exe",
    "csrss.exe",
    "smss.exe",
    "services.exe",
    "lsass.exe",
    "winlogon.exe",
])

# --- Critical System Processes Deny List ---
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
    
    # Development Tools
    "python.exe", "pythonw.exe", "python3.exe", "cryotask.exe",
    
    # Critical Background Services
    "wbengine.exe", "vssvc.exe", "msiexec.exe", "dism.exe",
    "taskmgr.exe", "perfmon.exe", "mmc.exe", "regedit.exe",
    
    # Graphics & Display
    "igfxem.exe", "igfxhk.exe", "igfxtray.exe",
    "nvdisplay.container.exe", "nvidia share.exe",
    "amdow.exe", "radeonsoft.exe",
    
    # Memory & Disk
    "memorycompression", "vds.exe", "defrag.exe",
])
