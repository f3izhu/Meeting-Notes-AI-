from __future__ import annotations

import queue
import threading
import warnings
from dataclasses import dataclass
from typing import Iterable, Optional

import numpy as np
import soundcard as sc


@dataclass
class DeviceInfo:
    id: str
    name: str
    is_loopback: bool


def list_input_devices() -> list[DeviceInfo]:
    devices: list[DeviceInfo] = []
    for mic in sc.all_microphones(include_loopback=True):
        name = mic.name or "Unknown"
        is_loopback = bool(getattr(mic, "isloopback", False))
        devices.append(
            DeviceInfo(
                id=name,
                name=name,
                is_loopback=is_loopback,
            )
        )
    return devices


def select_input_device(
    name_query: Optional[str] = None, prefer_loopback: bool = False
) -> sc.Microphone:
    microphones = sc.all_microphones(include_loopback=True)
    if not microphones:
        raise RuntimeError("No input devices found.")

    if name_query:
        lowered = name_query.lower()
        for mic in microphones:
            if lowered in (mic.name or "").lower():
                return mic
        raise RuntimeError(f"No input device matched query: {name_query}")

    if prefer_loopback:
        for mic in microphones:
            if bool(getattr(mic, "isloopback", False)):
                return mic

    default_mic = sc.default_microphone()
    if default_mic is not None:
        return default_mic

    return microphones[0]


def audio_chunks(
    microphone: sc.Microphone,
    samplerate: int,
    chunk_seconds: float,
    step_seconds: float = 0.5,
    buffer_chunks: int = 60,
) -> Iterable[np.ndarray]:
    chunk_frames = int(samplerate * chunk_seconds)
    step_frames = int(samplerate * step_seconds)
    if chunk_frames <= 0 or step_frames <= 0:
        raise ValueError("chunk_seconds and step_seconds must be > 0")

    chunk_queue: queue.Queue[np.ndarray | BaseException | None] = queue.Queue(maxsize=max(2, buffer_chunks))
    stop_event = threading.Event()

    def enqueue_chunk(chunk: np.ndarray) -> None:
        while not stop_event.is_set():
            try:
                chunk_queue.put(chunk, timeout=0.2)
                return
            except queue.Full:
                try:
                    chunk_queue.get_nowait()
                except queue.Empty:
                    pass

    def producer() -> None:
        cache = np.empty(0, dtype=np.float32)
        try:
            with microphone.recorder(samplerate=samplerate, channels=1) as recorder:
                while not stop_event.is_set():
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            message="data discontinuity in recording",
                            category=Warning,
                        )
                        frame = recorder.record(numframes=step_frames)
                    if frame.ndim > 1:
                        mono = frame.mean(axis=1, dtype=np.float32)
                    else:
                        mono = frame.astype(np.float32, copy=False)
                    cache = np.concatenate((cache, mono))

                    while cache.size >= chunk_frames:
                        enqueue_chunk(cache[:chunk_frames].copy())
                        cache = cache[chunk_frames:]
        except BaseException as exc:
            enqueue_chunk(exc)
        finally:
            enqueue_chunk(None)  # type: ignore[arg-type]

    thread = threading.Thread(target=producer, name="meeting-audio-capture", daemon=True)
    thread.start()
    try:
        while True:
            item = chunk_queue.get()
            if item is None:
                break
            if isinstance(item, BaseException):
                raise item
            yield item
    finally:
        stop_event.set()
        thread.join(timeout=2.0)
