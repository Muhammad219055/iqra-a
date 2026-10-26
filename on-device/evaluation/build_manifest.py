"""Builds evaluation clips and manifest.json from existing Al-Fatihah recordings. Never plays audio.
Run: .venv/bin/python on-device/evaluation/build_manifest.py"""
import hashlib
import json

import numpy as np

from common import EVAL, RATE, ROOT, read_wav, surah_words, write_wav

SOURCES = {
    "mishari": ("data/audio_cache/mishari/001_16k.wav", "ios/QuranTutor/Resources/surah_1_mishari.json"),
    "husary": ("data/audio_cache/husary/001_16k.wav", "data/timings/surah_1_husary.json"),
}
FADE = int(0.010 * RATE)   # 10 ms crossfade at each splice, to avoid clicks
PAD = int(0.060 * RATE)    # context kept around an ayah, never crossing into a neighbour word
# A splice is "verified" only when it lands in a near-pause. Continuous recitation joins words, so
# many internal boundaries will fail this check; those clips are still run but reported separately.
QUIET = 0.25

ms = lambda t: int(round(float(t) * RATE / 1000))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def load_timing(name, audio):
    path = ROOT / SOURCES[name][1]
    rows, issues = {}, []
    for ayah in json.loads(path.read_text())["timestamps"]:
        n = int(ayah["verse_key"].split(":")[1])
        good = []
        for seg in ayah["segments"]:
            if len(seg) != 3:
                issues.append(f"{ayah['verse_key']}: dropped malformed row {seg}"); continue
            idx, a, b = int(seg[0]), ms(seg[1]), ms(seg[2])
            if b > len(audio):
                issues.append(f"{ayah['verse_key']} word {idx}: end {seg[2]} ms clamped to audio end {len(audio) * 1000 // RATE} ms")
                b = len(audio)
            assert 0 <= a < b, f"{name} {ayah['verse_key']} word {idx}: empty interval"
            assert not good or (idx == good[-1][0] + 1 and a >= good[-1][2]), f"{name} {ayah['verse_key']}: non-monotonic words"
            good.append((idx, a, b))
        rows[n] = [(a, b) for _, a, b in good]
    return rows, issues


