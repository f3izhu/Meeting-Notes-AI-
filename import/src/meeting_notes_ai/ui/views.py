"""Views and panels for the Meeting Notes AI application."""
from __future__ import annotations
import calendar
import tkinter as tk
from tkinter import ttk
from datetime import date, datetime
from meeting_notes_ai.ui.styles import (
    BG_CRUST, BG_MANTLE, BG_SURFACE, BG_OVERLAY, TEXT_MAIN, TEXT_SUB, TEXT_MUTED,
    ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, ACCENT_YELLOW, COLOR_ACTIVE_HOVER,
    FONT_FAMILY, FONT_MONO, font_size, scale_factor,
)

MONTH_NAMES = list(calendar.month_name)[1:]


class ScrollableFrame(ttk.Frame):
    """A frame that scrolls vertically via an embedded Canvas.
    
    Use .interior as the parent for child widgets.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, bg=BG_SURFACE, highlightthickness=0, bd=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.interior = ttk.Frame(self.canvas, style="Card.TFrame")

        self.interior.bind("<Configure>", self._on_interior_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        self._window_id = self.canvas.create_window((0, 0), window=self.interior, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Enable mousewheel scrolling
        self.interior.bind("<Enter>", self._bind_mousewheel)
        self.interior.bind("<Leave>", self._unbind_mousewheel)

    def _on_interior_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.canvas.itemconfig(self._window_id, width=event.width)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class FlatButton(tk.Button):
    """Custom premium flat button with hover states."""
    def __init__(self, parent, text, command, accent=False, danger=False, **kwargs):
        bg_color = ACCENT_GREEN if accent else (ACCENT_RED if danger else BG_OVERLAY)
        fg_color = BG_MANTLE if (accent or danger) else TEXT_MAIN
        active_bg = "#bceeb7" if accent else ("#ff9bb5" if danger else COLOR_ACTIVE_HOVER)
        active_fg = bg_color if (accent or danger) else TEXT_MAIN
        
        fs = font_size(9)
        super().__init__(
            parent,
            text=text,
            font=(FONT_FAMILY, fs, "bold" if (accent or danger) else "normal"),
            bg=bg_color,
            fg=fg_color,
            activebackground=active_bg,
            activeforeground=active_fg,
            relief=tk.FLAT,
            bd=0,
            cursor="hand2",
            command=command,
            **kwargs
        )
        self._default_bg = bg_color
        self._hover_bg = active_bg
        self.bind("<Enter>", lambda e: self.configure(bg=self._hover_bg))
        self.bind("<Leave>", lambda e: self.configure(bg=self._default_bg))

    def set_bg(self, bg: str, hover_bg: str | None = None) -> None:
        """Update the default and hover bg colors (used for state changes like disabled buttons)."""
        self._default_bg = bg
        if hover_bg:
            self._hover_bg = hover_bg
        self.configure(bg=bg)


class EmptyStateWidget(ttk.Frame):
    """Styled empty state placeholder with icon and message."""
    def __init__(self, parent, icon: str, message: str, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        inner = ttk.Frame(self, style="Card.TFrame", padding=20)
        inner.pack(expand=True)
        ttk.Label(inner, text=icon, font=(FONT_FAMILY, font_size(24)), background=BG_SURFACE, foreground=TEXT_MUTED).pack()
        ttk.Label(inner, text=message, style="CardMuted.TLabel", wraplength=300, justify="center").pack(pady=(8, 0))


class DashboardView(ttk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        
        shell = ttk.Frame(self, padding=16)
        shell.pack(fill=tk.BOTH, expand=True)

        # Today Command Center Card
        top_card = ttk.Frame(shell, style="Card.TFrame", padding=16)
        top_card.pack(fill=tk.X, pady=(0, 16))
        
        ttk.Label(top_card, text="TODAY COMMAND CENTER", style="CardHeader.TLabel").pack(anchor="w")
        ttk.Label(top_card, textvariable=controller.dashboard_summary_var, style="CardText.TLabel").pack(anchor="w", pady=(10, 0))
        ttk.Label(top_card, textvariable=controller.dashboard_latest_var, style="CardMuted.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(top_card, textvariable=controller.ollama_status_var, style="CardMuted.TLabel").pack(anchor="w", pady=(4, 0))

        # Action Buttons row
        actions_frame = ttk.Frame(top_card, style="Card.TFrame")
        actions_frame.pack(fill=tk.X, pady=(14, 0))
        self.actions_frame = actions_frame
        
        self.action_buttons = []
        for text, cmd, is_acc in [
            ("Refresh Dashboard", controller.refresh_dashboard, False),
            ("Import Meeting Actions", controller.import_latest_meeting_actions, True),
            ("Check Ollama", controller.check_ollama_status, False),
            ("Open Output Folder", controller.open_outputs, False),
        ]:
            btn = FlatButton(actions_frame, text=text, command=cmd, accent=is_acc)
            self.action_buttons.append(btn)

        # Quick Capture Card
        quick_card = ttk.Frame(shell, style="Card.TFrame", padding=16)
        quick_card.pack(fill=tk.X, pady=(0, 16))
        
        ttk.Label(quick_card, text="QUICK CAPTURE", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        entry_row = ttk.Frame(quick_card, style="Card.TFrame")
        entry_row.pack(fill=tk.X)
        
        self.quick_entry = ttk.Entry(entry_row, textvariable=controller.quick_capture_var)
        self.quick_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.quick_entry.bind("<Return>", lambda e: controller.add_quick_capture())
        
        FlatButton(entry_row, "Add to Today", controller.add_quick_capture, accent=True).pack(side=tk.LEFT, ipady=4, ipadx=12)

        # Text grids for open tasks and meetings
        self.body_frame = ttk.Frame(shell)
        self.body_frame.pack(fill=tk.BOTH, expand=True)
        self.body_frame.columnconfigure(0, weight=1)
        self.body_frame.columnconfigure(1, weight=1)
        self.body_frame.rowconfigure(0, weight=1)

        # Left Widget: Open Tasks
        self.tasks_card = ttk.Frame(self.body_frame, style="Card.TFrame", padding=16)
        self.tasks_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        
        ttk.Label(self.tasks_card, text="OPEN TASKS & REMINDERS", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))
        
        self.tasks_text = tk.Text(
            self.tasks_card,
            wrap="word",
            bg=BG_MANTLE,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=(FONT_FAMILY, font_size(10)),
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10,
            height=8
        )
        self.tasks_text.pack(fill=tk.BOTH, expand=True)
        self.tasks_text.configure(state=tk.DISABLED)

        # Right Widget: Recent Meetings
        self.meetings_card = ttk.Frame(self.body_frame, style="Card.TFrame", padding=16)
        self.meetings_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        
        ttk.Label(self.meetings_card, text="RECENT MEETINGS", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))
        
        self.meetings_text = tk.Text(
            self.meetings_card,
            wrap="word",
            bg=BG_MANTLE,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=(FONT_FAMILY, font_size(10)),
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10,
            height=8
        )
        self.meetings_text.pack(fill=tk.BOTH, expand=True)
        self.meetings_text.configure(state=tk.DISABLED)

    def apply_layout(self, width: int) -> None:
        """Arrange elements based on layout width (wide vs compact)."""
        is_wide = width >= 900
        
        # Action buttons grid layout
        cols = 4 if is_wide else 2
        for i, btn in enumerate(self.action_buttons):
            btn.grid_forget()
            r, c = i // cols, i % cols
            btn.grid(row=r, column=c, sticky="ew", padx=4, pady=4, ipady=3)
            self.actions_frame.rowconfigure(r, weight=1)
        for col in range(cols):
            self.actions_frame.columnconfigure(col, weight=1)

        # Body grid layout
        self.tasks_card.grid_forget()
        self.meetings_card.grid_forget()
        
        if is_wide:
            self.body_frame.columnconfigure(0, weight=1)
            self.body_frame.columnconfigure(1, weight=1)
            self.body_frame.rowconfigure(0, weight=1)
            self.body_frame.rowconfigure(1, weight=0)
            self.tasks_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
            self.meetings_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        else:
            self.body_frame.columnconfigure(0, weight=1)
            self.body_frame.columnconfigure(1, weight=0)
            self.body_frame.rowconfigure(0, weight=1)
            self.body_frame.rowconfigure(1, weight=1)
            self.tasks_card.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 12))
            self.meetings_card.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)


class RecordView(ttk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        
        shell = ttk.Frame(self, padding=16)
        shell.pack(fill=tk.BOTH, expand=True)

        # Top Control & Telemetry Bar
        self.top_bar = ttk.Frame(shell, style="Card.TFrame", padding=14)
        self.top_bar.pack(fill=tk.X, pady=(0, 16))

        # Left side: title + status
        title_frame = ttk.Frame(self.top_bar, style="Card.TFrame")
        title_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(title_frame, text="LIVE RECORDING WORKSPACE", style="CardHeader.TLabel").pack(anchor="w")
        
        # Session info row with title and elapsed timer
        session_row = ttk.Frame(title_frame, style="Card.TFrame")
        session_row.pack(anchor="w", pady=(4, 0))
        
        self.session_title_lbl = ttk.Label(session_row, text="No active session", font=(FONT_FAMILY, font_size(9), "italic"), style="CardMuted.TLabel")
        self.session_title_lbl.pack(side=tk.LEFT)
        
        self.elapsed_lbl = ttk.Label(session_row, text="", font=(FONT_MONO, font_size(9), "bold"), style="CardMuted.TLabel")
        self.elapsed_lbl.pack(side=tk.LEFT, padx=(12, 0))

        # Settings preview row (shows current config at a glance)
        self.config_preview = ttk.Label(
            title_frame,
            text="",
            font=(FONT_FAMILY, font_size(8)),
            style="CardMuted.TLabel"
        )
        self.config_preview.pack(anchor="w", pady=(2, 0))
        self._update_config_preview()

        # Right side: Control buttons
        btn_frame = ttk.Frame(self.top_bar, style="Card.TFrame")
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self.start_btn = FlatButton(btn_frame, "▶  Start Recording", controller.start, accent=True)
        self.start_btn.pack(side=tk.LEFT, padx=4, ipady=4, ipadx=12)

        self.stop_btn = FlatButton(btn_frame, "⏹  Stop Recording", controller.stop, danger=True)
        self.stop_btn.pack(side=tk.LEFT, padx=4, ipady=4, ipadx=12)
        self.stop_btn.configure(state=tk.DISABLED)
        self.stop_btn.set_bg(BG_OVERLAY)
        self.stop_btn.configure(fg=TEXT_MUTED)

        # Split pane area for Transcript and Notes
        self.pane_frame = ttk.Frame(shell)
        self.pane_frame.pack(fill=tk.BOTH, expand=True)
        self.pane_frame.columnconfigure(0, weight=1)
        self.pane_frame.columnconfigure(1, weight=1)
        self.pane_frame.rowconfigure(0, weight=1)

        # Transcript Frame
        self.transcript_card = ttk.Frame(self.pane_frame, style="Card.TFrame", padding=14)
        self.transcript_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        
        ttk.Label(self.transcript_card, text="LIVE TRANSCRIPT", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        
        text_scroll_t = ttk.Frame(self.transcript_card)
        text_scroll_t.pack(fill=tk.BOTH, expand=True)
        
        self.transcript_log = tk.Text(
            text_scroll_t,
            wrap="word",
            bg=BG_MANTLE,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=(FONT_FAMILY, font_size(10)),
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10
        )
        self.transcript_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.transcript_log.insert(tk.END, "Waiting for transcription to begin...\n")
        self.transcript_log.configure(state=tk.DISABLED)

        t_scroll = ttk.Scrollbar(text_scroll_t, orient="vertical", command=self.transcript_log.yview)
        t_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.transcript_log.configure(yscrollcommand=t_scroll.set)

        # Live Notes Frame
        self.notes_card = ttk.Frame(self.pane_frame, style="Card.TFrame", padding=14)
        self.notes_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        
        ttk.Label(self.notes_card, text="LIVE AI SUMMARY & ACTIONS", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        
        text_scroll_n = ttk.Frame(self.notes_card)
        text_scroll_n.pack(fill=tk.BOTH, expand=True)
        
        self.notes_log = tk.Text(
            text_scroll_n,
            wrap="word",
            bg=BG_MANTLE,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=(FONT_FAMILY, font_size(10)),
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10
        )
        self.notes_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.notes_log.tag_configure("header", font=(FONT_FAMILY, font_size(11), "bold"), foreground=ACCENT_BLUE)
        self.notes_log.tag_configure("bullet", font=(FONT_FAMILY, font_size(10)), foreground=TEXT_MAIN)
        self.notes_log.tag_configure("muted", font=(FONT_FAMILY, font_size(10), "italic"), foreground=TEXT_MUTED)
        
        self.notes_log.insert(tk.END, "Highlights and action items will appear here once audio chunks are processed.\n", "muted")
        self.notes_log.configure(state=tk.DISABLED)

        n_scroll = ttk.Scrollbar(text_scroll_n, orient="vertical", command=self.notes_log.yview)
        n_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.notes_log.configure(yscrollcommand=n_scroll.set)

    def _update_config_preview(self) -> None:
        """Show current recording settings at a glance."""
        try:
            c = self.controller
            source = c.source_var.get()
            model = c.model_var.get()
            device = c.device_var.get() or "(Auto)"
            ollama = "Ollama" if c.ollama_var.get() else "Local"
            self.config_preview.configure(text=f"{source.upper()} · {model} · {device} · {ollama}")
        except Exception:
            pass

    def apply_layout(self, width: int) -> None:
        """Arrange components side-by-side or stacked."""
        self._update_config_preview()
        is_wide = width >= 960
        self.transcript_card.grid_forget()
        self.notes_card.grid_forget()
        
        if is_wide:
            self.pane_frame.columnconfigure(0, weight=1)
            self.pane_frame.columnconfigure(1, weight=1)
            self.pane_frame.rowconfigure(0, weight=1)
            self.pane_frame.rowconfigure(1, weight=0)
            self.transcript_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
            self.notes_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        else:
            self.pane_frame.columnconfigure(0, weight=1)
            self.pane_frame.columnconfigure(1, weight=0)
            self.pane_frame.rowconfigure(0, weight=1)
            self.pane_frame.rowconfigure(1, weight=1)
            self.transcript_card.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))
            self.notes_card.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)


class TodoView(ttk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        
        shell = ttk.Frame(self, padding=16)
        shell.pack(fill=tk.BOTH, expand=True)
        self.shell = shell

        # Left Panel: Calendar Grid
        self.calendar_panel = ttk.Frame(shell, style="Card.TFrame", padding=14)
        self.calendar_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 12))

        ttk.Label(self.calendar_panel, text="DAILY HISTORY", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))

        # Month and Year selection controls
        month_row = ttk.Frame(self.calendar_panel, style="Card.TFrame")
        month_row.pack(fill=tk.X, pady=(0, 8))
        
        self.month_combo = ttk.Combobox(
            month_row,
            textvariable=controller.todo_month_var,
            values=MONTH_NAMES,
            state="readonly",
            width=12,
        )
        self.month_combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 6))
        
        self.year_spin = tk.Spinbox(
            month_row,
            from_=2000,
            to=2100,
            textvariable=controller.todo_year_var,
            width=6,
            bg=BG_SURFACE,
            fg=TEXT_MAIN,
            buttonbackground=BG_OVERLAY,
            bd=0,
            relief=tk.FLAT,
        )
        self.year_spin.pack(side=tk.LEFT)
        
        controller.todo_month_var.trace_add("write", lambda *_: controller._render_calendar_from_controls())
        controller.todo_year_var.trace_add("write", lambda *_: controller._render_calendar_from_controls())

        # Previous, Today, Next Nav buttons
        nav_row = ttk.Frame(self.calendar_panel, style="Card.TFrame")
        nav_row.pack(fill=tk.X, pady=(0, 10))
        for label, cmd in [
            ("◀ Prev", lambda: controller._shift_todo_day(-1)),
            ("Today", lambda: controller._show_todo_date(date.today())),
            ("Next ▶", lambda: controller._shift_todo_day(1)),
        ]:
            FlatButton(nav_row, label, cmd).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2, ipady=3)

        self.calendar_grid = ttk.Frame(self.calendar_panel, style="Card.TFrame")
        self.calendar_grid.pack(fill=tk.X)

        # Right Panel: Task Editor & Notes
        self.editor_panel = ttk.Frame(shell, style="Card.TFrame", padding=16)
        self.editor_panel.grid(row=0, column=1, sticky="nsew")

        # Editor header
        header_row = ttk.Frame(self.editor_panel, style="Card.TFrame")
        header_row.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(header_row, textvariable=controller.todo_date_label_var, style="CardHeader.TLabel").pack(side=tk.LEFT)
        ttk.Label(header_row, textvariable=controller.todo_status_var, style="CardMuted.TLabel").pack(side=tk.RIGHT)

        # Add Task Row
        add_row = ttk.Frame(self.editor_panel, style="Card.TFrame")
        add_row.pack(fill=tk.X, pady=(0, 12))
        add_row.columnconfigure(0, weight=1)
        self.todo_add_row = add_row
        
        self.new_task_entry = ttk.Entry(add_row, textvariable=controller.new_task_var)
        self.new_task_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=2)
        self.new_task_entry.bind("<Return>", lambda e: controller._add_todo_task())
        
        self.todo_priority_combo = ttk.Combobox(
            add_row,
            textvariable=controller.new_task_priority_var,
            values=["High", "Normal", "Low"],
            state="readonly",
            width=8,
        )
        self.todo_priority_combo.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=2)
        
        self.todo_due_entry = ttk.Entry(add_row, textvariable=controller.new_task_due_var, width=12)
        self.todo_due_entry.grid(row=0, column=2, sticky="ew", padx=(0, 8), pady=2)
        # Add placeholder text
        self.todo_due_entry.insert(0, "YYYY-MM-DD")
        self.todo_due_entry.bind("<FocusIn>", self._clear_due_placeholder)
        self.todo_due_entry.bind("<FocusOut>", self._restore_due_placeholder)
        
        self.todo_add_btn = FlatButton(add_row, "Add Task", controller._add_todo_task, accent=True)
        self.todo_add_btn.grid(row=0, column=3, sticky="ew", ipady=4, ipadx=10, pady=2)

        # Tools Row
        tool_row = ttk.Frame(self.editor_panel, style="Card.TFrame")
        tool_row.pack(fill=tk.X, pady=(0, 12))
        self.tool_row = tool_row
        self.tool_buttons = []
        for text, cmd, is_acc in [
            ("Import Meeting Actions", controller.import_latest_meeting_actions, True),
            ("Export Today MD", lambda: controller.export_todos("today", "md"), False),
            ("Export Today HTML", lambda: controller.export_todos("today", "html"), False),
            ("Export All MD", lambda: controller.export_todos("all", "md"), False),
            ("Export All HTML", lambda: controller.export_todos("all", "html"), False),
        ]:
            btn = FlatButton(tool_row, text, cmd, accent=is_acc)
            self.tool_buttons.append(btn)

        # Tasks List Container — scrollable
        task_scroll_frame = ttk.Frame(self.editor_panel)
        task_scroll_frame.pack(fill=tk.BOTH, pady=(0, 12))
        
        self.task_list_scroll = ScrollableFrame(task_scroll_frame)
        self.task_list_scroll.pack(fill=tk.BOTH, expand=True)
        self.task_list_frame = self.task_list_scroll.interior

        # Daily Notes section
        ttk.Label(self.editor_panel, text="DAILY NOTES", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 6))
        
        text_scroll = ttk.Frame(self.editor_panel)
        text_scroll.pack(fill=tk.BOTH, expand=True)
        
        self.todo_text = tk.Text(
            text_scroll,
            wrap="word",
            bg=BG_MANTLE,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=(FONT_FAMILY, font_size(10)),
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=12,
            undo=True,
        )
        self.todo_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.todo_text.bind("<KeyRelease>", controller._schedule_todo_save)
        
        todo_scroll = ttk.Scrollbar(text_scroll, orient="vertical", command=self.todo_text.yview)
        todo_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.todo_text.configure(yscrollcommand=todo_scroll.set)

    def _clear_due_placeholder(self, event):
        if self.controller.new_task_due_var.get() == "YYYY-MM-DD":
            self.controller.new_task_due_var.set("")

    def _restore_due_placeholder(self, event):
        if not self.controller.new_task_due_var.get().strip():
            self.controller.new_task_due_var.set("YYYY-MM-DD")

    def apply_layout(self, width: int) -> None:
        """Arrange components based on width."""
        is_wide = width >= 960
        self.calendar_panel.grid_forget()
        self.editor_panel.grid_forget()
        
        # Tools row button columns layout
        cols = 5 if is_wide else 2
        for i, btn in enumerate(self.tool_buttons):
            btn.grid_forget()
            r, c = i // cols, i % cols
            btn.grid(row=r, column=c, sticky="ew", padx=3, pady=3, ipady=3)
            self.tool_row.rowconfigure(r, weight=1)
        for col in range(cols):
            self.tool_row.columnconfigure(col, weight=1)

        # Calendar and Editor main layouts
        if is_wide:
            self.shell.columnconfigure(0, weight=0)
            self.shell.columnconfigure(1, weight=1)
            self.shell.rowconfigure(0, weight=1)
            self.calendar_panel.grid(row=0, column=0, sticky="nsw", padx=(0, 12), pady=0)
            self.calendar_panel.configure(width=280)
            self.editor_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
            
            # Reposition Add Task controls to a single horizontal row
            self.new_task_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8), pady=2)
            self.todo_priority_combo.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=2)
            self.todo_due_entry.grid(row=0, column=2, sticky="ew", padx=(0, 8), pady=2)
            self.todo_add_btn.grid(row=0, column=3, sticky="ew", pady=2)
            self.todo_add_row.columnconfigure(0, weight=3)
            self.todo_add_row.columnconfigure(1, weight=1)
            self.todo_add_row.columnconfigure(2, weight=1)
            self.todo_add_row.columnconfigure(3, weight=0)
        else:
            self.shell.columnconfigure(0, weight=1)
            self.shell.columnconfigure(1, weight=0)
            self.shell.rowconfigure(0, weight=0)
            self.shell.rowconfigure(1, weight=1)
            self.calendar_panel.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 12))
            self.calendar_panel.configure(width=0)  # expands to full width
            self.editor_panel.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
            
            # Stack Add Task fields vertically for compact layouts
            self.new_task_entry.grid(row=0, column=0, columnspan=3, sticky="ew", padx=0, pady=2)
            self.todo_priority_combo.grid(row=1, column=0, columnspan=1, sticky="ew", padx=(0, 6), pady=2)
            self.todo_due_entry.grid(row=1, column=1, columnspan=1, sticky="ew", padx=(0, 6), pady=2)
            self.todo_add_btn.grid(row=1, column=2, columnspan=1, sticky="ew", pady=2)
            self.todo_add_row.columnconfigure(0, weight=1)
            self.todo_add_row.columnconfigure(1, weight=1)
            self.todo_add_row.columnconfigure(2, weight=1)
            self.todo_add_row.columnconfigure(3, weight=0)


class SearchView(ttk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        
        shell = ttk.Frame(self, padding=16)
        shell.pack(fill=tk.BOTH, expand=True)

        # Search Bar Frame
        bar_card = ttk.Frame(shell, style="Card.TFrame", padding=14)
        bar_card.pack(fill=tk.X, pady=(0, 16))
        
        ttk.Label(bar_card, text="SEARCH HUB (TODOS & MEETINGS)", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 10))
        
        row = ttk.Frame(bar_card, style="Card.TFrame")
        row.pack(fill=tk.X)
        
        self.search_entry = ttk.Entry(row, textvariable=controller.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.search_entry.bind("<Return>", lambda e: controller.run_search())
        
        FlatButton(row, "Run Search", controller.run_search, accent=True).pack(side=tk.LEFT, ipady=4, ipadx=14)

        # Search Results
        results_card = ttk.Frame(shell, style="Card.TFrame", padding=14)
        results_card.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(results_card, text="MATCHING SEARCH RESULTS", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        
        text_scroll = ttk.Frame(results_card)
        text_scroll.pack(fill=tk.BOTH, expand=True)
        
        self.search_result = tk.Text(
            text_scroll,
            wrap="word",
            bg=BG_MANTLE,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=(FONT_FAMILY, font_size(10)),
            relief=tk.FLAT,
            bd=0,
            padx=12,
            pady=12,
        )
        self.search_result.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.search_result.tag_configure("link", foreground=ACCENT_BLUE, underline=True)
        self.search_result.tag_configure("section", foreground=ACCENT_BLUE, font=(FONT_FAMILY, font_size(11), "bold"))
        self.search_result.configure(state=tk.DISABLED)

        s_scroll = ttk.Scrollbar(text_scroll, orient="vertical", command=self.search_result.yview)
        s_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.search_result.configure(yscrollcommand=s_scroll.set)


class SettingsView(ttk.Frame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent)
        self.controller = controller
        
        # We will use a main scrollable window or split-pane configurations to lay out all auxiliary items cleanly.
        shell = ttk.Frame(self, padding=16)
        shell.pack(fill=tk.BOTH, expand=True)
        
        # Left side: Transcriber Configuration Card
        # Right side: App system properties & logs Card
        self.body_frame = ttk.Frame(shell)
        self.body_frame.pack(fill=tk.BOTH, expand=True)
        self.body_frame.columnconfigure(0, weight=1)
        self.body_frame.columnconfigure(1, weight=1)
        self.body_frame.rowconfigure(0, weight=1)

        # Left Card: Session Configurations
        self.left_card = ttk.Frame(self.body_frame, style="Card.TFrame", padding=16)
        self.left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        
        ttk.Label(self.left_card, text="SESSION & WHISPER CONFIGURATION", style="CardHeader.TLabel").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 12))

        row = 1
        ttk.Label(self.left_card, text="Meeting Title", style="CardText.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        title_ent = ttk.Entry(self.left_card, textvariable=controller.title_var)
        title_ent.grid(row=row, column=1, sticky="ew", pady=4, padx=(12, 0))

        row += 1
        ttk.Label(self.left_card, text="Input Source", style="CardText.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        source_wrap = ttk.Frame(self.left_card, style="Card.TFrame")
        source_wrap.grid(row=row, column=1, sticky="w", pady=4, padx=(12, 0))
        ttk.Radiobutton(source_wrap, text="Microphone", value="mic", variable=controller.source_var).pack(side=tk.LEFT, padx=(0, 14))
        ttk.Radiobutton(source_wrap, text="Loopback (Online)", value="loopback", variable=controller.source_var).pack(side=tk.LEFT)

        row += 1
        ttk.Label(self.left_card, text="Audio Device", style="CardText.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        device_wrap = ttk.Frame(self.left_card, style="Card.TFrame")
        device_wrap.grid(row=row, column=1, sticky="ew", pady=4, padx=(12, 0))
        
        self.device_combo = ttk.Combobox(device_wrap, textvariable=controller.device_var, state="readonly")
        self.device_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        FlatButton(device_wrap, "Refresh", controller.refresh_devices).pack(side=tk.LEFT, padx=(8, 0), ipady=2, ipadx=6)

        row += 1
        ttk.Label(self.left_card, text="Whisper Profile", style="CardText.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        whisper_frame = ttk.Frame(self.left_card, style="Card.TFrame")
        whisper_frame.grid(row=row, column=1, sticky="w", pady=4, padx=(12, 0))
        
        ttk.Combobox(
            whisper_frame,
            textvariable=controller.profile_var,
            values=["auto", "fast", "balanced", "accurate"],
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=(0, 14))

        ttk.Label(whisper_frame, text="Backend", style="CardText.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Combobox(
            whisper_frame,
            textvariable=controller.inference_device_var,
            values=["cpu", "auto", "cuda"],
            state="readonly",
            width=8,
        ).pack(side=tk.LEFT)

        row += 1
        ttk.Label(self.left_card, text="Whisper Model", style="CardText.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        model_lang_frame = ttk.Frame(self.left_card, style="Card.TFrame")
        model_lang_frame.grid(row=row, column=1, sticky="w", pady=4, padx=(12, 0))
        
        ttk.Combobox(
            model_lang_frame,
            textvariable=controller.model_var,
            values=["tiny.en", "base.en", "small.en", "medium.en", "tiny", "base", "small", "medium", "large-v3"],
            state="readonly",
            width=12,
        ).pack(side=tk.LEFT, padx=(0, 14))

        ttk.Label(model_lang_frame, text="Language", style="CardText.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Combobox(
            model_lang_frame,
            textvariable=controller.language_var,
            values=["en", "es", "fr", "de", "it", "pt", "nl", "ja", "ko", "zh", "ar", "ru", "hi", "auto"],
            state="readonly",
            width=6,
        ).pack(side=tk.LEFT)

        row += 1
        ttk.Label(self.left_card, text="Output Folder", style="CardText.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        ttk.Entry(self.left_card, textvariable=controller.output_dir_var).grid(row=row, column=1, sticky="ew", pady=4, padx=(12, 0))

        row += 1
        ttk.Label(self.left_card, text="Ollama Summary", style="CardText.TLabel").grid(row=row, column=0, sticky="w", pady=4)
        ollama_wrap = ttk.Frame(self.left_card, style="Card.TFrame")
        ollama_wrap.grid(row=row, column=1, sticky="w", pady=4, padx=(12, 0))
        
        ttk.Checkbutton(ollama_wrap, text="Enabled", variable=controller.ollama_var).pack(side=tk.LEFT, padx=(0, 14))
        ttk.Label(ollama_wrap, text="Model", style="CardText.TLabel").pack(side=tk.LEFT, padx=(0, 6))
        ttk.Entry(ollama_wrap, textvariable=controller.ollama_model_var, width=12).pack(side=tk.LEFT)

        row += 1
        adv_wrap = ttk.Frame(self.left_card, style="Card.TFrame")
        adv_wrap.grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 0))
        
        ttk.Checkbutton(adv_wrap, text="Save preferences as defaults", variable=controller.save_pref_var).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Checkbutton(adv_wrap, text="Simulate Run", variable=controller.simulate_var).pack(side=tk.LEFT)
        
        ttk.Label(adv_wrap, text="Time(s)", style="CardText.TLabel").pack(side=tk.LEFT, padx=(8, 4))
        ttk.Entry(adv_wrap, textvariable=controller.sim_duration_var, width=5).pack(side=tk.LEFT)

        self.left_card.columnconfigure(1, weight=1)

        # Right Card: App Configuration & Logs
        self.right_card = ttk.Frame(self.body_frame, style="Card.TFrame", padding=16)
        self.right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        
        # Tabs inside Right Card: System Setup vs Manual Speaker Correction vs Debug Logs
        self.settings_notebook = ttk.Notebook(self.right_card)
        self.settings_notebook.pack(fill=tk.BOTH, expand=True)

        # Sub-tab 1: System settings (Startup & Encryption, folder options)
        sys_tab = ttk.Frame(self.settings_notebook, padding=10, style="Card.TFrame")
        self.settings_notebook.add(sys_tab, text=" System ")
        
        # Startup Settings widget
        startup_wrap = ttk.Frame(sys_tab, style="Card.TFrame")
        startup_wrap.pack(fill=tk.X, pady=(0, 12))
        ttk.Label(startup_wrap, text="WINDOWS STARTUP PROPERTIES", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(startup_wrap, textvariable=controller.startup_status_var, style="CardMuted.TLabel").pack(anchor="w", pady=(0, 6))
        
        startup_btns = ttk.Frame(startup_wrap, style="Card.TFrame")
        startup_btns.pack(fill=tk.X)
        FlatButton(startup_btns, "Enable Startup Link", controller.enable_startup).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4), ipady=3)
        FlatButton(startup_btns, "Disable Link", controller.disable_startup).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0), ipady=3)



        # Auxiliary Actions widget
        aux_wrap = ttk.Frame(sys_tab, style="Card.TFrame")
        aux_wrap.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(aux_wrap, text="AUXILIARY TOOLS", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        
        for text, cmd in [
            ("Open Configuration Folder", controller.open_config_folder),
            ("Force Export Last Session HTML", controller.export_last_html)
        ]:
            FlatButton(aux_wrap, text, cmd).pack(fill=tk.X, pady=4, ipady=3)
        
        ttk.Checkbutton(aux_wrap, text="Close button minimizes to background", variable=controller.minimize_on_close_var).pack(anchor="w", pady=(8, 0))

        # Keyboard shortcuts help
        shortcuts_wrap = ttk.Frame(sys_tab, style="Card.TFrame")
        shortcuts_wrap.pack(fill=tk.X, pady=(12, 0))
        ttk.Label(shortcuts_wrap, text="KEYBOARD SHORTCUTS", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 4))
        shortcuts_text = (
            "Ctrl+R — Start Recording    Ctrl+E — Stop Recording\n"
            "Ctrl+1 — Dashboard    Ctrl+2 — Live Session\n"
            "Ctrl+3 — Daily Todos    Ctrl+4 — Search Hub\n"
            "Ctrl+5 — Settings & Logs"
        )
        ttk.Label(shortcuts_wrap, text=shortcuts_text, style="CardMuted.TLabel", justify="left").pack(anchor="w")

        # Sub-tab 2: Manual Correction
        correct_tab = ttk.Frame(self.settings_notebook, padding=10, style="Card.TFrame")
        self.settings_notebook.add(correct_tab, text=" Speaker Correction ")
        
        ttk.Label(correct_tab, text="MANUAL SPEAKER CORRECTION", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(correct_tab, textvariable=controller.transcript_status_var, style="CardMuted.TLabel").pack(anchor="w", pady=(0, 8))
        
        correct_btns = ttk.Frame(correct_tab, style="Card.TFrame")
        correct_btns.pack(fill=tk.X, pady=(0, 8))
        FlatButton(correct_btns, "Load Latest Transcript", controller.load_latest_transcript_for_correction, accent=True).pack(side=tk.LEFT, padx=(0, 4), ipady=3, ipadx=6)
        FlatButton(correct_btns, "Save Corrected Copy", controller.save_corrected_transcript).pack(side=tk.LEFT, padx=(4, 0), ipady=3, ipadx=6)

        text_scroll_c = ttk.Frame(correct_tab)
        text_scroll_c.pack(fill=tk.BOTH, expand=True)
        self.transcript_editor = tk.Text(
            text_scroll_c,
            wrap="word",
            bg=BG_MANTLE,
            fg=TEXT_MAIN,
            insertbackground=TEXT_MAIN,
            font=(FONT_MONO, font_size(9)),
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=10,
            undo=True
        )
        self.transcript_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        c_scroll = ttk.Scrollbar(text_scroll_c, orient="vertical", command=self.transcript_editor.yview)
        c_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.transcript_editor.configure(yscrollcommand=c_scroll.set)

        # Sub-tab 3: System logs
        log_tab = ttk.Frame(self.settings_notebook, padding=10, style="Card.TFrame")
        self.settings_notebook.add(log_tab, text=" Debug Logs ")
        
        ttk.Label(log_tab, text="SYSTEM RUNTIME LOGS", style="CardHeader.TLabel").pack(anchor="w", pady=(0, 8))
        
        text_scroll_l = ttk.Frame(log_tab)
        text_scroll_l.pack(fill=tk.BOTH, expand=True)
        self.log_text = tk.Text(
            text_scroll_l,
            wrap="word",
            bg=BG_CRUST,
            fg=TEXT_SUB,
            insertbackground=TEXT_MAIN,
            font=(FONT_MONO, font_size(9)),
            relief=tk.FLAT,
            bd=0,
            padx=8,
            pady=8
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        l_scroll = ttk.Scrollbar(text_scroll_l, orient="vertical", command=self.log_text.yview)
        l_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.configure(yscrollcommand=l_scroll.set)

    def apply_layout(self, width: int) -> None:
        """Stack configurations vertically if window width is narrow."""
        is_wide = width >= 900
        self.left_card.grid_forget()
        self.right_card.grid_forget()
        
        if is_wide:
            self.body_frame.columnconfigure(0, weight=1)
            self.body_frame.columnconfigure(1, weight=1)
            self.body_frame.rowconfigure(0, weight=1)
            self.body_frame.rowconfigure(1, weight=0)
            self.left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)
            self.right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)
        else:
            self.body_frame.columnconfigure(0, weight=1)
            self.body_frame.columnconfigure(1, weight=0)
            self.body_frame.rowconfigure(0, weight=0)
            self.body_frame.rowconfigure(1, weight=1)
            self.left_card.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 12))
            self.right_card.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
