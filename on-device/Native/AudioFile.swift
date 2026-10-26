import AVFoundation

enum AudioFile {
    static func pcm(_ url: URL) throws -> Data {
        let file = try AVAudioFile(forReading: url)
        guard file.processingFormat.sampleRate == 16_000,
              file.processingFormat.channelCount == 1,
              file.length >= 1600, file.length <= 240_000,
              let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat,
                                           frameCapacity: AVAudioFrameCount(file.length)) else {
            throw NSError(domain: "AudioFile", code: 1,
                          userInfo: [NSLocalizedDescriptionKey: "Use mono 16 kHz audio, 0.1–15 seconds."])
        }
        try file.read(into: buffer)
        guard let samples = buffer.floatChannelData?[0] else {
            throw NSError(domain: "AudioFile", code: 2,
                          userInfo: [NSLocalizedDescriptionKey: "Could not decode Float32 PCM."])
        }
        return Data(bytes: samples, count: Int(buffer.frameLength) * MemoryLayout<Float>.size)
    }
}
