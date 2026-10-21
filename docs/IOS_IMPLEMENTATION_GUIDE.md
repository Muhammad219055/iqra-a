# iOS Native Implementation Architecture (Phase 2)

This document provides the technical blueprint for packaging the Quran Recitation Tutor as a 100% native, offline, on-device iOS application using Swift, SwiftUI, CoreML, and AVAudioEngine.

---

## 1. High-Level iOS Architecture

```
┌────────────────────────────────────────────────────────┐
│                   SwiftUI UI Layer                     │
│  - 15-Line Mushaf View (QPC / KFGQPC Hafs font)        │
│  - Real-time word highlight via SwiftUI View Modifiers │
│  - Memorization Mode (.blur(radius: 7))                │
└──────────────────────────┬─────────────────────────────┘
                           │ Combine / AsyncStream
┌──────────────────────────▼─────────────────────────────┐
│          RecitationCoordinator (ObservableObject)      │
│  - Manages State Machine (ALIGNING, POSITION, PROMPT)  │
│  - Coordinates Audio Capture and Playback              │
└──────────────┬───────────────────────────┬─────────────┘
               │                           │
┌──────────────▼─────────────┐ ┌───────────▼─────────────┐
│    Audio Capture Engine    │ │   Local AI Inference    │
│  - AVAudioEngine (16kHz)   │ │  - CoreML Whisper Model │
│  - Hardware DSP disabled   │ │    (Apple Neural Engine)│
│  - VoiceProcessingIO off   │ │  - Silero VAD (CoreML)  │
└────────────────────────────┘ └───────────┬─────────────┘
                                           │
                               ┌───────────▼─────────────┐
                               │     Offline Storage     │
                               │  - GRDB / SQLite.swift  │
                               │    (Tanzil text+timings)│
                               │  - Bundled Qari audio   │
                               └─────────────────────────┘
```

---

## 2. Audio Capture with Hardware DSP Disabled (`AudioCaptureService.swift`)

In standard iOS apps, `AVAudioSession` enables Acoustic Echo Cancellation (AEC) and Automatic Gain Control (AGC). As discovered in the Tarteel reverse-engineering analysis, these filters distort *Ghunnah*, *Madd*, and *Qalqalah*.

In iOS, we explicitly disable voice processing and noise suppression by setting `.measurement` mode and using raw `AVAudioEngine` tap:

```swift
import AVFoundation

final class AudioCaptureService {
    private let audioEngine = AVAudioEngine()
    private var inputNode: AVAudioInputNode { audioEngine.inputNode }
    private let targetFormat = AVAudioFormat(commonFormat: .pcmFormatInt16, sampleRate: 16000, channels: 1, interleaved: false)!

    func setupSession() throws {
        let session = AVAudioSession.sharedInstance()
        // Measurement mode disables Apple's automatic gain control and noise reduction
        try session.setCategory(.playAndRecord, mode: .measurement, options: [.duckOthers, .defaultToSpeaker])
        try session.setPreferredSampleRate(16000)
        try session.setActive(true)
    }

    func startCapture(onChunk: @escaping (Data) -> Void) throws {
        try setupSession()
        let nativeFormat = inputNode.outputFormat(forBus: 0)

        // Install tap and convert to 16kHz 16-bit mono PCM
        let converter = AVAudioConverter(from: nativeFormat, to: targetFormat)!

        inputNode.installTap(onBus: 0, bufferSize: 1600, format: nativeFormat) { buffer, time in
            let convertedBuffer = AVAudioPCMBuffer(pcmFormat: self.targetFormat, frameCapacity: 1600)!
            var error: NSError?
            converter.convert(to: convertedBuffer, error: &error) { _, outStatus in
                outStatus.pointee = .haveData
                return buffer
            }

            if let channelData = convertedBuffer.int16ChannelData {
                let data = Data(bytes: channelData[0], count: Int(convertedBuffer.frameLength) * 2)
                onChunk(data)
            }
        }

        try audioEngine.start()
    }

    func stopCapture() {
        inputNode.removeTap(onBus: 0)
        audioEngine.stop()
    }
}
```

---

## 3. On-Device Speech Recognition via CoreML / WhisperKit

For local on-device ASR without a server:
1. **Model Format:** Convert `tarteel-ai/whisper-base-ar-quran` to CoreML format using `coremltools` or use **WhisperKit** (Argmax's open-source Swift CoreML Whisper runner).
2. **Apple Neural Engine (ANE):** Whisper Base runs in under **120ms** per audio window on iPhone A15+ and M-series iPads with zero battery drain.
3. **Integration:**
   ```swift
   import WhisperKit

   let whisper = try await WhisperKit(model: "whisper-base-ar-quran")
   let transcription = try await whisper.transcribe(audioArray)
   ```

---

## 4. Headline Feature: Teacher Audio Prompting (`PromptAudioPlayer.swift`)

When a mistake or hesitation occurs:
1. `AudioCaptureService.stopCapture()` is called immediately (gating the mic).
2. The exact word interval is read from local timing SQLite:
   ```swift
   let player = try AVAudioPlayer(data: slicedAudioData)
   player.delegate = self
   player.play()
   ```
3. In `audioPlayerDidFinishPlaying`, add a `Task.sleep(nanoseconds: 150_000_000)` (150ms echo cooldown), then restart capture.

---

## 5. Offline Data Bundling
- Pre-bundle `quran-uthmani.sqlite` (containing word coordinates, page numbers, and line numbers).
- Pre-bundle word segment timings JSON (`timings_surah_1.json`) and compressed audio files.
