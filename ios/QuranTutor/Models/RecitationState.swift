import Foundation

public enum FeedbackMode: String, CaseIterable, Identifiable {
    case teacherPrompt = "Teacher Prompt"
    case buzzer = "Buzzer"
    case silent = "Silent"

    public var id: String { rawValue }
}

public enum ReciterChoice: String, CaseIterable, Identifiable {
    case mishari = "Mishari Rashid"
    case husary = "Mahmoud Al-Husary"

    public var id: String { rawValue }
    public var key: String {
        switch self {
        case .mishari: return "mishari"
        case .husary: return "husary"
        }
    }
}

public struct RecitationSessionStats {
    public var matchedCount: Int = 0
    public var mistakesCount: Int = 0
    public var promptsCount: Int = 0
    public var peeksCount: Int = 0

    public var accuracy: Double {
        let total = matchedCount + mistakesCount
        guard total > 0 else { return 0.0 }
        return (Double(matchedCount) / Double(total)) * 100.0
    }
}
