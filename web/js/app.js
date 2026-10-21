/**
 * Quran Recitation Tutor Frontend Application.
 * Handles AudioWorklet capture, WebSocket streaming, live Mushaf highlighting,
 * and teacher audio prompt playback.
 */

// Arabic numerals converter (e.g. 1 -> ١)
const toArabicNumerals = (num) => {
    const arabicDigits = ['٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'];
    return String(num).replace(/[0-9]/g, (d) => arabicDigits[d]);
};

class QuranTutorApp {
    constructor() {
        this.surahId = 1;
        this.wordsData = [];
        this.ws = null;
        this.audioContext = null;
        this.workletNode = null;
        this.mediaStream = null;
        this.isRecording = false;

        // Statistics
        this.stats = { matched: 0, mistakes: 0, prompts: 0, peeks: 0 };
        this.currentSessionMistakes = [];
        this.sessionStartTime = null;

        // DOM elements
        this.btnRecord = document.getElementById("btn-record");
        this.btnIcon = document.getElementById("btn-icon");
        this.btnText = document.getElementById("btn-text");
        this.statusDot = document.getElementById("status-dot");
        this.statusText = document.getElementById("status-text");
        this.promptBanner = document.getElementById("prompt-banner");
        this.micStatus = document.getElementById("mic-status");
        this.mushafBody = document.getElementById("mushaf-body");
        this.audioPlayer = document.getElementById("prompt-audio-player");
        this.selectQari = document.getElementById("select-qari");
        this.selectMode = document.getElementById("select-mode");
        this.promptWordsInput = document.getElementById("prompt-words");
        this.toggleMemorize = document.getElementById("toggle-memorize");
        this.historyList = document.getElementById("history-list");

        this.init();
    }

    async init() {
        await this.loadSurah(this.surahId);
        await this.loadHistory();
        this.btnRecord.addEventListener("click", () => this.toggleRecording());
        this.toggleMemorize.addEventListener("change", () => this.applyMemorizeMode());
    }

    async loadHistory() {
        try {
            const resp = await fetch("/api/sessions/history");
            const data = await resp.json();
            const list = data.history || [];
            if (list.length === 0) {
                this.historyList.innerHTML = "No previous sessions logged yet. Complete a recitation to record history.";
                return;
            }

            let html = `<table style="width: 100%; text-align: left; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid var(--border-color); color: var(--text-primary);">
                    <th style="padding: 6px 0;">Date</th>
                    <th>Matched</th>
                    <th>Mistakes</th>
                    <th>Prompts</th>
                    <th>Peeks</th>
                    <th>Accuracy</th>
                </tr>`;

            list.forEach((s) => {
                const dateStr = new Date(s.start_time * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', month: 'short', day: 'numeric' });
                html += `<tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                    <td style="padding: 6px 0;">${dateStr}</td>
                    <td>${s.total_words_matched}</td>
                    <td style="color: var(--color-mistake);">${s.total_mistakes}</td>
                    <td style="color: var(--color-prompt);">${s.total_prompts}</td>
                    <td>${s.total_peeks}</td>
                    <td><b>${s.accuracy.toFixed(1)}%</b></td>
                </tr>`;
            });
            html += `</table>`;
            this.historyList.innerHTML = html;
        } catch (e) {
            console.warn("Could not load history:", e);
        }
    }

    async loadSurah(surahId) {
        try {
            const resp = await fetch(`/api/surah/${surahId}`);
            const data = await resp.json();
            this.wordsData = data.words;
            this.renderMushaf(data);
        } catch (err) {
            console.error("Failed to load Surah:", err);
            this.mushafBody.innerHTML = `<div style="color: var(--color-mistake);">Failed to load Quran text.</div>`;
        }
    }

    renderMushaf(data) {
        this.mushafBody.innerHTML = "";
        let currentAyah = null;
        let ayahContainer = null;

        data.words.forEach((w) => {
            if (w.ayah !== currentAyah) {
                // If ending previous ayah, add ayah marker
                if (ayahContainer && currentAyah !== null) {
                    const marker = document.createElement("span");
                    marker.className = "ayah-end-marker";
                    marker.textContent = ` ۝${toArabicNumerals(currentAyah)} `;
                    ayahContainer.appendChild(marker);
                }

                currentAyah = w.ayah;
                ayahContainer = document.createElement("div");
                ayahContainer.className = "quran-ayah";
                ayahContainer.id = `ayah-${w.surah}-${w.ayah}`;
                this.mushafBody.appendChild(ayahContainer);
            }

            const wordSpan = document.createElement("span");
            wordSpan.className = "quran-word";
            wordSpan.id = `word-${w.surah}-${w.ayah}-${w.word_index_in_ayah}`;
            wordSpan.textContent = w.text_uthmani;
            wordSpan.dataset.surah = w.surah;
            wordSpan.dataset.ayah = w.ayah;
            wordSpan.dataset.word = w.word_index_in_ayah;

            wordSpan.addEventListener("click", () => this.onWordClick(wordSpan));
            ayahContainer.appendChild(wordSpan);
        });

        // Add final ayah marker
        if (ayahContainer && currentAyah !== null) {
            const marker = document.createElement("span");
            marker.className = "ayah-end-marker";
            marker.textContent = ` ۝${toArabicNumerals(currentAyah)} `;
            ayahContainer.appendChild(marker);
        }
    }

    onWordClick(wordSpan) {
        if (wordSpan.classList.contains("word-hidden")) {
            wordSpan.classList.remove("word-hidden");
            this.stats.peeks += 1;
            document.getElementById("stat-peeks").textContent = this.stats.peeks;

            // Record PEEKED_WORDS in session mistakes
            this.currentSessionMistakes.push({
                mistake_type: "PEEKED_WORDS",
                surah: parseInt(wordSpan.dataset.surah, 10),
                ayah: parseInt(wordSpan.dataset.ayah, 10),
                word: parseInt(wordSpan.dataset.word, 10),
                expected_text: wordSpan.textContent,
                received_text: "[PEEKED]",
                timestamp: Math.floor(Date.now() / 1000),
            });
        }
    }

    applyMemorizeMode() {
        const isMemorizing = this.toggleMemorize.checked;
        const allWords = document.querySelectorAll(".quran-word");
        allWords.forEach((el) => {
            if (isMemorizing && !el.classList.contains("word-matched")) {
                el.classList.add("word-hidden");
            } else {
                el.classList.remove("word-hidden");
            }
        });
    }

    async toggleRecording() {
        if (this.isRecording) {
            await this.stopRecording();
        } else {
            await this.startRecording();
        }
    }

    async startRecording() {
        try {
            this.sessionStartTime = Math.floor(Date.now() / 1000);
            this.currentSessionMistakes = [];
            this.stats = { matched: 0, mistakes: 0, prompts: 0, peeks: 0 };
            document.getElementById("stat-matched").textContent = "0";
            document.getElementById("stat-mistakes").textContent = "0";
            document.getElementById("stat-prompts").textContent = "0";
            document.getElementById("stat-peeks").textContent = "0";

            this.statusText.textContent = "Connecting to local ASR engine...";
            this.statusDot.className = "status-dot active";

            // Initialize AudioContext & AudioWorklet
            const AudioCtx = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioCtx({ sampleRate: 16000 });
            await this.audioContext.audioWorklet.addModule("/static/js/audio_worklet.js");

            // Capture raw microphone with DSP explicitly disabled
            this.mediaStream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    echoCancellation: false,
                    noiseSuppression: false,
                    autoGainControl: false,
                    channelCount: 1,
                    sampleRate: 16000,
                },
            });

