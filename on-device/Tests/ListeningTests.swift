import AVFoundation
import XCTest
@testable import QuranOffline

final class ListeningTests: XCTestCase {
    func testAlignmentDoesNotCallAnUnfinishedAyahAMistake() {
        let expected = ["بسم", "الله", "الرحمن", "الرحيم"]
        XCTAssertEqual(RecitationAlignment.compare(expected: expected, heard: ["بسم", "الله"]).map(\.status),
                       [.match, .match, .pending, .pending])
        XCTAssertEqual(RecitationAlignment.compare(expected: expected, heard: ["بسم", "الله", "الرحيم"]).map(\.status),
                       [.match, .match, .missing, .match])
        XCTAssertEqual(RecitationAlignment.compare(expected: expected, heard: ["بسم", "الله", "العالمين", "الرحيم"]).map(\.status),
                       [.match, .match, .incorrect, .match])
        let repetition = RecitationAlignment.compare(expected: expected, heard: ["بسم", "الله", "الله", "الرحمن", "الرحيم"])
        XCTAssertEqual(repetition.filter { $0.status == .extra }.count, 1)
        XCTAssertEqual(repetition.filter { $0.status == .match }.count, 4)
        XCTAssertEqual(RecitationAlignment.compare(expected: expected, heard: []).map(\.status),
                       [.pending, .pending, .pending, .pending])
        XCTAssertEqual(RecitationAlignment.compare(expected: [], heard: ["بسم"]).map(\.status), [.extra])
    }

    func testRollingAudioKeepsPrerollAndDropsCommittedAudio() throws {
        var audio = RollingAudio()
        try audio.append(Array(repeating: 0, count: 160_000))
        XCTAssertEqual(audio.samples.count, 3840, "Silence before speech keeps pre-roll only.")
        XCTAssertFalse(audio.heardSpeech)
        try audio.append(Array(repeating: 0.1, count: 3200))
        XCTAssertTrue(audio.hasNewSpeech)
        let snapshot = audio.snapshot()
        XCTAssertFalse(audio.hasNewSpeech)
        try audio.append(Array(repeating: 0, count: 16_000))
        XCTAssertEqual(audio.quietSeconds, 1, accuracy: 0.03)
        audio.drop(first: snapshot.count)
        XCTAssertEqual(audio.samples.count, 16_000, "Audio after the snapshot survives the drop.")
        try audio.append(Array(repeating: 0.1, count: 20 * 16_000))
        XCTAssertEqual(audio.snapshot().count, RollingAudio.maxSamples, "Each decode window is bounded.")
        var invalid = RollingAudio()
        XCTAssertThrowsError(try invalid.append([.nan]))
    }

    func testProgressTrackerReplay() {
        let words = ["بسم", "الله", "الرحمن", "الرحيم", "الحمد", "لله", "رب", "العلمين"]
        var tracker = ProgressTracker(expected: words)
        // Growing partials: provisional follows, stable needs two agreeing hypotheses.
        XCTAssertEqual(tracker.apply(["بسم", "الله"], final: false), .none)
        XCTAssertEqual(tracker.provisional, 2); XCTAssertEqual(tracker.stable, 0)
        XCTAssertEqual(tracker.apply(["بسم", "الله", "الرحمن"], final: false), .none)
        XCTAssertEqual(tracker.stable, 2)
        // Revised hypothesis: provisional falls back, stable never does.
        XCTAssertEqual(tracker.apply(["بسم", "الله", "الرحم"], final: false), .none)
        XCTAssertEqual(tracker.stable, 2)
        // Truncated trailing word is not a correction while speech continues.
        XCTAssertEqual(tracker.apply(["بسم", "الله", "الرحمن", "الر"], final: false), .none)
        // Spelling convention differences still match.
        XCTAssertEqual(tracker.apply(["بسم", "الله", "الرحمن", "الرحيم", "الحمد", "لله", "رب", "العالمين"], final: true), .none)
        XCTAssertEqual(tracker.stable, 8)

        // An omission needs two agreeing hypotheses with two later words.
        tracker.reset(to: 0)
        XCTAssertEqual(tracker.apply(["بسم", "الله", "الرحيم"], final: false), .none)
        XCTAssertEqual(tracker.apply(["بسم", "الله", "الرحيم", "الحمد"], final: false), .mistake(index: 2, missing: true))
        XCTAssertEqual(tracker.stable, 2)

        // After a pause it is reported immediately; a repetition is not a mistake.
        tracker.reset(to: 0)
        XCTAssertEqual(tracker.apply(["بسم", "الله", "الرحيم"], final: true), .mistake(index: 2, missing: true))
        tracker.reset(to: 0)
        XCTAssertEqual(tracker.apply(["بسم", "الله", "الله", "الرحمن", "الرحيم"], final: true), .none)
        XCTAssertEqual(tracker.stable, 4)
        // A new window that starts by repeating committed words only continues.
        tracker.reset(to: 4)
        XCTAssertEqual(tracker.apply(["الرحيم", "الحمد", "لله"], final: true), .none)
        XCTAssertEqual(tracker.stable, 6)
        // Empty and noise-only results never correct.
        tracker.reset(to: 6)
        XCTAssertEqual(tracker.apply([], final: true), .none)
        XCTAssertEqual(tracker.stable, 6)
    }

