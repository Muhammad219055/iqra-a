"""
WebSocket Recitation Streaming Handler.
Manages bidirectional real-time audio ingestion, ASR tracking, hesitation detection,
and teacher audio prompting with automatic mic gating.
"""

import asyncio
import base64
import io
import json
import time
from typing import Optional
import numpy as np
import soundfile as sf
from fastapi import WebSocket, WebSocketDisconnect

from src.aligner.tracker import RecitationTracker
from src.aligner.hesitation import HesitationDetector
from src.aligner.normalizer import tokenize_words
from src.asr.engine import QuranASREngine
from src.asr.vad import SimpleVAD
from src.audio.slicer import QuranAudioSlicer
from scripts.download_quran_text import download_surah_words


class RecitationSession:
    def __init__(self, websocket: WebSocket, asr_engine: QuranASREngine):
        self.ws = websocket
        self.asr = asr_engine
        self.vad = SimpleVAD()

        # Session configuration
        self.surah = 1
        self.reciter = "mishari"
        self.prompt_words = 3
        self.mode = "prompt"  # "prompt" | "buzzer" | "silent"

        # Components initialized on START_SESSION
        self.tracker: Optional[RecitationTracker] = None
        self.hesitation: Optional[HesitationDetector] = None
        self.slicer: Optional[QuranAudioSlicer] = None

        # Audio stream buffer
        self.audio_buffer = bytearray()
        self.is_active = False
        self.is_prompting = False
        self.lock = asyncio.Lock()

    async def run(self):
        await self.ws.accept()
        print("WebSocket client connected.")

        try:
            # Background task to monitor hesitation
            hesitation_task = asyncio.create_task(self._hesitation_loop())

            while True:
                message = await self.ws.receive()

                if "text" in message:
                    payload = json.loads(message["text"])
                    await self._handle_client_event(payload)

                elif "bytes" in message:
                    if self.is_active and not self.is_prompting:
                        pcm_chunk = message["bytes"]
                        await self._handle_audio_chunk(pcm_chunk)

        except WebSocketDisconnect:
            print("WebSocket client disconnected.")
        except Exception as e:
            print(f"WebSocket session error: {e}")
        finally:
            self.is_active = False
            hesitation_task.cancel()

    async def _handle_client_event(self, payload: dict):
        event = payload.get("event")

        if event == "START_SESSION":
            self.surah = payload.get("surah", 1)
            self.reciter = payload.get("reciter", "mishari")
            self.prompt_words = payload.get("prompt_words", 3)
            self.mode = payload.get("mode", "prompt")
            start_ayah = payload.get("start_ayah", 1)

            # Load Quran text
            text_data = download_surah_words(self.surah)
            self.tracker = RecitationTracker(text_data["words"], start_ayah=start_ayah)
            self.hesitation = HesitationDetector()
            self.slicer = QuranAudioSlicer(surah=self.surah, reciter=self.reciter)

            self.audio_buffer.clear()
            self.is_active = True
            self.is_prompting = False

            await self.ws.send_json({
                "event": "SESSION_STARTED",
                "surah": self.surah,
                "reciter": self.reciter,
                "current_word": self.tracker.current_expected_word,
            })
            print(f"Session started: Surah {self.surah}, Reciter {self.reciter}, Mode {self.mode}")

        elif event == "STOP_SESSION":
            self.is_active = False
            await self.ws.send_json({"event": "SESSION_STOPPED"})

        elif event == "PROMPT_FINISHED":
            # Client finished playing teacher prompt
            print("Client finished playing prompt. Cooling down 150ms before resuming mic...")
            await asyncio.sleep(0.15)  # 150ms echo drain
            self.audio_buffer.clear()
            if self.hesitation:
                self.hesitation.reset_timer()
            self.is_prompting = False
            await self.ws.send_json({"event": "RESUME_MIC"})

    async def _handle_audio_chunk(self, chunk: bytes):
        self.audio_buffer.extend(chunk)

        # Check speech activity with VAD
        if self.vad.is_speech(chunk) and self.hesitation:
            self.hesitation.on_speech_active()

        # Stream ~1.2s to 1.8s audio buffers (16kHz 16-bit mono = 32,000 bytes/sec)
        # 40,000 bytes ~= 1.25 seconds
        if len(self.audio_buffer) >= 40000:
            buffer_to_process = bytes(self.audio_buffer)
            # Keep 8000 bytes (250ms) overlap for smooth boundary transition
            self.audio_buffer = self.audio_buffer[-8000:]

            # Run ASR in thread pool to not block asyncio event loop
            asyncio.create_task(self._process_audio_async(buffer_to_process))

    async def _process_audio_async(self, pcm_bytes: bytes):
        if self.is_prompting or not self.tracker:
            return

        async with self.lock:
            loop = asyncio.get_running_loop()
            samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0

            transcription = await loop.run_in_executor(
                None, lambda: self.asr.transcribe(samples, sample_rate=16000)
            )

            raw_text = transcription.get("text", "").strip()
            if not raw_text:
                return

            tokens = tokenize_words(raw_text)
            if not tokens:
                return

            events, mistake = self.tracker.process_recognized_tokens(tokens)

            for ev in events:
                if self.hesitation:
                    self.hesitation.on_word_progress()
                await self.ws.send_json(ev)

            if mistake and not self.is_prompting:
                await self._trigger_prompt_or_alert(mistake)

    async def _hesitation_loop(self):
        """Monitors pause/hesitation duration and triggers prompt if stuck."""
        while True:
            await asyncio.sleep(0.2)
            if self.is_active and not self.is_prompting and self.hesitation and self.tracker:
                current_word = self.tracker.current_expected_word
                hesitation_event = self.hesitation.check_hesitation(current_word)
                if hesitation_event:
                    print(f"Hesitation detected! Stuck at: {hesitation_event['text_uthmani']}")
                    await self._trigger_prompt_or_alert(hesitation_event)

    async def _trigger_prompt_or_alert(self, trigger_info: dict):
        self.is_prompting = True
        self.audio_buffer.clear()

        # Send instant PAUSE_MIC command to browser
        await self.ws.send_json({"event": "PAUSE_MIC"})

        surah = trigger_info.get("surah", self.surah)
        ayah = trigger_info.get("ayah", 1)
        word = trigger_info.get("word", 1)

        print(f"Triggering Prompt at {surah}:{ayah}:{word} (Mode: {self.mode})...")

        if self.mode == "prompt" and self.slicer:
            try:
                loop = asyncio.get_running_loop()
                prompt_res = await loop.run_in_executor(
                    None,
                    lambda: self.slicer.slice_prompt(
                        ayah=ayah,
                        word=word,
                        prompt_length=self.prompt_words,
                    )
                )

                # Convert float32 samples to 16-bit PCM WAV in memory
                wav_io = io.BytesIO()
                sf.write(wav_io, prompt_res["audio_samples"], prompt_res["sample_rate"], format="WAV", subtype="PCM_16")
                audio_b64 = base64.b64encode(wav_io.getvalue()).decode("utf-8")

                await self.ws.send_json({
                    "event": "PLAY_PROMPT",
                    "trigger_type": trigger_info.get("event"),
                    "surah": surah,
                    "ayah": ayah,
                    "word": word,
                    "prompt_text": prompt_res["prompted_text_uthmani"],
                    "duration_ms": prompt_res["duration_ms"],
                    "audio_b64": audio_b64,
                })

                # Reset tracker cursor back to the prompted word so user repeats it
                if self.tracker:
                    self.tracker.reset_to_word(ayah, word)

            except Exception as e:
                print(f"Error slicing prompt: {e}")
                self.is_prompting = False
                await self.ws.send_json({"event": "RESUME_MIC"})

        elif self.mode == "buzzer":
            await self.ws.send_json({
                "event": "BUZZER_ALERT",
                "trigger_type": trigger_info.get("event"),
                "surah": surah,
                "ayah": ayah,
                "word": word,
            })
            await asyncio.sleep(0.5)
            self.is_prompting = False
            await self.ws.send_json({"event": "RESUME_MIC"})

        elif self.mode == "silent":
            await self.ws.send_json({
                "event": "SILENT_HIGHLIGHT",
                "trigger_type": trigger_info.get("event"),
                "surah": surah,
                "ayah": ayah,
                "word": word,
            })
            self.is_prompting = False
            await self.ws.send_json({"event": "RESUME_MIC"})
