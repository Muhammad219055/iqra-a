"""
Real-time Recitation State Machine and Position Tracker.
Maintains the active {surah, ayah, word} cursor and evaluates streaming ASR tokens.
"""

from typing import Dict, List, Optional, Tuple
from .diff import align_sequences, MistakeType
from .normalizer import normalize_for_matching


class RecitationTracker:
    def __init__(self, surah_words: List[dict], start_ayah: int = 1, start_word: int = 1):
        self.all_words = surah_words
        self.cursor_idx = 0

        # Locate initial cursor index
        for idx, w in enumerate(self.all_words):
            if w["ayah"] == start_ayah and w["word_index_in_ayah"] == start_word:
                self.cursor_idx = idx
                break

        self.last_matched_idx = self.cursor_idx - 1
        self.session_mistakes: List[dict] = []

    @property
    def current_expected_word(self) -> Optional[dict]:
        if 0 <= self.cursor_idx < len(self.all_words):
            return self.all_words[self.cursor_idx]
        return None

    def get_lookahead_window(self, window_size: int = 6) -> List[dict]:
        """Returns the upcoming expected words starting from current cursor."""
        end = min(self.cursor_idx + window_size, len(self.all_words))
        return self.all_words[self.cursor_idx:end]

    def process_recognized_tokens(self, recognized_tokens: List[str]) -> Tuple[List[dict], Optional[dict]]:
        """
        Compares recognized tokens against the upcoming expected words window.
        Returns:
            (events, mistake_event_if_any)
        """
        if not recognized_tokens or self.cursor_idx >= len(self.all_words):
            return [], None

        window = self.get_lookahead_window(window_size=max(len(recognized_tokens) + 3, 6))
        alignment = align_sequences(window, recognized_tokens)

        events = []
        mistake = None

        for token in alignment:
            if token.status == "MATCH" and token.expected_word:
                exp_w = token.expected_word
                # Advance cursor past this matched word
                for idx in range(self.cursor_idx, len(self.all_words)):
                    if self.all_words[idx]["word_index_global"] == exp_w["word_index_global"]:
                        self.cursor_idx = idx + 1
                        self.last_matched_idx = idx
                        break

                events.append({
                    "event": "WORD_MATCH",
                    "surah": exp_w["surah"],
                    "ayah": exp_w["ayah"],
                    "word": exp_w["word_index_in_ayah"],
                    "word_global": exp_w["word_index_global"],
                    "text_uthmani": exp_w["text_uthmani"],
                })

            elif token.status == "MISSED_WORDS" and token.expected_word:
                exp_w = token.expected_word
                mistake = {
                    "event": "MISTAKE",
                    "type": MistakeType.MISSED_WORDS,
                    "surah": exp_w["surah"],
                    "ayah": exp_w["ayah"],
                    "word": exp_w["word_index_in_ayah"],
                    "word_global": exp_w["word_index_global"],
                    "expected_text": exp_w["text_uthmani"],
                    "received_text": None,
                }
                self.session_mistakes.append(mistake)
                break

            elif token.status == "INCORRECT_WORDS" and token.expected_word:
                exp_w = token.expected_word
                mistake = {
                    "event": "MISTAKE",
                    "type": MistakeType.INCORRECT_WORDS,
                    "surah": exp_w["surah"],
                    "ayah": exp_w["ayah"],
                    "word": exp_w["word_index_in_ayah"],
                    "word_global": exp_w["word_index_global"],
                    "expected_text": exp_w["text_uthmani"],
                    "received_text": token.recognized_word,
                }
                self.session_mistakes.append(mistake)
                break

        return events, mistake

    def reset_to_word(self, ayah: int, word: int):
        """Sets the cursor back to a target position (e.g. after prompt)."""
        for idx, w in enumerate(self.all_words):
            if w["ayah"] == ayah and w["word_index_in_ayah"] == word:
                self.cursor_idx = idx
                break
