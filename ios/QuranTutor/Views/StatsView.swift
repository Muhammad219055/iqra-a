import SwiftUI

public struct StatsView: View {
    @ObservedObject var coordinator: RecitationCoordinator

    public init(coordinator: RecitationCoordinator) {
        self.coordinator = coordinator
    }

    public var body: some View {
        HStack(spacing: 12) {
            StatCard(label: "MATCHED", value: "\(coordinator.stats.matchedCount)", color: .green)
            StatCard(label: "MISTAKES", value: "\(coordinator.stats.mistakesCount)", color: .red)
            StatCard(label: "PROMPTS", value: "\(coordinator.stats.promptsCount)", color: .blue)
            StatCard(label: "PEEKS", value: "\(coordinator.stats.peeksCount)", color: .orange)
        }
    }
}

public struct StatCard: View {
    let label: String
    let value: String
    let color: Color

    public var body: some View {
        VStack(spacing: 4) {
            Text(value)
                .font(.system(size: 20, weight: .bold))
                .foregroundColor(color)
            Text(label)
                .font(.system(size: 9, weight: .semibold))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color(red: 0.1, green: 0.12, blue: 0.16))
        )
    }
}
