# Claude task: evaluate offline Quran mistake recognition

Work in `/Users/muhammad/quran-tutor`. Codex owns `on-device/Native/`, native
tests/project configuration, microphone capture, playback and the future Expo
bridge. Your separate deliverable is **only `on-device/evaluation/`**. Keep your
existing reader UI work; do not edit Codex's files, original recordings, shared
model weights, Python ASR/alignment code, or root `ios/`. Do not reset/stash work.

## Why this task matters

The native iOS 27 suite passes 9 tests, including an actual recognized omission
that triggers local word playback, cancellation/recovery, endpointing and audio
conversion. An unsigned iPhone build also passes. That demonstrates a narrow
working path, not general mistake-detection accuracy. The public fine-tuned model
may silently complete canonical Quran text and conceal a speaker's mistake.
Find where it does that before we trust correction behavior.

## Deliverable

Build and run a small reproducible evaluation with a machine-readable manifest,
results JSON, and a short findings report. Use the **actual native whisper.cpp
CLI**, not Python Transformers, a server, canned transcripts, or mocked ASR:

```
on-device/build-mac/bin/whisper-cli \
  -m on-device/models/ggml-model.bin -f <16k-mono-wav> \
  -l ar -t 4 -bs 1 -bo 1 -nf -nt -oj -of <output-prefix>
```

Check the pinned CLI's `--help` to confirm flags; match native greedy Arabic
decoding with temperature fallback disabled. The model revision/converted hash
are in `on-device/model-lock.json`. Native source is pinned in
`on-device/vendor/whisper.cpp`; CLI already exists. If it needs rebuilding, use
your own build directory under `on-device/evaluation/`, leaving existing builds
and model files alone. Record command, model hash, platform and settings.

Reuse existing fixtures first:

- `tests/audio/ayah_1_clean.wav` and `ayah_1_skipped_word3.wav`.
- `data/audio_cache/mishari/001_16k.wav` and `data/audio_cache/husary/001_16k.wav`.
- Word/ayah text: `data/text/quran_surah_1.json`.
- Mishari word timing: `ios/QuranTutor/Resources/surah_1_mishari.json`.
- Husary timing: `data/timings/surah_1_husary.json`. Never apply Mishari
  timestamps to another reciter; verify each file's timing against its audio.

Include clean ayahs, internal omissions, repetitions, silence and truncated
unfinished ayahs. Include wrong-word examples only where the audio edit and its
spoken ground truth can be verified; do not label a text-only substitution as an
audio mistake. Generated edits are **synthetic**, not human error recordings.
Ignore malformed timing rows such as `[1]`; validate intervals/sample boundaries.
Write generated clips only inside your evaluation directory. Record source
provenance, edit intervals and the exact normalized words actually audible in
each clip. If uncertain, mark the example unverified instead of inventing truth.

Use normalization from `src/aligner/normalizer.py`. Report:

- Correct-recitation word errors and false correction rate.
- Omission/repetition detection rate and cases the model silently repaired.
- Silence hallucinations and unfinished-ayah behavior.
- Per-clip decoding time / real-time factor, clearly labeled **Mac CLI**, not
  iPhone performance. Separate synthetic cases from original recitations and
  results by speaker; state the small sample's limits.

Do not change thresholds/models to make the report look better. Report the
failures and recommend the next experiment. Include one small check that the
scoring distinguishes correct, omitted, extra and unfinished words, and verify
the batch completed every manifest entry or explicitly reported its failure.

## Keep tests silent

Do not play audio, use the microphone, change macOS sound volume, or run native
playback tests. Audibility surprised the user; Codex has now muted native test
playback internally. File inference/evaluation needs no speaker output.

Finish with paths, exact run command, actual measured results, and limitations.
No app-store claims, broad accuracy claims or tajweed scoring from this dataset.
