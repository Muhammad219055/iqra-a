"""
Word-Level Quran Audio Slicer.
Given {surah, ayah, word} and prompt_length (e.g. 3 words: N to N+2),
slices the exact audio segment from locally cached Qari recitations.
Applies cosine fade-in/fade-out to eliminate boundary clicks.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import numpy as np
import soundfile as sf
import subprocess

from scripts.download_audio_data import download_surah_audio
from scripts.download_quran_text import download_surah_words


class QuranAudioSlicer:
    def __init__(self, surah: int = 1, reciter: str = "mishari", base_dir: str = "."):
        self.surah = surah
        self.reciter = reciter.lower()
        self.base_dir = Path(base_dir)

        self.audio_cache_dir = self.base_dir / "data" / "audio_cache" / self.reciter
        self.timing_dir = self.base_dir / "data" / "timings"
        self.text_dir = self.base_dir / "data" / "text"

        self.mp3_path = self.audio_cache_dir / f"{self.surah:03d}.mp3"
        self.wav_path = self.audio_cache_dir / f"{self.surah:03d}_16k.wav"
        self.timing_path = self.timing_dir / f"surah_{self.surah}_{self.reciter}.json"
        self.text_path = self.text_dir / f"quran_surah_{self.surah}.json"

        # Ensure all data and audio are downloaded and cached
        self._ensure_data_ready()

        # Load metadata and build unified word timing map
        self._load_words_and_timings()

        # Cache audio data in memory for instantaneous slicing (<5ms)
        self.audio_data, self.sr = sf.read(str(self.wav_path))

    def _ensure_data_ready(self):
        """Ensures text, timings, MP3, and 16kHz WAV are ready."""
        if not self.text_path.exists():
            download_surah_words(self.surah, str(self.text_path))

        if not self.timing_path.exists() or not self.mp3_path.exists():
            download_surah_audio(self.surah, self.reciter)

        # Convert MP3 to 16kHz mono WAV if not already converted
        if not self.wav_path.exists():
            print(f"Converting {self.mp3_path} to 16kHz mono WAV {self.wav_path}...")
            subprocess.run([
                "/opt/homebrew/bin/ffmpeg", "-y", "-i", str(self.mp3_path),
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(self.wav_path)
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _load_words_and_timings(self):
        """Builds a contiguous list of words with timing intervals."""
        with open(self.text_path, "r", encoding="utf-8") as f:
            text_data = json.load(f)

        with open(self.timing_path, "r", encoding="utf-8") as f:
            timing_data = json.load(f)

        # Map verse timings: {"1:1": [[w_idx, start_ms, end_ms], ...]}
        verse_segments: Dict[str, List[Tuple[int, float, float]]] = {}
        for item in timing_data.get("timestamps", []):
            v_key = item.get("verse_key")
            valid_segs = []
            for s in item.get("segments", []):
                if isinstance(s, list) and len(s) >= 3:
                    valid_segs.append((int(s[0]), float(s[1]), float(s[2])))
            verse_segments[v_key] = valid_segs

        # Merge with Quran text words
        self.words: List[dict] = []
        for w in text_data.get("words", []):
            surah = w["surah"]
            ayah = w["ayah"]
            w_idx = w["word_index_in_ayah"]
            v_key = f"{surah}:{ayah}"

            start_ms, end_ms = None, None
            if v_key in verse_segments:
                for seg_w_idx, s_ms, e_ms in verse_segments[v_key]:
                    if seg_w_idx == w_idx:
                        start_ms, end_ms = s_ms, e_ms
                        break

            word_entry = dict(w)
            word_entry["start_ms"] = start_ms
            word_entry["end_ms"] = end_ms
            self.words.append(word_entry)

    def find_word_index(self, ayah: int, word: int) -> int:
        """Finds the index in self.words matching {ayah, word}."""
        for idx, w in enumerate(self.words):
            if w["ayah"] == ayah and w["word_index_in_ayah"] == word:
                return idx
        raise ValueError(f"Word not found: Ayah {ayah}, Word {word} in Surah {self.surah}")

    def slice_prompt(
        self,
        ayah: int,
        word: int,
        prompt_length: int = 3,
        output_file: Optional[Path] = None,
    ) -> dict:
        """
        Slices audio for words [N : N + prompt_length].
        Returns metadata dict with sliced audio array, duration, and prompted words.
        """
        start_idx = self.find_word_index(ayah, word)
        end_idx = min(start_idx + prompt_length, len(self.words))
        prompted_words = self.words[start_idx:end_idx]

        # Determine start and end timestamps in milliseconds
        first_word = prompted_words[0]
        last_word = prompted_words[-1]

        if first_word["start_ms"] is None or last_word["end_ms"] is None:
            raise RuntimeError(f"Missing timing data for words {first_word} to {last_word}")

        start_ms = first_word["start_ms"]
        end_ms = last_word["end_ms"]

        # Ensure a small safety margin of 10ms
        start_sample = max(0, int((start_ms / 1000.0) * self.sr))
        end_sample = min(len(self.audio_data), int((end_ms / 1000.0) * self.sr))

        clip = self.audio_data[start_sample:end_sample].copy()

        # Apply 15ms cosine fade-in and 25ms cosine fade-out
        fade_in_len = min(int(0.015 * self.sr), len(clip) // 4)
        if fade_in_len > 0:
            fade_in = np.sin(np.linspace(0, np.pi / 2, fade_in_len)) ** 2
            clip[:fade_in_len] *= fade_in

        fade_out_len = min(int(0.025 * self.sr), len(clip) // 4)
        if fade_out_len > 0:
            fade_out = np.cos(np.linspace(0, np.pi / 2, fade_out_len)) ** 2
            clip[-fade_out_len:] *= fade_out

        duration_ms = (len(clip) / self.sr) * 1000.0

        if output_file is not None:
            output_file = Path(output_file)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            sf.write(str(output_file), clip, self.sr)

        return {
            "surah": self.surah,
            "ayah": ayah,
            "start_word": word,
            "count": len(prompted_words),
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": duration_ms,
            "prompted_text_uthmani": " ".join(w["text_uthmani"] for w in prompted_words),
            "words": prompted_words,
            "audio_samples": clip,
            "sample_rate": self.sr,
            "output_file": str(output_file) if output_file else None,
        }
