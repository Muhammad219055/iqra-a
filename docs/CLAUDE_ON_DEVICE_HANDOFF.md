# Superseded: Claude now owns UI

The user reversed this split. Use [CLAUDE_UI_HANDOFF.md](CLAUDE_UI_HANDOFF.md).
Codex owns `on-device/`. The older instructions below are historical only.

# Previous task split for Claude

Own the offline listening prototype; Codex owns the current mobile reader UI,
controls, motion, status bar, slider and haptics. Work only in `on-device/` so
there are no shared-file edits. Do not reset/stash/overwrite current uncommitted
work, modify `mobile/`, or prebuild over the separate root `ios/` prototype.

Read HANDOFF.md, docs/ON_DEVICE_LISTENING.md, src/asr/engine.py and src/aligner/.
Build an installable iOS 27 prototype that transcribes a local recording in
airplane mode using public tarteel-ai/whisper-base-ar-quran weights and a native
engine such as whisper.cpp/whisper.rn. Match the active mobile runtime versions
if using Expo. Keep package files and native build outputs inside on-device/.

Pin model revision, record licensing and conversion commands, and expose load,
transcribeLocalFile, cancel and release. Test with existing local recitation
audio. Report actual transcript, build result, inference time and memory, and
distinguish simulator from physical-device evidence. No server/cloud fallback.
Do not claim mistake detection or tajweed assessment from transcription; check
whether wrong/omitted words are silently corrected into canonical Quran text.

Save code, exact run commands, limits, and integration steps in
`on-device/HANDOFF.md`. First proof is offline file transcription; live PCM and
correction playback follow once that baseline works. No UI redesign.
