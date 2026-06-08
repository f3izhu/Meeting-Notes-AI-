from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def run_cmd(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=timeout,
        check=False,
    )


def latest(directory: Path, suffix: str) -> Path:
    files = sorted(directory.glob(f"*{suffix}"), key=lambda p: p.stat().st_mtime)
    assert files, f"missing {suffix} in {directory}"
    return files[-1]


def make_tk_root():
    import tkinter as tk

    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk runtime unavailable: {exc}")
    root.withdraw()
    return root


def test_simulated_pipeline_writes_all_outputs(tmp_path: Path) -> None:
    result = run_cmd(
        [
            str(PYTHON),
            "run.py",
            "--simulate",
            "--simulate-duration",
            "30",
            "--meeting-title",
            "Pytest Smoke",
            "--output-dir",
            str(tmp_path),
            "--no-ollama",
        ]
    )
    assert result.returncode == 0, result.stdout

    transcript = latest(tmp_path, "_transcript.txt")
    summary_json = latest(tmp_path, "_summary.json")
    notes_md = latest(tmp_path, "_notes.md")
    notes_html = latest(tmp_path, "_notes.html")

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    assert transcript.read_text(encoding="utf-8").strip()
    assert "## Summary" in notes_md.read_text(encoding="utf-8")
    assert notes_html.stat().st_size > 0
    assert summary["stats"]["segments_captured"] > 0
    assert isinstance(summary["structured_action_items"], list)


def test_stop_file_finalizes_partial_simulated_session(tmp_path: Path) -> None:
    stop_file = tmp_path / "stop.flag"
    process = subprocess.Popen(
        [
            str(PYTHON),
            "-u",
            "run.py",
            "--simulate",
            "--simulate-duration",
            "120",
            "--simulate-step-ms",
            "120",
            "--meeting-title",
            "Stop Smoke",
            "--output-dir",
            str(tmp_path),
            "--no-ollama",
            "--stop-file",
            str(stop_file),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    time.sleep(0.4)
    stop_file.write_text("stop", encoding="utf-8")
    output, _ = process.communicate(timeout=60)
    assert process.returncode == 0, output
    assert latest(tmp_path, "_summary.json").exists()
    assert latest(tmp_path, "_notes.html").exists()


def test_no_capture_summary_marks_diagnostic_status() -> None:
    from meeting_notes_ai.main import no_capture_summary

    summary = no_capture_summary(chunk_count=3, avg_dbfs=-120.0, stop_requested_flag=False)
    assert summary["diagnostic_status"] == "no_transcript_captured"
    assert "Audio level was very low" in summary["meeting_summary"]
    assert summary["capture_tips"]


def test_daily_todo_carries_previous_open_tasks(tmp_path: Path, monkeypatch) -> None:
    import tkinter as tk
    import ui

    monkeypatch.setattr(ui, "TODO_PATH", tmp_path / "daily_todos.json")
    monkeypatch.setattr(ui, "TODO_ENC_PATH", tmp_path / "daily_todos.enc")
    root = make_tk_root()
    try:
        app = ui.MeetingNotesUI(root)
        first_day = ui.date(2026, 5, 29)
        next_day = ui.date(2026, 5, 30)

        app._show_todo_date(first_day)
        app.new_task_var.set("Send the project recap")
        app._add_todo_task()

        app._show_todo_date(next_day)
        previous = app._iter_previous_open_tasks()
        assert len(previous) == 1
        assert previous[0][1]["text"] == "Send the project recap"

        app._toggle_task_done(previous[0][0], previous[0][1], True)
        assert app._iter_previous_open_tasks() == []
    finally:
        root.destroy()


def test_ui_imports_meeting_actions_and_exports_todos(tmp_path: Path, monkeypatch) -> None:
    import tkinter as tk
    import ui

    todo_path = tmp_path / "daily_todos.json"
    output_dir = tmp_path / "outputs"
    output_dir.mkdir()
    summary_path = output_dir / "meeting_20260530_summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "meeting_title": "Import Smoke",
                "meeting_started_at": "2026-05-30T09:00:00",
                "meeting_summary": "Smoke summary",
                "action_items": ["Follow up with QA"],
                "structured_action_items": [
                    {"task": "Send release notes", "owner": "Aisha", "due": "2026-05-31"}
                ],
                "stats": {"segments_captured": 1},
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(ui, "TODO_PATH", todo_path)
    monkeypatch.setattr(ui, "TODO_ENC_PATH", tmp_path / "daily_todos.enc")
    monkeypatch.setattr(ui, "APP_DIR", tmp_path)
    monkeypatch.setattr(ui.messagebox, "showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr(ui.messagebox, "showerror", lambda *args, **kwargs: None)
    monkeypatch.setattr(ui.os, "startfile", lambda *args, **kwargs: None, raising=False)

    root = make_tk_root()
    try:
        app = ui.MeetingNotesUI(root)
        app.output_dir_var.set(str(output_dir))
        app.import_latest_meeting_actions()
        today_record = app.todo_data[ui.date.today().isoformat()]
        imported = [task["text"] for task in today_record["tasks"]]
        assert any("Send release notes" in task for task in imported)
        assert any("Follow up with QA" in task for task in imported)

        app.export_todos("today", "md")
        assert list(tmp_path.glob("todo_export_today_*.md"))
    finally:
        root.destroy()


def test_todo_round_trip(tmp_path: Path, monkeypatch) -> None:
    import tkinter as tk
    import ui

    todo_path = tmp_path / "daily_todos.json"
    monkeypatch.setattr(ui, "TODO_PATH", todo_path)

    root = make_tk_root()
    try:
        app = ui.MeetingNotesUI(root)
        app.todo_data = {"2026-05-30": {"text": "private", "tasks": []}}
        app._write_todo_data()
        assert todo_path.exists()
        assert "private" in todo_path.read_text(encoding="utf-8")
    finally:
        root.destroy()

