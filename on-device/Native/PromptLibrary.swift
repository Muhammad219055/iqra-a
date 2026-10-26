import AVFoundation

struct QuranWord: Decodable {
    let ayah: Int
    let word_index_in_ayah: Int
    let text_uthmani: String
    let normalized: String
}

final class PromptLibrary {
    private struct Text: Decodable { let words: [QuranWord] }
    private struct Timing: Decodable {
        let verse_key: String
        let segments: [[Int]]
    }
    private struct Timings: Decodable { let timestamps: [Timing] }
    let words: [QuranWord]
    private let timings: [Timing]
    private let audio: URL

    init(reciter: String = "mishari", bundle: Bundle = .main) throws {
        guard ["mishari", "husary"].contains(reciter) else { throw CaptureError.invalidAudio }
        func resource(_ name: String, _ ext: String) throws -> URL {
            guard let url = bundle.url(forResource: name, withExtension: ext) else {
                throw NSError(domain: "PromptLibrary", code: 1,
                              userInfo: [NSLocalizedDescriptionKey: "Missing bundled resource: \(name).\(ext)"])
            }
            return url
        }
        words = try JSONDecoder().decode(Text.self, from: Data(contentsOf: resource("quran_surah_1", "json"))).words
        timings = try JSONDecoder().decode(Timings.self, from: Data(contentsOf: resource("surah_1_\(reciter)", "json"))).timestamps
        audio = try resource(reciter == "mishari" ? "001_16k" : "001_husary_16k", "wav")
    }

    func words(ayah: Int) -> [QuranWord] { words.filter { $0.ayah == ayah } }

    func buffer(ayah: Int, word: Int? = nil) throws -> AVAudioPCMBuffer {
        let segments = timings.first { $0.verse_key == "1:\(ayah)" }?.segments.filter {
            $0.count >= 3 && $0[1] >= 0 && $0[2] > $0[1] && (word == nil || $0[0] == word)
        } ?? []
        guard let startMS = segments.map({ $0[1] }).min(),
              let endMS = segments.map({ $0[2] }).max() else { throw CaptureError.invalidAudio }
        let file = try AVAudioFile(forReading: audio)
        let start = AVAudioFramePosition(Double(startMS) * file.processingFormat.sampleRate / 1000)
        let end = AVAudioFramePosition(Double(endMS) * file.processingFormat.sampleRate / 1000)
        guard start >= 0, end <= file.length, end > start,
              let buffer = AVAudioPCMBuffer(pcmFormat: file.processingFormat,
                                            frameCapacity: AVAudioFrameCount(end - start)) else {
            throw CaptureError.invalidAudio
        }
        file.framePosition = start
        try file.read(into: buffer, frameCount: AVAudioFrameCount(end - start))
        return buffer
    }
}

@MainActor
final class LocalPromptPlayer {
    private let volume: Float
    private var engine: AVAudioEngine?
    private var node: AVAudioPlayerNode?
    private var generation = UUID()

    init(volume: Float = 1) { self.volume = volume }

    func play(_ buffer: AVAudioPCMBuffer, completion: @escaping () -> Void) async throws {
        stop()
        let generation = self.generation
        try await AudioSessionControl.activate(recording: false)
        guard generation == self.generation else { throw CancellationError() }
        let engine = AVAudioEngine(), node = AVAudioPlayerNode()
        node.volume = volume
        engine.attach(node)
        engine.connect(node, to: engine.mainMixerNode, format: buffer.format)
        self.engine = engine; self.node = node
        node.scheduleBuffer(buffer, completionCallbackType: .dataPlayedBack) { [weak self] _ in
            DispatchQueue.main.async {
                guard let self, self.generation == generation else { return }
                self.stop()
                completion()
            }
        }
        do { try engine.start(); node.play() }
        catch { stop(); throw error }
    }

    func stop() {
        generation = UUID()
        node?.stop(); engine?.stop()
        node = nil; engine = nil
    }
}
