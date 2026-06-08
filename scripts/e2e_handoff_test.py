from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "Scripts" / "python.exe"
if not PYTHON.exists():
    PYTHON = Path(sys.executable)


def run_cmd(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )


def assert_ok(result: subprocess.CompletedProcess[str], name: str) -> None:
    if result.returncode != 0:
        raise RuntimeError(
            f"{name} failed (exit {result.returncode})\n"
            f"Command: {' '.join(result.args)}\n\nOutput:\n{result.stdout}"
        )


def find_latest_file(directory: Path, suffix: str) -> Path:
    files = sorted(directory.glob(f"*{suffix}"), key=lambda p: p.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No {suffix} file found in {directory}")
    return files[-1]


def main() -> int:
    run_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "outputs_e2e" / f"run_{run_stamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("1) Running doctor...")
    doctor = run_cmd([str(PYTHON), "run.py", "--doctor"])
    assert_ok(doctor, "doctor")
    print(doctor.stdout.strip())

    print("\n2) Running simulated full pipeline...")
    simulate = run_cmd(
        [
            str(PYTHON),
            "run.py",
            "--simulate",
            "--simulate-duration",
            "120",
            "--meeting-title",
            "Final Handoff Validation",
            "--output-dir",
            str(out_dir),
            "--no-ollama",
        ]
    )
    assert_ok(simulate, "simulate")
    print(simulate.stdout.strip())

    print("\n3) Validating generated artifacts...")
    transcript = find_latest_file(out_dir, "_transcript.txt")
    summary_json = find_latest_file(out_dir, "_summary.json")
    notes_md = find_latest_file(out_dir, "_notes.md")
    notes_html = find_latest_file(out_dir, "_notes.html")

    summary = json.loads(summary_json.read_text(encoding="utf-8"))
    required_keys = {
        "meeting_title",
        "meeting_started_at",
        "stats",
        "meeting_summary",
        "key_points",
        "action_items",
        "decisions",
        "structured_action_items",
    }
    missing = sorted(k for k in required_keys if k not in summary)
    if missing:
        raise RuntimeError(f"Summary JSON missing keys: {missing}")

    if not isinstance(summary["key_points"], list):
        raise RuntimeError("key_points is not a list")
    if not isinstance(summary["structured_action_items"], list):
        raise RuntimeError("structured_action_items is not a list")

    transcript_text = transcript.read_text(encoding="utf-8").strip()
    notes_text = notes_md.read_text(encoding="utf-8")
    if not transcript_text:
        raise RuntimeError("Transcript file is empty")
    if "## Summary" not in notes_text:
        raise RuntimeError("Notes markdown missing Summary section")
    if notes_html.stat().st_size <= 0:
        raise RuntimeError("HTML notes file is empty")

    print("Artifacts validated:")
    print(f"- {transcript}")
    print(f"- {summary_json}")
    print(f"- {notes_md}")
    print(f"- {notes_html}")

    print("\nE2E handoff test PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
