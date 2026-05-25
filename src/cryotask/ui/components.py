import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import threading
import psutil

from src.cryotask.utils.constants import ModernTheme, Strings
from src.cryotask.persistence.storage import save_presets, load_presets

class ProcessCard(ctk.CTkFrame):
    # Class-level cache for reusable strings
    _PROCESS_TEXT = "process"
    _PROCESSES_TEXT = "processes"
    
    def __init__(self, master, process_data, suspend_callback, trim_callback, refresh_callback=None, schedule_callback=None, pin_callback=None, *args, **kwargs):
        super().__init__(master, corner_radius=ModernTheme.RADIUS_CARD, fg_color=ModernTheme.BG_CARD, 
                         height=80, border_width=1, border_color=ModernTheme.BORDER_COLOR, *args, **kwargs)
        self.grid_propagate(False) 
        self.pack_propagate(False)
        
        self.proc_name = process_data['name']
        self.proc_name_lower = self.proc_name.lower()
        self.is_suspended = (process_data['status'] == "Suspended")
        self.suspend_callback = suspend_callback
        self.trim_callback = trim_callback
        self.refresh_callback = refresh_callback
        self.schedule_callback = schedule_callback
        self.pin_callback = pin_callback
        self.memory_mb = process_data['memory']
        self.process_count = process_data['count']
        self.cpu_percent = process_data.get('cpu', 0.0)
        self.is_critical = process_data.get('is_critical', False)
        self.has_schedule = process_data.get('has_schedule', False)
        self.is_pinned = process_data.get('is_pinned', False)
        self.is_trimmed = False
        self._trim_reset_job = None

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        
        # Setup Grid
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, minsize=45) # Status Dot
        self.grid_columnconfigure(1, minsize=30) # Star (Pin)
        self.grid_columnconfigure(2, minsize=40) # Clock (Schedule)
        self.grid_columnconfigure(3, weight=1)   # Text Area
        self.grid_columnconfigure(4, weight=0)   # Trim
        self.grid_columnconfigure(5, weight=0)   # Suspend

        # 1. Status Dot
        self.status_dot = ctk.CTkFrame(self, width=14, height=14, corner_radius=7,
                                      border_width=2, border_color=ModernTheme.BG_CARD)
        self.status_dot.grid(row=0, column=0, rowspan=2, padx=(15, 5))

        # Action Icons Grouped on the Left
        pin_color = "#D97706" if self.is_pinned else ModernTheme.TEXT_DIM
        pin_text = "★" if self.is_pinned else "☆"
        self.pin_btn = ctk.CTkButton(self, text=pin_text, width=30, height=30,
                                    fg_color="transparent", hover_color=ModernTheme.BTN_SECONDARY_HOVER,
                                    text_color=pin_color, font=("Segoe UI", 18), corner_radius=6,
                                    border_width=0, command=self.on_pin_click)
        self.pin_btn.grid(row=0, column=1, rowspan=2, padx=0)
        
        schedule_color = ModernTheme.ACCENT_BLUE if self.has_schedule else ModernTheme.TEXT_DIM
        self.schedule_btn = ctk.CTkButton(self, text="⏰", width=30, height=30,
                                         fg_color="transparent", hover_color=ModernTheme.BTN_SECONDARY_HOVER,
                                         text_color=schedule_color, font=("Segoe UI", 14), corner_radius=6,
                                         border_width=0, command=self.on_schedule_click)
        self.schedule_btn.grid(row=0, column=2, rowspan=2, padx=(0, 10))

        # 2. Text Info
        self.name_label = ctk.CTkLabel(self, text=self.proc_name, 
                                     font=ModernTheme.FONTS["title"], 
                                     text_color=ModernTheme.TEXT_MAIN, anchor="w")
        self.name_label.grid(row=0, column=3, sticky="sw", pady=(15, 0))
        
        count_text = f"{self.process_count} process{'es' if self.process_count > 1 else ''}"
        cpu_text = f"CPU: {self.cpu_percent:.1f}%" if self.cpu_percent > 0 else ""
        detail_parts = [f"💾 {self.memory_mb} MB", count_text]
        if cpu_text:
            detail_parts.append(cpu_text)
        
        self.detail_label = ctk.CTkLabel(self, 
                                       text=f"  •  ".join(detail_parts), 
                                       font=ModernTheme.FONTS["sub"], 
                                       text_color=ModernTheme.TEXT_SUB, anchor="w")
        self.detail_label.grid(row=1, column=3, sticky="nw", pady=(0, 15))

        # Bind children to parent hover
        for child in [self.status_dot, self.name_label, self.detail_label]:
            child.bind("<Enter>", self._on_enter)
            child.bind("<Leave>", self._on_leave)

        # The Pin and Schedule buttons have been moved to column 1 and 2


        self.trim_btn = ctk.CTkButton(self, text="⚡ Trim", width=110, height=38,
                                    fg_color=ModernTheme.BTN_TRIM, hover_color=ModernTheme.BTN_TRIM_HOVER,
                                    font=ModernTheme.FONTS["btn"], corner_radius=ModernTheme.RADIUS_BTN,
                                    border_width=0, command=self.on_trim_click)
        self.trim_btn.grid(row=0, column=4, rowspan=2, padx=(0, 20))
        
        self.suspend_btn = ctk.CTkButton(self, text="⏸ Suspend", width=110, height=38,
                                      fg_color=ModernTheme.BTN_SUSPEND, hover_color=ModernTheme.BTN_SUSPEND_HOVER,
                                      font=ModernTheme.FONTS["btn"], corner_radius=ModernTheme.RADIUS_BTN,
                                      border_width=0, command=self.on_suspend)
        self.suspend_btn.grid(row=0, column=5, rowspan=2, padx=(0, 20))

        self.update_visual_state()
    
    def _on_enter(self, event=None):
        self.configure(fg_color=ModernTheme.BG_CARD_HOVER)
        self.status_dot.configure(border_color=ModernTheme.BG_CARD_HOVER)
    
    def _on_leave(self, event=None):
        self.configure(fg_color=ModernTheme.BG_CARD)
        self.status_dot.configure(border_color=ModernTheme.BG_CARD)

    def update_visual_state(self):
        if self.is_suspended:
            self.status_dot.configure(fg_color="#EF4444", border_color="#EF4444")
            self.configure(border_width=2, border_color="#7F1D1D")
            self.suspend_btn.configure(text="▶ Resume", fg_color="#374151", hover_color="#4B5563")
            self.trim_btn.configure(state="disabled", fg_color="#2a2a2a", hover_color="#2a2a2a")
            self.name_label.configure(text_color="#FCA5A5")
            self.detail_label.configure(text_color=ModernTheme.TEXT_DIM)
        elif self.is_trimmed:
            self.status_dot.configure(fg_color=ModernTheme.DOT_RUNNING, border_color=ModernTheme.DOT_RUNNING)
            self.configure(border_width=2, border_color="#CA8A04")
            self.suspend_btn.configure(text="⏸ Suspend", fg_color=ModernTheme.BTN_SUSPEND, hover_color=ModernTheme.BTN_SUSPEND_HOVER)
            self.trim_btn.configure(state="normal", fg_color="#CA8A04", hover_color="#EAB308", text="✓ Done")
            self.name_label.configure(text_color="#FDE047")
            self.detail_label.configure(text_color="#EAB308")
        elif self.is_critical:
            self.status_dot.configure(fg_color="#F59E0B", border_color="#F59E0B")
            self.configure(border_width=1, border_color="#92400E")
            self.suspend_btn.configure(text="⚠️ Suspend", fg_color="#B45309", hover_color="#D97706")
            self.trim_btn.configure(state="normal", fg_color=ModernTheme.BTN_TRIM, hover_color=ModernTheme.BTN_TRIM_HOVER, text="⚡ Trim")
            self.name_label.configure(text_color="#FCD34D")
            self.detail_label.configure(text_color="#FBBF24")
        else:
            self.status_dot.configure(fg_color=ModernTheme.DOT_RUNNING, border_color=ModernTheme.DOT_RUNNING)
            self.configure(border_width=1, border_color=ModernTheme.BORDER_COLOR)
            self.suspend_btn.configure(text="⏸ Suspend", fg_color=ModernTheme.BTN_SUSPEND, hover_color=ModernTheme.BTN_SUSPEND_HOVER)
            self.trim_btn.configure(state="normal", fg_color=ModernTheme.BTN_TRIM, hover_color=ModernTheme.BTN_TRIM_HOVER, text="⚡ Trim")
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
        
        status_changed = (self.is_suspended and new_status != "Suspended") or \
                        (not self.is_suspended and new_status == "Suspended")
        critical_changed = self.is_critical != new_is_critical
        schedule_changed = self.has_schedule != new_has_schedule
        
        self.is_critical = new_is_critical
        self.has_schedule = new_has_schedule
        
        new_is_pinned = process_data.get('is_pinned', False)
        pinned_changed = self.is_pinned != new_is_pinned
        self.is_pinned = new_is_pinned
        
        if status_changed:
            self.is_suspended = (new_status == "Suspended")
            self.update_visual_state()
        elif critical_changed:
            self.update_visual_state()
        
        if schedule_changed:
            schedule_color = ModernTheme.ACCENT_BLUE if self.has_schedule else ModernTheme.TEXT_DIM
            self.schedule_btn.configure(text_color=schedule_color)
        
        if pinned_changed:
            pin_color = "#D97706" if self.is_pinned else ModernTheme.TEXT_DIM
            pin_text = "★" if self.is_pinned else "☆"
            self.pin_btn.configure(text=pin_text, text_color=pin_color)
            
        count_text = f"{self.process_count} process{'es' if self.process_count > 1 else ''}"
        cpu_text = f"CPU: {self.cpu_percent:.1f}%" if self.cpu_percent > 0 else ""
        detail_parts = [f"💾 {self.memory_mb} MB", count_text]
        if cpu_text: detail_parts.append(cpu_text)
        if self.is_pinned: detail_parts.append("⭐ Pinned")
        if self.is_critical: detail_parts.append("⚠️ System")
        if self.has_schedule: detail_parts.append("🕐 Scheduled")
        
        if self.detail_label.cget("text_color") != ModernTheme.DOT_RUNNING:
            text_color = ModernTheme.TEXT_SUB
            if self.is_pinned: text_color = "#FBBF24"
            elif self.is_critical: text_color = "#FBBF24"
            self.detail_label.configure(text=f"  •  ".join(detail_parts), text_color=text_color)
    
    def on_schedule_click(self):
        if self.schedule_callback:
            self.schedule_callback(self.proc_name, self.has_schedule)
    
    def on_pin_click(self):
        if self.pin_callback:
            new_status = self.pin_callback(self.proc_name)
            self.is_pinned = new_status
            pin_color = "#D97706" if self.is_pinned else ModernTheme.TEXT_DIM
            pin_text = "★" if self.is_pinned else "☆"
            self.pin_btn.configure(text=pin_text, text_color=pin_color)

    def on_trim_click(self):
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
            count_text = f"{self.process_count} process{'es' if self.process_count > 1 else ''}"
            saved = round(old_memory - new_total, 1)
            
            if saved > 0:
                self.detail_label.configure(text=f"⚡ {new_total} MB  •  {count_text}  •  Saved: {saved} MB")
            else:
                self.detail_label.configure(text=f"⚡ {new_total} MB  •  {count_text}")
        
        self.is_trimmed = True
        self.update_visual_state()
        
        def reset_trim_state():
            self.is_trimmed = False
            self._trim_reset_job = None
            if not self.is_suspended:
                self.update_visual_state()
            if self.refresh_callback:
                self.refresh_callback()
        
        if self._trim_reset_job:
            self.after_cancel(self._trim_reset_job)
        self._trim_reset_job = self.after(1000, reset_trim_state)

