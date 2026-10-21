"""
Milestone 2 Prompt Audio CLI:
Given {surah, ayah, word} and a Qari, plays words N to N+k from locally cached audio.
"""

import argparse
from pathlib import Path
import subprocess
import sys

from src.audio.slicer import QuranAudioSlicer

# ANSI Colors
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"


def play_prompt(
    surah: int = 1,
    ayah: int = 1,
    word: int = 1,
    count: int = 3,
    reciter: str = "mishari",
    auto_play: bool = True,
    output_path: str = "data/audio_cache/last_prompt.wav",
):
    print(f"\n{BOLD}{CYAN}=== Quran Recitation Tutor — Audio Prompt Subsystem (Milestone 2) ==={RESET}")
    print(f"Target: Surah {surah}, Ayah {ayah}, Word {word}")
    print(f"Prompt Length: {count} words | Reciter: {reciter.capitalize()}\n")

    slicer = QuranAudioSlicer(surah=surah, reciter=reciter)
    out_file = Path(output_path)

    result = slicer.slice_prompt(ayah=ayah, word=word, prompt_length=count, output_file=out_file)

    print(f"{BOLD}Prompt Details:{RESET}")
    print(f"  {GREEN}Uthmani Text     :{RESET} {BOLD}{result['prompted_text_uthmani']}{RESET}")
    print(f"  Word Coordinates : {', '.join(f'{w['surah']}:{w['ayah']}:{w['word_index_in_ayah']}' for w in result['words'])}")
    print(f"  Start Timing     : {result['start_ms']:.1f} ms")
    print(f"  End Timing       : {result['end_ms']:.1f} ms")
    print(f"  Audio Duration   : {result['duration_ms']:.1f} ms ({result['duration_ms']/1000.0:.2f}s)")
    print(f"  Exported File    : {result['output_file']}")

    if auto_play:
        print(f"\n{YELLOW}Playing audio prompt via macOS audio subsystem (afplay)...{RESET}")
        try:
            subprocess.run(["/usr/bin/afplay", str(out_file)], check=True)
            print(f"{GREEN}Playback completed successfully.{RESET}\n")
        except Exception as e:
            print(f"Audio playback note: {e}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Quran Word-Level Audio Prompt Generator")
    parser.add_argument("--surah", type=int, default=1, help="Surah number (default: 1)")
    parser.add_argument("--ayah", type=int, default=1, help="Ayah number (default: 1)")
    parser.add_argument("--word", type=int, default=1, help="Starting word index (default: 1)")
    parser.add_argument("--count", type=int, default=3, help="Number of prompt words (default: 3)")
    parser.add_argument("--reciter", type=str, default="mishari", choices=["mishari", "husary"], help="Reciter choice")
    parser.add_argument("--play", action="store_true", help="Play the prompt audio immediately")
    parser.add_argument("--out", type=str, default="data/audio_cache/last_prompt.wav", help="Output path")

    args = parser.parse_args()
    play_prompt(
        surah=args.surah,
        ayah=args.ayah,
        word=args.word,
        count=args.count,
        reciter=args.reciter,
        auto_play=args.play,
        output_path=args.out,
    )


if __name__ == "__main__":
    main()
