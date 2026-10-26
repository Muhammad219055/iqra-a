import AVFoundation

final class PCMResampler {
    private let converter: AVAudioConverter
    private let target: AVAudioFormat
    private var ended = false

    init(source: AVAudioFormat) throws {
        guard source.sampleRate > 0, source.channelCount > 0,
              let target = AVAudioFormat(commonFormat: .pcmFormatFloat32, sampleRate: 16_000,
                                        channels: 1, interleaved: false),
              let converter = AVAudioConverter(from: source, to: target) else {
            throw CaptureError.invalidAudio
        }
        self.target = target
        self.converter = converter
    }

    func convert(_ buffer: AVAudioPCMBuffer) throws -> [Float] {
        guard !ended else { throw CaptureError.invalidAudio }
        let capacity = AVAudioFrameCount(ceil(Double(buffer.frameLength) * 16_000 / buffer.format.sampleRate)) + 64
        return try read(buffer, capacity: capacity).0
    }

    func finish() throws -> [Float] {
        guard !ended else { return [] }
        ended = true
        var samples: [Float] = []
        while true {
            let (tail, status) = try read(nil, capacity: 1024)
            samples += tail
            if status != .haveData { return samples }
            guard !tail.isEmpty else { throw CaptureError.invalidAudio }
        }
    }

    private func read(_ buffer: AVAudioPCMBuffer?, capacity: AVAudioFrameCount) throws -> ([Float], AVAudioConverterOutputStatus) {
        guard let output = AVAudioPCMBuffer(pcmFormat: target, frameCapacity: capacity) else {
            throw CaptureError.invalidAudio
        }
        var supplied = false
        var error: NSError?
        let status = converter.convert(to: output, error: &error) { _, inputStatus in
            guard let buffer else { inputStatus.pointee = .endOfStream; return nil }
            guard !supplied else { inputStatus.pointee = .noDataNow; return nil }
            supplied = true
            inputStatus.pointee = .haveData
            return buffer
        }
        if let error { throw error }
        guard status != .error, let channel = output.floatChannelData?[0] else {
            throw CaptureError.invalidAudio
        }
        let samples = Array(UnsafeBufferPointer(start: channel, count: Int(output.frameLength)))
        guard samples.allSatisfy(\.isFinite) else { throw CaptureError.invalidAudio }
        return (samples.map { min(1, max(-1, $0)) }, status)
    }
}