class CustomMessageDialog(ctk.CTkToplevel):
    def __init__(self, master, title, message, icon_text="ℹ️"):
        super().__init__(master)
        self.title(title)
        self.geometry("400x200")
        self.configure(fg_color=ModernTheme.BG_ROOT)
        self.transient(master)
        self.grab_set()
        
        self.update_idletasks()
        try:
            x = master.winfo_x() + (master.winfo_width() // 2) - 200
            y = master.winfo_y() + (master.winfo_height() // 2) - 100
            self.geometry(f"+{x}+{y}")
        except: pass

        ctk.CTkLabel(self, text=icon_text, font=("Segoe UI Emoji", 40)).pack(pady=(20, 10))
        ctk.CTkLabel(self, text=message, font=ModernTheme.FONTS["sub"], 
                     text_color=ModernTheme.TEXT_MAIN, wraplength=350).pack(pady=10)
        ctk.CTkButton(self, text="OK", width=100, command=self.destroy,
                     fg_color=ModernTheme.ACCENT_BLUE, hover_color="#0891B2").pack(pady=20)

class PresetsDialog(ctk.CTkToplevel):
    def __init__(self, master, app_suspender):
        super().__init__(master)
        self.app_suspender = app_suspender
        self.title("Manage Presets")
        self.geometry("500x600")
        self.configure(fg_color=ModernTheme.BG_ROOT)
        
        self.update_idletasks()
        try:
            x = master.winfo_x() + (master.winfo_width() // 2) - (250)
            y = master.winfo_y() + (master.winfo_height() // 2) - (300)
            self.geometry(f"+{x}+{y}")
        except: pass
        
        self.presets = load_presets()
        self.setup_ui()
        
    def setup_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(header, text="Presets", font=ModernTheme.FONTS["header"], 
                     text_color=ModernTheme.TEXT_MAIN).pack(side="left")
                     
        ctk.CTkButton(header, text="+ New Preset", width=100, height=32,
                     fg_color=ModernTheme.BTN_TRIM, hover_color=ModernTheme.BTN_TRIM_HOVER,
                     font=ModernTheme.FONTS["btn"], corner_radius=ModernTheme.RADIUS_BTN,
                     command=self.create_new_preset).pack(side="right")

        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        self.refresh_presets_list()
        
    def refresh_presets_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()
            
        if not self.presets:
            ctk.CTkLabel(self.scroll_frame, text="No presets defined.", 
                         text_color=ModernTheme.TEXT_DIM).pack(pady=20)
            return
            
        for name, apps in self.presets.items():
            self.create_preset_card(name, apps)
            
    def create_preset_card(self, name, apps):
        card = ctk.CTkFrame(self.scroll_frame, fg_color=ModernTheme.BG_CARD, corner_radius=10)
        card.pack(fill="x", pady=5)
        
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(header, text=name, font=ModernTheme.FONTS["title"], 
                     text_color=ModernTheme.TEXT_MAIN).pack(side="left")
        
        app_count = len(apps)
        ctk.CTkLabel(header, text=f"{app_count} app{'s' if app_count != 1 else ''}", 
                     font=ModernTheme.FONTS["sub"], text_color=ModernTheme.TEXT_SUB).pack(side="left", padx=10)
                     
        actions = ctk.CTkFrame(header, fg_color="transparent")
        actions.pack(side="right")
        
        ctk.CTkButton(actions, text="▶ Apply", width=70, height=28,
                     fg_color=ModernTheme.ACCENT_BLUE, hover_color="#0891B2",
                     font=("Segoe UI", 11, "bold"),
                     command=lambda n=name: self.apply_preset(n)).pack(side="left", padx=5)

        ctk.CTkButton(actions, text="✏️", width=30, height=28,
                     fg_color=ModernTheme.BTN_SECONDARY, hover_color=ModernTheme.BTN_SECONDARY_HOVER,
                     font=("Segoe UI", 12),
                     command=lambda n=name: self.edit_preset(n)).pack(side="left", padx=5)
                     
        ctk.CTkButton(actions, text="🗑️", width=30, height=28,
                     fg_color="#374151", hover_color="#7f1d1d",
                     font=("Segoe UI", 12),
                     command=lambda n=name: self.delete_preset(n)).pack(side="left", padx=5)
                     
        preview = ctk.CTkFrame(card, fg_color="transparent")
        preview.pack(fill="x", padx=15, pady=(0, 10))
        
        desc_text = ", ".join([f"{app} ({mode})" for app, mode in list(apps.items())[:3]])
        if len(apps) > 3: desc_text += "..."
        
        ctk.CTkLabel(preview, text=desc_text, font=("Segoe UI", 11), 
                     text_color=ModernTheme.TEXT_DIM, anchor="w").pack(fill="x")

    def create_new_preset(self, edit_name=None):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Edit Preset" if edit_name else "New Preset")
        dialog.geometry("450x650")
        dialog.configure(fg_color=ModernTheme.BG_ROOT)
        dialog.transient(self)
        dialog.grab_set()
        
        try:
            x = self.winfo_x() + (self.winfo_width() // 2) - (225)
            y = self.winfo_y() + (self.winfo_height() // 2) - (325)
            dialog.geometry(f"+{x}+{y}")
        except: pass

        ctk.CTkLabel(dialog, text="Edit Preset" if edit_name else "Create Preset", 
                     font=ModernTheme.FONTS["title"], text_color=ModernTheme.TEXT_MAIN).pack(pady=(20, 10))
        
        ctk.CTkLabel(dialog, text="Preset Name:", font=ModernTheme.FONTS["sub"], text_color=ModernTheme.TEXT_SUB).pack(anchor="w", padx=20)
        name_entry = ctk.CTkEntry(dialog, fg_color=ModernTheme.BG_SEARCH, border_width=0, text_color=ModernTheme.TEXT_MAIN, height=35)
        name_entry.pack(fill="x", padx=20, pady=(5, 15))
        
        if edit_name:
            name_entry.insert(0, edit_name)
        
        selection_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        selection_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(selection_frame, text="Select App:", font=ModernTheme.FONTS["sub"], text_color=ModernTheme.TEXT_SUB).pack(anchor="w")
        
        running_apps = sorted(list(self.app_suspender.card_map.keys()))
        if not running_apps: running_apps = ["No apps found"]
        
        app_var = ctk.StringVar(value=running_apps[0])
        app_dropdown = ctk.CTkOptionMenu(selection_frame, variable=app_var, values=running_apps, 
                                       fg_color=ModernTheme.BG_SEARCH, button_color=ModernTheme.BTN_TRIM,
                                       dropdown_fg_color=ModernTheme.BG_CARD)
        app_dropdown.pack(fill="x", pady=(5, 10))
        
        ctk.CTkLabel(selection_frame, text="Action:", font=ModernTheme.FONTS["sub"], text_color=ModernTheme.TEXT_SUB).pack(anchor="w")
        action_var = ctk.StringVar(value="Suspend")
        action_dropdown = ctk.CTkOptionMenu(selection_frame, variable=action_var, values=["Suspend", "Trim", "Trim & Suspend"],
                                          fg_color=ModernTheme.BG_SEARCH, button_color=ModernTheme.BTN_TRIM,
                                          dropdown_fg_color=ModernTheme.BG_CARD)
        action_dropdown.pack(fill="x", pady=(5, 15))
        
        added_apps = {}
        if edit_name and edit_name in self.presets:
            added_apps = self.presets[edit_name].copy()
        
        list_label = ctk.CTkLabel(dialog, text="Apps in Preset:", font=ModernTheme.FONTS["sub"], text_color=ModernTheme.TEXT_SUB)
        list_label.pack(anchor="w", padx=20)
        
        apps_list_frame = ctk.CTkScrollableFrame(dialog, height=180, fg_color=ModernTheme.BG_CONTAINER)
        apps_list_frame.pack(fill="both", expand=True, padx=20, pady=(5, 10))
        
        def refresh_temp_list():
            for w in apps_list_frame.winfo_children(): w.destroy()
            if not added_apps:
                ctk.CTkLabel(apps_list_frame, text="No apps added yet", text_color=ModernTheme.TEXT_DIM).pack(pady=10)
                return
                
            for app, mode in added_apps.items():
                row = ctk.CTkFrame(apps_list_frame, fg_color="transparent")
                row.pack(fill="x", pady=2)
                
                mode_color = "#3b82f6"
                if "Trim" in mode: mode_color = "#8b5cf6"
                
                ctk.CTkLabel(row, text=app, text_color=ModernTheme.TEXT_MAIN, font=("Segoe UI", 12, "bold")).pack(side="left")
                ctk.CTkLabel(row, text=f"  •  {mode}", text_color=mode_color, font=("Segoe UI", 11)).pack(side="left")
                
                ctk.CTkButton(row, text="✕", width=24, height=24, fg_color="transparent", 
                             hover_color="#374151", text_color="#ef4444", 
                             font=("Arial", 14),
                             command=lambda a=app: remove_app(a)).pack(side="right")
                             
        def add_app():
            app = app_var.get()
            if app and app != "No apps found":
                added_apps[app] = action_var.get()
                refresh_temp_list()
                
        def remove_app(app):
            if app in added_apps:
                del added_apps[app]
                refresh_temp_list()
        
        ctk.CTkButton(selection_frame, text="+ Add to Preset", command=add_app, 
                     fg_color=ModernTheme.BG_CARD_HOVER, 
                     hover_color=ModernTheme.BG_CARD,
                     border_width=1, border_color=ModernTheme.BTN_TRIM).pack(fill="x", pady=(5, 0))

        refresh_temp_list()

        def save():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Preset name cannot be empty")
                return
            if not added_apps:
                messagebox.showerror("Error", "Add at least one app")
                return
            
            if edit_name and name != edit_name and edit_name in self.presets:
                 del self.presets[edit_name]
                
            self.presets[name] = added_apps
            save_presets(self.presets)
            self.refresh_presets_list()
            dialog.destroy()
            
        footer = ctk.CTkFrame(dialog, fg_color="transparent")
        footer.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkButton(footer, text="Cancel", command=dialog.destroy, 
                     width=100, height=40,
                     fg_color=ModernTheme.BTN_SECONDARY, hover_color=ModernTheme.BTN_SECONDARY_HOVER).pack(side="left")
                     
        ctk.CTkButton(footer, text="Save Preset", command=save, 
                     height=40,
                     fg_color=ModernTheme.ACCENT_BLUE, hover_color="#0891B2").pack(side="left", fill="x", expand=True, padx=(10, 0))

    def delete_preset(self, name):
        if messagebox.askyesno("Confirm", f"Delete preset '{name}'?"):
            if name in self.presets:
                del self.presets[name]
                save_presets(self.presets)
                self.refresh_presets_list()

    def apply_preset(self, name):
        if name not in self.presets: return
        
        apps = self.presets[name]
        attempted = 0
        success_count = 0
        
        for app_name, action in apps.items():
            attempted += 1
            try:
                is_running = False
                for p in psutil.process_iter(['name']):
                    if p.info['name'] == app_name:
                        is_running = True
                        break
                
                if not is_running:
                    continue

                if action == "Trim":
                    self.app_suspender.trim_group(app_name)
                    success_count += 1
                elif action == "Suspend":
                    if self.app_suspender.toggle_group_state(app_name, suspend_action=True):
                        success_count += 1
                elif action == "Trim & Suspend":
                    self.app_suspender.trim_group(app_name)
                    if self.app_suspender.toggle_group_state(app_name, suspend_action=True):
                        success_count += 1
            except Exception as e:
                print(f"Error applying preset to {app_name}: {e}")
            
        self.app_suspender.refresh_list(silent=True)
        
        msg = f"Preset '{name}' applied.\n\nTargeted: {attempted} apps\nSuccessfully actions: {success_count}"
        CustomMessageDialog(self, "Preset Applied", msg, icon_text="✅")

    def edit_preset(self, name):
        if name in self.presets:
            self.create_new_preset(edit_name=name)
