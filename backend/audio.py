"""Audio decoding and VAD helpers."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass, field

import numpy as np
import webrtcvad


TARGET_SAMPLE_RATE = 16_000
FRAME_MS = 30
FRAME_BYTES = int(TARGET_SAMPLE_RATE * (FRAME_MS / 1000.0) * 2)


def decode_media_chunk(chunk: bytes) -> np.ndarray:
    """Decode an encoded audio chunk to mono 16kHz float32 PCM."""
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-f",
        "s16le",
        "-acodec",
        "pcm_s16le",
        "-ac",
        "1",
        "-ar",
        str(TARGET_SAMPLE_RATE),
        "pipe:1",
    ]

    try:
        process = subprocess.run(
            command,
            input=chunk,
            capture_output=True,
            check=False,
            timeout=15,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("ffmpeg ist nicht installiert.") from exc

    if process.returncode == 0 and process.stdout:
        pcm_int16 = np.frombuffer(process.stdout, dtype=np.int16)
        return pcm_int16.astype(np.float32) / 32768.0

    if len(chunk) % 2 == 0:
        pcm_int16 = np.frombuffer(chunk, dtype=np.int16)
        return pcm_int16.astype(np.float32) / 32768.0

    stderr = process.stderr.decode("utf-8", errors="ignore").strip()
    raise ValueError(stderr or "Audio-Chunk konnte nicht dekodiert werden.")


@dataclass(slots=True)
class VADSegmenter:
    """Segments 16kHz mono audio into speech regions using WebRTC VAD."""

    aggressiveness: int = 2
    silence_ms_to_finalize: int = 700
    max_segment_seconds: float = 8.0
    _vad: webrtcvad.Vad = field(init=False)
    _incoming_bytes: bytes = field(default=b"")
    _active_bytes: bytearray = field(default_factory=bytearray)
    _in_speech: bool = field(default=False)
    _silence_frames: int = field(default=0)
    _last_partial_at: float = field(default_factory=time.monotonic)

    def __post_init__(self) -> None:
        self._vad = webrtcvad.Vad(self.aggressiveness)

    def consume(
        self,
        audio_float32: np.ndarray,
        partial_interval_seconds: float,
    ) -> tuple[list[np.ndarray], np.ndarray | None]:
        """Consume PCM float audio and return finalized and partial segments."""
        clipped_audio = np.clip(audio_float32, -1.0, 1.0)
        pcm_bytes = (clipped_audio * 32767.0).astype(np.int16).tobytes()
        self._incoming_bytes += pcm_bytes

        finalized_segments: list[np.ndarray] = []
        partial_segment: np.ndarray | None = None

        while len(self._incoming_bytes) >= FRAME_BYTES:
            frame = self._incoming_bytes[:FRAME_BYTES]
            self._incoming_bytes = self._incoming_bytes[FRAME_BYTES:]

            is_speech = self._vad.is_speech(frame, TARGET_SAMPLE_RATE)
            if is_speech:
                self._in_speech = True
                self._silence_frames = 0
                self._active_bytes.extend(frame)
            elif self._in_speech:
                self._silence_frames += 1
                self._active_bytes.extend(frame)

            if self._in_speech and self._should_emit_partial(partial_interval_seconds):
                partial_segment = self._bytes_to_float32(bytes(self._active_bytes))
                self._last_partial_at = time.monotonic()

            if self._should_finalize():
                finalized = self._finalize_active_segment()
                if finalized is not None:
                    finalized_segments.append(finalized)

        return finalized_segments, partial_segment

    def flush(self) -> np.ndarray | None:
        """Flush currently active speech segment at end of stream."""
        return self._finalize_active_segment()

    def _should_emit_partial(self, partial_interval_seconds: float) -> bool:
        if len(self._active_bytes) < TARGET_SAMPLE_RATE * 2:
            return False
        return (time.monotonic() - self._last_partial_at) >= partial_interval_seconds

    def _should_finalize(self) -> bool:
        if not self._in_speech:
            return False

        silence_frames_needed = max(1, self.silence_ms_to_finalize // FRAME_MS)
        segment_duration_seconds = len(self._active_bytes) / (2 * TARGET_SAMPLE_RATE)
        return self._silence_frames >= silence_frames_needed or segment_duration_seconds >= self.max_segment_seconds

    def _finalize_active_segment(self) -> np.ndarray | None:
        if not self._active_bytes:
            self._reset_active_state()
            return None

        trailing_silence = self._silence_frames * FRAME_BYTES
        if trailing_silence > 0 and trailing_silence < len(self._active_bytes):
            final_bytes = bytes(self._active_bytes[:-trailing_silence])
        else:
            final_bytes = bytes(self._active_bytes)

        self._reset_active_state()

        if not final_bytes:
            return None

        return self._bytes_to_float32(final_bytes)

    @staticmethod
    def _bytes_to_float32(pcm_bytes: bytes) -> np.ndarray:
        pcm_int16 = np.frombuffer(pcm_bytes, dtype=np.int16)
        return pcm_int16.astype(np.float32) / 32768.0

    def _reset_active_state(self) -> None:
        self._active_bytes.clear()
        self._in_speech = False
        self._silence_frames = 0
