const statusElement = document.getElementById("status");
const micButton = document.getElementById("micButton");
const languageSelect = document.getElementById("languageSelect");
const modelSelect = document.getElementById("modelSelect");
const finalTextElement = document.getElementById("finalText");
const partialTextElement = document.getElementById("partialText");
const copyButton = document.getElementById("copyButton");
const downloadButton = document.getElementById("downloadButton");
const clearButton = document.getElementById("clearButton");

let websocket = null;
let mediaRecorder = null;
let mediaStream = null;
let reconnectTimeout = null;
let isRecording = false;
let finalLines = [];
let partialLine = "";

function setStatus(message, type = "info") {
  statusElement.textContent = message;
  statusElement.dataset.type = type;
}

function renderTranscript() {
  finalTextElement.textContent = finalLines.join(" ").trim();
  partialTextElement.textContent = partialLine;
}

function getWebSocketUrl() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const params = new URLSearchParams({
    language: languageSelect.value,
    model: modelSelect.value || "small",
  });
  return `${protocol}://${window.location.host}/ws/transcribe?${params.toString()}`;
}

async function loadModels() {
  try {
    const response = await fetch("/api/models");
    const data = await response.json();
    modelSelect.innerHTML = "";

    for (const model of data.models || []) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      if (model === "small") {
        option.selected = true;
      }
      modelSelect.appendChild(option);
    }
  } catch (error) {
    setStatus(`Modellliste konnte nicht geladen werden: ${error.message}`, "error");
  }
}

function connectWebSocket() {
  if (websocket && (websocket.readyState === WebSocket.OPEN || websocket.readyState === WebSocket.CONNECTING)) {
    return;
  }

  websocket = new WebSocket(getWebSocketUrl());

  websocket.onopen = () => {
    setStatus(isRecording ? "Verbunden & aufnehmend" : "Verbunden", "ok");
  };

  websocket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    if (data.type === "partial") {
      partialLine = data.text || "";
      renderTranscript();
    } else if (data.type === "final") {
      if (data.text) {
        finalLines.push(data.text);
      }
      partialLine = "";
      renderTranscript();
    } else if (data.type === "error") {
      setStatus(`Fehler: ${data.message}`, "error");
    }
  };

  websocket.onclose = () => {
    websocket = null;
    if (isRecording) {
      setStatus("Verbindung verloren – Reconnect...", "warn");
      reconnectTimeout = window.setTimeout(connectWebSocket, 1500);
    } else {
      setStatus("Getrennt", "warn");
    }
  };

  websocket.onerror = () => {
    setStatus("WebSocket-Fehler", "error");
  };
}

function chooseMimeType() {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/mp4"];
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || "";
}

async function startRecording() {
  try {
    mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    connectWebSocket();

    const mimeType = chooseMimeType();
    mediaRecorder = mimeType ? new MediaRecorder(mediaStream, { mimeType }) : new MediaRecorder(mediaStream);

    mediaRecorder.ondataavailable = async (event) => {
      if (!event.data || event.data.size === 0) {
        return;
      }
      if (!websocket || websocket.readyState !== WebSocket.OPEN) {
        return;
      }
      const arrayBuffer = await event.data.arrayBuffer();
      websocket.send(arrayBuffer);
    };

    mediaRecorder.start(500);
    isRecording = true;
    micButton.classList.add("recording");
    setStatus("Aufnahme läuft", "ok");
  } catch (error) {
    setStatus(`Mikrofonzugriff fehlgeschlagen: ${error.message}`, "error");
  }
}

function stopRecording() {
  isRecording = false;
  if (reconnectTimeout) {
    window.clearTimeout(reconnectTimeout);
    reconnectTimeout = null;
  }

  if (mediaRecorder && mediaRecorder.state !== "inactive") {
    mediaRecorder.stop();
  }

  if (mediaStream) {
    mediaStream.getTracks().forEach((track) => track.stop());
  }

  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.close();
  }

  micButton.classList.remove("recording");
  setStatus("Bereit", "info");
}

micButton.addEventListener("click", async () => {
  if (isRecording) {
    stopRecording();
  } else {
    await startRecording();
  }
});

copyButton.addEventListener("click", async () => {
  const content = `${finalLines.join(" ")} ${partialLine}`.trim();
  if (!content) {
    return;
  }

  try {
    await navigator.clipboard.writeText(content);
    setStatus("Transkript kopiert", "ok");
  } catch (error) {
    setStatus(`Kopieren fehlgeschlagen: ${error.message}`, "error");
  }
});

downloadButton.addEventListener("click", () => {
  const content = `${finalLines.join(" ")} ${partialLine}`.trim();
  const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "voicepilot-transkript.txt";
  link.click();
  URL.revokeObjectURL(url);
});

clearButton.addEventListener("click", () => {
  finalLines = [];
  partialLine = "";
  renderTranscript();
  setStatus("Transkript gelöscht", "info");
});

modelSelect.addEventListener("change", () => {
  if (isRecording) {
    stopRecording();
    startRecording();
  }
});

languageSelect.addEventListener("change", () => {
  if (isRecording) {
    stopRecording();
    startRecording();
  }
});

loadModels();
renderTranscript();
