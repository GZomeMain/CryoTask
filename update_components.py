import re

with open("src/cryotask/ui/components.py", "r", encoding="utf-8") as f:
    content = f.read()

# Replace __init__ block
init_pattern = re.compile(r"def __init__\(self, master, process_data.*?self\.update_visual_state\(\)", re.DOTALL)
new_init = """def __init__(self, master, process_data, suspend_callback, trim_callback, refresh_callback=None, schedule_callback=None, pin_callback=None, *args, **kwargs):
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
        self.grid_columnconfigure(0, minsize=55) # Status Dot
        self.grid_columnconfigure(1, weight=1)   # Text Area
        self.grid_columnconfigure(2, weight=0)   # Pin
        self.grid_columnconfigure(3, weight=0)   # Schedule
        self.grid_columnconfigure(4, weight=0)   # Trim
        self.grid_columnconfigure(5, weight=0)   # Suspend

        # 1. Status Dot
        self.status_dot = ctk.CTkFrame(self, width=14, height=14, corner_radius=7,
                                      border_width=2, border_color=ModernTheme.BG_CARD)
        self.status_dot.grid(row=0, column=0, rowspan=2, padx=(20, 10))

        # 2. Text Info
        self.name_label = ctk.CTkLabel(self, text=self.proc_name, 
                                     font=ModernTheme.FONTS["title"], 
                                     text_color=ModernTheme.TEXT_MAIN, anchor="w")
        self.name_label.grid(row=0, column=1, sticky="sw", pady=(15, 0))
        
        count_text = f"{self.process_count} process{'es' if self.process_count > 1 else ''}"
        cpu_text = f"CPU: {self.cpu_percent:.1f}%" if self.cpu_percent > 0 else ""
        detail_parts = [f"💾 {self.memory_mb} MB", count_text]
        if cpu_text:
            detail_parts.append(cpu_text)
        
        self.detail_label = ctk.CTkLabel(self, 
                                       text=f"  •  ".join(detail_parts), 
                                       font=ModernTheme.FONTS["sub"], 
                                       text_color=ModernTheme.TEXT_SUB, anchor="w")
        self.detail_label.grid(row=1, column=1, sticky="nw", pady=(0, 15))

        # Bind children to parent hover
        for child in [self.status_dot, self.name_label, self.detail_label]:
            child.bind("<Enter>", self._on_enter)
            child.bind("<Leave>", self._on_leave)

        # 3. Actions
        pin_color = "#D97706" if self.is_pinned else ModernTheme.BTN_SECONDARY
        pin_hover = "#F59E0B" if self.is_pinned else ModernTheme.BTN_SECONDARY_HOVER
        pin_text = "⭐ Pinned" if self.is_pinned else "⭐ Pin"
        self.pin_btn = ctk.CTkButton(self, text=pin_text, width=90, height=36,
                                    fg_color=pin_color, hover_color=pin_hover,
                                    font=ModernTheme.FONTS["btn"], corner_radius=ModernTheme.RADIUS_BTN,
                                    border_width=0, command=self.on_pin_click)
        self.pin_btn.grid(row=0, column=2, rowspan=2, padx=(0, 10))
        
        schedule_color = ModernTheme.ACCENT_BLUE if self.has_schedule else ModernTheme.BTN_SECONDARY
        schedule_hover = "#0891B2" if self.has_schedule else ModernTheme.BTN_SECONDARY_HOVER
        schedule_text = "⏰ Rules (On)" if self.has_schedule else "⏰ Rules"
        self.schedule_btn = ctk.CTkButton(self, text=schedule_text, width=110, height=36,
                                         fg_color=schedule_color, hover_color=schedule_hover,
                                         font=ModernTheme.FONTS["btn"], corner_radius=ModernTheme.RADIUS_BTN,
                                         border_width=0, command=self.on_schedule_click)
        self.schedule_btn.grid(row=0, column=3, rowspan=2, padx=(0, 15))

        self.trim_btn = ctk.CTkButton(self, text="⚡ Trim", width=110, height=38,
                                    fg_color=ModernTheme.BTN_TRIM, hover_color=ModernTheme.BTN_TRIM_HOVER,
                                    font=ModernTheme.FONTS["btn"], corner_radius=ModernTheme.RADIUS_BTN,
                                    border_width=0, command=self.on_trim_click)
        self.trim_btn.grid(row=0, column=4, rowspan=2, padx=(0, 15))
        
        self.suspend_btn = ctk.CTkButton(self, text="⏸ Suspend", width=110, height=38,
                                      fg_color=ModernTheme.BTN_SUSPEND, hover_color=ModernTheme.BTN_SUSPEND_HOVER,
                                      font=ModernTheme.FONTS["btn"], corner_radius=ModernTheme.RADIUS_BTN,
                                      border_width=0, command=self.on_suspend)
        self.suspend_btn.grid(row=0, column=5, rowspan=2, padx=(0, 20))

        self.update_visual_state()"""