def frame_level(audio):
    frames = audio[: len(audio) // 320 * 320].reshape(-1, 320)
    return float(np.percentile(np.sqrt((frames ** 2).mean(1)), 90))


def boundary_ratio(audio, at, loud):
    window = audio[max(0, at - 240): at + 240]
    return round(float(np.sqrt((window ** 2).mean())) / loud, 3)


def splice(*pieces):
    out = pieces[0]
    for piece in pieces[1:]:
        ramp = np.linspace(0, 1, FADE, dtype=np.float32)
        out = np.concatenate([out[:-FADE], out[-FADE:] * (1 - ramp) + piece[:FADE] * ramp, piece[FADE:]])
    return out


def main():
    text = surah_words()
    canon = {a: [forms[0] for forms in ws] for a, ws in text.items()}
    manifest = {"clips": [], "timing_validation": {}, "sources": {}}
    clips = EVAL / "clips"

    def add(entry, samples, boundaries=(), audio=None, loud=None):
        path = clips / f"{entry['id']}.wav"
        write_wav(path, samples)
        ratios = [boundary_ratio(audio, b, loud) for b in boundaries] if boundaries else []
        entry.update(path=str(path.relative_to(ROOT)), seconds=round(len(samples) / RATE, 3),
                     boundary_energy_ratios=ratios,
                     boundary_check=("n/a" if not ratios else "verified" if max(ratios) <= QUIET else "unverified"))
        manifest["clips"].append(entry)

    for speaker, (wav, timing) in SOURCES.items():
        audio = read_wav(ROOT / wav)
        loud = frame_level(audio)
        rows, issues = load_timing(speaker, audio)
        ends = [rows[a][-1][1] for a in sorted(rows)][:-1]
        manifest["timing_validation"][speaker] = {
            "issues": issues,
            "audio_seconds": round(len(audio) / RATE, 3),
            "last_word_end_seconds": round(rows[7][-1][1] / RATE, 3),
            # Ayah endings should fall in pauses if this timing file belongs to this audio.
            "ayah_end_energy_ratios": [boundary_ratio(audio, e, loud) for e in ends],
        }
        manifest["sources"][speaker] = {"audio": wav, "audio_sha256": sha(ROOT / wav), "timing": timing, "timing_sha256": sha(ROOT / timing)}
        base = {"speaker": speaker, "source": wav}

        for a, ws in rows.items():
            start, end = max(0, ws[0][0] - PAD), min(len(audio), ws[-1][1] + PAD)
            if a > 1: start = max(start, rows[a - 1][-1][1])
            if a < 7: end = min(end, rows[a + 1][0][0])
            n = len(ws)
            span = {"source_interval_ms": [start * 1000 // RATE, end * 1000 // RATE]}
            add({**base, **span, "id": f"{speaker}_a{a}_original", "category": "original", "synthetic": False, "ayah": a,
                 "audible_words": canon[a]}, audio[start:end])
            for k in sorted({(n + 1) // 2, n - 1} if n >= 4 else {2} if n == 3 else set()):
                cut = (ws[k - 2][1], ws[k][0])
                add({**base, **span, "id": f"{speaker}_a{a}_omit_w{k}", "category": "omission", "synthetic": True, "ayah": a,
                     "edit": {"word_index": k, "removed_interval_ms": [ws[k - 1][0] * 1000 // RATE, ws[k - 1][1] * 1000 // RATE]},
                     "audible_words": canon[a][:k - 1] + canon[a][k:]},
                    splice(audio[start:cut[0]], audio[cut[1]:end]), boundaries=cut, audio=audio, loud=loud)
            if n >= 2:
                k = (n + 1) // 2
                w0, w1 = ws[k - 1]
                add({**base, **span, "id": f"{speaker}_a{a}_repeat_w{k}", "category": "repetition", "synthetic": True, "ayah": a,
                     "edit": {"repeated_words": [canon[a][k - 1]], "repeated_interval_ms": [w0 * 1000 // RATE, w1 * 1000 // RATE]},
                     "audible_words": canon[a][:k] + canon[a][k - 1:]},
                    splice(audio[start:w1], audio[w0:end]), boundaries=(w0, w1), audio=audio, loud=loud)
            if n >= 3:
                k = n // 2
                add({**base, **span, "id": f"{speaker}_a{a}_stop_w{k}", "category": "unfinished", "synthetic": True, "ayah": a,
                     "edit": {"stopped_after_word": k, "cut_ms": ws[k - 1][1] * 1000 // RATE},
                     "audible_words": canon[a][:k]},
                    audio[start:ws[k - 1][1]], boundaries=(ws[k - 1][1],), audio=audio, loud=loud)
        # Two-word phrase repetition in the long final ayah.
        ws = rows[7]; start = max(rows[6][-1][1], ws[0][0] - PAD); end = min(len(audio), ws[-1][1] + PAD)
        add({**base, "source_interval_ms": [start * 1000 // RATE, end * 1000 // RATE], "id": f"{speaker}_a7_repeat_w2-3",
             "category": "repetition", "synthetic": True, "ayah": 7,
             "edit": {"repeated_words": canon[7][1:3], "repeated_interval_ms": [ws[1][0] * 1000 // RATE, ws[2][1] * 1000 // RATE]},
             "audible_words": canon[7][:3] + canon[7][1:]},
            splice(audio[start:ws[2][1]], audio[ws[1][0]:end]), boundaries=(ws[1][0], ws[2][1]), audio=audio, loud=loud)
        add({**base, "id": f"{speaker}_full_surah", "category": "original", "synthetic": False, "ayah": None,
             "audible_words": [w for a in range(1, 8) for w in canon[a]]}, audio)

    # Existing fixtures, reused as-is. The omission matches Mishari word 3 (1409–2502 ms): 6.090 s − 1.093 s = 4.997 s.
    for name, cat, truth, edit in [
        ("ayah_1_clean", "original", canon[1], None),
        ("ayah_1_skipped_word3", "omission", canon[1][:2] + canon[1][3:], {"word_index": 3, "removed_interval_ms": [1409, 2502]}),
    ]:
        path = ROOT / "tests/audio" / f"{name}.wav"
        manifest["clips"].append({"id": f"fixture_{name}", "speaker": "mishari", "category": cat, "synthetic": cat != "original",
                                  "ayah": 1, "audible_words": truth, **({"edit": edit} if edit else {}),
                                  "path": str(path.relative_to(ROOT)), "source_sha256": sha(path),
                                  "seconds": round(len(read_wav(path)) / RATE, 3), "boundary_check": "existing fixture"})

    rng = np.random.default_rng(7)
    for name, samples in [("digital_silence_2s", np.zeros(2 * RATE, np.float32)),
                          ("digital_silence_8s", np.zeros(8 * RATE, np.float32)),
                          ("noise_minus50dbfs_5s", rng.normal(0, 10 ** (-50 / 20), 5 * RATE).astype(np.float32)),
                          ("noise_minus40dbfs_5s", rng.normal(0, 10 ** (-40 / 20), 5 * RATE).astype(np.float32))]:
        add({"id": name, "speaker": "none", "category": "silence", "synthetic": True, "ayah": None, "audible_words": [],
             "native_rms_guard_would_skip": bool(np.sqrt((samples ** 2).mean()) < 0.0001)}, samples)

    (EVAL / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1))
    by = {}
    for c in manifest["clips"]: by[c["category"]] = by.get(c["category"], 0) + 1
    print(f"{len(manifest['clips'])} clips", by)
    for s, v in manifest["timing_validation"].items(): print(s, v)


if __name__ == "__main__":
    main()
