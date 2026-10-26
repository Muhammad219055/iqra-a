# Claude takeover — 22 October 2026

User explicitly transferred the Quran app/model work to Claude. This supersedes earlier ownership splits in CLAUDE_ON_DEVICE_HANDOFF.md, CLAUDE_UI_HANDOFF.md and historical HANDOFF entries. Codex is stopping edits after this handoff. Preserve the existing uncommitted tree; do not reset/stash/recreate the project.

## Goal and constraints

Free, entirely on-device Quran listening with continuous passage tracking, possible mistake feedback and local spoken word/next-ayah assistance. No recognition server or hidden cloud fallback. The reader must retain exact 15-line Madinah glyph rendering, never raster page PNGs. User wants polished UI, black/white dark mode with surah-header gold accents, tap-revealed overlays without page reflow, hidden status bar in focus mode, fast page slider and restrained haptics. Existing UI work belongs to this working tree; preserve it while fixing the engine.

Automated tests must be silent: native prompt-player tests use volume 0. Do not play clips or start microphone capture automatically. The user was previously disturbed by audible testing. Keep capture user initiated. Do not collect/upload personal recordings.

## What actually works / fails

- Standalone Release Quran Tutor is installed and launched on the user's paired iPhone. No Metro needed. Whisper, Silero speech detector, Fatihah text and Mishari/Husary prompt audio are bundled.
- The user tested the microphone: recognition runs but is bad/faulty and does not feel like Tarteel. This is the active problem. No claim of phone accuracy, latency, airplane-mode performance or general Quran coverage is justified.
- Tutoring is **Al-Fatihah only**, despite the full 604-page reader. Do not imply full-Quran listening support.
- Current interaction: mic tap -> record -> 900 ms energy-based pause or second tap -> stop microphone -> VAD gate -> one final Whisper decode -> align remaining ayah -> optional local prompt -> wait for another mic tap. This is batch recognition, not continuous listening.
- Native input max 15 seconds; capture cap 14.8 seconds. Longer audio is rejected. Quiet input must pass Silero (threshold .6, minimum speech 250 ms). VAD rejects tested quiet noise, but phone room-noise calibration remains unverified.
- Ten muted native simulator tests passed, zero failures: `on-device/evidence/vad-gate.xcresult` and `.log`. Release device build and actual phone install succeeded. Tests are not a general accuracy benchmark.

## Read these first

1. `docs/TARTEEL_LISTENING_REVIEW.md`: fresh APK re-review, exact REA IDs / Hermes offsets, limitations and next slice. **Read before implementing another pause-threshold tweak.**
2. `on-device/README.md`: reproducible engine setup/current behavior.
3. `on-device/evaluation/REPORT.md`, `results.json`, `manifest.json`: Claude's 70-clip evaluation and limitations.
4. `mobile/App.js`, `mobile/nativeTutor.js`, `on-device/expo-module/ios/QuranOfflineModule.swift`, `on-device/Native/ListeningSession.swift` and `MicrophoneCapture.swift`: real production path.

## What REA found

The supplied Downloads APK v5.81.7 (Premium) has a Hermes v96 React Native bundle and native Nitro MicStream bridge. Its examined listening path streams to `wss://voice-v2.tarteel.io`, passes selected Quran start/end positions, requests interim results and word timestamps, and handles **server STATES_UPDATE** separately from PARTIAL_TRANSCRIPT. It has configurable mistake-reporting lag and state-update queue coalescing. Active flags, server model, actual lag and algorithm are unknown. The public Quran Whisper checkpoint is **not established as Tarteel's production model**. Hosted weights cannot be recovered from this client.

REA records: `on-device/research/tarteel5817/rea-evidence-final.json` (14 complete records). Separately decoded Hermes: `bundle.hasm` (178 MB), `focused/index.json`, focused function files. These are ignored proprietary research artifacts; do not commit them. Raw string pool has enormous concatenated lines: avoid unbounded rg output. REA session was closed. JADX Java inspection was unavailable due missing configured MCP jar; no APK runtime/server testing was performed. Decoder is P1sec/hermes-dec commit `2e796663e1fedb93dca51060797ebf3327b3fedb`, under research/tools, analysis-only dependency.

