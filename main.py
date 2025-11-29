"""
App Suspender & RAM Optimizer
A modern Windows utility to suspend processes and trim working sets.
Author: [Your Name]
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

# --- Configuration & Theme ---
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# --- Persistence File ---
STATE_FILE = "suspended_apps.json"

class Theme:
    BG_COLOR = "#2b2b2b"
    LIST_BG = "#202020"
    TEXT_WHITE = "#ffffff"
    TEXT_GRAY = "gray"
    ACCENT_BLUE = "#3b8ed0"
    ACCENT_HOVER = "#1f6aa5"
    SUCCESS_GREEN = "#2da44e"
    WARNING_ORANGE = "#fca503"
    ERROR_RED = "#ff5555"
    PURPLE_BTN = "#8a2be2"
    PURPLE_HOVER = "#6a1b9a"
    FONT_MAIN = ("Segoe UI", 12)
    FONT_BOLD = ("Segoe UI", 12, "bold")
    FONT_HEADER = ("Segoe UI", 24, "bold")

# --- Low Level Windows API ---
psapi = ctypes.WinDLL('psapi.dll')
kernel32 = ctypes.WinDLL('kernel32.dll')

PROCESS_SET_QUOTA = 0x0100
PROCESS_QUERY_INFORMATION = 0x0400

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Relaunch the app with admin rights"""
    ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)

def trim_pid(pid):
    """Trims a single PID using EmptyWorkingSet. Returns True/False."""
    try:
        handle = kernel32.OpenProcess(PROCESS_SET_QUOTA | PROCESS_QUERY_INFORMATION, False, pid)
        if not handle: return False
        result = psapi.EmptyWorkingSet(handle)
        kernel32.CloseHandle(handle)
        return bool(result)
    except:
        return False

def get_process_group_memory(proc_name):
    """Calculates total memory for all processes with a specific name."""
    total_mem = 0
    try:
        for p in psutil.process_iter(['name', 'memory_info']):
            if p.info['name'] == proc_name:
                total_mem += p.info['memory_info'].rss
    except:
        pass
    return round(total_mem / (1024 * 1024), 1)

# --- State Management ---
def load_suspended_state():
    """Loads the list of suspended apps from JSON."""
    if not os.path.exists(STATE_FILE):
        return []
    try:
        with open(STATE_FILE, 'r') as f:
            data = json.load(f)
            return data.get("suspended", [])
    except:
        return []

def save_suspended_state(app_name, is_suspended):
    """Updates the JSON file when an app is suspended or resumed."""
    current_list = load_suspended_state()
    
    if is_suspended:
        if app_name not in current_list:
            current_list.append(app_name)
    else:
        if app_name in current_list:
            current_list.remove(app_name)
            
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({"suspended": current_list}, f)
    except Exception as e:
        print(f"Error saving state: {e}")

# --- UI Components ---

