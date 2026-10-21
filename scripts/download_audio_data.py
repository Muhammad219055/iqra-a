"""
Script to fetch and cache Qari audio and segment timings.
Supported reciters:
- mishari: Mishari Rashid al-`Afasy (ID 7)
- husary: Mahmoud Khalil Al-Husary (ID 6)
"""

import json
from pathlib import Path
from typing import Tuple
import requests

RECITERS = {
    "mishari": 7,
    "husary": 6,
}


def download_surah_audio(surah_id: int = 1, reciter_name: str = "mishari") -> Tuple[Path, Path]:
    reciter_id = RECITERS.get(reciter_name.lower())
    if not reciter_id:
        raise ValueError(f"Unknown reciter '{reciter_name}'. Available: {list(RECITERS.keys())}")

    audio_dir = Path(f"data/audio_cache/{reciter_name}")
    timing_dir = Path("data/timings")
    audio_dir.mkdir(parents=True, exist_ok=True)
    timing_dir.mkdir(parents=True, exist_ok=True)

    timing_file = timing_dir / f"surah_{surah_id}_{reciter_name}.json"
    mp3_file = audio_dir / f"{surah_id:03d}.mp3"

    # 1. Fetch metadata with segment timestamps if not cached
    if not timing_file.exists():
        url = f"https://api.quran.com/api/v4/chapter_recitations/{reciter_id}/{surah_id}?segments=true"
        print(f"Fetching audio segments from {url}...")
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        data = resp.json().get("audio_file", {})
        with open(timing_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Saved segment timings to {timing_file}")
    else:
        with open(timing_file, "r", encoding="utf-8") as f:
            data = json.load(f)

    # 2. Download audio file (MP3) if not cached
    if not mp3_file.exists():
        audio_url = data.get("audio_url")
        if not audio_url:
            raise RuntimeError(f"No audio URL found for reciter {reciter_name}, Surah {surah_id}")
        print(f"Downloading audio from {audio_url} to {mp3_file}...")
        r = requests.get(audio_url, stream=True, timeout=30)
        r.raise_for_status()
        with open(mp3_file, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Audio downloaded: {mp3_file} ({mp3_file.stat().st_size} bytes)")
    else:
        print(f"Audio already cached: {mp3_file}")

    return mp3_file, timing_file


if __name__ == "__main__":
    download_surah_audio(1, "mishari")
    download_surah_audio(1, "husary")
