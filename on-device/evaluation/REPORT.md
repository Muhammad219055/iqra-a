# Offline recognition evaluation: Al-Fatihah, native whisper.cpp CLI

Run 2026-10-22. Measured with the actual native whisper.cpp CLI (pinned `on-device/vendor/whisper.cpp`). No Python ASR, server, mocks or canned transcripts. Nothing was played or recorded; the run is file inference only.

## Reproduce

```sh
.venv/bin/python on-device/evaluation/check_scoring.py    # scoring self-check
.venv/bin/python on-device/evaluation/build_manifest.py   # clips/ + manifest.json
.venv/bin/python on-device/evaluation/run_eval.py         # raw/ + results.json
```

Each clip runs:

`on-device/build-mac/bin/whisper-cli -m on-device/models/ggml-model.bin -f <clip> -l ar -t 4 -bs 1 -bo 1 -nf -nt -np -ng -oj -of <prefix>`

These settings match the native engine (`Native/QuranWhisper.mm`): greedy decoding, Arabic, temperature 0 with no fallback, no context, CPU (`-ng`).

- **Model:** `tarteel-ai/whisper-base-ar-quran`, revision `5c3c53fd…`, ggml-f16. The SHA256 `aaebca10…0ead` is checked against `model-lock.json` before the run.
- **Platform:** macOS 27.0.1, Apple M2 Pro.
- **Completion:** all 70/70 manifest entries completed, with no failures (`results.json → run.completed / failed`).

**One deliberate difference from the app:** the native engine returns empty text for digital silence when RMS < 1e-4, but the CLI has no such guard. So silence results below are the model's raw behaviour. The manifest records whether the native guard would have skipped each silence clip.

## Data and how the audible words were determined

- **Sources:** the existing 16 kHz Al-Fatihah recordings by Mishari and Husary, plus the two existing `tests/audio` fixtures. Every source hash is in `manifest.json`.
- **Timing files match their audio:**
  - Each reciter uses only their own timing file.
  - Every ayah ending falls in a pause, with an energy ratio of 0.02–0.15 against the recording's loud level.
  - Three malformed Mishari rows in 1:3 (`[1]`, `[2]`, `[1]`) were dropped and logged.
  - The last word end lies inside the audio for both reciters.
- **Original clips:** each of the 7 ayahs per reciter, the full surah per reciter, and the clean fixture. Their truth is the canonical text, on the assumption that professional murattal recitation is correct.
- **Synthetic clips:** made by cutting and joining the original audio at the published word boundaries, with a 10 ms crossfade:
  - omissions of an internal word;
  - repetitions of one word, or of a two-word phrase in 1:7;
  - unfinished ayahs cut after word k;
  - 4 silence clips: digital silence for 2 s and 8 s, and seeded noise at −50 and −40 dBFS for 5 s.
- **Every synthetic edit is marked `unverified` in the manifest.**
  - In this continuous recitation the published word boundaries fall in the middle of sound, at 0.17–1.41 of the loud level (the threshold for "pause" was ≤ 0.25).
  - So a cut may leave pieces of a neighbouring word, and the "audible words" recorded for those clips are the intended edit, not something a person heard and checked.
  - The existing skipped-word fixture has the same property: its boundaries sit at 0.53 and 0.77.
- **No wrong-word substitutions are included,** because none could be verified as an audio mistake.

## Results

| Group | Clips | Outcome | Word error rate against the audible words |
|---|---|---|---|
| Original ayahs (7 + fixture), Mishari | 8 | 8 exact | 0 |
| Original ayahs, Husary | 7 | 7 exact | 0 |
| Full surah (46–48 s), each reciter | 2 | **2 false corrections** | 6/29 and 7/29 |
| Omission, Mishari (synthetic) | 11 | 9 detected, 2 misrecognized, 0 silently repaired | 0.049 |
| Omission, Husary (synthetic) | 10 | 8 detected, 2 misrecognized, 0 silently repaired | 0.105 |
| Repetition, Mishari (synthetic) | 8 | 7 detected, **1 silently repaired** | 0.021 |
| Repetition, Husary (synthetic) | 8 | 3 detected, 3 extra word misspelled, **2 silently repaired** | 0.106 |
| Unfinished, both (synthetic) | 12 | 12 stopped where the audio stops, 0 auto-completed | 0.083 / 0.167 |
| Silence and quiet noise | 4 | **4/4 hallucinated** «وَالْمُؤْمِنِينَ» | — |

**Correct recitation:**
- On single-ayah clips the false correction rate was 0/15 clips.
- The two full-surah clips both failed. Each dropped all of 1:1, the Basmalah, and turned «الْمُسْتَقِيمَ» into «الْمُسْتَعِينَ». Husary's also left a stray fragment «ُسْتَقِيمَ».
- A 46–48 s recording spans two of Whisper's 30 s windows, so long buffers are unsafe for correction feedback.

**Omissions:**
- The model was never seen to fill in a missing word.
- The 4 misrecognized clips are fused words left over at the cut: «لِرَبِّ» and «لَلضَّالِّينَ» for Mishari, «وَالضَّالِّينَ» and «نَعْبُدُونَ السَّعِيرَ» for Husary. These look like artefacts of the edit, not the model filling in text, but they would still produce a confusing correction.

**Repetitions:** 3 of 16 were silently repaired to the canonical text:
- Husary 1:1 «اللَّهِ»
- Husary 1:2 «لِلَّهِ»
- Mishari 1:7 «غَيْرِ»

This is the "model quietly completes the canonical text" risk, observed on real model output. Three more Husary clips heard the extra word but wrote it differently: «وَالرَّحْمَنِ», «وَنَعْبُدُ», «عَلَّذِينَ».

**Unfinished ayahs:**
- No continuation was invented in any of the 12.
- The last word before the cut was sometimes misheard: «مَالِكِينَ» for «مَالِكِ», «اهْدِنَةٌ» for «اهْدِنَا».

**Silence:**
- Every silent or near-silent clip produced «وَالْمُؤْمِنِينَ».
- The native RMS guard would skip only the two digital-silence clips. Quiet room-level noise (−50 and −40 dBFS) gets past it, so on a phone a quiet pause would produce a false word.

**Speed (Mac CLI only, not iPhone):**
- Wall time is 0.28–1.04 s per clip, including model load.
- The median real-time factor is about 0.05–0.08 for whole ayahs and about 0.2 for short unfinished clips, where model load dominates.

Per-clip transcripts, alignments and timings are in `results.json`.

## Limits

- One surah, two professional reciters and 70 clips. That's far too small for any accuracy claim.
- Every mistake is a synthetic edit of professional audio, and none of the edits are verified. There are no recordings of ordinary learners, no ordinary microphones or rooms, and no real human mistakes.
- Nothing here measures tajweed. The word-level matching ignores vowel marks by design.

## Recommended next experiment

1. **Do something about silence before playing any correction.**
   - Add real voice detection, or a no-speech probability check, in front of the engine.
   - Then re-run the four silence clips plus real room-tone recordings.
   - The current RMS guard does not cover quiet noise.
2. **Bound the audio windows.** Run the full-surah clips again, split into ayah-sized or VAD-cut segments of 15 s or less, to check that long buffers are what drop 1:1.
3. **Record real mistakes.** Collect a small set of human recordings (several speakers, phone microphone) with deliberate omissions, repetitions and wrong words, labelled by a listener. Synthetic splices can't separate repair by the model from artefacts of the cut.
4. **Never treat a repetition as "correct" just because the transcript matches the canonical ayah.** Silent repair was observed in 3 of 16 cases, so the app must not trust that signal.
