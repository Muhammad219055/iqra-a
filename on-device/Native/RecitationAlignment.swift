import Foundation

struct WordComparison: Equatable {
    enum Status { case match, missing, incorrect, extra, pending }
    let expectedIndex: Int?
    let heardIndex: Int?
    let status: Status
}

enum RecitationAlignment {
    /// Spelling conventions differ between the Uthmani text and Whisper output (العلمين/العالمين),
    /// so one edit in a word of four or more letters still counts as that word.
    static func same(_ a: String, _ b: String) -> Bool {
        if a == b { return true }
        let x = Array(a), y = Array(b)
        guard min(x.count, y.count) >= 4, abs(x.count - y.count) <= 1 else { return false }
        var row = Array(0...y.count)
        for i in 1...x.count {
            var previous = row[0]; row[0] = i
            for j in 1...y.count {
                let saved = row[j]
                row[j] = min(row[j] + 1, row[j - 1] + 1, previous + (x[i - 1] == y[j - 1] ? 0 : 1))
                previous = saved
            }
        }
        return row[y.count] <= 1
    }

    static func compare(expected: [String], heard: [String]) -> [WordComparison] {
        let m = expected.count, n = heard.count
        var costs = Array(repeating: Array(repeating: 0, count: n + 1), count: m + 1)
        for i in 0...m { costs[i][0] = i }
        for j in 0...n { costs[0][j] = j }
        if m > 0 && n > 0 {
            for i in 1...m {
                for j in 1...n {
                    costs[i][j] = min(costs[i - 1][j] + 1, costs[i][j - 1] + 1,
                                      costs[i - 1][j - 1] + (same(expected[i - 1], heard[j - 1]) ? 0 : 1))
                }
            }
        }
        var i = m, j = n
        var result: [WordComparison] = []
        var hasLaterSpeech = false
        while i > 0 || j > 0 {
            let equal = i > 0 && j > 0 && same(expected[i - 1], heard[j - 1])
            if i > 0 && j > 0 && costs[i][j] == costs[i - 1][j - 1] + (equal ? 0 : 1) {
                result.append(WordComparison(expectedIndex: i - 1, heardIndex: j - 1,
                                             status: equal ? .match : .incorrect))
                hasLaterSpeech = true
                i -= 1; j -= 1
            } else if i > 0 && costs[i][j] == costs[i - 1][j] + 1 {
                // A pause before finishing an ayah is not evidence of an omitted word.
                result.append(WordComparison(expectedIndex: i - 1, heardIndex: nil,
                                             status: hasLaterSpeech ? .missing : .pending))
                i -= 1
            } else {
                result.append(WordComparison(expectedIndex: nil, heardIndex: j - 1, status: .extra))
                j -= 1
            }
        }
        return result.reversed()
    }
}

/// Turns successive hypotheses for one audio window into passage progress.
/// Provisional progress follows the latest hypothesis; stable progress needs two agreeing
/// hypotheses or a pause. A suspected mistake is reported only when two hypotheses agree on it
/// and two later words were matched, or at a pause.
struct ProgressTracker {
    enum Event: Equatable { case none, mistake(index: Int, missing: Bool) }
    let expected: [String]
    private(set) var anchor = 0
    private(set) var stable = 0
    private(set) var provisional = 0
    private var lastProgress = 0
    private var lastSuspect: Int?

    init(expected: [String]) { self.expected = expected }

    /// Start a new audio window at `index`.
    mutating func reset(to index: Int) {
        anchor = min(max(0, index), expected.count)
        stable = anchor; provisional = anchor; lastProgress = anchor; lastSuspect = nil
    }

    mutating func apply(_ heard: [String], final: Bool) -> Event {
        guard anchor < expected.count else { return .none }
        var progress = anchor, matchesAfter = 0
        var suspect: (index: Int, missing: Bool)?
        for token in RecitationAlignment.compare(expected: Array(expected[anchor...]), heard: heard) {
            guard let index = token.expectedIndex.map({ anchor + $0 }) else { continue }
            switch token.status {
            case .match: if suspect == nil { progress = index + 1 } else { matchesAfter += 1 }
            case .missing, .incorrect: if suspect == nil { suspect = (index, token.status == .missing) }
            case .extra, .pending: break
            }
        }
        provisional = progress
        stable = max(stable, final ? progress : min(progress, lastProgress))
        lastProgress = progress
        defer { lastSuspect = suspect?.index }
        guard let suspect, suspect.index >= stable,
              final || (matchesAfter >= 2 && lastSuspect == suspect.index) else { return .none }
        stable = suspect.index; provisional = suspect.index
        return .mistake(index: suspect.index, missing: suspect.missing)
    }
}
