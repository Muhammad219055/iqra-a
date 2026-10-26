# On-device listening: next implementation slice

The production target is phone-local recognition and correction with no server
or subscription. The current Expo app does not do this yet. `src/asr/engine.py`
runs the Quran Whisper model in Python; the older Swift coordinator also uses a
WebSocket. `expo-audio` records a file but does not supply live PCM to that engine.

Use the existing public [Quran Whisper base weights](https://huggingface.co/tarteel-ai/whisper-base-ar-quran)
as the initial candidate. The model card declares Apache 2.0, but its published
aggregate WER is not evidence of reliable mistake detection. A recognizer trained
to produce Quran text can correct a reciter's error in its transcript, hiding the
very error we need to detect. Evaluate that explicitly.

The first deliverable is a native development build that transcribes a local
recorded ayah in airplane mode. Use [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
through an existing [React Native binding](https://github.com/mybigday/whisper.rn)
if it passes the Expo 58 / RN 0.88 build check. Otherwise use a small native Expo
module around whisper.cpp. Expo Go cannot load this custom native engine.
Convert and pin the exact weights; check transcription before and after any
quantization. Do not overwrite the separate root `ios/` prototype during prebuild.

Then connect 16 kHz mono PCM microphone capture to bounded overlapping inference
windows, with silence handling and cancellation. Reuse the Arabic normalization
and alignment rules from `src/aligner/` after porting their behavior tests. Do not
copy the old Swift audio converter without checking its input-consumption logic.
Commit highlights only from stable results; never mark a word wrong from one
unstable partial transcript.

Finally, package local reciter audio/timings for the chosen range. Pause inference
while playing a word/next-ayah prompt so the app does not recognize its own
speaker. Test wrong words, omissions, repetitions, hesitations and correct
recitations from multiple speakers. Report false correction rate, delay, real-time
factor, peak memory and sustained-device thermal behavior. Choose a smaller model
only from these measurements. Word recognition does not establish tajweed scoring.

Completion proof: installed phone app, airplane mode, live recitation, a detected
mistake, and local spoken correction. Neither simulator UI tests nor a successful
Python transcription satisfy this acceptance condition.
