import AVFoundation
import Foundation

public final class AudioCaptureService: NSObject {
    private let audioEngine = AVAudioEngine()
    private var isCapturing = false
    private var isMuted = false

    private let targetSampleRate: Double = 16000.0
    private let targetFormat = AVAudioFormat(
        commonFormat: .pcmFormatInt16,
        sampleRate: 16000.0,
        channels: 1,
        interleaved: false
    )!

    public var onAudioChunk: ((Data) -> Void)?

    public override init() {
        super.init()
    }

    public func setupAudioSession() throws {
        let session = AVAudioSession.sharedInstance()
        // Mode .measurement explicitly disables Apple's hardware noise suppression,
        // echo cancellation, and automatic gain control, preserving Tajweed acoustics
        try session.setCategory(.playAndRecord, mode: .measurement, options: [.defaultToSpeaker, .allowBluetooth])
        try session.setPreferredSampleRate(targetSampleRate)
        try session.setActive(true, options: .notifyOthersOnDeactivation)
    }

    public func start() throws {
        guard !isCapturing else { return }
        try setupAudioSession()

        let inputNode = audioEngine.inputNode
        let nativeFormat = inputNode.outputFormat(forBus: 0)

        guard let converter = AVAudioConverter(from: nativeFormat, to: targetFormat) else {
            throw NSError(domain: "AudioCaptureService", code: -1, userInfo: [NSLocalizedDescriptionKey: "Failed to initialize AVAudioConverter"])
        }

        // 1600 samples = 100ms at 16kHz
        let bufferSize: AVAudioFrameCount = 1600

        inputNode.installTap(onBus: 0, bufferSize: bufferSize, format: nativeFormat) { [weak self] (buffer, time) in
            guard let self = self, !self.isMuted else { return }

            let convertedBuffer = AVAudioPCMBuffer(pcmFormat: self.targetFormat, frameCapacity: bufferSize)!
            var error: NSError?
            let status = converter.convert(to: convertedBuffer, error: &error) { inNumPackets, outStatus in
                outStatus.pointee = .haveData
                return buffer
            }

            if status != .error, let channelData = convertedBuffer.int16ChannelData {
                let bytesCount = Int(convertedBuffer.frameLength) * 2
                let data = Data(bytes: channelData[0], count: bytesCount)
                self.onAudioChunk?(data)
            }
        }

        try audioEngine.start()
        isCapturing = true
    }

    public func stop() {
        guard isCapturing else { return }
        audioEngine.inputNode.removeTap(onBus: 0)
        audioEngine.stop()
        isCapturing = false
    }

    public func setMuted(_ muted: Bool) {
        self.isMuted = muted
    }
}
