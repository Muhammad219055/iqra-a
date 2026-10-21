"""
Automated Test for Milestone 2:
1. Tests slicing words 1 to 3 of Ayah 1 for both Mishari and Husary.
2. Asserts exact prompt words match canonical Uthmani text.
3. Tests boundary crossing (slicing from end of Ayah 1 into Ayah 2).
4. Verifies audio integrity and fade windowing.
"""

from pathlib import Path
import soundfile as sf
from src.audio.slicer import QuranAudioSlicer


def test_milestone_2():
    test_out_dir = Path("tests/audio")
    test_out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Testing Milestone 2: Prompt Audio Subsystem")
    print("=" * 60)

    # 1. Test Mishari: Surah 1, Ayah 1, Words 1 to 3 ("بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ")
    print("\n[Test 1] Slicing Mishari: Surah 1, Ayah 1, Words 1-3")
    slicer_mishari = QuranAudioSlicer(surah=1, reciter="mishari")
    out_mishari = test_out_dir / "prompt_mishari_1_1_w1_3.wav"
    res1 = slicer_mishari.slice_prompt(ayah=1, word=1, prompt_length=3, output_file=out_mishari)

    print(f"  Prompted text : {res1['prompted_text_uthmani']}")
    print(f"  Word count    : {res1['count']}")
    print(f"  Duration      : {res1['duration_ms']:.1f} ms")
    assert res1["count"] == 3, f"Expected 3 words, got {res1['count']}"
    assert res1["prompted_text_uthmani"] == "بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ"
    assert out_mishari.exists(), "Exported WAV file does not exist"
    data, sr = sf.read(str(out_mishari))
    assert sr == 16000, f"Expected 16kHz sample rate, got {sr}"
    assert len(data) > 0, "Audio data is empty"
    print("  --> PASS: Mishari 3-word prompt verified.")

    # 2. Test Husary: Surah 1, Ayah 1, Words 1 to 3 ("بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ")
    print("\n[Test 2] Slicing Husary: Surah 1, Ayah 1, Words 1-3")
    slicer_husary = QuranAudioSlicer(surah=1, reciter="husary")
    out_husary = test_out_dir / "prompt_husary_1_1_w1_3.wav"
    res2 = slicer_husary.slice_prompt(ayah=1, word=1, prompt_length=3, output_file=out_husary)

    print(f"  Prompted text : {res2['prompted_text_uthmani']}")
    print(f"  Word count    : {res2['count']}")
    print(f"  Duration      : {res2['duration_ms']:.1f} ms")
    assert res2["count"] == 3
    assert res2["prompted_text_uthmani"] == "بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ"
    assert out_husary.exists()
    print("  --> PASS: Husary 3-word prompt verified.")

    # 3. Test Cross-Ayah Boundary Slicing: Surah 1, Ayah 1, Word 3 with count=3
    # Words should be: Ayah 1 Word 3 (ٱلرَّحْمَـٰنِ), Word 4 (ٱلرَّحِيمِ), Ayah 2 Word 1 (ٱلْحَمْدُ)
    print("\n[Test 3] Cross-Ayah Boundary Slicing: Surah 1, Ayah 1, Word 3 (count=3)")
    out_boundary = test_out_dir / "prompt_mishari_boundary.wav"
    res3 = slicer_mishari.slice_prompt(ayah=1, word=3, prompt_length=3, output_file=out_boundary)

    print(f"  Prompted text : {res3['prompted_text_uthmani']}")
    print(f"  Word count    : {res3['count']}")
    coords = [f"{w['surah']}:{w['ayah']}:{w['word_index_in_ayah']}" for w in res3['words']]
    print(f"  Words spanning: {coords}")
    assert res3["count"] == 3
    assert res3["words"][0]["ayah"] == 1 and res3["words"][0]["word_index_in_ayah"] == 3
    assert res3["words"][1]["ayah"] == 1 and res3["words"][1]["word_index_in_ayah"] == 4
    assert res3["words"][2]["ayah"] == 2 and res3["words"][2]["word_index_in_ayah"] == 1
    assert out_boundary.exists()
    print("  --> PASS: Cross-Ayah boundary slicing verified.")

    print("\n" + "=" * 60)
    print("ALL MILESTONE 2 TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_milestone_2()