            const sourceNode = this.audioContext.createMediaStreamSource(this.mediaStream);
            this.workletNode = new AudioWorkletNode(this.audioContext, "pcm-audio-processor");

            // Connect AudioWorklet to capture stream
            sourceNode.connect(this.workletNode);
            // Connect to dummy destination so processing runs
            const dummyGain = this.audioContext.createGain();
            dummyGain.gain.value = 0;
            this.workletNode.connect(dummyGain);
            dummyGain.connect(this.audioContext.destination);

            // Open WebSocket connection
            const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
            this.ws = new WebSocket(`${protocol}//${window.location.host}/ws/recite`);
            this.ws.binaryType = "arraybuffer";

            this.ws.onopen = () => {
                this.isRecording = true;
                this.btnRecord.classList.add("recording");
                this.btnIcon.textContent = "⏹️";
                this.btnText.textContent = "Stop Reciting";
                this.statusText.textContent = "Listening... Recite Al-Fatiha.";
                this.micStatus.textContent = "Mic: Active";

                // Send Start Session configuration
                this.ws.send(JSON.stringify({
                    event: "START_SESSION",
                    surah: this.surahId,
                    reciter: this.selectQari.value,
                    prompt_words: parseInt(this.promptWordsInput.value, 10),
                    mode: this.selectMode.value,
                    start_ayah: 1,
                }));

                // Forward AudioWorklet chunks directly over WebSocket
                this.workletNode.port.onmessage = (event) => {
                    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                        this.ws.send(event.data);
                    }
                };
            };

            this.ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                this.handleServerMessage(msg);
            };

            this.ws.onclose = () => {
                console.log("WebSocket disconnected.");
                if (this.isRecording) {
                    this.stopRecording();
                }
            };

        } catch (err) {
            console.error("Microphone access or WebSocket error:", err);
            this.statusText.textContent = `Mic error: ${err.message}`;
            this.statusDot.className = "status-dot";
        }
    }

    async stopRecording() {
        this.isRecording = false;
        this.btnRecord.classList.remove("recording");
        this.btnIcon.textContent = "🎙️";
        this.btnText.textContent = "Start Reciting";
        this.statusText.textContent = "Recitation paused.";
        this.statusDot.className = "status-dot";
        this.micStatus.textContent = "Mic: Idle";

        const sessionEndTime = Math.floor(Date.now() / 1000);

        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ event: "STOP_SESSION" }));
            this.ws.close();
        }

        if (this.mediaStream) {
            this.mediaStream.getTracks().forEach((t) => t.stop());
            this.mediaStream = null;
        }

        if (this.audioContext) {
            await this.audioContext.close();
            this.audioContext = null;
        }

        // Save session to SQLite database
        if (this.sessionStartTime && (this.stats.matched > 0 || this.stats.mistakes > 0 || this.stats.peeks > 0)) {
            const totalWords = this.stats.matched + this.stats.mistakes;
            const accuracy = totalWords > 0 ? (this.stats.matched / totalWords) * 100.0 : 0.0;
            try {
                await fetch("/api/sessions/save", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        surah: this.surahId,
                        start_time: this.sessionStartTime,
                        end_time: sessionEndTime,
                        total_words_matched: this.stats.matched,
                        total_mistakes: this.stats.mistakes,
                        total_prompts: this.stats.prompts,
                        total_peeks: this.stats.peeks,
                        accuracy: accuracy,
                        mistakes: this.currentSessionMistakes,
                    }),
                });
                await this.loadHistory();
            } catch (err) {
                console.warn("Could not save session to SQLite:", err);
            }
        }
    }

    handleServerMessage(msg) {
        const ev = msg.event;

        if (ev === "WORD_MATCH") {
            const wordEl = document.getElementById(`word-${msg.surah}-${msg.ayah}-${msg.word}`);
            if (wordEl) {
                wordEl.classList.remove("word-hidden", "word-mistake", "word-prompted");
                wordEl.classList.add("word-matched");
                this.statusText.textContent = `Reciting: ${msg.text_uthmani}`;
            }
            this.stats.matched += 1;
            document.getElementById("stat-matched").textContent = this.stats.matched;

        } else if (ev === "PAUSE_MIC") {
            // Immediately gate the microphone to prevent self-prompt feedback
            if (this.workletNode) {
                this.workletNode.port.postMessage({ action: "MUTE" });
            }
            this.micStatus.textContent = "Mic: Paused (Prompting)";
            this.statusDot.className = "status-dot prompting";

        } else if (ev === "PLAY_PROMPT") {
            this.stats.prompts += 1;
            document.getElementById("stat-prompts").textContent = this.stats.prompts;

            // Highlight the prompted word in Mushaf
            const wordEl = document.getElementById(`word-${msg.surah}-${msg.ayah}-${msg.word}`);
            if (wordEl) {
                wordEl.classList.remove("word-hidden");
                wordEl.classList.add("word-prompted");
            }

            // Show prompt banner
            this.promptBanner.classList.add("show");
            this.statusText.textContent = `Teacher prompting: ${msg.prompt_text}`;

            // Play the audio
            const audioBlob = this.base64ToBlob(msg.audio_b64, "audio/wav");
            const audioUrl = URL.createObjectURL(audioBlob);
            this.audioPlayer.src = audioUrl;
            this.audioPlayer.play().catch((e) => console.warn("Audio play prevented:", e));

            this.audioPlayer.onended = () => {
                this.promptBanner.classList.remove("show");
                URL.revokeObjectURL(audioUrl);
                // Inform backend prompt completed
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ event: "PROMPT_FINISHED" }));
                }
            };

        } else if (ev === "RESUME_MIC") {
            if (this.workletNode) {
                this.workletNode.port.postMessage({ action: "UNMUTE" });
            }
            this.micStatus.textContent = "Mic: Active";
            this.statusDot.className = "status-dot active";
            this.statusText.textContent = "Continue reciting...";

        } else if (ev === "BUZZER_ALERT") {
            this.playBuzzerSound();
            this.stats.mistakes += 1;
            document.getElementById("stat-mistakes").textContent = this.stats.mistakes;

        } else if (ev === "SILENT_HIGHLIGHT") {
            const wordEl = document.getElementById(`word-${msg.surah}-${msg.ayah}-${msg.word}`);
            if (wordEl) {
                wordEl.classList.add("word-mistake");
            }
            this.stats.mistakes += 1;
            document.getElementById("stat-mistakes").textContent = this.stats.mistakes;
        }
    }

    playBuzzerSound() {
        if (!this.audioContext) return;
        const osc = this.audioContext.createOscillator();
        const gain = this.audioContext.createGain();
        osc.type = "sawtooth";
        osc.frequency.setValueAtTime(160, this.audioContext.currentTime); // Low buzz
        gain.gain.setValueAtTime(0.2, this.audioContext.currentTime);
        gain.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + 0.35);
        osc.connect(gain);
        gain.connect(this.audioContext.destination);
        osc.start();
        osc.stop(this.audioContext.currentTime + 0.35);
    }

    base64ToBlob(base64Data, contentType) {
        const byteCharacters = atob(base64Data);
        const byteArrays = [];
        for (let offset = 0; offset < byteCharacters.length; offset += 512) {
            const slice = byteCharacters.slice(offset, offset + 512);
            const byteNumbers = new Array(slice.length);
            for (let i = 0; i < slice.length; i++) {
                byteNumbers[i] = slice.charCodeAt(i);
            }
            byteArrays.push(new Uint8Array(byteNumbers));
        }
        return new Blob(byteArrays, { type: contentType });
    }
}

// Start application when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    window.quranTutorApp = new QuranTutorApp();
});
