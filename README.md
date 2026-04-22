# VoicePilot

VoicePilot ist eine web-basierte Live-Diktier-App. Mehrere Geräte (Windows, macOS, Linux, iOS, Android) können per Browser auf dieselbe URL zugreifen, Mikrofon freigeben und Sprache in nahezu Echtzeit transkribieren.

## Basis: OpenAI Whisper + faster-whisper

- Whisper-Modelle stammen von **OpenAI Whisper**: https://github.com/openai/whisper
- Die App nutzt **faster-whisper** (CTranslate2) für schnellere Inferenz: https://github.com/SYSTRAN/faster-whisper

## Features

- Kontinuierliche Aufnahme im Browser
- WebSocket-Streaming von Audio-Chunks ans Backend
- Serverseitige Segmentierung via WebRTC VAD
- Teil- und Endergebnisse (`partial` / `final`)
- Sprachwahl (Auto / DE / EN / …)
- Modellwahl (tiny, base, small, medium, large-v3)
- Export: Kopieren + `.txt` Download
- Responsive UI (inkl. Mobile)

## Projektstruktur

```text
VoicePilot/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── transcriber.py
│   ├── audio.py
│   └── config.py
├── frontend/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .dockerignore
├── .gitignore
├── LICENSE
└── README.md
```

## Quick Start (Docker)

```bash
git clone https://github.com/GuidoM48/VoicePilot.git
cd VoicePilot
docker compose up --build
```

Danach erreichbar unter: `http://localhost:8000`

> Beim ersten Start wird das gewählte Whisper-Modell heruntergeladen. Das kann je nach Modell/Netz dauern.

## Lokale Entwicklung (ohne Docker)

Voraussetzungen: Python 3.11 und `ffmpeg` im Systempfad.

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

## API & WebSocket

- `GET /` → Frontend
- `GET /api/health` → `{"status":"ok","model":"<name>"}`
- `GET /api/models` → verfügbare Modelle
- `WS /ws/transcribe?language=<code>&model=<name>`
  - `{"type":"partial","text":"..."}`
  - `{"type":"final","text":"..."}`
  - `{"type":"error","message":"..."}`

## Konfiguration (ENV)

| Variable | Standard | Beschreibung |
|---|---|---|
| `WHISPER_MODEL` | `small` | Startmodell |
| `WHISPER_DEVICE` | `cpu` | `cpu` oder `cuda` |
| `WHISPER_COMPUTE_TYPE` | `int8` (CPU) / `float16` (CUDA) | Compute-Type |
| `WHISPER_AVAILABLE_MODELS` | `tiny,base,small,medium,large-v3` | Modellliste im UI |
| `VAD_AGGRESSIVENESS` | `2` | VAD-Stufe (0-3) |
| `VAD_SILENCE_MS` | `700` | Pause bis Segment-Ende |
| `VAD_MAX_SEGMENT_SECONDS` | `8` | Maximale Segmentdauer |
| `WS_PARTIAL_INTERVAL_SECONDS` | `1.2` | Intervall für Zwischenergebnisse |

## Zugriff von anderen Geräten (HTTPS-Hinweis)

Mikrofonzugriff im Browser erfordert i. d. R. **HTTPS** (Ausnahme: `localhost`). Für öffentliche Bereitstellung empfiehlt sich ein Reverse-Proxy (z. B. Caddy, Traefik, Nginx) oder Cloudflare Tunnel.

### Beispiel Caddyfile

```caddy
voicepilot.example.com {
    reverse_proxy 127.0.0.1:8000
}
```

## Nutzung

1. URL öffnen
2. Sprache & Modell auswählen
3. Mic-Button drücken
4. Zwischen- und Endtexte live sehen
5. Mit „Kopieren“ oder „Download .txt“ exportieren

## Screenshots

- Platzhalter: `docs/screenshot-main.png` (bei Bedarf ergänzen)

## Bekannte Einschränkungen

- iOS Safari unterstützt je nach Version `MediaRecorder`-Formate unterschiedlich (`audio/webm` ggf. nicht verfügbar; Fallback auf `audio/mp4` ist implementiert).
- Erste Modellinitialisierung kann deutlich länger dauern (Download + Warmup).
- Für beste Qualität kann `medium`/`large-v3` genutzt werden, benötigt aber mehr CPU/GPU-Ressourcen.
