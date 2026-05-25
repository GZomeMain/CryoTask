import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import psutil
import time
import os
import sys

from src.cryotask.utils.constants import ModernTheme, Strings, EXCLUDED_PROCESSES, CRITICAL_SYSTEM_PROCESSES
from src.cryotask.utils.helpers import resource_path, is_admin, run_as_admin
from src.cryotask.persistence.storage import (
    load_suspended_state, load_pinned_apps, load_scheduled_actions,
    get_apps_with_schedules, save_scheduled_actions, add_periodic_trim, remove_periodic_trim,
    toggle_pinned_app
)
from src.cryotask.core.process_manager import ProcessManager
from src.cryotask.ui.components import ProcessCard, PresetsDialog

class AppSuspender(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CryoTask")
        self.geometry("1000x750")
        self.minsize(800, 600)
        self.configure(fg_color=ModernTheme.BG_ROOT)
        
        # Set app icon
        try:
            icon_path = resource_path("assets/app_icon.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
        except Exception:
            pass  
        
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")

        if not is_admin():
            if messagebox.askyesno("Permission", "Restart as Administrator?"):
                run_as_admin()
                sys.exit()

        self.is_refreshing = False
        self.safe_mode = True
        
        self.setup_ui()
        
        self.card_map = {}
        self.card_rows = []
        
        self.scheduled_apps = get_apps_with_schedules()
        self.pinned_apps = set(load_pinned_apps())
        
        self.refresh_list()
        self._start_scheduler()

    def setup_ui(self):
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent", height=70)
        self.header_frame.pack(fill="x", padx=30, pady=(30, 15))

        title_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_frame.pack(side="left")
        
        ctk.CTkLabel(title_frame, text=Strings.APP_NAME, font=ModernTheme.FONTS["header"], 
                     text_color=ModernTheme.TEXT_MAIN).pack(side="left")

        self.refresh_btn = ctk.CTkButton(self.header_frame, text=Strings.BTN_REFRESH, width=110, height=38,
                                       fg_color=ModernTheme.BG_CARD, border_width=1, border_color=ModernTheme.BORDER_COLOR,
                                       text_color=ModernTheme.TEXT_MAIN, 
                                       hover_color=ModernTheme.BG_CARD_HOVER,
                                       font=ModernTheme.FONTS["btn"],
                                       corner_radius=ModernTheme.RADIUS_BTN,
                                       command=self.refresh_list)
        self.refresh_btn.pack(side="right")
        
        self.mode_btn = ctk.CTkButton(self.header_frame, text=Strings.BTN_SAFE_MODE, width=130, height=38,
                                     fg_color="#15803d",  
                                     hover_color="#166534",
                                     text_color=ModernTheme.TEXT_MAIN,
                                     font=ModernTheme.FONTS["btn"],
                                     corner_radius=ModernTheme.RADIUS_BTN,
                                     command=self.toggle_mode)
        self.mode_btn.pack(side="right", padx=(0, 12))
        
        self.presets_btn = ctk.CTkButton(self.header_frame, text="⚡ Presets", width=100, height=38,
                                       fg_color=ModernTheme.BG_CARD, border_width=1, border_color=ModernTheme.BORDER_COLOR,
                                       text_color=ModernTheme.TEXT_MAIN,
                                       hover_color=ModernTheme.BG_CARD_HOVER,
                                       font=ModernTheme.FONTS["btn"],
                                       corner_radius=ModernTheme.RADIUS_BTN,
                                       command=self.open_presets_dialog)
        self.presets_btn.pack(side="right", padx=(0, 12))
        
        self.system_overview = ctk.CTkFrame(self, fg_color=ModernTheme.BG_CARD, 
                                           corner_radius=ModernTheme.RADIUS_CARD, border_width=1, border_color=ModernTheme.BORDER_COLOR,
                                           height=90)
        self.system_overview.pack(fill="x", padx=30, pady=(0, 15))
        self.system_overview.pack_propagate(False)
        
        stats_container = ctk.CTkFrame(self.system_overview, fg_color="transparent")
        stats_container.pack(expand=True, fill="both", padx=20, pady=15)
        
        mem_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        mem_frame.pack(side="left", expand=True, fill="both")
        
        ctk.CTkLabel(mem_frame, text=Strings.LABEL_SYSTEM_MEMORY, font=ModernTheme.FONTS["sub"], 
                    text_color=ModernTheme.TEXT_SUB).pack(anchor="w")
        self.sys_mem_label = ctk.CTkLabel(mem_frame, text="0 / 0 GB (0%)", 
                                         font=ModernTheme.FONTS["title"], 
                                         text_color=ModernTheme.TEXT_MAIN)
        self.sys_mem_label.pack(anchor="w", pady=(2, 0))
        
        self.sys_mem_bar = ctk.CTkProgressBar(mem_frame, width=200, height=6, corner_radius=3,
                                             fg_color="#1a1a1a", progress_color=ModernTheme.ACCENT_BLUE)
        self.sys_mem_bar.pack(anchor="w", pady=(6, 0))
        self.sys_mem_bar.set(0)
        
        cpu_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        cpu_frame.pack(side="left", expand=True, fill="both")
        
        ctk.CTkLabel(cpu_frame, text=Strings.LABEL_CPU_USAGE, font=ModernTheme.FONTS["sub"], 
                    text_color=ModernTheme.TEXT_SUB).pack(anchor="w")
        self.sys_cpu_label = ctk.CTkLabel(cpu_frame, text="0%", 
                                         font=ModernTheme.FONTS["title"], 
                                         text_color=ModernTheme.TEXT_MAIN)
        self.sys_cpu_label.pack(anchor="w", pady=(2, 0))
        
        proc_frame = ctk.CTkFrame(stats_container, fg_color="transparent")
        proc_frame.pack(side="left", expand=True, fill="both")
        
        ctk.CTkLabel(proc_frame, text=Strings.LABEL_PROCESSES, font=ModernTheme.FONTS["sub"], 
                    text_color=ModernTheme.TEXT_SUB).pack(anchor="w")
        self.sys_proc_label = ctk.CTkLabel(proc_frame, text="0", 
                                          font=ModernTheme.FONTS["title"], 
                                          text_color=ModernTheme.TEXT_MAIN)
        self.sys_proc_label.pack(anchor="w", pady=(2, 0))

        self.search_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=30, pady=(0, 15))
        
        search_container = ctk.CTkFrame(self.search_frame, fg_color=ModernTheme.BG_SEARCH, 
                                       corner_radius=ModernTheme.RADIUS_BTN, border_width=1, border_color=ModernTheme.BORDER_COLOR)
        search_container.pack(fill="x")
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.filter_list)
        
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

        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=30, pady=(0, 15))
        
        self.scroll_frame = ctk.CTkScrollableFrame(self.container, fg_color="transparent",
                                                   corner_radius=0)
        self.scroll_frame.pack(fill="both", expand=True)
        
        self._setup_smooth_scroll()

        status_frame = ctk.CTkFrame(self, fg_color=ModernTheme.BG_CONTAINER, height=35)
        status_frame.pack(side="bottom", fill="x", padx=0, pady=0)
        status_frame.pack_propagate(False)
        
        self.status_bar = ctk.CTkLabel(status_frame, text="● Ready", 
                                     font=ModernTheme.FONTS["status"], 
                                     text_color=ModernTheme.TEXT_SUB)
        self.status_bar.pack(side="left", padx=30, pady=8)
        
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

        self.info_btn = ctk.CTkButton(status_frame, text="ℹ️ Info", width=60, height=20,
                                     font=("Segoe UI", 12),
                                     fg_color="transparent",
                                     hover_color=ModernTheme.BG_CARD_HOVER,
                                     text_color=ModernTheme.TEXT_DIM,
                                     command=self.show_info_dialog)
        self.info_btn.pack(side="right", padx=(0, 10))
        
        self.memory_summary = ctk.CTkLabel(status_frame, text="", 
                                         font=ModernTheme.FONTS["status"], 
                                         text_color=ModernTheme.TEXT_SUB)
        self.memory_summary.pack(side="right", padx=30, pady=8)
    
    def _setup_smooth_scroll(self):
        self._scroll_animation_running = False
        self._target_scroll = 0
        self._current_scroll = 0
        
        def _on_mousewheel(event):
            scroll_amount = int(-1 * (event.delta / 120) * 15)
            canvas = self.scroll_frame._parent_canvas
            scroll_region = canvas.cget("scrollregion").split()
            if len(scroll_region) == 4:
                total_height = float(scroll_region[3])
                if total_height > 0:
                    current_pos = canvas.yview()[0] * total_height
                    self._target_scroll = current_pos + (scroll_amount * 8)
                    if not self._scroll_animation_running:
                        self._current_scroll = current_pos
                        self._animate_scroll()
        
        def _animate_scroll_step():
            canvas = self.scroll_frame._parent_canvas
            scroll_region = canvas.cget("scrollregion").split()
            if len(scroll_region) != 4:
                self._scroll_animation_running = False
                return
                
            total_height = float(scroll_region[3])
            if total_height == 0:
                self._scroll_animation_running = False
                return
            
            diff = self._target_scroll - self._current_scroll
            if abs(diff) < 1:
                self._scroll_animation_running = False
                return
            
            card_count = len(self.card_rows)
            speed_factor = 0.25 
            frame_delay = 16    
            
            if card_count > 50:
                speed_factor = 0.45 
                frame_delay = 25    
            elif card_count > 25:
                speed_factor = 0.35
            
            step = diff * speed_factor
            self._current_scroll += step
            new_fraction = self._current_scroll / total_height
            canvas.yview_moveto(max(0, min(1, new_fraction)))
            self.after(frame_delay, _animate_scroll_step)
        
        self._animate_scroll = lambda: (
            setattr(self, '_scroll_animation_running', True),
            _animate_scroll_step()
        )
        self.scroll_frame._parent_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self._mousewheel_binding = _on_mousewheel
    
    def toggle_mode(self):
        if self.safe_mode:
            result = messagebox.askyesno(
                Strings.WARN_ADVANCED_TITLE,
                Strings.WARN_ADVANCED_MSG,
                icon='warning'
            )
            if result:
                self.safe_mode = False
                self.auto_refresh_interval = 5000
                self.mode_btn.configure(
                    text=Strings.BTN_ADVANCED_MODE,
                    fg_color="#991B1B",
                    hover_color="#B91C1C"
                )
                for card in list(self.card_map.values()):
                    card.destroy()
                self.card_map.clear()
                self.card_rows.clear()
                self.refresh_list()
        else:
            self.safe_mode = True
            self.auto_refresh_interval = 3000
            self.mode_btn.configure(
                text=Strings.BTN_SAFE_MODE,
                fg_color="#166534",
                hover_color="#15803d"
            )
            for card in list(self.card_map.values()):
                card.destroy()
            self.card_map.clear()
            self.card_rows.clear()
            self.refresh_list()

    def refresh_list(self, silent=False, visible_only=False):
        if self.is_refreshing:
            return
            
        self.is_refreshing = True
        
        if not silent:
            self.refresh_btn.configure(state="disabled", text="⏳ Scanning...")
            self.status_bar.configure(text="● Scanning processes...", text_color=ModernTheme.ACCENT_BLUE)
        
        threading.Thread(target=self._scan_process_thread, daemon=True, args=(silent, visible_only)).start()
    
    def _scan_process_thread(self, silent=False, visible_only=False):
        from collections import defaultdict
        final_list = []
        visible_pids = ProcessManager.get_visible_windows_info()
        visible_pid_set = set(visible_pids.keys())
        
        process_groups = defaultdict(lambda: {'mem': 0, 'count': 0, 'status': 'Running', 'cpu': 0.0, 'has_window': False})
        suspended_apps_history = set(load_suspended_state())
        
        safe_mode = self.safe_mode
        existing_card_names = set(self.card_map.keys()) if visible_only else set()
        
        sys_mem = psutil.virtual_memory()
        sys_cpu = psutil.cpu_percent(interval=0.1)
        total_processes = 0
        visible_process_names = set()

        try:
            for proc in psutil.process_iter(['pid', 'name', 'memory_info', 'status', 'cpu_percent']):
                try:
                    pid = proc.info['pid']
                    name = proc.info['name']
                    name_lower = name.lower()
                    
                    if name_lower in EXCLUDED_PROCESSES:
                        continue
                    if visible_only and name not in existing_card_names:
                        continue
                    
                    mem = proc.info['memory_info'].rss
                    cpu = proc.info.get('cpu_percent', 0.0) or 0.0
                    
                    process_groups[name]['mem'] += mem
                    process_groups[name]['cpu'] += cpu
                    process_groups[name]['count'] += 1
                    total_processes += 1
                    
                    if pid in visible_pid_set:
                        visible_process_names.add(name)
                        process_groups[name]['has_window'] = True
                    
                    if proc.info['status'] == 'suspended':
                        process_groups[name]['status'] = 'Suspended'
                    elif name in suspended_apps_history:
                        process_groups[name]['status'] = 'Suspended'
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if visible_only:
                process_names_to_show = existing_card_names
            elif safe_mode:
                process_names_to_show = visible_process_names
            else:
                process_names_to_show = set(process_groups.keys())
            
            for name in process_names_to_show:
                name_lower = name.lower()
                if safe_mode and not visible_only and name_lower in CRITICAL_SYSTEM_PROCESSES:
                    continue
                if name not in process_groups:
                    continue
                
                group_data = process_groups[name]
                total_mem_mb = round(group_data['mem'] / 1048576, 1)
                total_cpu = round(group_data['cpu'], 1)
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
        
        final_list.sort(key=lambda x: x['memory'], reverse=True)
        if not visible_only and len(final_list) > 75:
            final_list = final_list[:75]

        system_stats = {
            'mem_used_gb': round(sys_mem.used / 1073741824, 1),
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
        for p in data:
            p['is_pinned'] = p['name'] in self.pinned_apps
            
        data.sort(key=lambda x: (x['is_pinned'], x['memory']), reverse=True)
        total_memory = sum(p['memory'] for p in data)
        
        self.sys_mem_label.configure(
            text=f"{system_stats['mem_used_gb']} / {system_stats['mem_total_gb']} GB ({system_stats['mem_percent']:.0f}%)"
        )
        self.sys_mem_bar.set(system_stats['mem_percent'] / 100)
        self.sys_cpu_label.configure(text=f"{system_stats['cpu_percent']:.1f}%")
        self.sys_proc_label.configure(text=f"{system_stats['total_processes']} total")
        
        if system_stats['mem_percent'] > 80:
            self.sys_mem_bar.configure(progress_color="#EF4444")
        elif system_stats['mem_percent'] > 60:
            self.sys_mem_bar.configure(progress_color="#F59E0B")
        else:
            self.sys_mem_bar.configure(progress_color=ModernTheme.ACCENT_BLUE)
        
        if visible_only:
            data_map = {p['name']: p for p in data}
            for name, card in self.card_map.items():
                if name in data_map:
                    card.update_data(data_map[name])
            self.is_refreshing = False
            return
        
        current_names = set(item['name'] for item in data)
        
        cards_to_remove = [name for name in self.card_map.keys() if name not in current_names]
        for name in cards_to_remove:
            self.card_map[name].pack_forget()
        for name in cards_to_remove:
            self.card_map[name].destroy()
            del self.card_map[name]
        
        self.card_rows = []
        
        for p_data in data:
            name = p_data['name']
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
            
            self.card_rows.append(card)
        
        self.is_refreshing = False
        
        if not silent:
            self.refresh_btn.configure(state="normal", text="⟳ Refresh")
        
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
            for card in cards:
                card.pack(fill="x", pady=8, padx=4)
            visible_count = len(cards)
        else:
            for card in cards:
                if query in card.proc_name_lower:
                    card.pack(fill="x", pady=8, padx=4)
                    visible_count += 1
                else:
                    card.pack_forget()
        
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
        return ProcessManager.trim_group(process_name)

    def toggle_group_state(self, process_name, suspend_action):
        return ProcessManager.toggle_group_state(process_name, suspend_action)

    def toggle_pin_status(self, process_name):
        new_status = toggle_pinned_app(process_name)
        if new_status:
            self.pinned_apps.add(process_name)
        else:
            if process_name in self.pinned_apps: self.pinned_apps.remove(process_name)
        
        self.refresh_list(silent=True)
        return new_status 
    
    def _start_scheduler(self):
        self._scheduler_job = self.after(60000, self._run_scheduled_tasks)
    
    def _run_scheduled_tasks(self):
        current_time = time.time()
        data = load_scheduled_actions()
        tasks_ran = False
        
        for app_name, config in data.get("periodic_trim", {}).items():
            if not config.get("enabled", False):
                continue
            
            interval_seconds = config.get("interval", 15) * 60
            last_run = config.get("last_run", 0)
            
            if current_time - last_run >= interval_seconds:
                self.trim_group(app_name)
                data["periodic_trim"][app_name]["last_run"] = current_time
                tasks_ran = True
        
        ram_config = data.get("ram_threshold", {})
        if ram_config.get("enabled", False):
            threshold = ram_config.get("threshold", 80)
            ram_percent = psutil.virtual_memory().percent
            
            if ram_percent > threshold:
                for app_name in ram_config.get("apps", []):
                    if app_name in self.card_map:
                        card = self.card_map[app_name]
                        if not card.is_suspended:
                            self.toggle_group_state(app_name, True)
                            tasks_ran = True
        
        if tasks_ran:
            save_scheduled_actions(data)
            self.refresh_list(silent=True)
        
        self._scheduler_job = self.after(60000, self._run_scheduled_tasks)
    
    def open_schedule_dialog(self, app_name, has_schedule):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"Schedule Actions - {app_name}")
        dialog.geometry("450x350")
        dialog.configure(fg_color=ModernTheme.BG_ROOT)
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - (225)
            y = self.winfo_y() + (self.winfo_height() // 2) - (175)
            dialog.geometry(f"+{x}+{y}")
        except: pass
        
        data = load_scheduled_actions()
        current_trim = data.get("periodic_trim", {}).get(app_name, {})
        
        ctk.CTkLabel(dialog, text=f"⏰ Schedule for {app_name[:25]}...", 
                    font=ModernTheme.FONTS["title"],
                    text_color=ModernTheme.TEXT_MAIN).pack(pady=(20, 10))
        
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
        
        ctk.CTkLabel(dialog, text="💡 Periodic trim helps keep memory usage low\nwithout stopping the application.",
                    font=ModernTheme.FONTS["sub"],
                    text_color=ModernTheme.TEXT_DIM,
                    justify="center").pack(pady=10)
        
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

    def open_presets_dialog(self):
        try:
            if hasattr(self, 'presets_dialog') and self.presets_dialog.winfo_exists():
                self.presets_dialog.lift()
                self.presets_dialog.focus()
            else:
                self.presets_dialog = PresetsDialog(self, self)
                self.presets_dialog.grab_set()
        except:
            self.presets_dialog = PresetsDialog(self, self)
            self.presets_dialog.grab_set()

    def show_info_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("About")
        dialog.geometry("500x600")
        dialog.configure(fg_color=ModernTheme.BG_ROOT)
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - (250)
            y = self.winfo_y() + (self.winfo_height() // 2) - (300)
            dialog.geometry(f"+{x}+{y}")
        except:
            pass
        
        container = ctk.CTkFrame(dialog, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        icon_label = ctk.CTkLabel(container, text="⚡", font=("Segoe UI Emoji", 64))
        icon_label.pack(pady=(10, 0))
        
        title_label = ctk.CTkLabel(container, text="CryoTask", 
                                  font=("Segoe UI", 28, "bold"), 
                                  text_color=ModernTheme.TEXT_MAIN)
        title_label.pack(pady=(0, 5))
        
        sub_label = ctk.CTkLabel(container, text="Process Manager & RAM Optimizer", 
                                font=("Segoe UI", 14), 
                                text_color=ModernTheme.TEXT_SUB)
        sub_label.pack(pady=(0, 20))

        ctk.CTkFrame(container, height=1, fg_color=ModernTheme.BORDER_COLOR).pack(fill="x", padx=40, pady=(0, 20))
        
        features_frame = ctk.CTkFrame(container, fg_color=ModernTheme.BG_CARD, corner_radius=12, border_width=1, border_color=ModernTheme.BORDER_COLOR)
        features_frame.pack(fill="x", pady=10, padx=10)
        
        features_frame.grid_columnconfigure(0, minsize=50)
        features_frame.grid_columnconfigure(1, weight=0, minsize=90)
        features_frame.grid_columnconfigure(2, weight=1)
        
        features = [
            ("⏸", "Suspend", "Freezes apps to free up CPU."),
            ("⚡", "Trim", "Compresses app memory to free RAM."),
            ("🛡️", "Safe Mode", "Protects critical system processes."),
            ("⭐", "Pin", "Keep favorite apps at the top."),
            ("⏰", "Schedule", "Auto-trim or suspend apps.")
        ]
        
        for i, (icon, name, desc) in enumerate(features):
            ctk.CTkLabel(features_frame, text=icon, font=("Segoe UI Emoji", 18)).grid(row=i*2, column=0, pady=8, padx=0, sticky="ew")
            ctk.CTkLabel(features_frame, text=name, font=("Segoe UI", 14, "bold"), 
                        text_color=ModernTheme.TEXT_MAIN, anchor="w").grid(row=i*2, column=1, sticky="w", pady=8)
            ctk.CTkLabel(features_frame, text=desc, font=("Segoe UI", 13), 
                        text_color=ModernTheme.TEXT_SUB, anchor="w").grid(row=i*2, column=2, sticky="ew", padx=(10, 15), pady=8)
            
            if i < len(features) - 1:
                sep = ctk.CTkFrame(features_frame, height=1, fg_color=ModernTheme.BORDER_COLOR)
                sep.grid(row=i*2+1, column=0, columnspan=3, sticky="ew", padx=10)

        footer_frame = ctk.CTkFrame(container, fg_color="transparent")
        footer_frame.pack(side="bottom", fill="x", pady=20)
        
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

        btn_frame = ctk.CTkFrame(footer_frame, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        def open_github():
            import webbrowser
            webbrowser.open(Strings.INFO_GITHUB_URL)
            
        btn_width = 140
        center_btn_container = ctk.CTkFrame(btn_frame, fg_color="transparent")
        center_btn_container.pack(expand=True)
            
        ctk.CTkButton(center_btn_container, text="Close", width=btn_width, height=36,
                     fg_color=ModernTheme.BTN_SECONDARY,
                     hover_color=ModernTheme.BTN_SECONDARY_HOVER,
                     font=ModernTheme.FONTS["btn"],
                     command=dialog.destroy).pack(side="left", padx=10)
