import AVFoundation

private final class CaptureProcessor {
    private let lock = NSLock()
    private let resampler: PCMResampler
    private var audio = RollingAudio()
    private var failure: Error?

    init(format: AVAudioFormat) throws { resampler = try PCMResampler(source: format) }

    func consume(_ buffer: AVAudioPCMBuffer) {
        lock.lock(); defer { lock.unlock() }
        guard failure == nil else { return }
        do { try audio.append(resampler.convert(buffer)) } catch { failure = error }
    }

    func access<T>(_ body: (inout RollingAudio) throws -> T) throws -> T {
        lock.lock(); defer { lock.unlock() }
        if let failure { throw failure }
        return try body(&audio)
    }
}

/// Keeps the microphone open and accumulates 16 kHz audio until stopped.
@MainActor
final class MicrophoneCapture {
    private let engine = AVAudioEngine()
    private var processor: CaptureProcessor?
    private var tapInstalled = false
    private var generation = UUID()

    var isRunning: Bool { processor != nil }

    func start() async throws {
        stop()
        let generation = self.generation
        try await AudioSessionControl.activate(recording: true)
        guard generation == self.generation else { throw CancellationError() }
        do {
            let input = engine.inputNode
            let format = input.outputFormat(forBus: 0)
            let processor = try CaptureProcessor(format: format)
            self.processor = processor
            input.installTap(onBus: 0, bufferSize: 2048, format: format) { buffer, _ in processor.consume(buffer) }
            tapInstalled = true
            engine.prepare()
            try engine.start()
        } catch { stop(); throw error }
    }

    /// Nil when capture is stopped; throws the capture failure, if any.
    func access<T>(_ body: (inout RollingAudio) throws -> T) throws -> T? {
        try processor?.access(body)
    }

    func stop() {
        generation = UUID()
        if tapInstalled { engine.inputNode.removeTap(onBus: 0); tapInstalled = false }
        engine.stop()
        engine.reset()
        processor = nil
    }
}
