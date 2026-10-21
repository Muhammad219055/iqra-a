import AVFoundation
import Foundation

public final class PromptAudioPlayer: NSObject, AVAudioPlayerDelegate {
    private var audioPlayer: AVAudioPlayer?
    private var onFinished: (() -> Void)?

    public override init() {
        super.init()
    }

    public func playAudioData(_ data: Data, onFinished: @escaping () -> Void) {
        self.onFinished = onFinished
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default)
            try session.setActive(true)

            audioPlayer = try AVAudioPlayer(data: data)
            audioPlayer?.delegate = self
            audioPlayer?.prepareToPlay()
            audioPlayer?.play()
        } catch {
            print("Failed to play prompt audio: \(error)")
            onFinished()
        }
    }

    public func playAudioFile(url: URL, onFinished: @escaping () -> Void) {
        self.onFinished = onFinished
        do {
            let session = AVAudioSession.sharedInstance()
            try session.setCategory(.playback, mode: .default)
            try session.setActive(true)

            audioPlayer = try AVAudioPlayer(contentsOf: url)
            audioPlayer?.delegate = self
            audioPlayer?.prepareToPlay()
            audioPlayer?.play()
        } catch {
            print("Failed to play audio file: \(error)")
            onFinished()
        }
    }

    public func stop() {
        audioPlayer?.stop()
        audioPlayer = nil
    }

    public func audioPlayerDidFinishPlaying(_ player: AVAudioPlayer, successfully flag: Bool) {
        onFinished?()
        onFinished = nil
    }
}
