import SwiftUI

public struct ContentView: View {
    @StateObject private var coordinator = RecitationCoordinator()
    @State private var serverHost: String = "192.168.19.137:8000"

    public init() {}

    public var body: some View {
        ZStack {
            Color(red: 0.05, green: 0.06, blue: 0.08)
                .ignoresSafeArea()

            ScrollView {
                VStack(spacing: 20) {
                    // Header Status
                    HStack {
                        HStack(spacing: 8) {
                            Circle()
                                .fill(coordinator.isRecording ? Color.green : Color.secondary)
                                .frame(width: 10, height: 10)
                            Text(coordinator.statusMessage)
                                .font(.subheadline)
                                .foregroundColor(.white)
                                .lineLimit(1)
                        }

                        Spacer()

                        Text(coordinator.micStatus)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .padding(.horizontal, 4)

                    // Mushaf View Card
                    MushafView(coordinator: coordinator)

                    // Session Statistics
                    StatsView(coordinator: coordinator)

                    // Controls & Recording Button
                    ControlsBarView(coordinator: coordinator, serverHost: $serverHost)
                }
                .padding(16)
            }
        }
    }
}
