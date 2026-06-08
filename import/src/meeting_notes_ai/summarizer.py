from __future__ import annotations

import json
import shutil
import subprocess
import time
from typing import Any

import requests

from .notes import fallback_summary


def ensure_ollama(timeout: float = 6.0) -> bool:
    """Check if Ollama is reachable; if not, try to start it in the background.

    Returns True if the service is reachable after the check/startup attempt.
    """
    # 1. Quick check — is it already running?
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=1.5)
        if resp.status_code == 200:
            return True
    except Exception:
        pass

    # 2. Try to start the service
    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        print("[ollama] 'ollama' not found on PATH. Skipping auto-start.")
        return False

    print("[ollama] Service offline. Attempting auto-start...")
    try:
        subprocess.Popen(
            [ollama_bin, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as exc:
        print(f"[ollama] Failed to start: {exc}")
        return False

    # 3. Poll until ready or timeout
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=1.0)
            if resp.status_code == 200:
                print("[ollama] Service started successfully.")
                return True
        except Exception:
            pass
        time.sleep(0.5)

    print("[ollama] Service did not become ready in time.")
    return False


def _normalize_summary_payload(parsed: Any) -> dict[str, Any]:
    if not isinstance(parsed, dict):
        raise ValueError("Summary payload is not a JSON object.")

    meeting_summary = str(parsed.get("meeting_summary", "")).strip()
    key_points = parsed.get("key_points", [])
    action_items = parsed.get("action_items", [])
    decisions = parsed.get("decisions", [])
    structured_items = parsed.get("structured_action_items", [])

    if not isinstance(key_points, list):
        key_points = []
    if not isinstance(action_items, list):
        action_items = []
    if not isinstance(decisions, list):
        decisions = []
    if not isinstance(structured_items, list):
        structured_items = []

    return {
        "meeting_summary": meeting_summary,
        "key_points": [str(x).strip() for x in key_points if str(x).strip()],
        "action_items": [str(x).strip() for x in action_items if str(x).strip()],
        "decisions": [str(x).strip() for x in decisions if str(x).strip()],
        "structured_action_items": [x for x in structured_items if isinstance(x, dict)],
    }


def summarize_with_ollama(
    transcript_text: str,
    model: str = "gemma3:1b",
    timeout_s: int = 120,
) -> dict[str, Any]:
    prompt = (
        "You are a meeting-notes assistant.\n"
        "Summarize this transcript into JSON with keys: "
        "meeting_summary (string), key_points (array of strings), "
        "action_items (array of strings), decisions (array of strings), "
        "structured_action_items (array of objects with task, owner, due, source_text).\n"
        "Keep it concise and factual.\n\n"
        f"Transcript:\n{transcript_text[:14000]}"
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": {
            "type": "object",
            "properties": {
                "meeting_summary": {"type": "string"},
                "key_points": {"type": "array", "items": {"type": "string"}},
                "action_items": {"type": "array", "items": {"type": "string"}},
                "decisions": {"type": "array", "items": {"type": "string"}},
                "structured_action_items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string"},
                            "owner": {"type": ["string", "null"]},
                            "due": {"type": ["string", "null"]},
                            "source_text": {"type": "string"},
                        },
                        "required": ["task", "source_text"],
                    },
                },
            },
            "required": [
                "meeting_summary",
                "key_points",
                "action_items",
                "decisions",
                "structured_action_items",
            ],
        },
    }
    response = requests.post(
        "http://localhost:11434/api/chat",
        json=payload,
        timeout=(3.0, timeout_s),
    )
    response.raise_for_status()
    data = response.json()
    content = data.get("message", {}).get("content", "{}")
    parsed = json.loads(content)
    return _normalize_summary_payload(parsed)


def list_installed_ollama_models() -> list[str]:
    """Get the list of installed model names from local Ollama service."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=2.0)
        if resp.status_code == 200:
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        pass
    return []


def summarize_meeting(
    transcript_text: str,
    use_ollama: bool,
    ollama_model: str,
) -> dict[str, Any]:
    if use_ollama:
        try:
            if ensure_ollama():
                installed = list_installed_ollama_models()
                if installed:
                    matched_model = None
                    # 1. Look for exact match
                    if ollama_model in installed:
                        matched_model = ollama_model
                    # 2. Look for base name match (e.g. 'gemma3' prefix match)
                    if not matched_model:
                        req_base = ollama_model.split(":")[0].lower()
                        for model_name in installed:
                            if model_name.split(":")[0].lower() == req_base:
                                matched_model = model_name
                                break
                    # 3. Fallback to first available installed model
                    if not matched_model:
                        matched_model = installed[0]
                        print(f"[ollama] Model '{ollama_model}' not found. Falling back to installed model: '{matched_model}'")
                    
                    return summarize_with_ollama(transcript_text=transcript_text, model=matched_model)
        except Exception as exc:
            print(f"[ollama] Fallback active due to error: {exc}")
            pass

    fallback = fallback_summary(transcript_text)
    return {
        "meeting_summary": fallback["meeting_summary"],
        "key_points": fallback["key_points"],
        "action_items": fallback["action_items"],
        "decisions": fallback["decisions"],
        "structured_action_items": fallback["structured_action_items"],
    }
