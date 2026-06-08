from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from time import monotonic, sleep
from typing import Any

import numpy as np

from .audio import audio_chunks, list_input_devices, select_input_device
from .config import CONFIG_PATH, default_config, delete_config, load_config, save_config
from .notes import (
    export_html,
    extract_action_items,
    extract_decisions,
    extract_key_points,
    extract_structured_action_items,
)
from .summarizer import summarize_meeting
from .transcriber import RealTimeTranscriber, TranscriptSegment, transcript_to_text


PROFILE_PRESETS = {
    "fast": {"whisper_model": "tiny.en", "chunk_seconds": 6.0, "summary_every": 45},
    "balanced": {"whisper_model": "small.en", "chunk_seconds": 8.0, "summary_every": 60},
    "accurate": {"whisper_model": "medium.en", "chunk_seconds": 10.0, "summary_every": 75},
}


DEFAULT_SIMULATION_TEXT = "\n".join(
    [
        "Welcome everyone. This is the weekly product sync.",
        "We reviewed current sprint progress and confirmed backend tasks are on track.",
        "Decision: keep the launch date for May 22.",
        "Aisha will finalize the release notes by Friday.",
        "Owner: Daniel follow up with QA tomorrow about regression coverage.",
        "We agreed to defer advanced analytics to the next sprint.",
        "Action item: Priya should share the customer feedback summary by Monday.",
        "Next step is to prepare the go-live checklist and run a dry run.",
    ]
)


def format_hhmmss(seconds: float) -> str:
    whole = int(max(seconds, 0.0))
    h = whole // 3600
    m = (whole % 3600) // 60
    s = whole % 60
    return f"{h:02}:{m:02}:{s:02}"


