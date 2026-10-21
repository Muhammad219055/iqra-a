import SwiftUI

public struct ControlsBarView: View {
    @ObservedObject var coordinator: RecitationCoordinator
    @Binding var serverHost: String

    public init(coordinator: RecitationCoordinator, serverHost: Binding<String>) {
        self.coordinator = coordinator
        self._serverHost = serverHost
    }

    public var body: some View {
        VStack(spacing: 16) {
            // Reciter & Mode Selectors
            HStack(spacing: 12) {
                Picker("Qari", selection: $coordinator.selectedQari) {
                    ForEach(ReciterChoice.allCases) { qari in
                        Text(qari.rawValue).tag(qari)
                    }
                }
                .pickerStyle(.menu)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Color(red: 0.12, green: 0.14, blue: 0.18))
                .cornerRadius(8)

                Picker("Mode", selection: $coordinator.selectedMode) {
                    ForEach(FeedbackMode.allCases) { mode in
                        Text(mode.rawValue).tag(mode)
                    }
                }
                .pickerStyle(.menu)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Color(red: 0.12, green: 0.14, blue: 0.18))
                .cornerRadius(8)
            }

            // Memorize Toggle & Server Host
            HStack(spacing: 16) {
                Toggle("Memorize", isOn: Binding(
                    get: { coordinator.isMemorizeMode },
                    set: { _ in coordinator.toggleMemorizeMode() }
                ))
                .toggleStyle(SwitchToggleStyle(tint: Color(red: 0.9, green: 0.75, blue: 0.4)))
                .frame(maxWidth: 160)

                HStack {
                    Image(systemName: "network")
                        .foregroundColor(.secondary)
                    TextField("Server: 127.0.0.1:8000", text: $serverHost)
                        .font(.caption)
                        .textFieldStyle(.plain)
                        .foregroundColor(.white)
                }
                .padding(8)
                .background(Color(red: 0.1, green: 0.12, blue: 0.16))
                .cornerRadius(8)
            }

            // Big Start/Stop Reciting Button
            Button(action: {
                coordinator.toggleRecording(serverHost: serverHost)
            }) {
                HStack(spacing: 10) {
                    Image(systemName: coordinator.isRecording ? "stop.fill" : "mic.fill")
                        .font(.title3)
                    Text(coordinator.isRecording ? "Stop Reciting" : "Start Reciting")
                        .font(.headline)
                        .fontWeight(.semibold)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 14)
                .foregroundColor(coordinator.isRecording ? .white : Color(red: 0.08, green: 0.09, blue: 0.12))
                .background(
                    RoundedRectangle(cornerRadius: 12)
                        .fill(coordinator.isRecording ? Color.red : Color(red: 0.9, green: 0.75, blue: 0.4))
                )
                .shadow(color: coordinator.isRecording ? Color.red.opacity(0.4) : Color.clear, radius: 8)
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 14)
                .fill(Color(red: 0.07, green: 0.08, blue: 0.1))
        )
    }
}
