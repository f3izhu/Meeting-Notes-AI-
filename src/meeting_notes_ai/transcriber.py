from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from faster_whisper import WhisperModel


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


class RealTimeTranscriber:
    def __init__(
        self,
        model_name: str = "small.en",
        compute_type: str = "int8",
        language: str = "en",
        inference_device: str = "cpu",
    ) -> None:
        self.model_name = model_name
        self.compute_type = compute_type
        self.inference_device = inference_device
        self.active_device = inference_device
        self.model = self._load_model_with_fallback()
        self.language = language

    def _load_model_with_fallback(self) -> WhisperModel:
        tried: list[str] = []

        candidate_devices = [self.inference_device]
        if "cpu" not in candidate_devices:
            candidate_devices.append("cpu")

        for dev in candidate_devices:
            try:
                model = WhisperModel(self.model_name, device=dev, compute_type=self.compute_type)
                self.active_device = dev
                return model
            except Exception as exc:
                tried.append(f"{dev}/{self.compute_type}: {exc}")

        if self.compute_type != "int8":
            try:
                model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
                self.active_device = "cpu"
                self.compute_type = "int8"
                return model
            except Exception as exc:
                tried.append(f"cpu/int8: {exc}")

        raise RuntimeError("Unable to initialize Whisper model. Attempts: " + " | ".join(tried))

    def _recover_if_cuda_runtime_error(self, err: Exception) -> bool:
        msg = str(err).lower()
        needs_cpu = any(marker in msg for marker in ["cublas", "cuda", "cudnn"])
        if not needs_cpu:
            return False
        if self.active_device == "cpu":
            return False
        self.inference_device = "cpu"
        self.compute_type = "int8"
        self.model = WhisperModel(self.model_name, device="cpu", compute_type="int8")
        self.active_device = "cpu"
        return True

    def transcribe_chunk(self, audio_chunk: np.ndarray, chunk_offset: float) -> list[TranscriptSegment]:
        try:
            segments, _ = self.model.transcribe(
                audio_chunk,
                language=self.language,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
            )
        except Exception as exc:
            recovered = False
            try:
                recovered = self._recover_if_cuda_runtime_error(exc)
            except Exception:
                recovered = False
            if not recovered:
                raise
            segments, _ = self.model.transcribe(
                audio_chunk,
                language=self.language,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
                beam_size=1,
                best_of=1,
                condition_on_previous_text=False,
            )
        output: list[TranscriptSegment] = []
        for seg in segments:
            text = seg.text.strip()
            if not text:
                continue
            output.append(
                TranscriptSegment(
                    start=chunk_offset + float(seg.start),
                    end=chunk_offset + float(seg.end),
                    text=text,
                )
            )
        return output


def transcript_to_text(segments: Iterable[TranscriptSegment]) -> str:
    return " ".join(segment.text for segment in segments).strip()
