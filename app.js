const modeSelect = document.getElementById("mode");
const statusEl = document.getElementById("status");
const rawTextEl = document.getElementById("rawText");
const outputTextEl = document.getElementById("outputText");

class RecorderAgent {
  constructor(onTranscript, onStatus) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      this.available = false;
      this.onTranscript = onTranscript;
      this.onStatus = onStatus;
      this.onStatus("Spracherkennung nicht verfügbar. Bitte Chrome/Edge verwenden.");
      return;
    }

    this.available = true;
    this.onTranscript = onTranscript;
    this.onStatus = onStatus;
    this.isRecording = false;
    this.buffer = "";

    this.recognition = new SpeechRecognition();
    this.recognition.lang = "de-DE";
    this.recognition.continuous = true;
    this.recognition.interimResults = false;

    this.recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        if (event.results[i].isFinal) {
          this.buffer += `${event.results[i][0].transcript.trim()} `;
        }
      }
    };

    this.recognition.onerror = (event) => {
      this.onStatus(`Fehler bei der Spracherkennung: ${event.error}`);
      this.isRecording = false;
    };

    this.recognition.onend = () => {
      if (!this.isRecording) {
        const finalText = this.buffer.trim();
        this.buffer = "";
        if (finalText) {
          this.onTranscript(finalText);
        }
        this.onStatus("Bereit");
      }
    };
  }

  toggle() {
    if (!this.available) {
      this.onStatus("Spracherkennung nicht verfügbar. Bitte Chrome/Edge verwenden.");
      return;
    }

    if (this.isRecording) {
      this.isRecording = false;
      this.recognition.stop();
      this.onStatus("Aufnahme wird beendet...");
      return;
    }

    this.buffer = "";
    this.isRecording = true;
    this.recognition.start();
    this.onStatus("Aufnahme läuft... (nochmal R zum Stoppen)");
  }
}

class DictationAgent {
  process(text) {
    return text;
  }
}

class RewriteAgent {
  process(text) {
    const normalized = text.replace(/\s+/g, " ").trim();
    if (!normalized) {
      return "";
    }
    const withUppercase = normalized.charAt(0).toUpperCase() + normalized.slice(1);
    return /[.!?]$/.test(withUppercase) ? withUppercase : `${withUppercase}.`;
  }
}

class PositivityAgent {
  constructor() {
    this.map = {
      scheiße: "nicht optimal",
      scheisse: "nicht optimal",
      scheiß: "ungünstig",
      dumm: "noch ausbaufähig",
      idiot: "Mensch mit Potenzial",
      hasse: "mag ich gerade nicht",
      schlimm: "herausfordernd",
      schlecht: "verbesserbar",
      problem: "Chance zur Verbesserung",
      nervt: "fordert Geduld"
    };
    this.rewriteAgent = new RewriteAgent();
  }

  process(text) {
    let output = text;
    Object.entries(this.map).forEach(([negative, positive]) => {
      const pattern = new RegExp(`\\b${negative}\\b`, "gi");
      output = output.replace(pattern, positive);
    });
    return this.rewriteAgent.process(output);
  }
}

const agents = {
  dictation: new DictationAgent(),
  rewrite: new RewriteAgent(),
  positive: new PositivityAgent()
};

const recorder = new RecorderAgent(
  (transcript) => {
    rawTextEl.value = transcript;
    const mode = modeSelect.value;
    outputTextEl.value = agents[mode].process(transcript);
  },
  (message) => {
    statusEl.textContent = message;
  }
);

document.addEventListener("keydown", (event) => {
  if (event.key.toLowerCase() === "r" && !event.repeat) {
    event.preventDefault();
    recorder.toggle();
  }
});
