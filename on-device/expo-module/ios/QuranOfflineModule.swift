import ExpoModulesCore
import Combine
import AVFoundation

public final class QuranOfflineModule: Module {
    @MainActor private var session: ListeningSession?
    @MainActor private var observer: AnyCancellable?
    @MainActor private var notificationObservers: [NSObjectProtocol] = []

    public func definition() -> ModuleDefinition {
        Name("QuranOffline")
        Events("onChange")
        AsyncFunction("prepare") { () async throws -> Void in
            await MainActor.run { self.getSession().prepare() }
            for _ in 0..<600 {
                let loading = await MainActor.run { self.getSession().state == .loading }
                if !loading { break }
                try await Task.sleep(nanoseconds: 50_000_000)
            }
            try await MainActor.run {
                guard self.getSession().isLoaded else {
                    throw NSError(domain: "QuranOffline", code: 1,
                                  userInfo: [NSLocalizedDescriptionKey: self.getSession().message])
                }
                self.publish()
            }
        }
        AsyncFunction("listen") { () async -> Void in await self.getSession().listen() }
        AsyncFunction("stop") { () async -> Void in await MainActor.run { self.session?.stop() } }
        AsyncFunction("finish") { () async -> Void in await MainActor.run { self.session?.finish() } }
        AsyncFunction("selectAyah") { (ayah: Int) async -> Void in
            await MainActor.run { self.getSession().select(ayah: ayah) }
        }
        AsyncFunction("selectReciter") { (reciter: String) async throws -> Void in
            try await MainActor.run { try self.getSession().selectReciter(reciter) }
        }
        AsyncFunction("setFeedbackMode") { (mode: String) async -> Void in
            await MainActor.run { self.getSession().setFeedbackMode(mode) }
        }
        AsyncFunction("playWord") { () async -> Void in await MainActor.run { self.getSession().playWord() } }
        AsyncFunction("playNextAyah") { () async -> Void in await MainActor.run { self.getSession().playNextAyah() } }
        OnAppEntersBackground { Task { @MainActor in self.session?.stop() } }
        OnDestroy { Task { @MainActor in
            self.session?.stop(); self.observer = nil
            self.notificationObservers.forEach { NotificationCenter.default.removeObserver($0) }
            self.notificationObservers = []
        } }
    }

    @MainActor private func getSession() -> ListeningSession {
        if let session { return session }
        let session = ListeningSession()
        self.session = session
        observer = session.objectWillChange.sink { [weak self] _ in
            DispatchQueue.main.async { self?.publish() }
        }
        for name in [AVAudioSession.interruptionNotification, AVAudioSession.routeChangeNotification] {
            notificationObservers.append(NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { [weak session] note in
                if name == AVAudioSession.routeChangeNotification,
                   (note.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt) == AVAudioSession.RouteChangeReason.categoryChange.rawValue { return }
                if name == AVAudioSession.interruptionNotification,
                   (note.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt) != AVAudioSession.InterruptionType.began.rawValue { return }
                Task { @MainActor in session?.stop() }
            })
        }
        return session
    }

    @MainActor private func publish() {
        guard let session else { return }
        sendEvent("onChange", ["state": String(describing: session.state), "ayah": session.ayah,
                              "cursor": session.cursor, "message": session.message,
                              "transcript": session.transcript, "loaded": session.isLoaded,
                              "seconds": session.seconds])
    }
}