## Code map and important behavior

- `Native/QuranWhisper.h/.mm`: CPU+Accelerate whisper.cpp; per-request sticky atomic cancellation and mutex rejects concurrent inference. Arabic greedy decode, no context/prompt, temperature 0. VAD gate before decode; validates mono16k Float32 finite bounded input, .1–15 seconds. Speech recognition can still silently repair actual mistakes.
- `UtteranceBuffer.swift`: 20 ms energy frames, 240 ms pre-roll, 900 ms endpoint, idle timeout and memory cap. `MicrophoneCapture.swift`: hardware tap/resampler; stops capture before delivering a completed utterance. CaptureProcessor synchronizes automatic endpoint/manual finish. AudioSessionControl serializes session activation/deactivation.
- `PCMResampler.swift`: AVAudioConverter hardware44.1/48k ->16k mono; consumes each input once and drains trailing samples on finish. Preserve these fixes.
- `ListeningSession.swift`: serial recognition worker, generation guards for stale callbacks, prepare/permission/listen/recognize/prompt lifecycle; background/route/interruption cancellation; selected ayah and cursor. Only final transcript currently drives alignment.
- `RecitationAlignment.swift`, `ArabicMatching.swift`: normalized token edit-distance alignment. Trailing unspoken expected words remain pending, not missing. A transcript match is not proof of correct repetition/pronunciation. Possible corrections stop at first suspect word.
- `PromptLibrary.swift`: reciter whitelist Mishari/Husary; validates text/timing/audio ranges and drops malformed rows. `LocalPromptPlayer` is separate output engine with cancellation and test volume0.
- `OfflineApp.swift`: SwiftUI lab/test host, **not** the product reader. Separate root `ios/` is also an older prototype. Product workspace is **mobile/ios/**.
- `expo-module/ios/QuranOfflineModule.swift`: actual local Expo bridge, snapshots through onChange; async prepare/load, listen/finish/stop, ayah/qari/feedback selection, word/next-ayah playback. JS `nativeTutor.js` loads optional module. Unavailable in Expo Go.
- `mobile/App.js`: native events and lifecycle, mic and local prompts; no WebSocket/server recorder. Existing `MushafReader.js` UI preserved except native integration/settings. Page change cancels session; tutoring restricted to page1.

## Accuracy evidence

70 clips through real Mac CLI: 15/15 clean single ayahs exact; both ~47s full-surah clips wrong; 17/21 synthetic omissions detected; 10/16 repetitions exact-detected, 3 extra misspelled, **3 silently repaired**; 12/12 unfinished clips not completed; all4 silence/noise clips hallucinated a word in raw model. Native Silero gate was added afterward, but the complete70 suite has not been rerun through native gating. Synthetic cuts are unverified and may leave fused word fragments. Only Fatihah/two professional reciters, no verified real substitutions, no tajweed/general-speaker claims. Mac speed is not iPhone speed.

Next engine slice: continuous capture with bounded overlapping windows, one inference worker with coalesced pending work, provisional versus stable progress, conservative correction timing, microphone stopped for audible prompts, and preserved cancellation. Add silent replay checks for boundaries, repeated/revised hypotheses, noise, queue bounds and stale results. Evaluate recognizer quality separately with listener-verified human errors; smoother streaming cannot fix Whisper repairing mistakes. Full acceptance details are in the REA review. No streaming changes are implemented yet.

## Build / signing / installation

**Only signing account `mki_15@outlook.com`**, verified in Xcode as Muhammad Arshad (Personal Team), **GUY9JCSF5U**. Do not choose Muhammad Khizar or infer identity from another keychain certificate. Phone UDID `00008150-001E395E0A63401C`, iPhone17ProMax, iOS27.0.1; Xcode27.1. App bundle `com.mki15.qurantutor`.

Run from repository root as needed (existing dependencies/models are present):

```sh
python3 on-device/scripts/build-native.py
python3 on-device/scripts/build-native.py --device
python3 on-device/scripts/prepare-expo.py
```

prepare-expo creates an XCFramework only if absent; rebuilding C++ requires regenerating that artifact deliberately. Native Swift/ObjC files are individually symlinked into an actual `expo-module/ios/Core/` directory: CocoaPods did not discover files when Core itself was a directory symlink. Preserve individual links. Resources are generated links too; do not commit binaries. If adding native files, rerun preparation and pod install.

From `mobile/ios`:

```sh
/Users/muhammad/.rbenv/versions/3.2.2/bin/ruby /Users/muhammad/gems/bin/pod install
xcodebuild -workspace QuranTutor.xcworkspace -scheme QuranTutor -configuration Release -destination 'id=00008150-001E395E0A63401C' -derivedDataPath /private/tmp/quran-iphone IPHONEOS_DEPLOYMENT_TARGET=17.0 DEVELOPMENT_TEAM=GUY9JCSF5U CODE_SIGN_STYLE=Automatic -allowProvisioningUpdates build
```

Installed artifact: `/private/tmp/quran-iphone/Build/Products/Release-iphoneos/QuranTutor.app`. Final successful build `/private/tmp/quran-iphone-core-build.log`; initial quran-iphone-build.log failed before the Core-link fix and is superseded. Install/launch evidence `/private/tmp/quran-install.json`, `/private/tmp/quran-launch.json`; device console `/private/tmp/quran-device-console.log` confirms native Whisper/Silero loading and actual user inference. Later process exit0 does not establish crash cause.

```sh
xcrun devicectl device install app --device 00008150-001E395E0A63401C /private/tmp/quran-iphone/Build/Products/Release-iphoneos/QuranTutor.app
xcrun devicectl device process launch --device 00008150-001E395E0A63401C com.mki15.qurantutor
```

Reader static check: **from mobile/** `node scripts/check-reader.cjs`. Scoring check: from repo root `.venv/bin/python on-device/evaluation/check_scoring.py`. Native test project is `on-device/project.yml` / generated QuranOffline.xcodeproj, scheme QuranOffline, target OfflineTests. Pick an available simulator with simctl; keep all playback muted. Do not claim historical reader UI checks prove today's UI perfect. `on-device/evidence/verification.json` is an older21Oct artifact with superseded missing-live-capture claims; use current README/handoff and newer test bundle.

Model details: Quran Whisper revision `5c3c53fdf9272c4f6ee0bee09a1e5a4a615ee25c`, F16 GGML147951465bytes SHA256 `aaebca10e2a65a6dda073a6b3ac59900f91887628acf872c565a0198ee850ead`; whisper.cppv1.9.5 commit `d1be6fde11ac6e0407606b4e42fe72d34add8037`; Silero `ggml-org/whisper-vad` revision `9ffd54a1e1ee413ddf265af9913beaf518d1639b`, SHA256 `2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987`. prepare-model.py pins downloads/checksums. No runtime downloads.

## Remain and boundaries

Claude already owns Remain's phone crash. Separate handoff: `/Users/muhammad/Desktop/Remain/docs/PHONE_INSTALL_HANDOFF.md`. Widget-enabled personal signing installation succeeded; free Personal Team **does** support the app's tested widget/App Group setup. Do not incorrectly require paid membership. Remain bundle com.mki15.remain, widget .widget, App Group group.com.mki15.remain. No financial data erased/imported/reset. Keep its investigation separate from this Quran engine.

No commits were made. Many files are untracked and belong to ongoing work. No active REA session or engine build remains to resume. The last changes were documentation/research-ignore only; the phone still runs the batch prototype described above.

## Claude progress — 22 October 2026

Continuous listening implemented and installed on the iPhone (not yet user-tested):
- `MicrophoneCapture` keeps the mic open into `RollingAudio` (UtteranceBuffer.swift; 12 s bounded window, 240 ms pre-roll).
- `ListeningSession` ticks every 250 ms; one decode in flight, newest audio wins (no queue). Partial decode every ~400 ms of new speech; final decode at 0.8 s pause or Finish. Committed audio is dropped after a pause, correction or full window.
- `ProgressTracker` (RecitationAlignment.swift) tracks all 29 Fatihah words across ayahs: provisional = latest hypothesis, stable = two agreeing hypotheses or pause. Corrections need two agreeing hypotheses plus two later words, or a pause. Leading repeats/extras are ignored.
- Word match tolerates one edit for words of 4+ letters (Uthmani vs Whisper spelling, e.g. العلمين/العالمين).
- Prompt feedback stops the mic, plays the word, then resumes listening automatically.
- Whisper `suppress_nst` enabled. Beam 5 vs greedy on the 68 eval clips: no improvement (33 vs 32 word errors), so greedy stays.
- Tests: 11/11 muted simulator tests pass (`/private/tmp/qt-stream.xcresult`), incl. real-engine streaming replay of both fixtures. Device build `/private/tmp/quran-stream-build.log`.

Not done: model hardening (fine-tuning / larger model), real-speaker evaluation, iPhone latency measurement.

## Status at end of 23 October 2026 (resume Monday)

Word model (Whisper, verbatim fine-tune, Colab A100, notebooks in on-device/training/, generator make_notebook.py):
- v3 stage 2 base q8_0 = best. Held-out spliced WER 0.076 (orig 0.39, v2 0.17); midstart 76%, cross-ayah 59% verbatim; real Kaggle speakers WER 0.27 (orig 0.40). Local 68-clip set: ~5 errors on clips <=15 s, 35 detected, 0 hidden; loops only on 47 s full-surah clips (app never sends >12 s).
- Silence still transcribed (97% of silence clips) - app's Silero gate covers it.
- Files: on-device/models/ggml-model-verbatim-v3-stage2-q8_0.bin (sha 33d49b5c...) and ...-v3-tiny-q5_0.bin. Resources symlink now points to v3 stage2. Release app BUILT (/private/tmp/quran-iphone, generic iOS) but NOT installed: iPhone unreachable. Next: connect phone, `xcrun devicectl device install app ...`.
- QuranWhisper.mm: temperature fallback 0.2 + entropy 2.4 (loop guard). Muted native tests not rerun since.
- tlog via public mirror catsOfpeople/bin3jb (byte-identical sizes); credit Tarteel AI (CC-BY-4.0).
- Optional: qv3_full_whisper.py (whisper-large-v3-turbo "full" model) not run.

Harakat (phoneme model, separate notebook quran_harakat_colab.ipynb, generator make_harakat_notebook.py, outputs Drive quran-harakat/ on a second Google account):
- wav2vec2-base CTC on IqraEval (Iqra_train + Iqra_TTS): dev PER 0.154; QuranMB.v2 free decoding P 0.21 R 0.67 F1 0.32; GOP forced alignment best P 0.28 R 0.54 F1 0.37. int8 ONNX 95 MB (agreement 0.974).
- Muaalem (obadx/muaalem-model-v3_2, code license QML-1.0: AI notice, no ads, free path) on RetaSy Al-Fatihah: AUC 0.68 per clip; needs phoneme-set mapping to score on QuranMB.
- harakat_teacher_student.py (w2v-bert-2.0 teacher -> distilled 95M student): OOM'd because a crashed run held 77.8 GB; fixed to batch 16 x accum 2, no checkpointing. Next: Restart session and run all, then the exec cell. If OOM persists: cap teacher clips at 12 s.

Shared write-up for Affan: Claude Doc https://claude.ai/artifact/YNv7jmfgDzGLiAHCN8B4BR (private until user shares).
Working copies of Colab scripts: on-device/training/desktop-copies/. Nothing committed.
User preferences learned: deliver Colab code via pbcopy (terminal copy mangles long lines), never run training locally, test code against real data/API before handing over.
