"""
Automated Test for Milestone 1:
1. Verifies clean recitation of Surah Al-Fatiha (Ayah 1).
2. Generates an audio clip with one deliberate skipped word:
   Ayah 1: "بِسْمِ ٱللَّهِ ٱلرَّحِيمِ" (skipping "ٱلرَّحْمَـٰنِ").
3. Asserts that the alignment engine correctly detects MISSED_WORDS for the skipped word.
"""

import json
from pathlib import Path
import subprocess
import numpy as np
import soundfile as sf

from src.aligner.diff import align_sequences, MistakeType
from src.aligner.normalizer import tokenize_words
from src.asr.engine import QuranASREngine
from scripts.download_quran_text import download_surah_words
from scripts.download_audio_data import download_surah_audio


def prepare_test_audio():
    # 1. Download text & audio for Surah 1
    download_surah_words(1, "data/text/quran_surah_1.json")
    mp3_file, timing_file = download_surah_audio(1, 7, "mishari")

    test_dir = Path("tests/audio")
    test_dir.mkdir(parents=True, exist_ok=True)

    wav_full = test_dir / "al_fatiha_full.wav"
    # Convert MP3 to 16kHz mono WAV using ffmpeg
    subprocess.run([
        "/opt/homebrew/bin/ffmpeg", "-y", "-i", str(mp3_file),
        "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav_full)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Load timings
    with open(timing_file, "r", encoding="utf-8") as f:
        timing_data = json.load(f)

    # In Mishari's Surah 1, verse 1 timestamp:
    # Segments: [[1, 0, 580], [2, 580, 1409], [3, 1409, 2502], [4, 2502, 5840]]
    # Word 1: بِسْمِ (0 to 580ms)
    # Word 2: ٱللَّهِ (580 to 1409ms)
    # Word 3: ٱلرَّحْمَـٰنِ (1409 to 2502ms)
    # Word 4: ٱلرَّحِيمِ (2502 to 5840ms)
    v1_timing = timing_data["timestamps"][0]
    segments = v1_timing["segments"]

    audio_data, sr = sf.read(str(wav_full))

    # Slice Ayah 1 clean (0 to 5840ms)
    ayah1_end_sample = int(v1_timing["timestamp_to"] * sr / 1000)
    ayah1_clean = audio_data[:ayah1_end_sample]
    wav_ayah1_clean = test_dir / "ayah_1_clean.wav"
    sf.write(str(wav_ayah1_clean), ayah1_clean, sr)

    # Create Ayah 1 with word 3 ("ٱلرَّحْمَـٰنِ") deliberately skipped:
    # Keep word 1 & 2: 0 to 1409ms
    # Skip word 3: 1409ms to 2502ms
    # Keep word 4: 2502ms to end of Ayah 1
    w2_end_sample = int(segments[1][2] * sr / 1000)
    w4_start_sample = int(segments[3][1] * sr / 1000)

    # Concatenate word 1+2 directly to word 4
    skipped_audio = np.concatenate([
        audio_data[:w2_end_sample],
        audio_data[w4_start_sample:ayah1_end_sample]
    ])
    wav_ayah1_skipped = test_dir / "ayah_1_skipped_word3.wav"
    sf.write(str(wav_ayah1_skipped), skipped_audio, sr)

    print(f"Prepared test files:")
    print(f"  Clean: {wav_ayah1_clean}")
    print(f"  Skipped Word: {wav_ayah1_skipped}")

    return wav_ayah1_clean, wav_ayah1_skipped


def test_milestone_1():
    wav_clean, wav_skipped = prepare_test_audio()

    # Load expected words for Ayah 1
    with open("data/text/quran_surah_1.json", "r", encoding="utf-8") as f:
        surah1_data = json.load(f)

    expected_ayah1 = [w for w in surah1_data["words"] if w["ayah"] == 1]
    print("\nExpected Ayah 1 words:")
    for w in expected_ayah1:
        print(f"  Word {w['word_index_in_ayah']}: {w['text_uthmani']} (normalized: {w['normalized']})")

    asr = QuranASREngine()

    # 1. Test Clean Recitation
    print("\n" + "=" * 50)
    print("Testing 1: Clean Recitation (Ayah 1)")
    print("=" * 50)
    clean_transcription = asr.transcribe(wav_clean)
    clean_tokens = tokenize_words(clean_transcription["text"])
    clean_alignment = align_sequences(expected_ayah1, clean_tokens)

    for a in clean_alignment:
        exp_w = a.expected_word["text_uthmani"] if a.expected_word else "None"
        print(f"  {exp_w:<15} -> Rec: {str(a.recognized_word):<15} Status: {a.status}")

    # 2. Test Skipped Word Recitation
    print("\n" + "=" * 50)
    print("Testing 2: Deliberate Skipped Word (Word 3: ٱلرَّحْمَـٰنِ omitted)")
    print("=" * 50)
    skipped_transcription = asr.transcribe(wav_skipped)
    skipped_tokens = tokenize_words(skipped_transcription["text"])
    skipped_alignment = align_sequences(expected_ayah1, skipped_tokens)

    detected_missed_words = []
    for a in skipped_alignment:
        exp_w = a.expected_word["text_uthmani"] if a.expected_word else "None"
        print(f"  {exp_w:<15} -> Rec: {str(a.recognized_word):<15} Status: {a.status}")
        if a.status == "MISSED_WORDS":
            detected_missed_words.append(a.expected_word)

    print("\n" + "=" * 50)
    print(f"Verification Results:")
    assert len(detected_missed_words) > 0, "Failed: Skipped word was not detected as MISSED_WORDS!"
    assert any(w["word_index_in_ayah"] == 3 for w in detected_missed_words), (
        "Failed: Specifically word 3 (ar-Rahman) was not flagged as MISSED_WORDS!"
    )
    print("PASSED: Engine correctly identified the skipped word (ٱلرَّحْمَـٰنِ) as MISSED_WORDS!")
    print("=" * 50)


if __name__ == "__main__":
    test_milestone_1()
