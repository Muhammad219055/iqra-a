import Foundation
import Combine
import SwiftUI

@MainActor
public final class RecitationCoordinator: ObservableObject {
    @Published public var words: [QuranWord] = []
    @Published public var wordStatuses: [String: WordRecitationStatus] = [:]
    @Published public var isRecording: Bool = false
    @Published public var statusMessage: String = "Ready to recite. Press Start."
    @Published public var isPrompting: Bool = false
    @Published public var micStatus: String = "Mic: Idle"

    @Published public var selectedQari: ReciterChoice = .mishari
    @Published public var selectedMode: FeedbackMode = .teacherPrompt
    @Published public var promptWordCount: Int = 3
    @Published public var isMemorizeMode: Bool = false

    @Published public var stats = RecitationSessionStats()

    private let audioCapture = AudioCaptureService()
    private let promptPlayer = PromptAudioPlayer()
    private var webSocketTask: URLSessionWebSocketTask?
    private var currentHost: String = "192.168.19.137:8000"

    public init() {
        loadSurahData()
        setupAudioCapture()
    }

    private func loadSurahData() {
        guard let url = Bundle.main.url(forResource: "quran_surah_1", withExtension: "json") ??
              Bundle(for: Self.self).url(forResource: "quran_surah_1", withExtension: "json") else {
            print("Warning: quran_surah_1.json not found in bundle.")
            return
        }

        do {
            let data = try Data(contentsOf: url)
            let surah = try JSONDecoder().decode(SurahData.self, from: data)
            self.words = surah.words
            resetWordStatuses()
        } catch {
            print("Failed to decode Quran text: \(error)")
        }
    }

    public func resetWordStatuses() {
        var statuses: [String: WordRecitationStatus] = [:]
        for w in words {
            statuses[w.id] = isMemorizeMode ? .hidden : .normal
        }
        self.wordStatuses = statuses
    }

    public func toggleMemorizeMode() {
        isMemorizeMode.toggle()
        for w in words {
            if wordStatuses[w.id] != .matched {
                wordStatuses[w.id] = isMemorizeMode ? .hidden : .normal
            }
        }
    }

    public func peekWord(_ word: QuranWord) {
        if wordStatuses[word.id] == .hidden {
            wordStatuses[word.id] = .normal
            stats.peeksCount += 1
        }
    }

    private func setupAudioCapture() {
        audioCapture.onAudioChunk = { [weak self] pcmData in
            guard let self = self else { return }
            self.sendAudioChunk(pcmData)
        }
    }

    public func toggleRecording(serverHost: String = "127.0.0.1:8000") {
        if isRecording {
            stopRecording()
        } else {
            startRecording(serverHost: serverHost)
        }
    }

    public func startRecording(serverHost: String = "127.0.0.1:8000") {
        self.currentHost = serverHost
        self.isRecording = true
        self.statusMessage = "Connecting to ASR Engine..."
        self.micStatus = "Mic: Active"
        self.stats = RecitationSessionStats()
        resetWordStatuses()

        connectWebSocket()

        do {
            try audioCapture.start()
        } catch {
            self.statusMessage = "Mic error: \(error.localizedDescription)"
            self.isRecording = false
        }
    }

    public func stopRecording() {
        isRecording = false
        micStatus = "Mic: Idle"
        statusMessage = "Recitation stopped."
        audioCapture.stop()
        disconnectWebSocket()
    }

    private func connectWebSocket() {
        guard let url = URL(string: "ws://\(currentHost)/ws/recite") else { return }
        let session = URLSession(configuration: .default)
        webSocketTask = session.webSocketTask(with: url)
        webSocketTask?.resume()

        // Send START_SESSION
        let startMsg: [String: Any] = [
            "event": "START_SESSION",
            "surah": 1,
            "reciter": selectedQari.key,
            "prompt_words": promptWordCount,
            "mode": selectedMode == .teacherPrompt ? "prompt" : (selectedMode == .buzzer ? "buzzer" : "silent"),
            "start_ayah": 1
        ]
        if let jsonStr = try? String(data: JSONSerialization.data(withJSONObject: startMsg), encoding: .utf8) {
            webSocketTask?.send(.string(jsonStr)) { _ in }
        }

        listenToWebSocket()
    }

    private func listenToWebSocket() {
        webSocketTask?.receive { [weak self] result in
            guard let self = self else { return }
            switch result {
            case .success(let message):
                switch message {
                case .string(let text):
                    Task { @MainActor in
                        self.handleServerMessage(text)
                    }
                case .data(let data):
                    if let text = String(data: data, encoding: .utf8) {
                        Task { @MainActor in
                            self.handleServerMessage(text)
                        }
                    }
                @unknown default:
                    break
                }
                // Continue listening
                self.listenToWebSocket()

            case .failure(let error):
                print("WebSocket error: \(error)")
            }
        }
    }

    private func disconnectWebSocket() {
        let stopMsg = "{\"event\": \"STOP_SESSION\"}"
        webSocketTask?.send(.string(stopMsg)) { _ in }
        webSocketTask?.cancel(with: .goingAway, reason: nil)
        webSocketTask = nil
    }

    private func sendAudioChunk(_ data: Data) {
        guard isRecording, !isPrompting else { return }
        webSocketTask?.send(.data(data)) { error in
            if let error = error {
                print("Error sending PCM chunk: \(error)")
            }
        }
    }

    private func handleServerMessage(_ jsonString: String) {
        guard let data = jsonString.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let event = json["event"] as? String else {
            return
        }

        switch event {
        case "SESSION_STARTED":
            statusMessage = "Listening... Recite Al-Fatiha."

        case "WORD_MATCH":
            if let surah = json["surah"] as? Int,
               let ayah = json["ayah"] as? Int,
               let word = json["word"] as? Int,
               let text = json["text_uthmani"] as? String {
                let id = "\(surah):\(ayah):\(word)"
                wordStatuses[id] = .matched
                stats.matchedCount += 1
                statusMessage = "Reciting: \(text)"
            }

        case "PAUSE_MIC":
            audioCapture.setMuted(true)
            micStatus = "Mic: Paused (Prompting)"
            isPrompting = true

        case "PLAY_PROMPT":
            stats.promptsCount += 1
            if let surah = json["surah"] as? Int,
               let ayah = json["ayah"] as? Int,
               let word = json["word"] as? Int,
               let promptText = json["prompt_text"] as? String,
               let audioB64 = json["audio_b64"] as? String,
               let audioData = Data(base64Encoded: audioB64) {

                let id = "\(surah):\(ayah):\(word)"
                wordStatuses[id] = .prompted
                statusMessage = "Teacher prompting: \(promptText)"

                promptPlayer.playAudioData(audioData) { [weak self] in
                    guard let self = self else { return }
                    // 150ms echo drain
                    DispatchQueue.main.asyncAfter(deadline: .now() + 0.15) {
                        self.webSocketTask?.send(.string("{\"event\": \"PROMPT_FINISHED\"}")) { _ in }
                    }
                }
            }

        case "RESUME_MIC":
            audioCapture.setMuted(false)
            micStatus = "Mic: Active"
            isPrompting = false
            statusMessage = "Continue reciting..."

        case "BUZZER_ALERT":
            stats.mistakesCount += 1
            statusMessage = "Buzzer alert: Mistake detected"

        case "SILENT_HIGHLIGHT":
            stats.mistakesCount += 1
            if let surah = json["surah"] as? Int,
               let ayah = json["ayah"] as? Int,
               let word = json["word"] as? Int {
                let id = "\(surah):\(ayah):\(word)"
                wordStatuses[id] = .mistake
            }

        default:
            break
        }
    }
}
