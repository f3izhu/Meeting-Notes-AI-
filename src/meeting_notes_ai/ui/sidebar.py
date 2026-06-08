"""Sidebar navigation component for Meeting Notes AI."""
from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from meeting_notes_ai.ui.styles import (
    BG_CRUST, BG_MANTLE, BG_SURFACE, BG_OVERLAY, TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, ACCENT_YELLOW, COLOR_ACTIVE_HOVER, FONT_FAMILY, FONT_MONO,
    font_size, scale_factor,
)


class AudioMeter(tk.Canvas):
    """Smooth audio level meter with color-banded segments."""

    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, height=12, bg=BG_CRUST, highlightthickness=0, **kwargs)
        self.level = -120.0
        self._display_level = -120.0  # for smooth interpolation
        self._animating = False
        self.bind("<Configure>", lambda e: self.draw_meter())

    def set_level(self, dbfs: float) -> None:
        self.level = dbfs
        if not self._animating:
            self._animating = True
            self._animate_meter()

    def _animate_meter(self) -> None:
        """Smoothly interpolate displayed level toward target level."""
        diff = self.level - self._display_level
        if abs(diff) < 0.5:
            self._display_level = self.level
            self._animating = False
        else:
            # Fast rise, slow fall (like a real meter)
            rate = 0.4 if diff > 0 else 0.15
            self._display_level += diff * rate
            self.after(30, self._animate_meter)
        self.draw_meter()

    def draw_meter(self) -> None:
        self.delete("all")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1:
            width = 200
        if height <= 1:
            height = 12

        # Background track with rounded look
        self.create_rectangle(0, 0, width, height, fill=BG_OVERLAY, outline="")

        # Map DBFS from [-60, 0] to [0.0, 1.0]
        pct = max(0.0, min(1.0, (self._display_level + 60.0) / 60.0))
        fill_width = int(pct * width)

        if fill_width > 0:
            # Color bands: Green (safe), Yellow (warning), Red (peak)
            green_end = int(width * 0.65)
            yellow_end = int(width * 0.85)

            # Segment 1: Green
            w1 = min(fill_width, green_end)
            if w1 > 0:
                self.create_rectangle(0, 1, w1, height - 1, fill=ACCENT_GREEN, outline="")

            # Segment 2: Yellow
            if fill_width > green_end:
                w2 = min(fill_width, yellow_end)
                self.create_rectangle(green_end, 1, w2, height - 1, fill=ACCENT_YELLOW, outline="")

            # Segment 3: Red
            if fill_width > yellow_end:
                self.create_rectangle(yellow_end, 1, fill_width, height - 1, fill=ACCENT_RED, outline="")

        # Draw decibel tick marks
        for db in [-50, -40, -30, -20, -10]:
            x = int(((db + 60.0) / 60.0) * width)
            self.create_line(x, 0, x, height, fill=BG_CRUST, width=1)


class SidebarButton(tk.Button):
    def __init__(self, parent, icon, text, command, **kwargs):
        self.icon = icon
        self.text = text
        self.full_text = f"  {icon}   {text}"
        fs = font_size(10)
        super().__init__(
            parent,
            text=self.full_text,
            font=(FONT_FAMILY, fs, "normal"),
            bg=BG_CRUST,
            fg=TEXT_SUB,
            activebackground=BG_SURFACE,
            activeforeground=ACCENT_BLUE,
            relief=tk.FLAT,
            bd=0,
            anchor="w",
            padx=16,
            pady=10,
            cursor="hand2",
            command=command,
            **kwargs
        )
        self.bind("<Enter>", self.on_hover)
        self.bind("<Leave>", self.on_leave)
        self.is_active = False
        self._fs = fs

    def set_active(self, active: bool):
        self.is_active = active
        self.update_colors()

    def on_hover(self, e):
        if not self.is_active:
            self.configure(bg=BG_SURFACE, fg=TEXT_MAIN)

    def on_leave(self, e):
        if not self.is_active:
            self.configure(bg=BG_CRUST, fg=TEXT_SUB)

    def update_colors(self):
        if self.is_active:
            self.configure(bg=BG_SURFACE, fg=ACCENT_BLUE, font=(FONT_FAMILY, self._fs, "bold"))
        else:
            self.configure(bg=BG_CRUST, fg=TEXT_SUB, font=(FONT_FAMILY, self._fs, "normal"))

    def set_compact(self, compact: bool):
        if compact:
            self.configure(text=f" {self.icon} ", anchor="center", padx=0)
        else:
            self.configure(text=self.full_text, anchor="w", padx=16)


