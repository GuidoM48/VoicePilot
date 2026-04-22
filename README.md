# VoicePilot

VoicePilot ist eine einfache Web-App mit 3 Sprach-Modi und 4 Agenten.

## Features

- **Modus 1 – 1:1 Mitschrift**: Gesprochenen Text unverändert ausgeben.
- **Modus 2 – Neu formulieren**: Gesprochenen Text als sauberen geschriebenen Satz darstellen.
- **Modus 3 – Positiv darstellen**: Schimpfwörter/negative Begriffe in eine positive Form bringen.
- **Tastensteuerung**: Mit **R** Aufnahme starten/stoppen.

## 4 Agenten

1. `RecorderAgent` – übernimmt Aufnahme + Speech-to-Text (Web Speech API).
2. `DictationAgent` – gibt den Text 1:1 zurück.
3. `RewriteAgent` – formatiert den gesprochenen Text zu lesbarem Text.
4. `PositivityAgent` – ersetzt negative Begriffe und formatiert das Ergebnis.

## Start

Da es eine statische Web-App ist, reicht ein lokaler HTTP-Server:

```bash
cd /home/runner/work/VoicePilot/VoicePilot
python3 -m http.server 8000
```

Dann im Browser öffnen:

`http://localhost:8000`

> Hinweis: Für die Spracherkennung wird ein Browser mit Web Speech API benötigt (z. B. Chrome oder Edge).
