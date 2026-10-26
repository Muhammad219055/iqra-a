import XCTest
@testable import QuranOffline

final class OfflineTests: XCTestCase {
    func testVoiceGateRejectsQuietNoiseAndLongBuffers() throws {
        let path = try XCTUnwrap(Bundle.main.path(forResource: "ggml-model", ofType: "bin"))
        let engine = try QuranWhisper(modelPath: path)
        var seed: UInt32 = 20261022
        for rms: Float in [0.0031623, 0.01] {
            let samples: [Float] = (0..<80_000).map { _ in
                seed = 1664525 &* seed &+ 1013904223
                return (Float(seed) / Float(UInt32.max) * 2 - 1) * rms * sqrt(3)
            }
            let pcm = samples.withUnsafeBytes { Data($0) }
            let result = try engine.transcribePCM(pcm, request: QuranWhisperRequest())
            XCTAssertEqual(result["text"] as? String, "", "Room-level noise must not produce a correction.")
            XCTAssertEqual(result["noSpeech"] as? Bool, true)
        }
        XCTAssertThrowsError(try engine.transcribePCM(Data(repeating: 0, count: 240_001 * 4), request: QuranWhisperRequest()))
    }
    func testNativeRecognition() throws {
        let bundle = Bundle.main
        let model = try XCTUnwrap(bundle.url(forResource: "ggml-model", withExtension: "bin"))
        let engine = try QuranWhisper(modelPath: model.path)
        var evidence: [[String: Any]] = []
        let expected = [
            "ayah_1_clean": ["بسم", "الله", "الرحمن", "الرحيم"],
            "ayah_1_skipped_word3": ["بسم", "الله", "الرحيم"]
        ]
        for name in ["ayah_1_clean", "ayah_1_skipped_word3"] {
            let audio = try XCTUnwrap(bundle.url(forResource: name, withExtension: "wav"))
            let input = try AudioFile.pcm(audio).withUnsafeBytes { Array($0.bindMemory(to: Float.self)) }
            // Silent streaming replay: decode growing windows every 400 ms, then once at the pause.
            var rolling = RollingAudio()
            var tracker = ProgressTracker(expected: ["بسم", "الله", "الرحمن", "الرحيم"])
            var events: [ProgressTracker.Event] = []
            for offset in stride(from: 0, to: input.count, by: 6400) {
                try rolling.append(Array(input[offset..<min(input.count, offset + 6400)]))
                guard rolling.hasNewSpeech, rolling.samples.count >= 9600 else { continue }
                let partial = try engine.transcribePCM(rolling.snapshot().withUnsafeBytes { Data($0) }, request: QuranWhisperRequest())
                events.append(tracker.apply(ArabicMatching.words(partial["text"] as? String ?? ""), final: false))
            }
            try rolling.append(Array(repeating: 0, count: 14_400))
            let pcm = rolling.snapshot().withUnsafeBytes { Data($0) }
            let result = try engine.transcribePCM(pcm, request: QuranWhisperRequest())
            let text = try XCTUnwrap(result["text"] as? String)
            XCTAssertEqual(ArabicMatching.words(text), expected[name],
                           "The recognizer must preserve the omission instead of completing the ayah.")
            events.append(tracker.apply(ArabicMatching.words(text), final: true))
            let mistakes = events.filter { $0 != .none }
            XCTAssertEqual(mistakes, name == "ayah_1_clean" ? [] : [.mistake(index: 2, missing: true)],
                           "Exactly one correction, and none for a clean recitation.")
            if name == "ayah_1_clean" { XCTAssertEqual(tracker.stable, 4) }
            evidence.append(["fixture": name, "text": text, "seconds": result["seconds"]!])
        }
        let silence = Data(repeating: 0, count: 16_000 * 4)
        XCTAssertEqual(try engine.transcribePCM(silence, request: QuranWhisperRequest())["text"] as? String, "")
        XCTAssertThrowsError(try engine.transcribePCM(Data(), request: QuranWhisperRequest()))
        var nan = Float.nan
        let invalid = Data(bytes: &nan, count: 4)
        XCTAssertThrowsError(try engine.transcribePCM(Data(repeating: 0, count: 6396) + invalid,
                                                   request: QuranWhisperRequest()))
        let json = try JSONSerialization.data(withJSONObject: evidence, options: [.prettyPrinted, .sortedKeys])
        let attachment = XCTAttachment(data: json, uniformTypeIdentifier: "public.json")
        attachment.name = "offline-transcriptions"
        attachment.lifetime = .keepAlways
        add(attachment)
        print("OFFLINE_EVIDENCE " + String(decoding: json, as: UTF8.self))
    }

    func testArabicNormalization() {
        XCTAssertEqual(ArabicMatching.words("بِسْمِ ٱللَّهِ الرَّحْمَـٰنِ الرَّحِيمِ ۝١"),
                       ["بسم", "الله", "الرحمن", "الرحيم"])
        XCTAssertEqual(ArabicMatching.words("أ إ آ ٱ ى ة ؤ ئ"), ["ا", "ا", "ا", "ا", "ي", "ه", "و", "ي"])
    }

    func testCancellationBusyRejectionAndRecovery() throws {
        let model = try XCTUnwrap(Bundle.main.url(forResource: "ggml-model", withExtension: "bin"))
        let audio = try XCTUnwrap(Bundle.main.url(forResource: "ayah_1_clean", withExtension: "wav"))
        let engine = try QuranWhisper(modelPath: model.path)
        let pcm = try AudioFile.pcm(audio)
        let preCancelled = QuranWhisperRequest()
        preCancelled.cancel()
        XCTAssertThrowsError(try engine.transcribePCM(pcm, request: preCancelled)) {
            XCTAssertEqual(($0 as NSError).code, 4)
        }
        let request = QuranWhisperRequest()
        let cancelled = expectation(description: "Active native inference aborted")
        DispatchQueue.global(qos: .userInitiated).async {
            defer { cancelled.fulfill() }
            for _ in 0..<200 {
                do {
                    _ = try engine.transcribePCM(pcm, request: request)
                    XCTFail("An active cancelled call must not return a transcript.")
                    return
                } catch {
                    if (error as NSError).code == 2 {
                        Thread.sleep(forTimeInterval: 0.001)
                        continue
                    }
                    XCTAssertEqual((error as NSError).code, 4)
                    return
                }
            }
            XCTFail("The cancellation test could not start inference.")
        }
        var sawBusy = false
        for _ in 0..<200 {
            do { _ = try engine.transcribePCM(Data(repeating: 0, count: 6400), request: QuranWhisperRequest()) }
            catch {
                if (error as NSError).code == 2 { sawBusy = true; break }
                else { XCTFail("Unexpected error: \(error)") }
            }
            Thread.sleep(forTimeInterval: 0.005)
        }
        XCTAssertTrue(sawBusy, "Cancel only after proving the first call is active.")
        request.cancel()
        wait(for: [cancelled], timeout: 5)
        let recovered = try engine.transcribePCM(pcm, request: QuranWhisperRequest())
        XCTAssertEqual(ArabicMatching.words(try XCTUnwrap(recovered["text"] as? String)),
                       ["بسم", "الله", "الرحمن", "الرحيم"])
    }
}
