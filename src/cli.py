"""
Milestone 1 Offline CLI:
Feed it an audio file (WAV) of reciting Al-Fatiha.
It prints aligned words, coordinates, and detected mistakes.
"""

import argparse
import json
from pathlib import Path
import sys

from src.aligner.diff import align_sequences, MistakeType
from src.aligner.normalizer import tokenize_words
from src.asr.engine import QuranASREngine
from scripts.download_quran_text import download_surah_words


# ANSI terminal colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
MAGENTA = "\033[95m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def load_expected_words(surah_id: int = 1, start_ayah: int = 1, end_ayah: int = 7) -> list[dict]:
    cache_file = Path(f"data/text/quran_surah_{surah_id}.json")
    if not cache_file.exists():
        data = download_surah_words(surah_id, str(cache_file))
    else:
        with open(cache_file, "r", encoding="utf-8") as f:
            data = json.load(f)

    selected_words = []
    for w in data.get("words", []):
        if start_ayah <= w["ayah"] <= end_ayah:
            selected_words.append(w)
    return selected_words


def run_recitation_audit(audio_path: str, surah_id: int = 1, start_ayah: int = 1, end_ayah: int = 7):
    audio_file = Path(audio_path)
    if not audio_file.exists():
        print(f"{RED}Error: Audio file not found at {audio_path}{RESET}")
        sys.exit(1)

    print(f"{BOLD}{CYAN}=== Quran Recitation Offline Tutor (Milestone 1) ==={RESET}")
    print(f"Audio File: {BOLD}{audio_file.resolve()}{RESET}")
    print(f"Target: Surah {surah_id}, Ayahs {start_ayah} to {end_ayah}\n")

    # 1. Load Quran expected words
    expected_words = load_expected_words(surah_id, start_ayah, end_ayah)
    print(f"Loaded {len(expected_words)} expected Quranic words.")

    # 2. Transcribe audio with local ASR
    asr = QuranASREngine()
    print(f"Transcribing {audio_file.name} with local Whisper Quran model...")
    transcription = asr.transcribe(audio_file)
    raw_text = transcription["text"]
    print(f"\n{BOLD}Raw ASR Output:{RESET}\n{raw_text}\n")

    # 3. Tokenize recognized speech
    rec_tokens = tokenize_words(raw_text)
    print(f"Recognized {len(rec_tokens)} word tokens.")

    # 4. Run Sequence Alignment
    alignment = align_sequences(expected_words, rec_tokens)

    # 5. Display Aligned Results
    print(f"\n{BOLD}{CYAN}--- Word Alignment & Mistake Analysis ---{RESET}")
    header = f"{'Pos':<8} | {'Expected (Uthmani)':<22} | {'Recognized':<18} | {'Status':<16}"
    print(header)
    print("-" * len(header))

    matches = 0
    missed = 0
    incorrect = 0
    extra = 0

    for token in alignment:
        if token.status == "MATCH":
            matches += 1
            pos_str = f"{token.expected_word['surah']}:{token.expected_word['ayah']}:{token.expected_word['word_index_in_ayah']}"
            exp_str = token.expected_word["text_uthmani"]
            rec_str = token.recognized_word
            status_str = f"{GREEN}MATCH{RESET}"
            print(f"{pos_str:<8} | {exp_str:<22} | {rec_str:<18} | {status_str}")

        elif token.status == "MISSED_WORDS":
            missed += 1
            pos_str = f"{token.expected_word['surah']}:{token.expected_word['ayah']}:{token.expected_word['word_index_in_ayah']}"
            exp_str = token.expected_word["text_uthmani"]
            rec_str = "---"
            status_str = f"{YELLOW}{BOLD}MISSED_WORD{RESET}"
            print(f"{pos_str:<8} | {exp_str:<22} | {rec_str:<18} | {status_str}")

        elif token.status == "INCORRECT_WORDS":
            incorrect += 1
            pos_str = f"{token.expected_word['surah']}:{token.expected_word['ayah']}:{token.expected_word['word_index_in_ayah']}"
            exp_str = token.expected_word["text_uthmani"]
            rec_str = token.recognized_word
            status_str = f"{RED}{BOLD}INCORRECT_WORD{RESET}"
            print(f"{pos_str:<8} | {exp_str:<22} | {rec_str:<18} | {status_str}")

        elif token.status == "EXTRA_WORDS":
            extra += 1
            pos_str = "---"
            exp_str = "---"
            rec_str = token.recognized_word
            status_str = f"{MAGENTA}{BOLD}EXTRA_WORD{RESET}"
            print(f"{pos_str:<8} | {exp_str:<22} | {rec_str:<18} | {status_str}")

    # Summary
    total_expected = len(expected_words)
    accuracy = (matches / total_expected * 100) if total_expected > 0 else 0

    print("-" * len(header))
    print(f"{BOLD}Summary:{RESET}")
    print(f"  Total Expected Words : {total_expected}")
    print(f"  {GREEN}Matched Words        : {matches}{RESET}")
    print(f"  {YELLOW}Missed Words         : {missed}{RESET}")
    print(f"  {RED}Incorrect Words      : {incorrect}{RESET}")
    print(f"  {MAGENTA}Extra Words          : {extra}{RESET}")
    print(f"  {BOLD}Accuracy             : {accuracy:.1f}%{RESET}\n")

    return {
        "total_expected": total_expected,
        "matches": matches,
        "missed": missed,
        "incorrect": incorrect,
        "extra": extra,
        "accuracy": accuracy,
        "alignment": alignment,
    }


def main():
    parser = argparse.ArgumentParser(description="Offline Quran Recitation Aligner and Mistake Detector")
    parser.add_argument("audio", help="Path to WAV audio file")
    parser.add_argument("--surah", type=int, default=1, help="Surah number (default: 1)")
    parser.add_argument("--start-ayah", type=int, default=1, help="Start Ayah (default: 1)")
    parser.add_argument("--end-ayah", type=int, default=7, help="End Ayah (default: 7)")

    args = parser.parse_args()
    run_recitation_audit(args.audio, args.surah, args.start_ayah, args.end_ayah)


if __name__ == "__main__":
    main()
