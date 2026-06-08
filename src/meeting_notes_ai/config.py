from __future__ import annotations

import json
from pathlib import Path
from typing import Any


APP_DIR = Path.home() / ".meeting-notes-ai"
CONFIG_PATH = APP_DIR / "config.json"


def default_config() -> dict[str, Any]:
    return {
        "profile": "auto",
        "device": None,
        "loopback": False,
        "sample_rate": 16000,
        "chunk_seconds": 8.0,
        "summary_every": 60,
        "autosave_seconds": 30,
        "whisper_model": None,
        "compute_type": "int8",
        "inference_device": "cpu",
        "language": "en",
        "output_dir": "outputs",
        "use_ollama": True,
        "ollama_model": "gemma3:1b",
        "max_minutes": 0,
    }


def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    merged = default_config()
    if not CONFIG_PATH.exists():
        return merged
    changed = False
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            output_dir = str(data.get("output_dir", "")).strip().lower()
            if output_dir == "ouputrs":
                data["output_dir"] = "outputs"
                changed = True
            if data.get("inference_device") not in {None, "cpu", "auto", "cuda"}:
                data["inference_device"] = "cpu"
                changed = True
            
            # Merge loaded data into defaults
            for k, v in data.items():
                merged[k] = v
                
            if changed:
                save_config(merged)
            return merged
    except Exception:
        pass
    return merged


def save_config(config: dict[str, Any]) -> Path:
    ensure_app_dir()
    CONFIG_PATH.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return CONFIG_PATH


def delete_config() -> bool:
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
        return True
    return False
