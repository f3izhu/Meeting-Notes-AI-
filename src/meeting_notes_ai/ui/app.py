"""Core UI application controller for Meeting Notes AI."""
from __future__ import annotations

import calendar
import json
import os
import queue
import re
import subprocess
import sys
import threading
import traceback
import tkinter as tk
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from time import monotonic
from tkinter import messagebox, simpledialog, ttk
from typing import Any

from meeting_notes_ai.audio import list_input_devices
from meeting_notes_ai.config import load_config
from meeting_notes_ai.notes import export_html

# Local modular imports
from meeting_notes_ai.ui.styles import (
    configure_styles, enable_dpi_awareness, scale_factor, scaled, font_size,
    BG_CRUST, BG_MANTLE, BG_SURFACE, BG_OVERLAY,
    TEXT_MAIN, TEXT_SUB, TEXT_MUTED, ACCENT_BLUE, ACCENT_GREEN, ACCENT_RED, ACCENT_YELLOW,
    COLOR_ACTIVE_HOVER, FONT_FAMILY, FONT_MONO,
)
from meeting_notes_ai.ui.todo_manager import TodoManager
from meeting_notes_ai.ui.sidebar import Sidebar
from meeting_notes_ai.ui.views import DashboardView, RecordView, TodoView, SearchView, SettingsView

ROOT = Path(__file__).resolve().parents[3]
MONTH_NAMES = list(calendar.month_name)[1:]

class MeetingNotesUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Meeting Notes AI")
        
        # Scale initial geometry and minsize based on DPI
        sf = scale_factor(root)
        geo_w, geo_h = int(1020 * sf), int(720 * sf)
        min_w, min_h = int(680 * sf), int(500 * sf)
        
        # Clamp to screen size
        scr_w = root.winfo_screenwidth()
        scr_h = root.winfo_screenheight()
        geo_w = min(geo_w, scr_w - 50)
        geo_h = min(geo_h, scr_h - 80)
        
        self.root.geometry(f"{geo_w}x{geo_h}")
        self.root.minsize(min_w, min_h)

        # Set window icon and Windows taskbar app identity
        icon_path = ROOT / "assets" / "MeetingNotesAI.ico"
        if icon_path.exists():
            try:
                self.root.iconbitmap(str(icon_path))
            except Exception:
                pass
        if os.name == "nt":
            import ctypes
            try:
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("com.meetingnotesai.app.1.0")
            except Exception:
                pass

        # Process and queue state
        self.process: subprocess.Popen[str] | None = None
        self.log_queue: queue.Queue[str] = queue.Queue()
        self.devices: list[str] = []
        self.stop_flag_path = ROOT / ".ui_stop.flag"
        self.last_run_had_diagnostic = False
        self.last_run_error = ""
        self.corrected_transcript_path: Path | None = None
        
        # Session timer state
        self._session_start_time: float | None = None
        self._timer_job: str | None = None
        
        # Tray support
        self.tray_icon = None
        self.tray_thread: threading.Thread | None = None
        
        # Todo manager & state
        self.todo_manager = TodoManager()
        self.todo_encryption_passphrase: str | None = None
        
        # Load Daily Todos database
        self.todo_data: dict[str, dict[str, Any]] = self.todo_manager.load_todo_data()
        self.selected_todo_date = date.today()
        self.todo_save_after: str | None = None

        # Regex patterns for parsing unbuffered output
        self.status_pattern = re.compile(
            r"\[status\]\s+level=\s*(?P<level>[-\d.]+)\s*dBFS\s*\|\s*transcribe=\s*(?P<transcribe>[-\d.]+)s\s*\|\s*rtf=\s*(?P<rtf>[-\d.]+)\s*\|\s*chunks=\s*(?P<chunks>\d+)"
        )
        self.segment_pattern = re.compile(r"^\[\d{2}:\d{2}:\d{2}\]\s+.*")

        defaults = load_config()

        # UI Variables
        self.title_var = tk.StringVar(value="")
        self.profile_var = tk.StringVar(value=str(defaults.get("profile", "balanced")))
        self.source_var = tk.StringVar(value="loopback" if defaults.get("loopback") else "mic")
        self.device_var = tk.StringVar(value="")
        self.model_var = tk.StringVar(value=str(defaults.get("whisper_model", "small.en")))
        self.inference_device_var = tk.StringVar(value=str(defaults.get("inference_device", "cpu")))
        self.ollama_var = tk.BooleanVar(value=bool(defaults.get("use_ollama", True)))
        self.ollama_model_var = tk.StringVar(value=str(defaults.get("ollama_model", "gemma3:1b")))
        self.max_minutes_var = tk.StringVar(value=str(defaults.get("max_minutes", "0")))
        self.output_dir_var = tk.StringVar(value=str(defaults.get("output_dir", "outputs")))
        self.language_var = tk.StringVar(value=str(defaults.get("language", "en")))
        self.save_pref_var = tk.BooleanVar(value=False)
        self.simulate_var = tk.BooleanVar(value=False)
        self.sim_duration_var = tk.StringVar(value="90")
        self.last_output_dir: str | None = None

        self.status_var = tk.StringVar(value="Idle")
        self.todo_date_label_var = tk.StringVar()
        self.todo_month_var = tk.StringVar(value=MONTH_NAMES[self.selected_todo_date.month - 1])
        self.todo_year_var = tk.StringVar(value=str(self.selected_todo_date.year))
        self.todo_status_var = tk.StringVar(value="")
        self.startup_status_var = tk.StringVar()
        self.new_task_var = tk.StringVar(value="")
        self.new_task_priority_var = tk.StringVar(value="Normal")
        self.new_task_due_var = tk.StringVar(value="")
        self.dashboard_summary_var = tk.StringVar(value="")
        self.dashboard_latest_var = tk.StringVar(value="")
        self.ollama_status_var = tk.StringVar(value="Ollama: checking...")
        self.quick_capture_var = tk.StringVar(value="")
        self.search_var = tk.StringVar(value="")
        self.transcript_status_var = tk.StringVar(value="Load a transcript to begin.")
        self.minimize_on_close_var = tk.BooleanVar(value=False)
        self.responsive_mode: str | None = None
        self._last_width: int = 0

        # Telemetry variables
        self.dbfs_label_var = tk.StringVar(value="-120.0 dBFS")
        self.transcribe_time_var = tk.StringVar(value="0.00s")
        self.rtf_var = tk.StringVar(value="0.00")
        self.chunks_var = tk.StringVar(value="0")

        # Configure premium style system
        configure_styles(self.root)

        # Build responsive layout components
        self._build_main_structure()
        
        # Load data values
        self.refresh_devices()
        self.refresh_startup_status()
        self.refresh_dashboard()
        self.check_ollama_status()
        
        # Start background polling and system bounds
        self.root.after(120, self._drain_logs)
        self.root.bind("<Configure>", self._on_root_resize)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Keyboard shortcuts
        self.root.bind("<Control-r>", lambda e: self.start())
        self.root.bind("<Control-e>", lambda e: self.stop())
        self.root.bind("<Control-Key-1>", lambda e: self.switch_view("dashboard"))
        self.root.bind("<Control-Key-2>", lambda e: self.switch_view("record"))
        self.root.bind("<Control-Key-3>", lambda e: self.switch_view("todo"))
        self.root.bind("<Control-Key-4>", lambda e: self.switch_view("search"))
        self.root.bind("<Control-Key-5>", lambda e: self.switch_view("settings"))
        self.root.report_callback_exception = self._report_callback_exception

    def _build_main_structure(self) -> None:
        """Create main layout wrapper with sidebar and center frame."""
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill=tk.BOTH, expand=True)

        # Left Sidebar Panel
        self.sidebar = Sidebar(self.main_container, self)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Main view area (active view sits here)
        self.content_area = ttk.Frame(self.main_container)
        self.content_area.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Instantiate View Panels
        self.views = {
            "dashboard": DashboardView(self.content_area, self),
            "record": RecordView(self.content_area, self),
            "todo": TodoView(self.content_area, self),
            "search": SearchView(self.content_area, self),
            "settings": SettingsView(self.content_area, self),
        }
        self.active_view_name = "dashboard"
        self.views[self.active_view_name].pack(fill=tk.BOTH, expand=True)

    def switch_view(self, view_name: str) -> None:
        """Toggle active panels in the right pane."""
        if view_name not in self.views or view_name == self.active_view_name:
            return

        self.views[self.active_view_name].pack_forget()
        self.active_view_name = view_name
        self.views[self.active_view_name].pack(fill=tk.BOTH, expand=True)
        self.sidebar.set_active_button(view_name)
        
        # Re-apply responsive layouts for active view
        self._apply_responsive_layout(force=True)

    def _on_root_resize(self, event: tk.Event) -> None:
        if event.widget is self.root:
            self._apply_responsive_layout()

    def _apply_responsive_layout(self, force: bool = False) -> None:
        width = max(self.root.winfo_width(), 1)
        
        # Skip if width hasn't changed significantly (debounce)
        if not force and abs(width - self._last_width) < 20:
            return
        self._last_width = width
        
        # Three-level responsive breakpoints
        sidebar_compact = width < 780
        self.sidebar.set_compact(sidebar_compact)

        # Determine mode from three breakpoints
        if width < 780:
            mode = "compact"
        elif width < 1200:
            mode = "normal"
        else:
            mode = "wide"
            
        if mode == self.responsive_mode and not force:
            return
        self.responsive_mode = mode

        # Ask views to adapt their internal grid properties
        for view in self.views.values():
            if hasattr(view, "apply_layout"):
                view.apply_layout(width)

    # Public helper overrides expected by tests and views
    def _write_todo_data(self) -> None:
        self.todo_manager.todo_data = self.todo_data
        self.todo_manager.write_todo_data()

    def _normalize_todo_data(self, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        return self.todo_manager.normalize_todo_data(data)

    def _day_record(self, key: str) -> dict[str, Any]:
        return self.todo_manager.day_record(key)

    def _record_has_content(self, record: dict[str, Any]) -> bool:
        return self.todo_manager.record_has_content(record)

    def _open_tasks_for_day(self, day: date) -> list[tuple[str, dict[str, Any]]]:
        self.todo_manager.todo_data = self.todo_data
        return self.todo_manager.open_tasks_for_day(day)

    def _iter_previous_open_tasks(self) -> list[tuple[str, dict[str, Any]]]:
        self.todo_manager.todo_data = self.todo_data
        return self.todo_manager.iter_previous_open_tasks(self.selected_todo_date)

    def _task_due_state(self, task: dict[str, Any]) -> str:
        return self.todo_manager.task_due_state(task)

    def _output_dir_path(self) -> Path:
        out = self.output_dir_var.get().strip() or "outputs"
        path = Path(out)
        return path if path.is_absolute() else ROOT / path

    def _latest_files(self, suffix: str, limit: int = 5) -> list[Path]:
        output_dir = self._output_dir_path()
        if not output_dir.exists():
            return []
        return sorted(output_dir.rglob(f"*{suffix}"), key=lambda p: p.stat().st_mtime, reverse=True)[:limit]

    def refresh_dashboard(self) -> None:
        today = date.today()
        open_tasks = self._open_tasks_for_day(today)
        overdue = [task for _, task in open_tasks if self._task_due_state(task).startswith("Overdue")]
        due_today = [task for _, task in open_tasks if self._task_due_state(task) == "Due today"]
        
        self.dashboard_summary_var.set(
            f"{len(open_tasks)} open task(s) today | {len(due_today)} due today | {len(overdue)} overdue"
        )

        latest_summaries = self._latest_files("_summary.json", limit=5)
        self.dashboard_latest_var.set(
            f"Latest meeting: {latest_summaries[0].name if latest_summaries else 'none yet'}"
        )

        # Update Dashboard Text Areas
        dashboard_view = self.views["dashboard"]
        
        dashboard_view.tasks_text.configure(state=tk.NORMAL)
        dashboard_view.tasks_text.delete("1.0", tk.END)
        if open_tasks:
            for day_key, task in open_tasks:
                priority = str(task.get("priority", "Normal"))
                due = self._task_due_state(task)
                prefix = f"[{priority}]"
                origin = "" if day_key == today.isoformat() else f" from {day_key}"
                suffix = f" | {due}" if due else ""
                dashboard_view.tasks_text.insert(tk.END, f"- {prefix} {task.get('text', '')}{origin}{suffix}\n")
        else:
            dashboard_view.tasks_text.insert(tk.END, "No open tasks. The runway is clear.\n")
        dashboard_view.tasks_text.configure(state=tk.DISABLED)

        dashboard_view.meetings_text.configure(state=tk.NORMAL)
        dashboard_view.meetings_text.delete("1.0", tk.END)
        if latest_summaries:
            for path in latest_summaries:
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                    title = data.get("meeting_title") or "Untitled"
                    started = data.get("meeting_started_at", "")
                    summary = str(data.get("meeting_summary", "")).strip()
                    dashboard_view.meetings_text.insert(tk.END, f"{title} | {started}\n{summary[:220]}\n\n")
                except Exception:
                    dashboard_view.meetings_text.insert(tk.END, f"{path.name}\nUnable to read summary.\n\n")
        else:
            dashboard_view.meetings_text.insert(tk.END, "No meeting summaries found yet.\n")
        dashboard_view.meetings_text.configure(state=tk.DISABLED)

    def check_ollama_status(self) -> None:
        self.ollama_status_var.set("Ollama: checking...")

        def worker() -> None:
            status = "Ollama: offline (fallback summaries active)"
            try:
                req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
                with urllib.request.urlopen(req, timeout=3) as response:
                    if response.status == 200:
                        status = "Ollama: online"
            except Exception:
                pass
            try:
                if self.root.winfo_exists():
                    self.root.after(0, self.ollama_status_var.set, status)
            except (RuntimeError, tk.TclError):
                # The app may be closing while the background status check returns.
                pass

        threading.Thread(target=worker, daemon=True).start()

    def add_quick_capture(self) -> None:
        text = self.quick_capture_var.get().strip()
        if not text:
            return
        today = date.today()
        if self.selected_todo_date != today:
            self._show_todo_date(today)
        stamp = datetime.now().strftime("%H:%M")
        
        todo_view = self.views["todo"]
        current = todo_view.todo_text.get("1.0", "end-1c").strip()
        addition = f"[{stamp}] {text}"
        todo_view.todo_text.delete("1.0", tk.END)
        todo_view.todo_text.insert("1.0", f"{current}\n{addition}".strip())
        self.quick_capture_var.set("")
        self._save_current_todo()
        self.refresh_dashboard()

    def _render_calendar_from_controls(self) -> None:
        try:
            month = MONTH_NAMES.index(self.todo_month_var.get()) + 1
            year = int(self.todo_year_var.get())
        except ValueError:
            return
        self._render_calendar(year, month)

    def _render_calendar(self, year: int, month: int) -> None:
        todo_view = self.views["todo"]
        for child in todo_view.calendar_grid.winfo_children():
            child.destroy()

        for col, name in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            ttk.Label(todo_view.calendar_grid, text=name, style="CardMuted.TLabel", anchor="center").grid(
                row=0, column=col, sticky="ew", padx=1, pady=(0, 4)
            )
            todo_view.calendar_grid.columnconfigure(col, weight=1)

        today = date.today()
        selected_key = self.selected_todo_date.isoformat()
        for row, week in enumerate(calendar.monthcalendar(year, month), start=1):
            for col, day_num in enumerate(week):
                if day_num == 0:
                    ttk.Label(todo_view.calendar_grid, text="", style="CardMuted.TLabel").grid(row=row, column=col, padx=1, pady=1)
                    continue
                day = date(year, month, day_num)
                key = day.isoformat()
                record = self.todo_data.get(key, {})
                has_content = self._record_has_content(record)
                label = f"{day_num}{'*' if has_content else ''}"
                is_selected = key == selected_key
                is_today = day == today
                
                bg = ACCENT_BLUE if is_selected else (ACCENT_GREEN if is_today else BG_OVERLAY)
                fg = BG_CRUST if (is_selected or is_today) else TEXT_MAIN
                
                btn = tk.Button(
                    todo_view.calendar_grid,
                    text=label,
                    font=(FONT_FAMILY, 9, "bold" if is_selected else "normal"),
                    bg=bg,
                    fg=fg,
                    activebackground=COLOR_ACTIVE_HOVER,
                    activeforeground=TEXT_MAIN,
                    relief=tk.FLAT,
                    bd=0,
                    cursor="hand2",
                    command=lambda d=day: self._show_todo_date(d),
                )
                btn.grid(row=row, column=col, sticky="ew", padx=1, pady=1, ipady=4)

    def _shift_todo_day(self, delta: int) -> None:
        self._show_todo_date(self.selected_todo_date + timedelta(days=delta))

    def _show_todo_date(self, day: date) -> None:
        self._save_current_todo()
        self.selected_todo_date = day
        self.todo_month_var.set(MONTH_NAMES[day.month - 1])
        self.todo_year_var.set(str(day.year))
        self.todo_date_label_var.set(day.strftime("%A, %B %d, %Y"))
        
        record = self.todo_data.get(day.isoformat(), {})
        text = str(record.get("text", ""))
        
        todo_view = self.views["todo"]
        todo_view.todo_text.delete("1.0", tk.END)
        todo_view.todo_text.insert("1.0", text)
        self.new_task_var.set("")
        self.todo_status_var.set("Saved")
        self._render_task_lists()
        self._render_calendar(day.year, day.month)

    def _render_task_lists(self) -> None:
        todo_view = self.views["todo"]
        for child in todo_view.task_list_frame.winfo_children():
            child.destroy()

        key = self.selected_todo_date.isoformat()
        tasks = self.todo_data.get(key, {}).get("tasks", [])
        previous_tasks = self._iter_previous_open_tasks()

        today = date.today()
        if self.selected_todo_date == today:
            tasks_header = "Today's Tasks"
        elif self.selected_todo_date < today:
            tasks_header = f"Tasks for {self.selected_todo_date.strftime('%b %d')} (Past)"
        else:
            tasks_header = f"Tasks for {self.selected_todo_date.strftime('%b %d')}"

        self._render_task_section(tasks_header, [(key, task) for task in tasks])
        self._render_task_section("Carried Previous Tasks", previous_tasks)

        if not tasks and not previous_tasks:
            ttk.Label(
                todo_view.task_list_frame,
                text="No tasks yet. Add one above, then check it when it is done.",
                style="CardMuted.TLabel",
            ).pack(anchor="w", pady=(0, 6))

    def _render_task_section(self, title: str, tasks: list[tuple[str, dict[str, Any]]]) -> None:
        if not tasks:
            return
        todo_view = self.views["todo"]
        ttk.Label(todo_view.task_list_frame, text=title.upper(), style="CardMuted.TLabel").pack(anchor="w", pady=(4, 4))
        for day_key, task in tasks:
            row = ttk.Frame(todo_view.task_list_frame, style="Card.TFrame")
            row.pack(fill=tk.X, pady=2)
            var = tk.BooleanVar(value=bool(task.get("done", False)))
            cb = tk.Checkbutton(
                row,
                variable=var,
                bg=BG_SURFACE,
                activebackground=BG_SURFACE,
                selectcolor=BG_CRUST,
                command=lambda d=day_key, t=task, v=var: self._toggle_task_done(d, t, v.get()),
            )
            cb.pack(side=tk.LEFT, padx=(0, 6))
            task_text = str(task.get("text", "")).strip()
            meta = [str(task.get("priority", "Normal"))]
            due_state = self._task_due_state(task)
            if due_state:
                meta.append(due_state)
            if "Previous" in title:
                origin = datetime.strptime(day_key, "%Y-%m-%d").strftime("%b %d")
                meta.append(f"from {origin}")
            task_text = f"{task_text}  ({' | '.join(meta)})"
            fg = TEXT_MUTED if task.get("done") else TEXT_MAIN
            # Dynamic wraplength based on current content width
            content_w = max(300, self.root.winfo_width() - 400)
            tk.Label(
                row,
                text=task_text,
                bg=BG_SURFACE,
                fg=fg,
                anchor="w",
                justify=tk.LEFT,
                wraplength=content_w,
                font=(FONT_FAMILY, font_size(10), "overstrike" if task.get("done") else "normal"),
            ).pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _add_todo_task(self) -> None:
        text = self.new_task_var.get().strip()
        if not text:
            return
        key = self.selected_todo_date.isoformat()
        record = self._day_record(key)
        record["tasks"].append(
            {
                "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                "text": text,
                "done": False,
                "priority": self.new_task_priority_var.get() or "Normal",
                "due": self.new_task_due_var.get().strip(),
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )
        record["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self.new_task_var.set("")
        self.new_task_due_var.set("")
        self._write_todo_data()
        self.todo_status_var.set("Saved")
        self._render_task_lists()
        self._render_calendar(self.selected_todo_date.year, self.selected_todo_date.month)
        self.refresh_dashboard()

    def _toggle_task_done(self, day_key: str, task: dict[str, Any], done: bool) -> None:
        task["done"] = done
        if done:
            task["completed_at"] = datetime.now().isoformat(timespec="seconds")
        else:
            task.pop("completed_at", None)
        record = self._day_record(day_key)
        record["updated_at"] = datetime.now().isoformat(timespec="seconds")
        self._write_todo_data()
        self.todo_status_var.set("Saved")
        self._render_task_lists()
        self._render_calendar(self.selected_todo_date.year, self.selected_todo_date.month)
        self.refresh_dashboard()

    def import_latest_meeting_actions(self) -> None:
        summaries = self._latest_files("_summary.json", limit=1)
        if not summaries:
            messagebox.showinfo("No Meeting Summary", "No meeting summary files were found in the output folder.")
            return
        try:
            data = json.loads(summaries[0].read_text(encoding="utf-8"))
        except Exception as exc:
            messagebox.showerror("Import Error", f"Could not read {summaries[0].name}:\n{exc}")
            return

        candidates: list[str] = []
        for item in data.get("structured_action_items", []):
            if isinstance(item, dict):
                task = str(item.get("task") or item.get("source_text") or "").strip()
                owner = str(item.get("owner") or "").strip()
                due = str(item.get("due") or "").strip()
                if owner:
                    task = f"{task} | Owner: {owner}"
                if due:
                    task = f"{task} | Due: {due}"
                if task:
                    candidates.append(task)
        for item in data.get("action_items", []):
            text = str(item).strip()
            if text:
                candidates.append(text)

        key = date.today().isoformat()
        record = self._day_record(key)
        existing = {str(task.get("text", "")).strip().lower() for task in record.get("tasks", [])}
        added = 0
        for text in candidates:
            if text.lower() in existing:
                continue
            record["tasks"].append(
                {
                    "id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
                    "text": text,
                    "done": False,
                    "priority": "Normal",
                    "due": "",
                    "source": summaries[0].name,
                    "created_at": datetime.now().isoformat(timespec="seconds"),
                }
            )
            existing.add(text.lower())
            added += 1

        if added:
            record["updated_at"] = datetime.now().isoformat(timespec="seconds")
            self._write_todo_data()
            self._show_todo_date(date.today())
            self.refresh_dashboard()
        messagebox.showinfo("Meeting Actions Imported", f"Imported {added} task(s) from {summaries[0].name}.")

    def _todo_markdown(self, scope: str) -> str:
        keys = [self.selected_todo_date.isoformat()] if scope == "today" else sorted(self.todo_data)
        lines = ["# Daily Todo Export", ""]
        for key in keys:
            record = self.todo_data.get(key, {})
            if not self._record_has_content(record):
                continue
            lines.extend([f"## {key}", ""])
            tasks = record.get("tasks", [])
            if tasks:
                lines.append("### Tasks")
                for task in tasks:
                    done = "x" if task.get("done") else " "
                    priority = task.get("priority", "Normal")
                    due = f" | Due: {task.get('due')}" if task.get("due") else ""
                    lines.append(f"- [{done}] {task.get('text', '')} ({priority}{due})")
                lines.append("")
            text = str(record.get("text", "")).strip()
            if text:
                lines.extend(["### Notes", text, ""])
        return "\n".join(lines).strip() + "\n"

    def export_todos(self, scope: str, fmt: str) -> None:
        app_dir = self.todo_manager.get_app_dir()
        app_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = app_dir / f"todo_export_{scope}_{stamp}"
        markdown = self._todo_markdown(scope)
        if fmt == "md":
            path = base.with_suffix(".md")
            path.write_text(markdown, encoding="utf-8")
        else:
            path = base.with_suffix(".html")
            body = (
                markdown.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace("\n", "<br>\n")
            )
            path.write_text(
                "<!doctype html><html><head><meta charset='utf-8'><title>Todo Export</title>"
                "<style>body{font-family:Segoe UI,sans-serif;max-width:850px;margin:32px auto;line-height:1.55}"
                "body{background:#f7f8fb;color:#1e2430}</style></head><body>"
                f"{body}</body></html>",
                encoding="utf-8",
            )
        try:
            os.startfile(str(path))
        except Exception:
            pass
        messagebox.showinfo("Export Complete", f"Saved export:\n{path}")

    def run_search(self) -> None:
        query = self.search_var.get().strip().lower()
        search_view = self.views["search"]
        search_view.search_result.configure(state=tk.NORMAL)
        search_view.search_result.delete("1.0", tk.END)
        if not query:
            search_view.search_result.insert(tk.END, "Type something to search.\n")
            search_view.search_result.configure(state=tk.DISABLED)
            return

        hits = 0
        search_view.search_result.insert(tk.END, "TODOS\n", "section")
        for day_key, record in sorted(self.todo_data.items(), reverse=True):
            text = str(record.get("text", ""))
            if query in text.lower():
                tag_name = f"todo_note_{day_key}"
                search_view.search_result.tag_configure(tag_name, foreground=ACCENT_BLUE, underline=True)
                search_view.search_result.insert(tk.END, f"  📅 {day_key}", tag_name)
                search_view.search_result.tag_bind(tag_name, "<Button-1>", lambda e, dk=day_key: self._navigate_search_to_todo(dk))
                search_view.search_result.insert(tk.END, f": note match\n{text[:260]}\n\n")
                hits += 1
            for task in record.get("tasks", []):
                task_text = str(task.get("text", ""))
                if query in task_text.lower():
                    done = "done" if task.get("done") else "open"
                    tag_name = f"todo_task_{day_key}_{hits}"
                    search_view.search_result.tag_configure(tag_name, foreground=ACCENT_BLUE, underline=True)
                    search_view.search_result.insert(tk.END, f"  📅 {day_key}", tag_name)
                    search_view.search_result.tag_bind(tag_name, "<Button-1>", lambda e, dk=day_key: self._navigate_search_to_todo(dk))
                    search_view.search_result.insert(tk.END, f": [{done}] {task_text}\n")
                    hits += 1

        search_view.search_result.insert(tk.END, "\nMEETINGS\n", "section")
        for suffix in ("_summary.json", "_transcript.txt", "_notes.md"):
            for path in self._latest_files(suffix, limit=40):
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if query in content.lower():
                    idx = content.lower().find(query)
                    snippet = content[max(0, idx - 120) : idx + 240].replace("\n", " ")
                    search_view.search_result.insert(tk.END, f"  📄 {path.name}\n  {snippet}\n\n")
                    hits += 1
        if hits == 0:
            search_view.search_result.insert(tk.END, "No matches found.\n")
        search_view.search_result.configure(state=tk.DISABLED)

    def _navigate_search_to_todo(self, day_key: str) -> None:
        """Navigate from search result to the Todo view for the given date."""
        try:
            target_date = date.fromisoformat(day_key)
            self._show_todo_date(target_date)
            self.switch_view("todo")
        except ValueError:
            pass

    def load_latest_transcript_for_correction(self) -> None:
        files = self._latest_files("_transcript.txt", limit=1)
        if not files:
            messagebox.showinfo("No Transcript", "No transcript files were found in the output folder.")
            return
        path = files[0]
        try:
            text = path.read_text(encoding="utf-8")
        except Exception as exc:
            messagebox.showerror("Transcript Error", f"Could not read transcript:\n{exc}")
            return
        self.corrected_transcript_path = path
        
        settings_view = self.views["settings"]
        settings_view.transcript_editor.delete("1.0", tk.END)
        settings_view.transcript_editor.insert("1.0", text)
        self.transcript_status_var.set(f"Loaded: {path.name}")

    def save_corrected_transcript(self) -> None:
        if not self.corrected_transcript_path:
            messagebox.showinfo("No Transcript", "Load a transcript first.")
            return
        corrected = self.corrected_transcript_path.with_name(
            self.corrected_transcript_path.name.replace("_transcript.txt", "_corrected_transcript.txt")
        )
        settings_view = self.views["settings"]
        corrected.write_text(settings_view.transcript_editor.get("1.0", "end-1c"), encoding="utf-8")
        self.transcript_status_var.set(f"Saved: {corrected.name}")
        try:
            os.startfile(str(corrected))
        except Exception:
            pass

    def _schedule_todo_save(self, _event: tk.Event | None = None) -> None:
        self.todo_status_var.set("Saving...")
        if self.todo_save_after:
            self.root.after_cancel(self.todo_save_after)
        self.todo_save_after = self.root.after(450, self._save_current_todo)

    def _save_current_todo(self) -> None:
        if self.todo_save_after:
            self.root.after_cancel(self.todo_save_after)
            self.todo_save_after = None
        key = self.selected_todo_date.isoformat()
        
        todo_view = self.views["todo"]
        text = todo_view.todo_text.get("1.0", "end-1c")
        record = self._day_record(key)
        record["text"] = text
        if self._record_has_content(record):
            record["updated_at"] = datetime.now().isoformat(timespec="seconds")
        else:
            self.todo_data.pop(key, None)
        self._write_todo_data()
        self.todo_status_var.set("Saved")
        
        self._render_task_lists()
        self._render_calendar(self.selected_todo_date.year, self.selected_todo_date.month)
        self.refresh_dashboard()

    def startup_enabled(self) -> bool:
        startup_file = (
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
            / "Meeting Notes AI.cmd"
        )
        return startup_file.exists()

    def refresh_startup_status(self) -> None:
        if self.startup_enabled():
            self.startup_status_var.set("Startup: enabled")
        else:
            self.startup_status_var.set("Startup: disabled")

    def enable_startup(self) -> None:
        startup_file = (
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
            / "Meeting Notes AI.cmd"
        )
        try:
            startup_file.parent.mkdir(parents=True, exist_ok=True)
            startup_file.write_text(
                f'@echo off\ncd /d "{ROOT}"\ncall "{ROOT / "Launch.bat"}"\n',
                encoding="utf-8",
            )
            self.refresh_startup_status()
            messagebox.showinfo("Startup Enabled", "Meeting Notes AI will open when you sign in to Windows.")
        except Exception as exc:
            messagebox.showerror("Startup Error", f"Could not enable startup:\n{exc}")

    def disable_startup(self) -> None:
        startup_file = (
            Path(os.environ.get("APPDATA", ""))
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
            / "Meeting Notes AI.cmd"
        )
        try:
            startup_file.unlink(missing_ok=True)
            self.refresh_startup_status()
            messagebox.showinfo("Startup Disabled", "Meeting Notes AI will no longer open automatically.")
        except Exception as exc:
            messagebox.showerror("Startup Error", f"Could not disable startup:\n{exc}")

    def _tray_available(self) -> bool:
        try:
            import pystray
            from PIL import Image, ImageDraw
            return True
        except Exception:
            return False

    def _make_tray_image(self):
        from PIL import Image, ImageDraw
        image = Image.new("RGB", (64, 64), BG_SURFACE)
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((10, 10, 54, 54), radius=10, fill=ACCENT_BLUE)
        draw.rectangle((20, 24, 44, 29), fill=BG_SURFACE)
        draw.rectangle((20, 35, 40, 40), fill=BG_SURFACE)
        return image

    def minimize_to_tray(self) -> None:
        if not self._tray_available():
            messagebox.showinfo("Tray Unavailable", "Tray support dependencies are not installed. Minimizing normally.")
            self.root.iconify()
            return

        import pystray
        self.root.withdraw()
        if self.tray_icon:
            return

        menu = pystray.Menu(
            pystray.MenuItem("Show Meeting Notes AI", lambda _icon, _item: self.root.after(0, self.restore_from_tray)),
            pystray.MenuItem("Quit", lambda _icon, _item: self.root.after(0, self.quit_from_tray)),
        )
        self.tray_icon = pystray.Icon("Meeting Notes AI", self._make_tray_image(), "Meeting Notes AI", menu)
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def restore_from_tray(self) -> None:
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_from_tray(self) -> None:
        if self.tray_icon:
            self.tray_icon.stop()
            self.tray_icon = None
        self.minimize_on_close_var.set(False)
        self._on_close()

    def python_executable(self) -> str:
        venv_python = ROOT / ".venv" / "Scripts" / "python.exe"
        if venv_python.exists():
            return str(venv_python)
        return sys.executable

    def refresh_devices(self) -> None:
        try:
            discovered = list_input_devices()
            names = ["(Auto)"]
            names.extend(device.name for device in discovered)
            self.devices = names
            self.views["settings"].device_combo["values"] = names
            if not self.device_var.get() or self.device_var.get() not in names:
                self.device_var.set("(Auto)")
        except Exception as exc:
            messagebox.showerror("Device Error", f"Failed to list devices:\n{exc}")

    def build_command(self) -> list[str]:
        cmd = [self.python_executable(), "-u", "run.py"]

        title = self.title_var.get().strip()
        if title:
            cmd.extend(["--meeting-title", title])

        profile = self.profile_var.get().strip()
        if profile:
            cmd.extend(["--profile", profile])

        model = self.model_var.get().strip()
        if model:
            cmd.extend(["--whisper-model", model])
        inference_device = self.inference_device_var.get().strip()
        if inference_device:
            cmd.extend(["--inference-device", inference_device])

        language = self.language_var.get().strip()
        if language and language != "en":
            cmd.extend(["--language", language])

        if self.source_var.get() == "loopback":
            cmd.append("--loopback")

        device = self.device_var.get().strip()
        if device and device != "(Auto)":
            cmd.extend(["--device", device])

        if self.ollama_var.get():
            cmd.append("--use-ollama")
            ollama_model = self.ollama_model_var.get().strip()
            if ollama_model:
                cmd.extend(["--ollama-model", ollama_model])
        else:
            cmd.append("--no-ollama")

        max_minutes = self.max_minutes_var.get().strip()
        if max_minutes:
            try:
                max_int = int(max_minutes)
                if max_int < 0:
                    raise ValueError
                cmd.extend(["--max-minutes", str(max_int)])
            except ValueError:
                raise ValueError("Max Minutes must be a whole number >= 0.")

        if self.save_pref_var.get():
            cmd.append("--save-preferences")

        output_dir = self.output_dir_var.get().strip()
        if output_dir:
            cmd.extend(["--output-dir", output_dir])

        if self.simulate_var.get():
            cmd.append("--simulate")
            duration = self.sim_duration_var.get().strip() or "90"
            try:
                duration_int = int(duration)
                if duration_int <= 0:
                    raise ValueError
            except ValueError:
                raise ValueError("Simulation duration must be a whole number > 0.")
            cmd.extend(["--simulate-duration", str(duration_int)])
            cmd.extend(["--simulate-step-ms", "80"])

        cmd.extend(["--stop-file", str(self.stop_flag_path)])
        return cmd

    def _set_notes_message(self, text: str, tag: str = "muted") -> None:
        record_view = self.views["record"]
        record_view.notes_log.configure(state=tk.NORMAL)
        record_view.notes_log.delete("1.0", tk.END)
        record_view.notes_log.insert(tk.END, text, tag)
        record_view.notes_log.configure(state=tk.DISABLED)

    def start(self) -> None:
        if self.process and self.process.poll() is None:
            return

        try:
            cmd = self.build_command()
        except ValueError as exc:
            messagebox.showerror("Invalid Input", str(exc))
            return

        self.last_run_had_diagnostic = False
        self.last_run_error = ""
        
        settings_view = self.views["settings"]
        settings_view.log_text.insert(tk.END, f"\n$ {' '.join(cmd)}\n\n")
        settings_view.log_text.see(tk.END)

        # Clear transcript tab and set placeholder
        record_view = self.views["record"]
        record_view.transcript_log.configure(state=tk.NORMAL)
        record_view.transcript_log.delete("1.0", tk.END)
        record_view.transcript_log.insert(tk.END, "Initializing transcription model...\n")
        record_view.transcript_log.configure(state=tk.DISABLED)

        self._set_notes_message("Waiting for notes update...\n")

        if self.stop_flag_path.exists():
            try:
                self.stop_flag_path.unlink()
            except Exception:
                pass

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
        except Exception as exc:
            messagebox.showerror("Launch Error", f"Could not start process:\n{exc}")
            return

        title = self.title_var.get().strip() or f"Session {datetime.now().strftime('%H:%M')}"
        record_view.session_title_lbl.configure(text=f"Active: {title}", font=(FONT_FAMILY, font_size(9), "normal"))

        # Switch to record view automatically so user can watch progress
        self.switch_view("record")

        self.status_var.set("Recording")
        self.sidebar.status_indicator.configure(bg=ACCENT_GREEN, fg=BG_CRUST)
        self.sidebar.start_pulse()
        record_view.start_btn.configure(state=tk.DISABLED)
        record_view.start_btn.set_bg(BG_OVERLAY)
        record_view.start_btn.configure(fg=TEXT_MUTED)
        record_view.stop_btn.configure(state=tk.NORMAL)
        record_view.stop_btn.set_bg(ACCENT_RED, "#ff9bb5")
        record_view.stop_btn.configure(fg=BG_CRUST)
        
        # Start session timer
        self._session_start_time = monotonic()
        self._update_session_timer()
        
        threading.Thread(target=self._read_output, daemon=True).start()

    def _read_output(self) -> None:
        if not self.process or not self.process.stdout:
            return
        try:
            for line in self.process.stdout:
                self.log_queue.put(line)
        finally:
            code = self.process.wait() if self.process else 0
            if self.stop_flag_path.exists():
                try:
                    self.stop_flag_path.unlink()
                except Exception:
                    pass
            self.log_queue.put(f"\n[process exited with code {code}]\n")
            self.root.after(0, self._mark_stopped, code)

    @staticmethod
    def format_hhmmss(seconds: float) -> str:
        """Format elapsed seconds as HH:MM:SS."""
        s = int(seconds)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        if h > 0:
            return f"{h:d}:{m:02d}:{sec:02d}"
        return f"{m:d}:{sec:02d}"

    def _update_session_timer(self) -> None:
        """Tick the elapsed timer every second during active recording."""
        if self._session_start_time is None:
            return
        elapsed = monotonic() - self._session_start_time
        elapsed_str = self.format_hhmmss(elapsed)
        record_view = self.views["record"]
        record_view.elapsed_lbl.configure(text=f"\u23f1 {elapsed_str}")
        self._timer_job = self.root.after(1000, self._update_session_timer)

    def _stop_session_timer(self) -> None:
        """Stop the session timer."""
        self._session_start_time = None
        if self._timer_job:
            self.root.after_cancel(self._timer_job)
            self._timer_job = None
        record_view = self.views["record"]
        record_view.elapsed_lbl.configure(text="")

    def _mark_stopped(self, exit_code: int | None = 0) -> None:
        record_view = self.views["record"]
        self.sidebar.stop_pulse()
        self._stop_session_timer()
        
        if self.last_run_had_diagnostic:
            self.status_var.set("Check audio")
            self.sidebar.status_indicator.configure(bg=ACCENT_YELLOW, fg=BG_CRUST)
        elif exit_code not in (None, 0):
            self.status_var.set("Error")
            self.sidebar.status_indicator.configure(bg=ACCENT_RED, fg=BG_CRUST)
            if self.last_run_error:
                self._set_notes_message(self.last_run_error.strip() + "\n")
        else:
            self.status_var.set("Idle")
            self.sidebar.status_indicator.configure(bg=BG_OVERLAY, fg=TEXT_MAIN)
            
        record_view.start_btn.configure(state=tk.NORMAL)
        record_view.start_btn.set_bg(ACCENT_GREEN, "#bceeb7")
        record_view.start_btn.configure(fg=BG_CRUST)
        record_view.stop_btn.configure(state=tk.DISABLED)
        record_view.stop_btn.set_bg(BG_OVERLAY)
        record_view.stop_btn.configure(fg=TEXT_MUTED)
        record_view.session_title_lbl.configure(text="No active session", font=(FONT_FAMILY, font_size(9), "italic"))
        self.title_var.set("")
        
        # Reset visual metrics
        self.sidebar.audio_meter.set_level(-120.0)
        self.dbfs_label_var.set("-120.0 dBFS")
        self.transcribe_time_var.set("0.00s")
        self.rtf_var.set("0.00")
        self.chunks_var.set("0")
        self.refresh_dashboard()

    def stop(self) -> None:
        if not self.process or self.process.poll() is not None:
            self._mark_stopped(0)
            return

        self.status_var.set("Stopping")
        self.sidebar.status_indicator.configure(bg=ACCENT_YELLOW, fg=BG_CRUST)
        try:
            self.stop_flag_path.write_text("stop", encoding="utf-8")
        except Exception:
            pass

        def force_kill() -> None:
            if self.process and self.process.poll() is None:
                try:
                    self.process.terminate()
                except Exception:
                    pass

        self.root.after(8000, force_kill)

    def open_outputs(self) -> None:
        out = self.output_dir_var.get().strip() or "outputs"
        output_dir = Path(out)
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(output_dir))

    def open_config_folder(self) -> None:
        config_dir = Path.home() / ".meeting-notes-ai"
        config_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(config_dir))

    def export_last_html(self) -> None:
        """Find the latest summary JSON in the output folder and open its HTML report."""
        import webbrowser
        from meeting_notes_ai.notes import export_html

        out = self.output_dir_var.get().strip() or "outputs"
        output_dir = Path(out)
        if not output_dir.is_absolute():
            output_dir = ROOT / output_dir

        json_files = sorted(output_dir.glob("*_summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not json_files:
            messagebox.showinfo("No Meeting Data", "No meeting summary files found in the output folder.")
            return

        latest_json = json_files[0]
        try:
            with open(latest_json, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            messagebox.showerror("Read Error", f"Could not read {latest_json.name}:\n{exc}")
            return

        html_path = latest_json.with_name(latest_json.name.replace("_summary.json", "_notes.html"))
        transcript_path = latest_json.with_name(latest_json.name.replace("_summary.json", "_transcript.txt"))
        
        transcript_lines: list[str] = []
        if transcript_path.exists():
            try:
                transcript_lines = transcript_path.read_text(encoding="utf-8").splitlines()
            except Exception:
                pass

        stats = data.get("stats", {})
        duration_s = float(stats.get("duration_seconds", 0))
        duration_str = self.format_hhmmss(duration_s)

        html_content = export_html(
            meeting_title=data.get("meeting_title", "Untitled"),
            meeting_date=data.get("meeting_started_at", ""),
            duration=duration_str,
            segments_captured=int(stats.get("segments_captured", 0)),
            avg_latency=float(stats.get("avg_transcribe_seconds", 0.0)),
            summary=data,
            transcript_lines=transcript_lines,
        )
        html_path.write_text(html_content, encoding="utf-8")
        webbrowser.open(str(html_path))
        self.log_queue.put(f"[export] HTML report opened: {html_path}\n")

    def format_hhmmss(self, seconds: float) -> str:
        whole = int(max(seconds, 0.0))
        h = whole // 3600
        m = (whole % 3600) // 60
        s = whole % 60
        return f"{h:02}:{m:02}:{s:02}"

    def _load_autosave_json(self, path_str: str) -> None:
        try:
            path = Path(path_str)
            if not path.is_absolute():
                path = ROOT / path
            if not path.exists():
                return

            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Sync Live Notes view
            record_view = self.views["record"]
            record_view.notes_log.configure(state=tk.NORMAL)
            record_view.notes_log.delete("1.0", tk.END)

            live_notes = data.get("live_notes", {})
            has_notes = False

            kp = live_notes.get("key_points", [])
            if kp:
                has_notes = True
                record_view.notes_log.insert(tk.END, "KEY POINTS\n", "header")
                for item in kp:
                    record_view.notes_log.insert(tk.END, f"- {item}\n", "bullet")
                record_view.notes_log.insert(tk.END, "\n")

            dec = live_notes.get("decisions", [])
            if dec:
                has_notes = True
                record_view.notes_log.insert(tk.END, "DECISIONS\n", "header")
                for item in dec:
                    record_view.notes_log.insert(tk.END, f"- {item}\n", "bullet")
                record_view.notes_log.insert(tk.END, "\n")

            ai = live_notes.get("action_items", [])
            if ai:
                has_notes = True
                record_view.notes_log.insert(tk.END, "ACTION ITEMS\n", "header")
                for item in ai:
                    record_view.notes_log.insert(tk.END, f"- {item}\n", "bullet")
                record_view.notes_log.insert(tk.END, "\n")

            sai = live_notes.get("structured_action_items", [])
            if sai:
                has_notes = True
                record_view.notes_log.insert(tk.END, "STRUCTURED ACTION ITEMS\n", "header")
                for item in sai:
                    task = item.get("task", "")
                    owner = item.get("owner") or "Unassigned"
                    due = item.get("due") or "No due date"
                    record_view.notes_log.insert(tk.END, f"- {task}\n  Owner: {owner} | Due: {due}\n", "bullet")
                record_view.notes_log.insert(tk.END, "\n")

            if not has_notes:
                record_view.notes_log.insert(tk.END, "No highlights or action items detected yet. The system updates this section automatically as the meeting progresses.", "muted")

            record_view.notes_log.configure(state=tk.DISABLED)

            # Sync Live Transcript tab history
            segments = data.get("segments", [])
            if segments:
                record_view.transcript_log.configure(state=tk.NORMAL)
                record_view.transcript_log.delete("1.0", tk.END)
                for seg in segments:
                    start_str = self.format_hhmmss(seg.get("start", 0.0))
                    end_str = self.format_hhmmss(seg.get("end", 0.0))
                    text = seg.get("text", "")
                    record_view.transcript_log.insert(tk.END, f"[{start_str} - {end_str}] {text}\n")
                record_view.transcript_log.see(tk.END)
                record_view.transcript_log.configure(state=tk.DISABLED)

        except Exception as exc:
            # Silently catch brief load conflict glitches
            print(f"Error loading autosave: {exc}")

    def _drain_logs(self) -> None:
        drained = False
        settings_view = self.views["settings"]
        record_view = self.views["record"]
        
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            drained = True
            
            # Write to raw System Log
            settings_view.log_text.insert(tk.END, line)
            
            if "No transcript captured. Saved diagnostic notes" in line:
                self.last_run_had_diagnostic = True
                self._set_notes_message(
                    "No speech was transcribed, but diagnostic notes were saved.\n\n"
                    "Check that the selected device is the one actually playing meeting audio. "
                    "For online meetings, use a loopback device that matches your active speakers or headphones.\n"
                )
                continue
                
            if "[error]" in line or "Transcription runtime error:" in line or "Transcriber initialization failed:" in line:
                self.last_run_error = line
            
            # Parse status metrics
            status_match = self.status_pattern.search(line)
            if status_match:
                level = float(status_match.group("level"))
                transcribe = float(status_match.group("transcribe"))
                rtf = float(status_match.group("rtf"))
                chunks = int(status_match.group("chunks"))

                self.sidebar.audio_meter.set_level(level)
                self.dbfs_label_var.set(f"{level:.1f} dB")
                self.transcribe_time_var.set(f"{transcribe:.2f}s")
                self.rtf_var.set(f"{rtf:.2f}")
                self.chunks_var.set(str(chunks))
                continue
                
            # Parse realtime segment printing
            segment_match = self.segment_pattern.search(line)
            if segment_match:
                record_view.transcript_log.configure(state=tk.NORMAL)
                # Clear placeholder on first transcription segment
                if "Waiting for transcription" in record_view.transcript_log.get("1.0", "2.0"):
                    record_view.transcript_log.delete("1.0", tk.END)
                record_view.transcript_log.insert(tk.END, line)
                record_view.transcript_log.see(tk.END)
                record_view.transcript_log.configure(state=tk.DISABLED)
                continue

            # Parse autosave triggers
            if "[autosave]" in line:
                parts = line.split("[autosave]")
                if len(parts) > 1:
                    autosave_path_str = parts[1].strip()
                    self.root.after(150, lambda p=autosave_path_str: self._load_autosave_json(p))

        if drained:
            settings_view.log_text.see(tk.END)
        self.root.after(120, self._drain_logs)

    def _on_close(self) -> None:
        self._save_current_todo()
        if self.minimize_on_close_var.get():
            self.root.iconify()
            return
        if self.process and self.process.poll() is None:
            if not messagebox.askyesno("Exit", "A recording is running. Stop and exit?"):
                return
            self.stop()
        self.root.after(200, self.root.destroy)

    def _report_callback_exception(self, exc: type[BaseException], value: BaseException, tb) -> None:
        details = "".join(traceback.format_exception(exc, value, tb))
        self.log_queue.put("\n[ui-error]\n")
        self.log_queue.put(details + "\n")
        self.status_var.set("UI error")
        try:
            messagebox.showerror("UI Error", f"An internal UI error occurred.\n\n{value}")
        except Exception:
            pass


def main() -> int:
    # Enable DPI awareness before creating Tk root
    enable_dpi_awareness()
    
    root = tk.Tk()
    app = MeetingNotesUI(root)
    _ = app
    try:
        root.mainloop()
    except KeyboardInterrupt:
        pass
    return 0
