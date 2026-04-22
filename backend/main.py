"""FastAPI entrypoint for VoicePilot."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .audio import VADSegmenter, decode_media_chunk
from .config import settings
from .transcriber import WhisperService

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="VoicePilot", version="1.0.0")
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

transcriber = WhisperService()


@app.on_event("startup")
def startup_event() -> None:
    """Preload default whisper model."""
    transcriber.preload_default()


@app.get("/")
def root() -> FileResponse:
    """Serve web frontend."""
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Health endpoint."""
    return {"status": "ok", "model": settings.whisper_model}


@app.get("/api/models")
def list_models() -> dict[str, list[str]]:
    """List selectable whisper models."""
    return {"models": settings.available_models}


@app.websocket("/ws/transcribe")
async def ws_transcribe(websocket: WebSocket) -> None:
    """Receive audio chunks and return partial/final transcripts."""
    await websocket.accept()

    language = websocket.query_params.get("language", "auto")
    model_name = websocket.query_params.get("model", settings.whisper_model)

    if model_name not in settings.available_models:
        await websocket.send_json(
            {
                "type": "error",
                "message": f"Unbekanntes Modell '{model_name}'.",
            }
        )
        await websocket.close(code=1003)
        return

    segmenter = VADSegmenter(
        aggressiveness=settings.vad_aggressiveness,
        silence_ms_to_finalize=settings.vad_silence_ms,
        max_segment_seconds=settings.vad_max_segment_seconds,
    )

    last_partial_text = ""

    try:
        while True:
            message = await websocket.receive()
            chunk: bytes | None = message.get("bytes")
            if not chunk:
                continue

            try:
                audio = decode_media_chunk(chunk)
            except Exception as exc:  # noqa: BLE001
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": f"Audio-Dekodierung fehlgeschlagen: {exc}",
                    }
                )
                continue

            finalized_segments, partial_segment = segmenter.consume(
                audio,
                partial_interval_seconds=settings.ws_partial_interval_seconds,
            )

            if partial_segment is not None:
                partial_text = transcriber.transcribe(
                    partial_segment,
                    language=language,
                    model_name=model_name,
                )
                if partial_text and partial_text != last_partial_text:
                    last_partial_text = partial_text
                    await websocket.send_json({"type": "partial", "text": partial_text})

            for finalized_audio in finalized_segments:
                final_text = transcriber.transcribe(
                    finalized_audio,
                    language=language,
                    model_name=model_name,
                )
                if final_text:
                    last_partial_text = ""
                    await websocket.send_json({"type": "final", "text": final_text})

    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        flushed_audio = segmenter.flush()
        if flushed_audio is not None:
            final_text = transcriber.transcribe(
                flushed_audio,
                language=language,
                model_name=model_name,
            )
            if final_text:
                await websocket.send_json({"type": "final", "text": final_text})
