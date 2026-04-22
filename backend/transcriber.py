"""faster-whisper wrapper."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from faster_whisper import WhisperModel

from .config import settings


@dataclass(slots=True)
class WhisperService:
    """Manage model loading and transcription calls."""

    _models: dict[str, WhisperModel] = field(default_factory=dict)

    def preload_default(self) -> None:
        """Load default model at startup."""
        self._load_model(settings.whisper_model)

    def _load_model(self, model_name: str) -> WhisperModel:
        if model_name in self._models:
            return self._models[model_name]

        model = WhisperModel(
            model_size_or_path=model_name,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
        )
        self._models[model_name] = model
        return model

    def transcribe(
        self,
        audio: np.ndarray,
        language: str | None,
        model_name: str,
    ) -> str:
        """Transcribe mono 16kHz float32 audio and return plain text."""
        if audio.size == 0:
            return ""

        model = self._load_model(model_name)
        task_language = None if language in {None, "", "auto"} else language

        segments, _ = model.transcribe(
            audio,
            language=task_language,
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False,
        )
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        return text.strip()
