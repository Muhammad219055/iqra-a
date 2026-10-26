import AVFoundation

enum AudioSessionControl {
    // Serial activation also orders Stop before a subsequent Listen/Play request.
    private static let queue = DispatchQueue(label: "quran.offline.audio-session", qos: .userInitiated)

    static func activate(recording: Bool) async throws {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            queue.async {
                do {
                    let session = AVAudioSession.sharedInstance()
                    try session.setCategory(recording ? .playAndRecord : .playback, mode: .default,
                                            options: recording ? [.defaultToSpeaker] : [])
                    if recording { try session.setPreferredSampleRate(16_000) }
                    try session.setActive(true)
                    continuation.resume()
                } catch { continuation.resume(throwing: error) }
            }
        }
    }

    static func deactivate() {
        queue.async {
            try? AVAudioSession.sharedInstance().setActive(false, options: .notifyOthersOnDeactivation)
        }
    }
}