class Sidebar(ttk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, style="Sidebar.TFrame")
        self.controller = controller
        self.is_compact = False
        self._pulse_job = None  # recording pulse animation
        self._pulse_state = False

        # Header Title Area
        self.header_frame = ttk.Frame(self, style="Sidebar.TFrame", padding=(16, 20, 16, 20))
        self.header_frame.pack(fill=tk.X)
        
        self.header_lbl = ttk.Label(self.header_frame, text="MEETING NOTES AI", style="SidebarHeader.TLabel")
        self.header_lbl.pack(anchor="w")

        # Navigation Buttons Frame
        self.nav_frame = ttk.Frame(self, style="Sidebar.TFrame")
        self.nav_frame.pack(fill=tk.X, pady=10)

        self.buttons: dict[str, SidebarButton] = {}
        for view_name, icon, label in [
            ("dashboard", "🏠", "Dashboard"),
            ("record", "🎙️", "Live Session"),
            ("todo", "📅", "Daily Todos"),
            ("search", "🔍", "Search Hub"),
            ("settings", "⚙️", "Settings & Logs"),
        ]:
            cmd = lambda v=view_name: controller.switch_view(v)
            btn = SidebarButton(self.nav_frame, icon, label, cmd)
            btn.pack(fill=tk.X, pady=2)
            self.buttons[view_name] = btn

        # Divider/Spacer
        ttk.Frame(self, style="Sidebar.TFrame", height=1).pack(fill=tk.X, expand=True)

        # Bottom global Session Status & Telemetry Widget
        self.telemetry_card = ttk.Frame(self, style="Sidebar.TFrame", padding=14)
        self.telemetry_card.pack(fill=tk.X, side=tk.BOTTOM, pady=(0, 10))

        self.telemetry_title = ttk.Label(self.telemetry_card, text="SESSION STATUS", style="CardMuted.TLabel", font=(FONT_FAMILY, font_size(8), "bold"), background=BG_CRUST)
        self.telemetry_title.pack(anchor="w", pady=(0, 6))

        # Status badge row
        status_row = ttk.Frame(self.telemetry_card, style="Sidebar.TFrame")
        status_row.pack(fill=tk.X, pady=(0, 6))
        
        self.status_indicator = tk.Label(
            status_row,
            textvariable=controller.status_var,
            font=(FONT_FAMILY, font_size(9), "bold"),
            bg=BG_OVERLAY,
            fg=TEXT_MAIN,
            padx=10,
            pady=3,
            relief="flat"
        )
        self.status_indicator.pack(side=tk.LEFT)

        # Level meter and label
        self.meter_row = ttk.Frame(self.telemetry_card, style="Sidebar.TFrame")
        self.meter_row.pack(fill=tk.X, pady=(6, 4))
        
        self.audio_meter = AudioMeter(self.meter_row)
        self.audio_meter.pack(fill=tk.X, pady=(0, 2))
        
        self.dbfs_label = ttk.Label(self.meter_row, textvariable=controller.dbfs_label_var, style="CardMuted.TLabel", font=(FONT_MONO, font_size(8)), background=BG_CRUST)
        self.dbfs_label.pack(anchor="e")

        # Telemetry metrics grid
        self.metrics_grid = ttk.Frame(self.telemetry_card, style="Sidebar.TFrame")
        self.metrics_grid.pack(fill=tk.X, pady=(6, 0))
        self.metrics_grid.columnconfigure(1, weight=1)

        metrics = [
            ("Latency", controller.transcribe_time_var, 0),
            ("RT Factor", controller.rtf_var, 1),
            ("Chunks", controller.chunks_var, 2),
        ]
        self.metric_widgets = []
        for lbl, var, row_idx in metrics:
            l_lbl = ttk.Label(self.metrics_grid, text=f"{lbl}:", style="CardMuted.TLabel", background=BG_CRUST)
            l_lbl.grid(row=row_idx, column=0, sticky="w", pady=1)
            
            l_val = ttk.Label(self.metrics_grid, textvariable=var, style="CardText.TLabel", font=(FONT_MONO, font_size(8), "bold"), background=BG_CRUST)
            l_val.grid(row=row_idx, column=1, sticky="e", pady=1)
            self.metric_widgets.extend([l_lbl, l_val])

        # Active view default
        self.set_active_button("dashboard")

    def set_active_button(self, view_name: str) -> None:
        """Mark active navigation button."""
        for name, btn in self.buttons.items():
            btn.set_active(name == view_name)

    def start_pulse(self) -> None:
        """Start a pulsing animation on the status indicator for active recording."""
        self._pulse_state = True
        self._do_pulse()

    def stop_pulse(self) -> None:
        """Stop the pulsing animation."""
        self._pulse_state = False
        if self._pulse_job:
            self.after_cancel(self._pulse_job)
            self._pulse_job = None

    def _do_pulse(self) -> None:
        """Alternate between bright and dim green to create a pulse effect."""
        if not self._pulse_state:
            return
        current_bg = self.status_indicator.cget("bg")
        if current_bg == ACCENT_GREEN:
            self.status_indicator.configure(bg="#7bc977")  # slightly dimmer green
        else:
            self.status_indicator.configure(bg=ACCENT_GREEN)
        self._pulse_job = self.after(800, self._do_pulse)

    def set_compact(self, compact: bool) -> None:
        """Set responsive visual state (collapsing or expanding text)."""
        if self.is_compact == compact:
            return
        self.is_compact = compact

        if compact:
            self.header_lbl.pack_forget()
            if not hasattr(self, "header_lbl_comp") or not self.header_lbl_comp.winfo_exists():
                self.header_lbl_comp = ttk.Label(self.header_frame, text="M", style="SidebarHeader.TLabel")
            self.header_lbl_comp.pack(anchor="center")
            
            for btn in self.buttons.values():
                btn.set_compact(True)
                
            self.telemetry_title.pack_forget()
            self.dbfs_label.pack_forget()
            self.metrics_grid.pack_forget()
            # Keep textvariable bound — just shrink padding
            self.status_indicator.configure(padx=4, font=(FONT_FAMILY, font_size(7), "bold"))
        else:
            if hasattr(self, "header_lbl_comp") and self.header_lbl_comp.winfo_exists():
                self.header_lbl_comp.pack_forget()
            self.header_lbl.pack(anchor="w")
            
            for btn in self.buttons.values():
                btn.set_compact(False)
                
            self.telemetry_title.pack(anchor="w", pady=(0, 6))
            self.dbfs_label.pack(anchor="e")
            self.metrics_grid.pack(fill=tk.X, pady=(6, 0))
            self.status_indicator.configure(padx=10, font=(FONT_FAMILY, font_size(9), "bold"))
