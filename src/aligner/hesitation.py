"""
Hesitation & Stuck-State Detector.
Tracks recitation stalls, silence, or mid-verse pauses.
Differentiates legitimate Waqf (breath stops) from stuck reciters.
"""

import time
from typing import Optional


class HesitationDetector:
    def __init__(
        self,
        mid_verse_threshold_s: float = 2.5,
        waqf_threshold_s: float = 5.0,
    ):
        self.mid_verse_threshold_s = mid_verse_threshold_s
        self.waqf_threshold_s = waqf_threshold_s

        self.last_progress_time: float = time.time()
        self.last_speech_time: float = time.time()
        self.is_stuck_flagged: bool = False

    def on_word_progress(self):
        """Called whenever the student successfully articulates a word."""
        self.last_progress_time = time.time()
        self.is_stuck_flagged = False

    def on_speech_active(self):
        """Called when VAD detects vocal activity."""
        self.last_speech_time = time.time()

    def check_hesitation(self, current_word: Optional[dict]) -> Optional[dict]:
        """
        Evaluates elapsed time against thresholds.
        Returns a prompt trigger event if stuck, else None.
        """
        if self.is_stuck_flagged or current_word is None:
            return None

        now = time.time()
        elapsed_since_progress = now - self.last_progress_time

        # Check if the word is an ayah boundary (word 1 after ayah end or last word)
        is_ayah_start_or_end = (current_word["word_index_in_ayah"] == 1)
        threshold = self.waqf_threshold_s if is_ayah_start_or_end else self.mid_verse_threshold_s

        if elapsed_since_progress >= threshold:
            self.is_stuck_flagged = True
            return {
                "event": "HESITATION_STUCK",
                "elapsed_seconds": round(elapsed_since_progress, 2),
                "threshold_seconds": threshold,
                "surah": current_word["surah"],
                "ayah": current_word["ayah"],
                "word": current_word["word_index_in_ayah"],
                "text_uthmani": current_word["text_uthmani"],
            }

        return None

    def reset_timer(self):
        """Resets timers (e.g. after a prompt has finished playing)."""
        self.last_progress_time = time.time()
        self.last_speech_time = time.time()
        self.is_stuck_flagged = False