class ProcessRow(ctk.CTkFrame):
    def __init__(self, master, process_data, suspend_callback, trim_callback, *args, **kwargs):
        super().__init__(master, corner_radius=10, fg_color=Theme.BG_COLOR, border_width=1, border_color="#3a3a3a", *args, **kwargs)
        self.pack(fill="x", padx=10, pady=5)
        
        self.proc_name = process_data['name']
        self.is_suspended = (process_data['status'] == "Suspended")
        self.suspend_callback = suspend_callback
        self.trim_callback = trim_callback

        # Layout
        self.grid_columnconfigure(1, weight=1) 

        # 1. Status Indicator
        self.status_indicator = ctk.CTkLabel(self, text="●", font=("Arial", 24), width=30)
        self.status_indicator.grid(row=0, column=0, padx=(15, 5), pady=10)

        # 2. Name & Stats
        self.name_label = ctk.CTkLabel(self, text=self.proc_name, font=("Segoe UI", 14, "bold"), anchor="w")
        self.name_label.grid(row=0, column=1, sticky="w", padx=5)
        
        count_text = f"({process_data['count']} processes)" if process_data['count'] > 1 else ""
        self.detail_label = ctk.CTkLabel(self, text=f"Total RAM: {process_data['memory']} MB {count_text}", 
                                       font=("Segoe UI", 11), text_color=Theme.TEXT_GRAY, anchor="w")
        self.detail_label.grid(row=1, column=1, sticky="w", padx=5, pady=(0, 10))

        # 3. Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=0, column=2, rowspan=2, padx=10)

        self.trim_btn = ctk.CTkButton(self.btn_frame, text="🧹 Trim Group", width=80, height=30,
                                    fg_color=Theme.PURPLE_BTN, hover_color=Theme.PURPLE_HOVER,
                                    command=self.on_trim, font=("Segoe UI", 11, "bold"))
        self.trim_btn.pack(side="left", padx=5)

        self.suspend_btn = ctk.CTkButton(self.btn_frame, text="Suspend", width=90, height=30, 
                                      command=self.on_suspend, font=("Segoe UI", 11, "bold"))
        self.suspend_btn.pack(side="left", padx=5)

        self.update_visual_state()

    def update_visual_state(self):
        if self.is_suspended:
            self.status_indicator.configure(text_color=Theme.WARNING_ORANGE)
            self.suspend_btn.configure(text="Resume", fg_color=Theme.SUCCESS_GREEN, hover_color="#2c974b")
            self.configure(border_color=Theme.WARNING_ORANGE)
            self.trim_btn.configure(state="disabled")
        else:
            self.status_indicator.configure(text_color="#4ec9b0")
            self.suspend_btn.configure(text="Suspend", fg_color=Theme.ACCENT_BLUE, hover_color=Theme.ACCENT_HOVER)
            self.configure(border_color="#3a3a3a")
            self.trim_btn.configure(state="normal")

    def on_suspend(self):
        # We pass the inverted current state (if suspended, we want to resume)
        success = self.suspend_callback(self.proc_name, not self.is_suspended)
        if success:
            self.is_suspended = not self.is_suspended
            self.update_visual_state()

    def on_trim(self):
        new_total = self.trim_callback(self.proc_name)
        if new_total is not None:
            self.detail_label.configure(text=f"Total RAM: {new_total} MB")
            self.detail_label.configure(text_color="#4ec9b0")
            self.after(600, lambda: self.detail_label.configure(text_color=Theme.TEXT_GRAY))

