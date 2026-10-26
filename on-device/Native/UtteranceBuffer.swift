import Foundation

enum CaptureError: LocalizedError {
    case noSpeech, tooLong, invalidAudio
    var errorDescription: String? {
        switch self {
        case .noSpeech: return "No speech detected. Move closer to the microphone and try again."
        case .tooLong: return "The recording reached 15 seconds. Pause sooner to check a shorter passage."
        case .invalidAudio: return "The microphone returned invalid audio."
        }
    }
}

/// Continuous 16 kHz capture window. The listening session snapshots it for each decode and
/// drops the decoded prefix once progress is committed, so memory stays bounded.
struct RollingAudio {
    static let maxSamples = 12 * 16_000
    private(set) var samples: [Float] = []
    /// Voiced audio arrived since the last snapshot, so a new decode could change the hypothesis.
    private(set) var hasNewSpeech = false
    private(set) var heardSpeech = false
    private var quietFrames = 0
    private var partial: [Float] = []

    var quietSeconds: Double { Double(quietFrames) * 0.02 }

    mutating func append(_ input: [Float]) throws {
        guard input.allSatisfy({ $0.isFinite && abs($0) <= 1 }) else { throw CaptureError.invalidAudio }
        partial.append(contentsOf: input)
        var offset = 0
        defer { partial.removeFirst(offset) }
        while partial.count - offset >= 320 {
            let frame = partial[offset..<(offset + 320)]
            offset += 320
            let rms = sqrt(frame.reduce(Float(0)) { $0 + $1 * $1 } / 320)
            // ponytail: energy only decides when to decode; Silero in QuranWhisper decides what is speech.
            if rms >= 0.004 { heardSpeech = true; hasNewSpeech = true; quietFrames = 0 } else { quietFrames += 1 }
            samples.append(contentsOf: frame)
            // Before speech keep 240 ms of pre-roll only.
            if !heardSpeech && samples.count > 3840 { samples.removeFirst(samples.count - 3840) }
        }
    }

    /// Bounded copy for one decode; clears the new-speech flag.
    mutating func snapshot() -> [Float] {
        hasNewSpeech = false
        return Array(samples.suffix(Self.maxSamples))
    }

    /// Drops audio that a committed decode already covered; later audio stays for the next window.
    mutating func drop(first count: Int) {
        samples.removeFirst(min(count, samples.count))
        heardSpeech = hasNewSpeech
    }

    var isFull: Bool { samples.count >= Self.maxSamples }
}
