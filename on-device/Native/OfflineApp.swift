import SwiftUI
import AVFoundation

@main
struct OfflineApp: App {
    @StateObject private var session = ListeningSession()
    @Environment(\.scenePhase) private var scenePhase
    var body: some Scene {
        WindowGroup {
            NavigationStack {
                Form {
                    Section("Offline engine lab · Al-Fatihah") {
                        Text("Model, text and reciter audio are bundled. No server is used.")
                        Picker("Ayah", selection: Binding(get: { session.ayah }, set: { session.select(ayah: $0) })) {
                            ForEach(1...7, id: \.self) { Text(String($0)).tag($0) }
                        }
                        .disabled(session.state == .loading)
                        Text(session.words.map(\.text_uthmani).joined(separator: " "))
                            .font(.title2).multilineTextAlignment(.trailing)
                        if session.cursor < session.words.count {
                            Text("Continue from: \(session.words[session.cursor].text_uthmani)")
                        }
                        Text(session.message).accessibilityIdentifier("sessionMessage")
                        Text("State: \(String(describing: session.state))").accessibilityIdentifier("sessionState")
                        if !session.isLoaded {
                            Button("Load model") { session.prepare() }.disabled(session.state != .ready)
                        }
                        Button("Listen") { Task { await session.listen() } }
                            .disabled(!session.isLoaded || session.state != .ready)
                        Button("Finish recording") { session.finish() }.disabled(session.state != .listening)
                        Button("Stop", role: .destructive) { session.stop() }
                    }
                    Section("Local prompts") {
                        Button("Hear this word") { session.playWord() }
                            .disabled(!session.isLoaded || session.state != .ready || session.cursor == session.words.count)
                        Button("Hear next ayah") { session.playNextAyah() }
                            .disabled(!session.isLoaded || session.state != .ready || session.ayah == 7)
                        Text("The microphone stays off during checking and playback. Tap Listen to continue.")
                    }
                    Section("Recorded regression examples") {
                        Button("Clean ayah") { session.example("ayah_1_clean") }
                        Button("Ayah with a skipped word") { session.example("ayah_1_skipped_word3") }
                    }.disabled(!session.isLoaded || session.state != .ready)
                    if !session.transcript.isEmpty {
                        Section("Recognized") {
                            Text(session.transcript).accessibilityIdentifier("transcript")
                            if let seconds = session.seconds { Text(String(format: "Inference: %.2f seconds", seconds)) }
                        }
                    }
                }.navigationTitle("Local listening")
            }
            .onChange(of: scenePhase) { phase in if phase == .background { session.stop() } }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.interruptionNotification)) { note in
                if let raw = note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,
                   raw == AVAudioSession.InterruptionType.began.rawValue { session.stop() }
            }
            .onReceive(NotificationCenter.default.publisher(for: AVAudioSession.routeChangeNotification)) { note in
                if let raw = note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,
                   raw != AVAudioSession.RouteChangeReason.categoryChange.rawValue { session.stop() }
            }
        }
    }
}
