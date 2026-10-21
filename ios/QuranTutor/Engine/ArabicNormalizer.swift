import Foundation

public struct ArabicNormalizer {

    private static let harakatSet: CharacterSet = {
        var set = CharacterSet()
        // 0x064B to 0x065F (Fathah, Dammah, Kasrah, Sukun, Shaddah, Tanween)
        for code in 0x064B...0x065F {
            if let scalar = UnicodeScalar(code) { set.insert(scalar) }
        }
        // Dagger Alif (0x0670) and Quranic Waqf symbols (0x06D6 to 0x06ED)
        if let dagger = UnicodeScalar(0x0670) { set.insert(dagger) }
        for code in 0x06D6...0x06ED {
            if let scalar = UnicodeScalar(code) { set.insert(scalar) }
        }
        return set
    }()

    public static func stripHarakat(_ text: String) -> String {
        return text.unicodeScalars.filter { !harakatSet.contains($0) }.map { String($0) }.joined()
    }

    public static func normalizeForMatching(_ text: String) -> String {
        guard !text.isEmpty else { return "" }
        var t = stripHarakat(text)

        // Strip tatweel (kashida \u0640)
        t = t.replacingOccurrences(of: "\u{0640}", with: "")

        // Normalize forms of Alif: أ, إ, آ, ٱ -> ا
        t = t.replacingOccurrences(of: "[\u{0622}\u{0623}\u{0625}\u{0671}]", with: "\u{0627}", options: .regularExpression)

        // Normalize Alif Maqsura (ى) -> Yaa (ي)
        t = t.replacingOccurrences(of: "\u{0649}", with: "\u{064A}")

        // Normalize Taa Marbuta (ة) -> Haa (ه)
        t = t.replacingOccurrences(of: "\u{0629}", with: "\u{0647}")

        // Normalize Waw with Hamza (ؤ) -> و and Yaa with Hamza (ئ) -> ي
        t = t.replacingOccurrences(of: "\u{0624}", with: "\u{0648}")
        t = t.replacingOccurrences(of: "\u{0626}", with: "\u{064A}")

        // Remove non-Arabic characters except whitespace
        t = t.replacingOccurrences(of: "[^\u{0621}-\u{064A}\\s]", with: "", options: .regularExpression)

        // Collapse multiple spaces
        t = t.replacingOccurrences(of: "\\s+", with: " ", options: .regularExpression).trimmingCharacters(in: .whitespacesAndNewlines)

        return t
    }

    public static func levenshteinDistance(_ s1: String, _ s2: String) -> Int {
        let a = Array(s1)
        let b = Array(s2)
        let m = a.count
        let n = b.count

        if m == 0 { return n }
        if n == 0 { return m }

        var dp = Array(repeating: Array(repeating: 0, count: n + 1), count: m + 1)
        for i in 0...m { dp[i][0] = i }
        for j in 0...n { dp[0][j] = j }

        for i in 1...m {
            for j in 1...n {
                let cost = a[i - 1] == b[j - 1] ? 0 : 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,       // deletion
                    dp[i][j - 1] + 1,       // insertion
                    dp[i - 1][j - 1] + cost // substitution
                )
            }
        }
        return dp[m][n]
    }
}
