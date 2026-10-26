import AVFoundation
import Combine
import UIKit

@MainActor
final class ListeningSession: ObservableObject {
    enum State: Equatable { case loading, ready, permission, listening, recognizing, prompting }
    @Published private(set) var state: State = .ready
    @Published private(set) var ayah = 1
    @Published private(set) var cursor = 0
    @Published private(set) var transcript = ""
    @Published private(set) var message = "Load the model to begin."
    @Published private(set) var seconds: Double?
    private(set) var library: PromptLibrary?
    private var engine: QuranWhisper?
    private let worker = DispatchQueue(label: "quran.offline.inference", qos: .userInitiated)
    private let microphone = MicrophoneCapture()
    private let player: LocalPromptPlayer
    private var request: QuranWhisperRequest?
    private var generation = UUID()
    private var feedbackMode = "prompt"
    private var tracker = ProgressTracker(expected: [])
    private var continuous = false
    private var decoding = false
    private var finishing = false

    init(promptVolume: Float = 1) { player = LocalPromptPlayer(volume: promptVolume) }

    var words: [QuranWord] { library?.words(ayah: ayah) ?? [] }
    private var allWords: [QuranWord] { library?.words ?? [] }
    var isLoaded: Bool { engine != nil && library != nil }

    func setFeedbackMode(_ mode: String) {
        if ["prompt", "buzzer", "silent"].contains(mode) { feedbackMode = mode }
    }

    func selectReciter(_ reciter: String) throws {
        guard state == .ready else { return }
        library = try PromptLibrary(reciter: reciter)
    }

    func prepare() {
        guard !isLoaded, state == .ready else { return }
        state = .loading
        message = "Loading the bundled model…"
        let generation = self.generation
        worker.async { [weak self] in
            let result = Result { () -> (QuranWhisper, PromptLibrary) in
                guard let path = Bundle.main.path(forResource: "ggml-model", ofType: "bin") else {
                    throw NSError(domain: "ListeningSession", code: 1,
                                  userInfo: [NSLocalizedDescriptionKey: "The bundled model is missing."])
                }
                return (try QuranWhisper(modelPath: path), try PromptLibrary())
            }
            DispatchQueue.main.async {
                guard let self, self.generation == generation else { return }
                self.state = .ready
                switch result {
                case .success(let loaded):
                    self.engine = loaded.0; self.library = loaded.1
                    self.tracker = ProgressTracker(expected: loaded.1.words.map(\.normalized))
                    self.tracker.reset(to: loaded.1.words.firstIndex { $0.ayah == self.ayah } ?? 0)
                    self.message = "Ready. Recite the selected ayah, then pause."
                case .failure(let error): self.message = error.localizedDescription
                }
            }
        }
    }

    func select(ayah: Int) {
        guard (1...7).contains(ayah) else { return }
        stop()
        self.ayah = ayah; cursor = 0; transcript = ""; seconds = nil
        tracker.reset(to: allWords.firstIndex { $0.ayah == ayah } ?? 0)
        message = "Ready for ayah \(ayah)."
    }

    func listen() async {
        guard isLoaded, state == .ready else { return }
        if tracker.stable >= allWords.count { select(ayah: 1) }
        state = .permission
        let generation = self.generation
        let permitted: Bool
        if #available(iOS 17, *) { permitted = await AVAudioApplication.requestRecordPermission() }
        else {
            permitted = await withCheckedContinuation { continuation in
                AVAudioSession.sharedInstance().requestRecordPermission { continuation.resume(returning: $0) }
            }
        }
        guard generation == self.generation else { return }
        guard permitted else {
            state = .ready; message = "Microphone access is off. Enable it in Settings to recite."
            return
        }
        do {
            try await microphone.start()
            guard generation == self.generation else { return }
            state = .listening; continuous = true; finishing = false
            message = "Listening locally. Keep reciting; progress follows you."
            Task { [weak self] in
                while let self, self.generation == generation, self.state == .listening {
                    self.tick()
                    try? await Task.sleep(nanoseconds: 250_000_000)
                }
            }
        } catch {
            guard generation == self.generation else { return }
            endListening(error.localizedDescription)
        }
    }

    /// Stops after one last decode of the audio heard so far.
    func finish() { if state == .listening { finishing = true; tick() } }

    func example(_ name: String) {
        guard isLoaded, state == .ready else { return }
        select(ayah: 1)
        do {
            guard ["ayah_1_clean", "ayah_1_skipped_word3"].contains(name),
                  let url = Bundle.main.url(forResource: name, withExtension: "wav") else {
                throw CaptureError.invalidAudio
            }
            let pcm = try AudioFile.pcm(url)
            state = .recognizing
            message = "Checking locally."
            decode(pcm.withUnsafeBytes { Array($0.bindMemory(to: Float.self)) }, final: true, covered: 0, full: false)
        } catch { message = error.localizedDescription }
    }

