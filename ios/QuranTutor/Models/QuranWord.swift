import Foundation

public enum WordRecitationStatus: Equatable {
    case normal
    case matched
    case active
    case mistake
    case prompted
    case hidden
}

public struct QuranWord: Identifiable, Codable, Equatable {
    public var id: String { "\(surah):\(ayah):\(word_index_in_ayah)" }
    public let surah: Int
    public let ayah: Int
    public let word_index_in_ayah: Int
    public let word_index_global: Int
    public let text_uthmani: String
    public let normalized: String
    public var start_ms: Double?
    public var end_ms: Double?

    public init(
        surah: Int,
        ayah: Int,
        word_index_in_ayah: Int,
        word_index_global: Int,
        text_uthmani: String,
        normalized: String,
        start_ms: Double? = nil,
        end_ms: Double? = nil
    ) {
        self.surah = surah
        self.ayah = ayah
        self.word_index_in_ayah = word_index_in_ayah
        self.word_index_global = word_index_global
        self.text_uthmani = text_uthmani
        self.normalized = normalized
        self.start_ms = start_ms
        self.end_ms = end_ms
    }
}

public struct SurahData: Codable {
    public let surah: Int
    public let total_ayahs: Int
    public let total_words: Int
    public let words: [QuranWord]
}
