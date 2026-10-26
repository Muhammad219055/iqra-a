# Tarteel listening review — 22 October 2026

The user's physical-phone test confirms our app recognizes speech, but recognition is inaccurate and the interaction does not feel like Tarteel. The installed app remains a batch prototype, not a streaming tutor. This review changes no installed recognition behavior.

## Target and method

Examined the supplied `Tarteel v5.81.7 (Premium).apk`, SHA-256 `f223968f52ea86431507f7a6f16d6f13f2b79a323c46dea7e5f2f1603f659e94`. Findings describe this artifact, not necessarily a current official release.

REA inspected the APK archive and disassembled/decompiled its ARM64 `libNitroTarteel.so`. The React Native bundle is Hermes bytecode version 96. Separately, P1sec/hermes-dec at commit `2e796663e1fedb93dca51060797ebf3327b3fedb` decoded it statically. Hermes findings below are decoder evidence, not REA output. No target code ran, no Tarteel service was contacted, and no credentials or subscription controls were used.

Local analysis artifacts are ignored under `on-device/research/tarteel5817/`. `rea-evidence-final.json` preserves 14 complete REA records; `bundle.hasm` and `focused/` preserve the Hermes disassembly. Do not commit extracted proprietary binaries/disassembly.

## Observed listening path

- Hermes function #27894, `StreamingClient`, offset `0x00e13724`, selects `wss://voice-v2.tarteel.io` or its development counterpart and registers MicStream event handlers.
- #27895, `startRecognizing`, offset `0x00e1390c`, passes the URL, client configuration and audio configuration to `MicStream.initialize`. It supplies selected start/end positions, with a page-range fallback, plus memorization/diacritics settings and a configurable `mistakeReportingTimeLag`. Flag values and the actual lag selected at runtime are unknown.
- #27920, offset `0x00e148d1`, constructs an audio configuration with bufferSize 512, sampleRate 16000, bitsPerChannel 16 and channelsPerFrame 1. Native buffer units were not established; no frame-duration claim follows from 512 alone.
- #27925, offset `0x00e14a1f`, constructs recognition configuration including `enableInterimResults: true`, `enableWordTimeOffsets: true` and maxAlternatives 1. Runtime code fills/overrides configuration; defaults do not establish the active server model.
- #27903, `processMessage`, offset `0x00e1411c`, parses message types including PARTIAL_TRANSCRIPT and STATES_UPDATE. State updates invoke `onUpdateStates`; #27904 coalesces consecutive queued state updates. This is richer than displaying a final transcript. #27939 dispatches the partial transcript's queryText to recording-query state; partial text alone is not established as the highlighting algorithm.
- A legacy streaming hook (#49753) wires matching and state-update callbacks. Static presence does not prove which legacy/current implementation a particular account uses.

REA native evidence corroborates the configuration boundary, rather than revealing the hosted recognition algorithm:

| Evidence | Observation |
| --- | --- |
| `ev_e4fd323cdb3e16980e5392978da148b30e6e10282bec3f16c6218e11dc12641a` | APK archive inventory |
| `ev_594c5d312b44219d6d2aa572927a6d5a34de4130dd55a67393851fdacef101c9` | AudioConfig converter, `0x169120` |
| `ev_7f16f2be2953a656f3c1eb52ea2b3b08b0427b0a7bf65d4468c9af64c7dd717d` | STTConfig converter, `0x16948c`, including interim-results configuration |
| `ev_9c147a2b367b3dcd8f6cdca0c5b90842383ec23fa6a8fa5bcff118b6027a9740` | Native strings for start/end positions, strict start, sample rate, interim results and word timestamps |
| `ev_cc3dda447d854cda3e83c013cfe41742bae5d8ee5d632c8608bc81d05c226190` | JNI MicStream.send bridge, `0x1cd584`; not the underlying transport implementation |

The bounded archive filename inventory found no obvious ONNX/TFLite/GGUF/PTL recognizer assets. That does not rule out downloaded models or other formats. JADX inspection was unavailable because REA lacks its configured JADX MCP jar; Java microphone internals were not recovered.

## Implications for our offline engine

Our MicrophoneCapture stops the microphone at the energy endpoint. ListeningSession then runs one Whisper decode, aligns its final text, optionally plays a correction and waits for another tap. There are no live interim word states. Tuning the pause duration cannot provide Tarteel's observed streaming behavior.

The public Quran Whisper checkpoint is not established as Tarteel's production recognizer. Client reverse engineering cannot recover hosted weights, training data, acoustic verification or the server's correction/stability algorithm. Claude's tests also show the checkpoint sometimes silently repairs repetitions; correct-looking text cannot certify a correct recitation.

## Next bounded engine slice

1. Keep capture running during local inference. Use bounded overlapping windows and one inference worker, coalescing pending work rather than accumulating stale decodes. Stop capture for spoken prompts to avoid self-recognition.
2. Separate provisional recognized words from stable passage progress. Keep trailing unspoken words pending, and delay corrections until sufficient stable evidence or a genuine phrase endpoint. Preserve cancellation on stop, background and page changes.
3. Add silent file replay checks for window boundaries, duplicate/revised partials, repeated words, noise and cancellation. Verify this path in the actual native bridge before reinstalling.
4. Measure iPhone latency and recognition quality separately using several real speakers and listener-verified mistakes. Benchmark alternative local recognizers/acoustic checks if Whisper continues to repair mistakes; do not infer accuracy improvements from smoother animation or more frequent decoding.

Acceptance: continuous progress through a short Al-Fatihah recitation without repeated microphone taps; bounded memory/work queue; no correction on silence or provisional trailing words; existing local prompts/cancellation preserved. Offline accuracy parity with Tarteel remains unproven and is a separate requirement.