class AppSuspender(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CryoTask - App Manager")
        self.geometry("750x700")
        
        # Admin Check
        if not is_admin():
            response = messagebox.askyesno("Admin Rights", "This app works best as Administrator.\nDo you want to restart with Admin rights?")
            if response:
                run_as_admin()
                sys.exit()

        # Load Icon if exists
        try:
            # Check for assets folder in current directory or PyInstaller temp dir
            if hasattr(sys, "_MEIPASS"):
                icon_path = os.path.join(sys._MEIPASS, "assets", "app_icon.ico")
            else:
                icon_path = os.path.join("assets", "app_icon.ico")
            
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except:
            pass

        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        # Header
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=20, pady=(20, 10))

        title = ctk.CTkLabel(self.header_frame, text="Active Applications", font=Theme.FONT_HEADER)
        title.pack(side="left")

        if not is_admin():
            admin_warning = ctk.CTkLabel(self.header_frame, text="⚠️ Restricted Mode", text_color=Theme.ERROR_RED, font=Theme.FONT_BOLD)
            admin_warning.pack(side="left", padx=10, pady=5)

        self.refresh_btn = ctk.CTkButton(self.header_frame, text="↻ Refresh", width=80, command=self.refresh_list, fg_color="#444444")
        self.refresh_btn.pack(side="right")

        # Search
        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=20, pady=5)
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_list)
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Search process...", textvariable=self.search_var, height=40)
        self.search_entry.pack(fill="x")

        # Scroll Area
        self.scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=15, fg_color=Theme.LIST_BG)
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Footer
        self.footer_label = ctk.CTkLabel(self, text="Ready", text_color="gray", font=("Segoe UI", 11))
        self.footer_label.pack(side="bottom", pady=5)

    def get_visible_windows_info(self):
        """Returns visible process PIDs."""
        visible_map = {}
        def enum_window_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                visible_map[pid] = True
        try:
            win32gui.EnumWindows(enum_window_callback, None)
        except: pass
        return visible_map

    def refresh_list(self):
        self.footer_label.configure(text="Scanning...")
        self.refresh_btn.configure(state="disabled")
        threading.Thread(target=self._scan_process_thread, daemon=True).start()

    def _scan_process_thread(self):
        final_list = []
        visible_pids = self.get_visible_windows_info()
        process_groups = defaultdict(lambda: {'mem': 0, 'count': 0, 'status': 'Running'})
        
        # Load our saved state
        suspended_apps_history = load_suspended_state()

        try:
            # 1. Group all processes by name
            for proc in psutil.process_iter(['name', 'memory_info', 'status']):
                name = proc.info['name']
                mem = proc.info['memory_info'].rss
                process_groups[name]['mem'] += mem
                process_groups[name]['count'] += 1
                
                # Check OS status OR our saved history
                if proc.info['status'] == 'suspended':
                    process_groups[name]['status'] = 'Suspended'
                elif name in suspended_apps_history:
                    # If it's in our history file, assume we suspended it
                    process_groups[name]['status'] = 'Suspended'

            # 2. Filter only visible apps
            seen_names = set()
            for pid in visible_pids:
                try:
                    p = psutil.Process(pid)
                    name = p.name()
                    if name.lower() == "python.exe" or name.lower().startswith("cryotask"): continue
                    
                    if name not in seen_names:
                        group_data = process_groups[name]
                        total_mem_mb = round(group_data['mem'] / (1024 * 1024), 1)
                        final_list.append({
                            "name": name,
                            "status": group_data['status'],
                            "memory": total_mem_mb,
                            "count": group_data['count']
                        })
                        seen_names.add(name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Scan Error: {e}")

        self.after(0, lambda: self._update_ui_list(final_list))

    def _update_ui_list(self, data):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
        
        self.process_rows = []
        data.sort(key=lambda x: x['memory'], reverse=True) 

        for p_data in data:
            row = ProcessRow(self.scroll_frame, p_data, self.toggle_group_state, self.trim_group)
            self.process_rows.append(row)
        
        self.filter_list()
        self.refresh_btn.configure(state="normal")
        self.footer_label.configure(text=f"Found {len(data)} applications.")

    def filter_list(self, *args):
        query = self.search_var.get().lower()
        for row in self.process_rows:
            if query in row.proc_name.lower():
                row.pack(fill="x", padx=10, pady=5)
            else:
                row.pack_forget()

    def trim_group(self, process_name):
        count = 0
        success_count = 0
        for p in psutil.process_iter(['pid', 'name']):
            if p.info['name'] == process_name:
                count += 1
                if trim_pid(p.info['pid']):
                    success_count += 1
        
        new_total = get_process_group_memory(process_name)
        self.footer_label.configure(text=f"Trimmed {success_count}/{count} processes for {process_name}", text_color="#4ec9b0")
        return new_total

    def toggle_group_state(self, process_name, suspend_action):
        action_name = "Suspended" if suspend_action else "Resumed"
        count = 0
        
        # Save state to file
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
                            if suspend_action:
                                win32process.SuspendThread(t_handle)
                            else:
                                # Resume until count is 0
                                while True:
                                    if win32process.ResumeThread(t_handle) <= 1: break
                            win32api.CloseHandle(t_handle)
                    win32api.CloseHandle(handle)
                    count += 1
                except: pass
        self.footer_label.configure(text=f"{action_name} {count} processes for {process_name}", text_color="#4ec9b0")
        return True 

if __name__ == "__main__":
    app = AppSuspender()
    app.mainloop()