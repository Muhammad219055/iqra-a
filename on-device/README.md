# On-device Quran tutor

Current checkpoint, 22 October 2026: the engine is integrated into the actual
Expo reader and installed as a standalone Release app on the paired iPhone.
Model, speech detector, text and reciter audio are bundled. Recognition has no
server, runtime downloads, WebSocket or Metro dependency. Tutoring and spoken
prompts currently cover **Al-Fatihah**; the full 604-page reader remains available.

## Current behavior

The user's iPhone test reports inaccurate recognition and an interaction unlike
Tarteel. The APK review in [TARTEEL_LISTENING_REVIEW.md](../docs/TARTEEL_LISTENING_REVIEW.md)
documents the streaming architecture gap and the next bounded engine slice.
Continuous local listening and Tarteel-level accuracy are not implemented/proven.

Tap the microphone on page 1. Recite, then pause for about 0.9 seconds, or tap the
microphone again to finish. The app stops capture during inference and playback.
It keeps the cursor at the first possible omitted/wrong word and can speak that
word locally. An unfinished ayah's remaining words are pending, not omissions.
Tap the mic to continue from that cursor. After completing an ayah, the next
Listen advances to the next ayah. Changing page/backgrounding cancels the session.

Settings select Mishari/Husary, spoken correction/vibration/quiet highlighting,
and explicit next-word / next-ayah playback. Prompt audio is cut from each
reciter's own bundled recording and timestamps.

The capture stage uses energy endpointing with pre-roll and a 14.8-second cap.
Before Whisper runs, **Silero VAD** must find a speech segment (threshold 0.6,
minimum 250 ms). No speech means no recognized text or correction. Engine/file
input is limited to 15 seconds; long recordings are rejected rather than fed
through Whisper's unreliable long-buffer path. Quiet/noisy-room calibration and
false speech detections still need physical-device evaluation.

The transcript is evidence of recognized words, **not proof of perfect recitation**.
Claude's evaluation observed silently repaired repetitions. This model does not
establish tajweed or pronunciation correctness. See `evaluation/REPORT.md` for
baseline results and the synthetic edits' unverified ground truth.

## Verified

- Native iOS 27 simulator: **10 tests passed**, including clean/omitted-word
  recognition through endpointing, quiet noise rejection at approximately −50
  and −40 dBFS, 44.1/48 kHz resampling and converter draining, local prompt
  playback, omission-to-prompt integration, cancellation/busy rejection/recovery,
  and discarded stale results. Automated playback uses volume 0.
- The reader component checks pass; evaluation scoring self-check passes.
- Actual app Release build succeeded with Expo 58 / RN 0.88 / Xcode 27.1.
- Model/VAD checksums, both reciter resources and embedded JS were verified in
  the signed `.app`. Signed by the explicitly authorized Personal Team
  `GUY9JCSF5U` (`mki_15@outlook.com`), bundle ID `com.mki15.qurantutor`.
- Installation succeeded on iPhone 17 Pro Max / iOS 27.0.1. Launch succeeded.

Launch proof is narrower than a live microphone/airplane-mode test. Battery,
thermal behavior, broad learner accuracy and sustained phone performance have
not been measured. Do not turn simulator/Mac timings into iPhone claims.

## Native / Expo boundary

`Native/QuranWhisper.h` accepts mono 16 kHz Float32 PCM (0.1–15 seconds), a new
`QuranWhisperRequest` per operation, and returns `text` / inference `seconds`.
Construction and inference belong off the UI thread. One context rejects
concurrent inference. Requests support thread-safe sticky cancellation, including
before inference starts; the context remains reusable with a new request.

`ListeningSession.swift` owns capture, recognition, alignment and prompt state.
`expo-module/ios/QuranOfflineModule.swift` exposes that session to the reader.
`mobile/nativeTutor.js` loads the native module; Expo Go intentionally cannot
run it. Native notifications stop capture for interruptions/routes/background.
Shared engine files stay in `Native/`; generated per-file links avoid maintaining
an independent copy inside the Expo module. Audio session changes run on a serial
worker queue; microphone audio stays in bounded memory and is not saved.

## Reproduce native libraries and bundle resources

Prerequisites: Xcode, CMake, XcodeGen, CocoaPods and the repository Python venv
(torch, transformers, numpy). From repository root:

```sh
python3 on-device/scripts/build-native.py
.venv/bin/python on-device/scripts/prepare-model.py
python3 on-device/scripts/build-native.py --device
python3 on-device/scripts/prepare-expo.py
```

Exact engine/checkpoint/VAD revisions and hashes are in `model-lock.json`.
`prepare-model.py` verifies source weights/filter/VAD checksums. The checkpoint's
1024 generation max_length differs from its 448-token positional tensor; a
separate conversion config fixes that upstream-converter mismatch. Original
weights remain untouched. CPU + Accelerate, at most four threads, Arabic greedy
decoding, no transcript/Quran prompt, no temperature fallback, no quantization.

From `mobile/`, generate only its own native project (never the root `ios/`):

```sh
npx expo prebuild --platform ios --no-install
cd ios
pod install
xcodebuild -workspace QuranTutor.xcworkspace -scheme QuranTutor \
  -configuration Release -destination 'generic/platform=iOS' \
  IPHONEOS_DEPLOYMENT_TARGET=17.0 DEVELOPMENT_TEAM=GUY9JCSF5U \
  CODE_SIGN_STYLE=Automatic -allowProvisioningUpdates build
```

Native regression tests, from `on-device/` after XcodeGen generation:

```sh
xcodebuild -project QuranOffline.xcodeproj -scheme QuranOffline \
  -destination 'platform=iOS Simulator,name=iPhone 18 Pro,OS=27.0' \
  -derivedDataPath build-xcode test
```

Model card declares Apache-2.0; whisper.cpp and Silero VAD use MIT. Preserve the
upstream notices when distributing. This installation is personal development,
not an App Store release. Personal Team provisioning expires after seven days.