    func testHardwareRateConversionConsumesEachInputOnce() throws {
        for rate in [44_100.0, 48_000.0] {
            let format = try XCTUnwrap(AVAudioFormat(commonFormat: .pcmFormatFloat32,
                                                   sampleRate: rate, channels: 1, interleaved: false))
            let resampler = try PCMResampler(source: format)
            let frames = Int(rate / 10)
            var output: [Float] = []
            for chunk in 0..<10 {
                let input = try XCTUnwrap(AVAudioPCMBuffer(pcmFormat: format, frameCapacity: AVAudioFrameCount(frames)))
                input.frameLength = AVAudioFrameCount(frames)
                for i in 0..<frames {
                    input.floatChannelData![0][i] = Float(0.1 * sin(2 * .pi * 440 * Double(chunk * frames + i) / rate))
                }
                output += try resampler.convert(input)
            }
            output += try resampler.finish()
            XCTAssertLessThanOrEqual(abs(output.count - 16_000), 1, "Drain the converter without repeating input.")
            XCTAssertTrue(output.allSatisfy { $0.isFinite && abs($0) <= 1 })
            XCTAssertGreaterThan(output.map { $0 * $0 }.reduce(0, +) / Float(output.count), 0.004)
        }
    }

    func testAllBundledWordAndAyahPromptsHaveValidAudioRanges() throws {
        let library = try PromptLibrary()
        XCTAssertEqual(library.words.count, 29)
        for ayah in 1...7 {
            XCTAssertGreaterThan(try library.buffer(ayah: ayah).frameLength, 0)
            for word in library.words(ayah: ayah) {
                XCTAssertGreaterThan(try library.buffer(ayah: ayah, word: word.word_index_in_ayah).frameLength, 0)
            }
        }
        let word = try library.buffer(ayah: 1, word: 3)
        XCTAssertEqual(word.frameLength, 17_488) // 1409–2502 ms at 16 kHz.
        let next = try library.buffer(ayah: 2)
        XCTAssertEqual(next.frameLength, 88_400) // Word bounds include the start of الحمد.
        XCTAssertThrowsError(try library.buffer(ayah: 8))
        XCTAssertThrowsError(try library.buffer(ayah: 1, word: 5))
    }

    @MainActor
    func testLocalWordPlaybackCompletes() async throws {
        let player = LocalPromptPlayer(volume: 0)
        let finished = expectation(description: "Bundled word played to the local audio output")
        try await player.play(PromptLibrary().buffer(ayah: 1, word: 3)) { finished.fulfill() }
        await fulfillment(of: [finished], timeout: 5)
        player.stop()
        AudioSessionControl.deactivate()
    }

    @MainActor
    func testRecognizedOmissionTriggersLocalWordPromptAndStopDiscardsStaleResults() async throws {
        let session = ListeningSession(promptVolume: 0)
        session.prepare()
        for _ in 0..<200 where !session.isLoaded { try await Task.sleep(nanoseconds: 50_000_000) }
        XCTAssertTrue(session.isLoaded, session.message)
        session.example("ayah_1_skipped_word3")
        var heardPrompt = false
        for _ in 0..<200 {
            if session.state == .prompting { heardPrompt = true }
            if session.state == .ready { break }
            try await Task.sleep(nanoseconds: 50_000_000)
        }
        XCTAssertTrue(heardPrompt, "An internal omission should play its bundled word.")
        XCTAssertEqual(session.state, .ready)
        XCTAssertEqual(session.cursor, 2)
        XCTAssertTrue(session.message.contains("omission"), session.message)
        XCTAssertEqual(ArabicMatching.words(session.transcript), ["بسم", "الله", "الرحيم"])
        session.example("ayah_1_clean")
        session.stop()
        try await Task.sleep(nanoseconds: 2_000_000_000)
        XCTAssertEqual(session.state, .ready)
        XCTAssertEqual(session.cursor, 0)
        XCTAssertEqual(session.transcript, "", "Cancelled inference must not change the new session.")
        XCTAssertTrue(session.message.hasPrefix("Stopped"))
    }
}
