"""Daily Todo and Action Items data manager with cryptography support."""
from __future__ import annotations

import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from meeting_notes_ai.config import APP_DIR

TODO_PATH = APP_DIR / "daily_todos.json"
TODO_ENC_PATH = APP_DIR / "daily_todos.enc"

class TodoManager:
    def __init__(self) -> None:
        self.todo_data: dict[str, dict[str, Any]] = {}
        self.todo_encryption_passphrase: str | None = None

    def get_todo_path(self) -> Path:
        try:
            import ui
            return getattr(ui, "TODO_PATH", TODO_PATH)
        except ImportError:
            return TODO_PATH

    def get_todo_enc_path(self) -> Path:
        try:
            import ui
            return getattr(ui, "TODO_ENC_PATH", TODO_ENC_PATH)
        except ImportError:
            return TODO_ENC_PATH

    def get_app_dir(self) -> Path:
        try:
            import ui
            return getattr(ui, "APP_DIR", APP_DIR)
        except ImportError:
            return APP_DIR

    def load_todo_data(self) -> dict[str, dict[str, Any]]:
        """Loads daily todos."""
        todo_p = self.get_todo_path()
        if not todo_p.exists():
            self.todo_data = {}
            return {}
        try:
            data = json.loads(todo_p.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                self.todo_data = self.normalize_todo_data(data)
                return self.todo_data
        except Exception:
            pass
        self.todo_data = {}
        return {}

    def normalize_todo_data(self, data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        normalized: dict[str, dict[str, Any]] = {}
        for day, value in data.items():
            if not isinstance(value, dict):
                continue
            record = dict(value)
            record.setdefault("text", "")
            tasks = record.get("tasks", [])
            if not isinstance(tasks, list):
                tasks = []
            record["tasks"] = [
                task
                for task in tasks
                if isinstance(task, dict) and str(task.get("text", "")).strip()
            ]
            normalized[str(day)] = record
        return normalized

    def write_todo_data(self) -> None:
        todo_p = self.get_todo_path()
        self.get_app_dir().mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.todo_data, indent=2, ensure_ascii=False)
        todo_p.write_text(payload, encoding="utf-8")

    def day_record(self, key: str) -> dict[str, Any]:
        record = self.todo_data.setdefault(key, {"text": "", "tasks": []})
        record.setdefault("text", "")
        record.setdefault("tasks", [])
        return record

    def record_has_content(self, record: dict[str, Any]) -> bool:
        return bool(str(record.get("text", "")).strip() or record.get("tasks"))

    def open_tasks_for_day(self, day: date) -> list[tuple[str, dict[str, Any]]]:
        key = day.isoformat()
        todays = [(key, task) for task in self.todo_data.get(key, {}).get("tasks", []) if not task.get("done")]
        return self.iter_previous_open_tasks(day) + todays

    def iter_previous_open_tasks(self, for_day: date) -> list[tuple[str, dict[str, Any]]]:
        selected_key = for_day.isoformat()
        carried: list[tuple[str, dict[str, Any]]] = []
        for day_key in sorted(self.todo_data):
            if day_key >= selected_key:
                continue
            for task in self.todo_data.get(day_key, {}).get("tasks", []):
                if not bool(task.get("done", False)):
                    carried.append((day_key, task))
        return carried

    def task_due_state(self, task: dict[str, Any]) -> str:
        due_raw = str(task.get("due", "")).strip()
        if not due_raw:
            return ""
        try:
            due_date = date.fromisoformat(due_raw)
        except ValueError:
            return f"Due {due_raw}"
        today = date.today()
        if due_date < today and not task.get("done"):
            return f"Overdue {due_raw}"
        if due_date == today and not task.get("done"):
            return "Due today"
        return f"Due {due_raw}"
