"""Application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


DEFAULT_MODELS = ["tiny", "base", "small", "medium", "large-v3"]


@dataclass(slots=True)
class Settings:
    """Runtime settings loaded from environment variables."""

    whisper_model: str = os.getenv("WHISPER_MODEL", "small")
    whisper_device: str = os.getenv("WHISPER_DEVICE", "cpu")
    whisper_compute_type: str = os.getenv(
        "WHISPER_COMPUTE_TYPE",
        "float16" if os.getenv("WHISPER_DEVICE", "cpu") == "cuda" else "int8",
    )
    ws_partial_interval_seconds: float = float(os.getenv("WS_PARTIAL_INTERVAL_SECONDS", "1.2"))
    vad_aggressiveness: int = int(os.getenv("VAD_AGGRESSIVENESS", "2"))
    vad_silence_ms: int = int(os.getenv("VAD_SILENCE_MS", "700"))
    vad_max_segment_seconds: float = float(os.getenv("VAD_MAX_SEGMENT_SECONDS", "8"))
    available_models: list[str] = field(
        default_factory=lambda: [
            model.strip()
            for model in os.getenv("WHISPER_AVAILABLE_MODELS", ",".join(DEFAULT_MODELS)).split(",")
            if model.strip()
        ]
    )


settings = Settings()
