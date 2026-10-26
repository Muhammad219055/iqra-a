import Foundation

enum ArabicMatching {
    // Keep these substitutions aligned with src/aligner/normalizer.py.
    static func words(_ text: String) -> [String] {
        var normalized = text
        for (pattern, replacement) in [
            (#"[\u064B-\u065F\u0670\u06D6-\u06ED\u0640]"#, ""),
            (#"[\u0622\u0623\u0625\u0671]"#, "ا"),
            (#"\u0649"#, "ي"), (#"\u0629"#, "ه"),
            (#"\u0624"#, "و"), (#"\u0626"#, "ي"),
            (#"[^\u0621-\u064A\s]"#, "")
        ] {
            normalized = normalized.replacingOccurrences(of: pattern, with: replacement,
                                                         options: .regularExpression)
        }
        return normalized.split(whereSeparator: \.isWhitespace).map(String.init)
    }
}