content = init_pattern.sub(new_init, content)

# _on_enter and _on_leave
on_enter_old = """    def _on_enter(self, event=None):
        self.configure(fg_color=ModernTheme.BG_CARD_HOVER)
    
    def _on_leave(self, event=None):
        self.configure(fg_color=ModernTheme.BG_CARD)"""

on_enter_new = """    def _on_enter(self, event=None):
        self.configure(fg_color=ModernTheme.BG_CARD_HOVER)
        self.status_dot.configure(border_color=ModernTheme.BG_CARD_HOVER)
    
    def _on_leave(self, event=None):
        self.configure(fg_color=ModernTheme.BG_CARD)
        self.status_dot.configure(border_color=ModernTheme.BG_CARD)"""

content = content.replace(on_enter_old, on_enter_new)

# update_data schedules changes
update_data_schedule_old = """        if schedule_changed:
            schedule_color = ModernTheme.ACCENT_BLUE if self.has_schedule else ModernTheme.BTN_SECONDARY
            schedule_hover = "#0891B2" if self.has_schedule else ModernTheme.BTN_SECONDARY_HOVER
            self.schedule_btn.configure(fg_color=schedule_color, hover_color=schedule_hover)"""

update_data_schedule_new = """        if schedule_changed:
            schedule_color = ModernTheme.ACCENT_BLUE if self.has_schedule else ModernTheme.BTN_SECONDARY
            schedule_hover = "#0891B2" if self.has_schedule else ModernTheme.BTN_SECONDARY_HOVER
            schedule_text = "⏰ Rules (On)" if self.has_schedule else "⏰ Rules"
            self.schedule_btn.configure(text=schedule_text, fg_color=schedule_color, hover_color=schedule_hover)"""
content = content.replace(update_data_schedule_old, update_data_schedule_new)


# update_data pin changes
update_data_pin_text_old = """        if pinned_changed:
            pin_color = "#D97706" if self.is_pinned else ModernTheme.BTN_SECONDARY
            pin_hover = "#F59E0B" if self.is_pinned else ModernTheme.BTN_SECONDARY_HOVER
            pin_text = "⭐" if self.is_pinned else "☆"
            self.pin_btn.configure(text=pin_text, fg_color=pin_color, hover_color=pin_hover)"""
update_data_pin_text_new = """        if pinned_changed:
            pin_color = "#D97706" if self.is_pinned else ModernTheme.BTN_SECONDARY
            pin_hover = "#F59E0B" if self.is_pinned else ModernTheme.BTN_SECONDARY_HOVER
            pin_text = "⭐ Pinned" if self.is_pinned else "⭐ Pin"
            self.pin_btn.configure(text=pin_text, fg_color=pin_color, hover_color=pin_hover)"""
content = content.replace(update_data_pin_text_old, update_data_pin_text_new)

# on_pin_click changes
on_pin_click_old = """    def on_pin_click(self):
        if self.pin_callback:
            new_status = self.pin_callback(self.proc_name)
            self.is_pinned = new_status
            pin_color = "#D97706" if self.is_pinned else ModernTheme.BTN_SECONDARY
            pin_hover = "#F59E0B" if self.is_pinned else ModernTheme.BTN_SECONDARY_HOVER
            pin_text = "⭐" if self.is_pinned else "☆"
            self.pin_btn.configure(text=pin_text, fg_color=pin_color, hover_color=pin_hover)"""
on_pin_click_new = """    def on_pin_click(self):
        if self.pin_callback:
            new_status = self.pin_callback(self.proc_name)
            self.is_pinned = new_status
            pin_color = "#D97706" if self.is_pinned else ModernTheme.BTN_SECONDARY
            pin_hover = "#F59E0B" if self.is_pinned else ModernTheme.BTN_SECONDARY_HOVER
            pin_text = "⭐ Pinned" if self.is_pinned else "⭐ Pin"
            self.pin_btn.configure(text=pin_text, fg_color=pin_color, hover_color=pin_hover)"""
content = content.replace(on_pin_click_old, on_pin_click_new)

with open("src/cryotask/ui/components.py", "w", encoding="utf-8") as f:
    f.write(content)