    /// One decode in flight; later ticks use the newest audio instead of queueing stale windows.
    private func tick() {
        guard state == .listening, !decoding else { return }
        let finishing = self.finishing
        do {
            let next = try microphone.access { audio -> (pcm: [Float], final: Bool, covered: Int, full: Bool)? in
                let pause = audio.heardSpeech && audio.quietSeconds >= 0.8
                guard pause || finishing || (audio.hasNewSpeech && audio.samples.count >= 9600) else { return nil }
                guard audio.heardSpeech, audio.samples.count >= 1600 else { return nil }
                let covered = audio.samples.count, full = audio.isFull
                return (audio.snapshot(), pause || finishing, covered, full)
            } ?? nil
            if let next { decode(next.pcm, final: next.final, covered: next.covered, full: next.full) }
            else if finishing { endListening("Stopped. Tap Listen when ready.") }
        } catch { endListening(error.localizedDescription) }
    }

    private func decode(_ pcm: [Float], final: Bool, covered: Int, full: Bool) {
        guard let engine else { return }
        decoding = true
        let request = QuranWhisperRequest(), generation = self.generation
        self.request = request
        let data = pcm.withUnsafeBytes { Data($0) }
        worker.async { [weak self] in
            let result = Result { try engine.transcribePCM(data, request: request) }
            DispatchQueue.main.async {
                guard let self, self.generation == generation else { return }
                self.request = nil; self.decoding = false
                switch result {
                case .success(let result):
                    self.seconds = result["seconds"] as? Double
                    self.apply(result["text"] as? String ?? "", final: final, covered: covered, full: full)
                case .failure(let error):
                    _ = try? self.microphone.access { $0.drop(first: covered) }
                    self.message = error.localizedDescription
                    if self.state == .recognizing { self.state = .ready }
                }
            }
        }
    }

    private func apply(_ text: String, final: Bool, covered: Int, full: Bool) {
        let heard = ArabicMatching.words(text)
        if !heard.isEmpty { transcript = text }
        let event = heard.isEmpty ? .none : tracker.apply(heard, final: final)
        if final || full || event != .none {
            _ = try? microphone.access { $0.drop(first: covered) }
            tracker.reset(to: final || event != .none ? tracker.stable : tracker.provisional)
        }
        if state == .recognizing { state = .ready }
        if case .mistake(let index, let missing) = event {
            refresh(at: index)
            message = "Possible \(missing ? "omission" : "wrong word"): \(allWords[index].text_uthmani). Listen, then continue from this word."
            if feedbackMode == "prompt" {
                microphone.stop()
                state = .ready
                playWord()
            } else if feedbackMode == "buzzer" { UINotificationFeedbackGenerator().notificationOccurred(.warning) }
            return
        }
        refresh()
        if tracker.stable >= allWords.count {
            endListening("Al-Fatihah complete. Repetitions and pronunciation still need checking.")
        } else if finishing && final {
            endListening("Stopped at ayah \(ayah), word \(cursor + 1).")
        } else if state == .listening {
            message = heard.isEmpty ? "Listening locally. Keep reciting." : "Following ayah \(ayah). Keep reciting."
        } else if heard.isEmpty {
            message = "No words recognized. Try again."
        } else {
            message = "Matched \(cursor) of \(words.count) words. Continue from the highlighted word."
        }
    }

    /// Publishes ayah/cursor for the UI: the last recognized word, or the word at `index`.
    private func refresh(at index: Int? = nil) {
        let all = allWords
        guard !all.isEmpty else { return }
        let g = index ?? max(tracker.stable, tracker.provisional)
        if index != nil || g == tracker.anchor {
            let word = all[min(g, all.count - 1)]
            ayah = word.ayah; cursor = g < all.count ? word.word_index_in_ayah - 1 : word.word_index_in_ayah
        } else {
            ayah = all[g - 1].ayah; cursor = all[g - 1].word_index_in_ayah
        }
    }

    private func endListening(_ text: String) {
        continuous = false; finishing = false
        microphone.stop()
        AudioSessionControl.deactivate()
        state = .ready; message = text
    }

    func playWord() {
        guard cursor < words.count else { return }
        play(ayah: ayah, word: words[cursor].word_index_in_ayah)
    }

    func playNextAyah() { if ayah < 7 { play(ayah: ayah + 1) } }

    private func play(ayah: Int, word: Int? = nil) {
        guard let library, state == .ready else { return }
        microphone.stop()
        do {
            let buffer = try library.buffer(ayah: ayah, word: word)
            state = .prompting
            let generation = self.generation
            Task { [weak self] in
                guard let self, self.generation == generation else { return }
                do {
                    try await self.player.play(buffer) { [weak self] in
                        guard let self, self.generation == generation else { return }
                        AudioSessionControl.deactivate()
                        self.state = .ready
                        // Microphone stays off while the prompt plays, then recitation resumes.
                        if self.continuous { Task { await self.listen() } }
                    }
                } catch {
                    guard self.generation == generation else { return }
                    AudioSessionControl.deactivate()
                    self.continuous = false
                    self.state = .ready; self.message = error.localizedDescription
                }
            }
        } catch { state = .ready; message = error.localizedDescription }
    }

    func stop() {
        generation = UUID()
        continuous = false; finishing = false; decoding = false
        request?.cancel(); request = nil
        microphone.stop(); player.stop()
        state = .ready
        AudioSessionControl.deactivate()
        message = isLoaded ? "Stopped. Tap Listen when ready." : "Load the model to begin."
    }
}