def slugify(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def choose_auto_profile() -> str:
    cpu = os.cpu_count() or 4
    if cpu <= 4:
        return "fast"
    return "balanced"


def resolve_profile(profile: str | None) -> tuple[str, str]:
    requested = profile or "auto"
    if requested == "auto":
        return requested, choose_auto_profile()
    if requested not in PROFILE_PRESETS:
        return "auto", choose_auto_profile()
    return requested, requested


def print_devices() -> None:
    devices = list_input_devices()
    if not devices:
        print("No input devices found.")
        return
    print("Available input devices:")
    for idx, d in enumerate(devices, start=1):
        loop = " [loopback]" if d.is_loopback else ""
        print(f"{idx:>2}. {d.name}{loop}")


def merge_runtime_settings(args: argparse.Namespace) -> dict[str, Any]:
    stored = load_config()
    requested_profile, effective_profile = resolve_profile(args.profile or stored.get("profile"))

    merged = default_config()
    merged.update(PROFILE_PRESETS[effective_profile])
    merged.update(stored)

    overrides = {
        "profile": requested_profile,
        "device": args.device,
        "loopback": args.loopback,
        "sample_rate": args.sample_rate,
        "chunk_seconds": args.chunk_seconds,
        "summary_every": args.summary_every,
        "autosave_seconds": args.autosave_seconds,
        "whisper_model": args.whisper_model,
        "compute_type": args.compute_type,
        "inference_device": args.inference_device,
        "language": args.language,
        "output_dir": args.output_dir,
        "use_ollama": args.use_ollama,
        "ollama_model": args.ollama_model,
        "max_minutes": args.max_minutes,
    }

    for key, value in overrides.items():
        if value is not None:
            merged[key] = value

    if not merged.get("whisper_model"):
        merged["whisper_model"] = PROFILE_PRESETS[effective_profile]["whisper_model"]

    merged["effective_profile"] = effective_profile
    merged["autosave_seconds"] = int(max(0, int(merged.get("autosave_seconds", 30))))
    merged["summary_every"] = int(max(10, int(merged.get("summary_every", 60))))
    merged["sample_rate"] = int(max(8000, int(merged.get("sample_rate", 16000))))
    merged["chunk_seconds"] = float(max(2.0, float(merged.get("chunk_seconds", 8.0))))
    merged["max_minutes"] = int(max(0, int(merged.get("max_minutes", 0))))
    merged["use_ollama"] = bool(merged.get("use_ollama", True))
    output_dir = str(merged.get("output_dir", "outputs")).strip()
    merged["output_dir"] = output_dir if output_dir else "outputs"
    if merged.get("inference_device") not in {"cpu", "auto", "cuda"}:
        merged["inference_device"] = "cpu"
    return merged


def ask_with_default(prompt: str, default: str) -> str:
    raw = input(f"{prompt} [{default}]: ").strip()
    return raw if raw else default


def run_setup_wizard() -> int:
    current = default_config()
    current.update(load_config())

    print("Meeting Notes AI setup")
    print("Press Enter to keep default values.")
    print()

    source_default = "loopback" if current.get("loopback") else "mic"
    source = ask_with_default("Default source (mic/loopback)", source_default).lower()
    current["loopback"] = source.startswith("loop")

    devices = list_input_devices()
    if devices:
        print("\nAudio devices:")
        for idx, device in enumerate(devices, start=1):
            tag = " loopback" if device.is_loopback else ""
            print(f"  {idx}. {device.name}{tag}")

        current_device = current.get("device") or "auto"
        chosen = ask_with_default("Choose default device index or 'auto'", current_device)
        if chosen.lower() == "auto":
            current["device"] = None
        elif chosen.isdigit() and 1 <= int(chosen) <= len(devices):
            current["device"] = devices[int(chosen) - 1].name

    profile = ask_with_default("Profile (auto/fast/balanced/accurate)", str(current.get("profile", "auto")))
    if profile not in {"auto", "fast", "balanced", "accurate"}:
        profile = "auto"
    current["profile"] = profile

    current["summary_every"] = int(ask_with_default("Live notes frequency in seconds", str(current.get("summary_every", 60))))
    current["autosave_seconds"] = int(
        ask_with_default("Autosave frequency in seconds (0 to disable)", str(current.get("autosave_seconds", 30)))
    )
    current["max_minutes"] = int(
        ask_with_default("Max minutes per session (0 for unlimited)", str(current.get("max_minutes", 0)))
    )
    inference_device = ask_with_default(
        "Inference device (cpu/auto/cuda)",
        str(current.get("inference_device", "cpu")),
    ).lower()
    if inference_device not in {"cpu", "auto", "cuda"}:
        inference_device = "cpu"
    current["inference_device"] = inference_device

    ollama_default = "yes" if current.get("use_ollama", True) else "no"
    use_ollama = ask_with_default("Use Ollama when available? (yes/no)", ollama_default).lower()
    current["use_ollama"] = use_ollama.startswith("y")
    current["ollama_model"] = ask_with_default("Ollama model", str(current.get("ollama_model", "gemma3:1b")))

    current["output_dir"] = ask_with_default("Output directory", str(current.get("output_dir", "outputs")))

    requested, effective = resolve_profile(current.get("profile"))
    current["profile"] = requested
    if not current.get("whisper_model"):
        current["whisper_model"] = PROFILE_PRESETS[effective]["whisper_model"]

    path = save_config(current)
    print(f"\nSaved setup to: {path}")
    return 0


def chunk_dbfs(chunk: np.ndarray) -> float:
    if chunk.size == 0:
        return -120.0
    rms = float(np.sqrt(np.mean(np.square(chunk))))
    if rms <= 1e-8:
        return -120.0
    return float(20.0 * np.log10(rms + 1e-12))


def write_text_with_retry(path: Path, text: str, encoding: str = "utf-8", attempts: int = 5) -> None:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            path.write_text(text, encoding=encoding)
            return
        except PermissionError as exc:
            last_error = exc
            sleep(0.15 * (attempt + 1))
    if last_error:
        raise last_error


def save_autosave(
    output_dir: Path,
    base_name: str,
    meeting_title: str,
    started_at: datetime,
    segments: list[TranscriptSegment],
    live_notes: dict[str, Any],
    settings: dict[str, Any],
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    autosave_path = output_dir / f"{base_name}_autosave.json"
    payload = {
        "meeting_title": meeting_title,
        "started_at": started_at.isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "settings": {
            "profile": settings.get("profile"),
            "effective_profile": settings.get("effective_profile"),
            "sample_rate": settings.get("sample_rate"),
            "chunk_seconds": settings.get("chunk_seconds"),
            "whisper_model": settings.get("whisper_model"),
            "use_ollama": settings.get("use_ollama"),
            "ollama_model": settings.get("ollama_model"),
        },
        "live_notes": live_notes,
        "segments": [
            {"start": round(seg.start, 2), "end": round(seg.end, 2), "text": seg.text}
            for seg in segments[-600:]
        ],
    }
    write_text_with_retry(autosave_path, json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return autosave_path


def save_outputs(
    output_dir: Path,
    base_name: str,
    start_dt: datetime,
    meeting_title: str,
    segments: list[TranscriptSegment],
    final_summary: dict[str, Any],
    stats: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = output_dir / f"{base_name}_transcript.txt"
    json_path = output_dir / f"{base_name}_summary.json"
    md_path = output_dir / f"{base_name}_notes.md"
    html_path = output_dir / f"{base_name}_notes.html"

    transcript_lines = [
        f"[{format_hhmmss(seg.start)} - {format_hhmmss(seg.end)}] {seg.text}" for seg in segments
    ]
    transcript_body = "\n".join(transcript_lines)
    write_text_with_retry(transcript_path, transcript_body, encoding="utf-8")

    summary_payload = {
        "meeting_title": meeting_title,
        "meeting_started_at": start_dt.isoformat(timespec="seconds"),
        "stats": stats,
        **final_summary,
    }
    write_text_with_retry(json_path, json.dumps(summary_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = ["# Meeting Notes", ""]
    if meeting_title:
        md_lines.append(f"- Title: {meeting_title}")
    md_lines.extend(
        [
            f"- Date: {start_dt.isoformat(timespec='seconds')}",
            f"- Duration: {format_hhmmss(float(stats.get('duration_seconds', 0)))}",
            f"- Segments captured: {int(stats.get('segments_captured', 0))}",
            f"- Avg transcription latency: {float(stats.get('avg_transcribe_seconds', 0.0)):.2f}s",
            "",
            "## Summary",
            str(final_summary.get("meeting_summary", "")).strip(),
            "",
            "## Key Points",
        ]
    )
    for point in final_summary.get("key_points", []):
        md_lines.append(f"- {point}")

    md_lines.extend(["", "## Decisions"])
    for item in final_summary.get("decisions", []):
        md_lines.append(f"- {item}")

    md_lines.extend(["", "## Action Items"])
    for item in final_summary.get("action_items", []):
        md_lines.append(f"- {item}")

    structured = final_summary.get("structured_action_items", [])
    if structured:
        md_lines.extend(["", "## Structured Action Items"])
        for item in structured:
            task = item.get("task") or "(unspecified task)"
            owner = item.get("owner") or "Unassigned"
            due = item.get("due") or "No due date"
            md_lines.append(f"- {task} | Owner: {owner} | Due: {due}")

    md_lines.extend(["", "## Full Transcript", "```text", transcript_body, "```", ""])
    write_text_with_retry(md_path, "\n".join(md_lines), encoding="utf-8")

    # Generate styled HTML report
    html_content = export_html(
        meeting_title=meeting_title,
        meeting_date=start_dt.isoformat(timespec="seconds"),
        duration=format_hhmmss(float(stats.get("duration_seconds", 0))),
        segments_captured=int(stats.get("segments_captured", 0)),
        avg_latency=float(stats.get("avg_transcribe_seconds", 0.0)),
        summary=final_summary,
        transcript_lines=transcript_lines,
    )
    write_text_with_retry(html_path, html_content, encoding="utf-8")

    print("\nSaved:")
    print(f"- {transcript_path}")
    print(f"- {json_path}")
    print(f"- {md_path}")
    print(f"- {html_path}")


def no_capture_summary(
    chunk_count: int,
    avg_dbfs: float | None,
    stop_requested_flag: bool,
    error_message: str = "",
) -> dict[str, Any]:
    tips = [
        "Confirm the correct input source: use loopback for online meetings, microphone for in-person.",
        "Pick the exact output device carrying meeting audio (e.g., your active headphones/speakers).",
        "Let recording run at least 20-40 seconds before stopping.",
        "If speech is non-English, set the right language with --language.",
    ]

    if chunk_count == 0:
        reason = "No audio chunks were processed before stopping."
    elif avg_dbfs is not None and avg_dbfs < -70:
        reason = "Audio level was very low, likely wrong input device or muted source."
    else:
        reason = "Audio was captured but no transcript segments were produced."

    status = "Stopped by user before transcript was captured." if stop_requested_flag else "Run finished without transcript."
    summary = {
        "meeting_summary": f"{status} {reason}",
        "diagnostic_status": "no_transcript_captured",
        "key_points": [],
        "action_items": [],
        "decisions": [],
        "structured_action_items": [],
        "capture_tips": tips,
    }
    if error_message:
        summary["error"] = error_message
    return summary


def persist_current_settings(settings: dict[str, Any]) -> None:
    to_save = {
        "profile": settings.get("profile", "auto"),
        "device": settings.get("device"),
        "loopback": settings.get("loopback", False),
        "sample_rate": settings.get("sample_rate", 16000),
        "chunk_seconds": settings.get("chunk_seconds", 8.0),
        "summary_every": settings.get("summary_every", 60),
        "autosave_seconds": settings.get("autosave_seconds", 30),
        "whisper_model": settings.get("whisper_model"),
        "compute_type": settings.get("compute_type", "int8"),
        "inference_device": settings.get("inference_device", "cpu"),
        "language": settings.get("language", "en"),
        "output_dir": settings.get("output_dir", "outputs"),
        "use_ollama": settings.get("use_ollama", True),
        "ollama_model": settings.get("ollama_model", "gemma3:1b"),
        "max_minutes": settings.get("max_minutes", 0),
    }
    path = save_config(to_save)
    print(f"Saved current preferences to: {path}")


def run_doctor() -> int:
    print("Meeting Notes AI Doctor")
    print("-----------------------")

    checks: list[tuple[str, bool, str, bool]] = []

    py_ok = sys.version_info >= (3, 10)
    checks.append(
        (
            "Python version",
            py_ok,
            f"{platform.python_version()} (requires >= 3.10)",
            True,
        )
    )

    try:
        import faster_whisper  # noqa: F401

        checks.append(("faster-whisper import", True, "available", True))
    except Exception as exc:
        checks.append(("faster-whisper import", False, str(exc), True))

    try:
        devices = list_input_devices()
        checks.append(("Audio devices", len(devices) > 0, f"{len(devices)} device(s) detected", True))
    except Exception as exc:
        checks.append(("Audio devices", False, str(exc), True))

    try:
        output_dir = Path("outputs")
        output_dir.mkdir(parents=True, exist_ok=True)
        probe = output_dir / f".write_test_{os.getpid()}.tmp"
        write_text_with_retry(probe, "ok", encoding="utf-8")
        for _ in range(5):
            try:
                probe.unlink(missing_ok=True)
                break
            except PermissionError:
                sleep(0.15)
        checks.append(("Output folder write", True, str(output_dir.resolve()), True))
    except Exception as exc:
        checks.append(("Output folder write", False, str(exc), True))

    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as response:
            status_ok = response.status == 200
        checks.append(("Ollama service", status_ok, "reachable on localhost:11434", False))
    except Exception as exc:
        checks.append(("Ollama service", False, f"not reachable ({exc})", False))

    failed = 0
    for name, ok, details, required in checks:
        if ok:
            icon = "PASS"
        elif required:
            icon = "FAIL"
        else:
            icon = "WARN"
        print(f"[{icon}] {name}: {details}")
        if required and not ok:
            failed += 1

    if failed == 0:
        print("\nDoctor result: healthy")
        return 0

    print(f"\nDoctor result: {failed} check(s) need attention")
    return 1


def simulated_segments(
    text: str,
    chunk_seconds: float,
    duration_seconds: int,
) -> list[TranscriptSegment]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        lines = [DEFAULT_SIMULATION_TEXT]

    segments: list[TranscriptSegment] = []
    t = 0.0
    idx = 0
    while t < duration_seconds:
        line = lines[idx % len(lines)]
        start = t
        end = min(t + max(chunk_seconds * 0.9, 2.0), float(duration_seconds))
        segments.append(TranscriptSegment(start=start, end=end, text=line))
        t += max(chunk_seconds, 2.0)
        idx += 1
    return segments


def run(args: argparse.Namespace) -> int:
    if args.list_devices:
        print_devices()
        return 0

    settings = merge_runtime_settings(args)
    effective_profile = settings["effective_profile"]
    print(f"Profile: {settings.get('profile')} (effective: {effective_profile})")
    print(
        "Whisper model: "
        f"{settings.get('whisper_model')} | compute: {settings.get('compute_type')} | "
        f"inference_device: {settings.get('inference_device')}"
    )
    print("Recording started. Press Ctrl+C to stop.\n")

    meeting_start = datetime.now()
    meeting_stamp = meeting_start.strftime("%Y%m%d_%H%M%S")
    title_slug = slugify(args.meeting_title or "")
    base_name = f"meeting_{meeting_stamp}"
    if title_slug:
        base_name = f"{base_name}_{title_slug}"

    output_dir = Path(str(settings["output_dir"]))
    output_dir.mkdir(parents=True, exist_ok=True)
    stop_file = Path(args.stop_file) if getattr(args, "stop_file", None) else None
    if stop_file and stop_file.exists():
        try:
            stop_file.unlink()
        except Exception:
            pass

    def stop_requested() -> bool:
        return bool(stop_file and stop_file.exists())
    start_ts = monotonic()
    segments: list[TranscriptSegment] = []
    chunk_offset = 0.0
    next_live_notes = int(settings["summary_every"])
    autosave_every = int(settings["autosave_seconds"])
    next_autosave = autosave_every if autosave_every > 0 else 10**9

    chunk_count = 0
    latencies: list[float] = []
    rtf_values: list[float] = []
    levels_dbfs: list[float] = []

    live_notes: dict[str, Any] = {
        "key_points": [],
        "action_items": [],
        "decisions": [],
        "structured_action_items": [],
    }

    if args.simulate:
        print("Using input device: [simulation]")
        print("Simulation mode enabled. Running without microphone/model download.")
        simulation_text = DEFAULT_SIMULATION_TEXT
        if args.simulate_script:
            script_path = Path(args.simulate_script)
            if script_path.exists():
                simulation_text = script_path.read_text(encoding="utf-8")

        simulated = simulated_segments(
            text=simulation_text,
            chunk_seconds=float(settings["chunk_seconds"]),
            duration_seconds=max(15, int(args.simulate_duration)),
        )
        segments = []
        for seg in simulated:
            if stop_requested():
                print("Stop requested from UI. Finalizing notes...")
                break
            segments.append(seg)
            print(f"[{format_hhmmss(seg.start)}] {seg.text}")
            if args.simulate_step_ms > 0:
                sleep(args.simulate_step_ms / 1000.0)

        if stop_requested() and not segments:
            print("Stopped before any transcript was captured.")
            return 0
        if not segments:
            print("No transcript captured.")
            return 1

        elapsed = max(1.0, float(max(seg.end for seg in segments)))
        chunk_count = len(segments)
        latencies = [0.02 for _ in range(chunk_count)]
        rtf_values = [latencies[0] / max(float(settings["chunk_seconds"]), 0.001) for _ in range(max(1, chunk_count))]

        recent_text = transcript_to_text(segments[-50:])
        live_notes = {
            "key_points": extract_key_points(recent_text, max_points=4),
            "action_items": extract_action_items(recent_text, max_items=4),
            "decisions": extract_decisions(recent_text, max_items=3),
            "structured_action_items": extract_structured_action_items(recent_text, max_items=4),
        }

        full_text = transcript_to_text(segments)
        final_summary = summarize_meeting(
            transcript_text=full_text,
            use_ollama=bool(settings["use_ollama"]),
            ollama_model=str(settings["ollama_model"]),
        )
        final_summary.setdefault("meeting_summary", "")
        final_summary.setdefault("key_points", [])
        final_summary.setdefault("action_items", [])
        final_summary.setdefault("decisions", [])
        final_summary.setdefault("structured_action_items", [])
        if not final_summary.get("structured_action_items"):
            final_summary["structured_action_items"] = extract_structured_action_items(full_text)

        stats = {
            "duration_seconds": round(elapsed, 2),
            "segments_captured": len(segments),
            "chunks_processed": chunk_count,
            "avg_transcribe_seconds": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
            "avg_rtf": round(sum(rtf_values) / len(rtf_values), 3) if rtf_values else 0.0,
        }
        save_outputs(
            output_dir=output_dir,
            base_name=base_name,
            start_dt=meeting_start,
            meeting_title=args.meeting_title or "",
            segments=segments,
            final_summary=final_summary,
            stats=stats,
        )
        if args.save_preferences:
            persist_current_settings(settings)
        return 0

    mic = select_input_device(name_query=settings.get("device"), prefer_loopback=bool(settings.get("loopback")))
    print(f"Using input device: {mic.name}")

    transcribe_runtime_error = ""
    try:
        transcriber = RealTimeTranscriber(
            model_name=str(settings["whisper_model"]),
            compute_type=str(settings["compute_type"]),
            language=str(settings["language"]),
            inference_device=str(settings.get("inference_device", "cpu")),
        )
    except KeyboardInterrupt:
        print("Startup canceled during model initialization/download.")
        return 1
    except Exception as exc:
        transcribe_runtime_error = f"Transcriber initialization failed: {exc}"
        print(transcribe_runtime_error)
        transcriber = None

    if transcriber is not None:
        try:
            for chunk in audio_chunks(
                microphone=mic,
                samplerate=int(settings["sample_rate"]),
                chunk_seconds=float(settings["chunk_seconds"]),
            ):
                if stop_requested():
                    print("Stop requested from UI. Finalizing notes...")
                    break

                chunk_count += 1
                level_db = chunk_dbfs(chunk)
                levels_dbfs.append(level_db)

                t0 = monotonic()
                try:
                    chunk_segments = transcriber.transcribe_chunk(chunk, chunk_offset=chunk_offset)
                except Exception as exc:
                    transcribe_runtime_error = f"Transcription runtime error: {exc}"
                    print(transcribe_runtime_error)
                    break
                latency = monotonic() - t0
                latencies.append(latency)

                chunk_offset += float(settings["chunk_seconds"])
                rtf = latency / max(float(settings["chunk_seconds"]), 0.001)
                rtf_values.append(rtf)

                print(
                    f"[status] level={level_db:6.1f} dBFS | transcribe={latency:4.2f}s "
                    f"| rtf={rtf:4.2f} | chunks={chunk_count}"
                )

                if chunk_segments:
                    segments.extend(chunk_segments)
                    for seg in chunk_segments:
                        print(f"[{format_hhmmss(seg.start)}] {seg.text}")

                elapsed = monotonic() - start_ts
                if elapsed >= next_live_notes and segments:
                    recent_text = transcript_to_text(segments[-50:])
                    live_notes = {
                        "key_points": extract_key_points(recent_text, max_points=4),
                        "action_items": extract_action_items(recent_text, max_items=4),
                        "decisions": extract_decisions(recent_text, max_items=3),
                        "structured_action_items": extract_structured_action_items(recent_text, max_items=4),
                    }
                    has_live_note = any(
                        live_notes[key]
                        for key in ("key_points", "decisions", "structured_action_items", "action_items")
                    )

                    print("\n--- Live Notes ---")
                    if live_notes["key_points"]:
                        print("Key points:")
                        for p in live_notes["key_points"]:
                            print(f"- {p}")

                    if live_notes["decisions"]:
                        print("Decisions:")
                        for d in live_notes["decisions"]:
                            print(f"- {d}")

                    if live_notes["structured_action_items"]:
                        print("Structured action items:")
                        for item in live_notes["structured_action_items"]:
                            task = item.get("task") or "(unspecified task)"
                            owner = item.get("owner") or "Unassigned"
                            due = item.get("due") or "No due date"
                            print(f"- {task} | Owner: {owner} | Due: {due}")
                    elif live_notes["action_items"]:
                        print("Action items:")
                        for a in live_notes["action_items"]:
                            print(f"- {a}")
                    if not has_live_note:
                        print("- No clear highlights yet.")
                    print("------------------\n")
                    next_live_notes += int(settings["summary_every"])

                if elapsed >= next_autosave and autosave_every > 0:
                    autosave_path = save_autosave(
                        output_dir=output_dir,
                        base_name=base_name,
                        meeting_title=args.meeting_title or "",
                        started_at=meeting_start,
                        segments=segments,
                        live_notes=live_notes,
                        settings=settings,
                    )
                    print(f"[autosave] {autosave_path}")
                    next_autosave += autosave_every

                if int(settings["max_minutes"]) and elapsed > int(settings["max_minutes"]) * 60:
                    print("Reached max duration, stopping.")
                    break

        except KeyboardInterrupt:
            print("\nStopping meeting capture...")
        except Exception as exc:
            transcribe_runtime_error = f"Audio capture error: {exc}"
            print(f"\n[error] {transcribe_runtime_error}")

    duration = monotonic() - start_ts
    stats = {
        "duration_seconds": round(duration, 2),
        "segments_captured": len(segments),
        "chunks_processed": chunk_count,
        "avg_transcribe_seconds": round(sum(latencies) / len(latencies), 3) if latencies else 0.0,
        "avg_rtf": round(sum(rtf_values) / len(rtf_values), 3) if rtf_values else 0.0,
        "avg_level_dbfs": round(sum(levels_dbfs) / len(levels_dbfs), 2) if levels_dbfs else None,
    }

    if not segments:
        final_summary = no_capture_summary(
            chunk_count=chunk_count,
            avg_dbfs=stats["avg_level_dbfs"],
            stop_requested_flag=stop_requested(),
            error_message=transcribe_runtime_error,
        )
        save_outputs(
            output_dir=output_dir,
            base_name=base_name,
            start_dt=meeting_start,
            meeting_title=args.meeting_title or "",
            segments=segments,
            final_summary=final_summary,
            stats=stats,
        )
        print(f"No transcript captured. Saved diagnostic notes in {output_dir}.")
        if transcribe_runtime_error and not stop_requested():
            return 1
        return 0

    full_text = transcript_to_text(segments)
    final_summary = summarize_meeting(
        transcript_text=full_text,
        use_ollama=bool(settings["use_ollama"]),
        ollama_model=str(settings["ollama_model"]),
    )

    final_summary.setdefault("meeting_summary", "")
    final_summary.setdefault("key_points", [])
    final_summary.setdefault("action_items", [])
    final_summary.setdefault("decisions", [])
    final_summary.setdefault("structured_action_items", [])
    if not final_summary.get("structured_action_items"):
        final_summary["structured_action_items"] = extract_structured_action_items(full_text)

    save_outputs(
        output_dir=output_dir,
        base_name=base_name,
        start_dt=meeting_start,
        meeting_title=args.meeting_title or "",
        segments=segments,
        final_summary=final_summary,
        stats=stats,
    )

    if args.save_preferences:
        persist_current_settings(settings)

    if stop_file and stop_file.exists():
        try:
            stop_file.unlink()
        except Exception:
            pass

    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Local meeting notes AI (free/offline transcription + local summary)."
    )
    parser.add_argument("--setup", action="store_true", help="Run interactive setup wizard.")
    parser.add_argument("--doctor", action="store_true", help="Run environment diagnostics and exit.")
    parser.add_argument("--show-config", action="store_true", help="Print effective runtime config and exit.")
    parser.add_argument("--reset-config", action="store_true", help="Delete saved config and exit.")
    parser.add_argument("--save-preferences", action="store_true", help="Save this run's settings as new defaults.")

    parser.add_argument("--list-devices", action="store_true", help="List available audio input devices.")
    parser.add_argument("--meeting-title", type=str, default="", help="Optional meeting title for output files.")
    parser.add_argument("--profile", choices=["auto", "fast", "balanced", "accurate"], default=None)
    parser.add_argument("--device", type=str, default=None, help="Select input device by partial name.")

    parser.add_argument(
        "--loopback",
        dest="loopback",
        action="store_true",
        default=None,
        help="Prefer system loopback input (best for online meetings).",
    )
    parser.add_argument("--no-loopback", dest="loopback", action="store_false", help=argparse.SUPPRESS)

    parser.add_argument("--sample-rate", type=int, default=None, help="Audio sample rate.")
    parser.add_argument("--chunk-seconds", type=float, default=None, help="Chunk size to transcribe.")
    parser.add_argument("--summary-every", type=int, default=None, help="Seconds between live notes snapshots.")
    parser.add_argument("--autosave-seconds", type=int, default=None, help="Seconds between autosave snapshots.")

    parser.add_argument("--whisper-model", type=str, default=None, help="Faster-Whisper model name.")
    parser.add_argument("--compute-type", type=str, default=None, help="Whisper compute type.")
    parser.add_argument(
        "--inference-device",
        type=str,
        choices=["cpu", "auto", "cuda"],
        default=None,
        help="Inference device backend for transcription (recommended: cpu).",
    )
    parser.add_argument("--language", type=str, default=None, help="Transcription language.")
    parser.add_argument("--output-dir", type=str, default=None, help="Directory for notes files.")

    parser.add_argument(
        "--use-ollama",
        dest="use_ollama",
        action="store_true",
        default=None,
        help="Use local Ollama for improved final summary quality.",
    )
    parser.add_argument("--no-ollama", dest="use_ollama", action="store_false")
    parser.add_argument("--ollama-model", type=str, default=None, help="Local Ollama model to summarize.")

    parser.add_argument("--max-minutes", type=int, default=None, help="Auto-stop after N minutes (0 = unlimited).")
    parser.add_argument("--simulate", action="store_true", help="Run a local simulation without live audio capture.")
    parser.add_argument("--simulate-duration", type=int, default=90, help=argparse.SUPPRESS)
    parser.add_argument("--simulate-script", type=str, default="", help=argparse.SUPPRESS)
    parser.add_argument("--simulate-step-ms", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--stop-file", type=str, default="", help=argparse.SUPPRESS)

    return parser.parse_args(argv)


def main() -> int:
    args = parse_args(sys.argv[1:])

    if args.reset_config:
        removed = delete_config()
        if removed:
            print(f"Removed saved config at: {CONFIG_PATH}")
        else:
            print("No saved config found.")
        return 0

    if args.setup:
        return run_setup_wizard()

    if args.doctor:
        return run_doctor()

    if args.show_config:
        settings = merge_runtime_settings(args)
        print(json.dumps(settings, indent=2, ensure_ascii=False))
        return 0

    if not CONFIG_PATH.exists() and sys.stdin.isatty():
        print("Tip: run 'python run.py --setup' once for guided defaults.")

    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
