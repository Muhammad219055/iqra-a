"""
Script to fetch and cache Quranic text with word-level coordinates and text_uthmani.
"""

import json
from pathlib import Path
import requests

from src.aligner.normalizer import normalize_for_matching


def download_surah_words(surah_id: int = 1, output_path: str = "data/text/quran_surah_1.json"):
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)

    url = f"https://api.quran.com/api/v4/verses/by_chapter/{surah_id}?words=true&word_fields=text_uthmani,text_imlaei"
    print(f"Fetching Surah {surah_id} from {url}...")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    words_list = []
    ayahs_list = []
    global_word_counter = 1

    for v in data.get("verses", []):
        ayah_num = v["verse_number"]
        ayah_words = []
        for w in v.get("words", []):
            if w.get("char_type_name") == "word":
                word_entry = {
                    "surah": surah_id,
                    "ayah": ayah_num,
                    "word_index_in_ayah": w["position"],
                    "word_index_global": global_word_counter,
                    "text_uthmani": w.get("text_uthmani", ""),
                    "text_imlaei": w.get("text_imlaei", ""),
                    "normalized": normalize_for_matching(w.get("text_uthmani", "")),
                }
                ayah_words.append(word_entry)
                words_list.append(word_entry)
                global_word_counter += 1

        ayahs_list.append({
            "surah": surah_id,
            "ayah": ayah_num,
            "words": ayah_words,
            "full_uthmani": " ".join(w["text_uthmani"] for w in ayah_words),
            "full_normalized": " ".join(w["normalized"] for w in ayah_words),
        })

    result = {
        "surah": surah_id,
        "total_ayahs": len(ayahs_list),
        "total_words": len(words_list),
        "ayahs": ayahs_list,
        "words": words_list,
    }

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"Successfully saved {len(words_list)} words for Surah {surah_id} to {out_file}")
    return result


if __name__ == "__main__":
    download_surah_words(1)
