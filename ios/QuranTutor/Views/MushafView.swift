import SwiftUI

public extension Font {
    static func quranic(size: CGFloat) -> Font {
        // Try KFGQPC Hafs font first, then Amiri Quran, then fallback
        if UIFont(name: "KFGQPCHAFSUthmanicScript-Regula", size: size) != nil {
            return .custom("KFGQPCHAFSUthmanicScript-Regula", size: size)
        } else if UIFont(name: "KFGQPC HAFS Uthmanic Script", size: size) != nil {
            return .custom("KFGQPC HAFS Uthmanic Script", size: size)
        } else if UIFont(name: "AmiriQuran-Regular", size: size) != nil {
            return .custom("AmiriQuran-Regular", size: size)
        } else {
            return .system(size: size, weight: .regular, design: .serif)
        }
    }
}

public struct MushafView: View {
    @ObservedObject var coordinator: RecitationCoordinator

    public init(coordinator: RecitationCoordinator) {
        self.coordinator = coordinator
    }

    public var body: some View {
        VStack(spacing: 16) {
            // Authentic Ornate Surah Header Frame
            SurahHeaderFrame(title: "سُورَةُ الفَاتِحَةِ", versesCount: 7)

            // Medina Mushaf Symmetrical Verse-by-Verse Layout
            VStack(spacing: 5) {
                // Verse 1: Basmalah
                verseLine(ayahNumber: 1, words: wordsFor(ayah: 1))

                // Verse 2
                verseLine(ayahNumber: 2, words: wordsFor(ayah: 2))

                // Verse 3
                verseLine(ayahNumber: 3, words: wordsFor(ayah: 3))

                // Verse 4
                verseLine(ayahNumber: 4, words: wordsFor(ayah: 4))

                // Verse 5
                verseLine(ayahNumber: 5, words: wordsFor(ayah: 5))

                // Verse 6
                verseLine(ayahNumber: 6, words: wordsFor(ayah: 6))

                // Verse 7 (Divided across two balanced lines as in printed Madani Mushaf)
                let ayah7Words = wordsFor(ayah: 7)
                if ayah7Words.count >= 9 {
                    verseLine(ayahNumber: nil, words: Array(ayah7Words[0..<4]))
                    verseLine(ayahNumber: 7, words: Array(ayah7Words[4..<ayah7Words.count]))
                } else {
                    verseLine(ayahNumber: 7, words: ayah7Words)
                }
            }
            .environment(\.layoutDirection, .rightToLeft)
            .padding(.vertical, 2)
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(Color(red: 0.07, green: 0.08, blue: 0.11))
                .overlay(
                    // Classical double ornate gold border
                    RoundedRectangle(cornerRadius: 16)
                        .stroke(
                            LinearGradient(
                                colors: [Color(red: 0.85, green: 0.7, blue: 0.35), Color(red: 0.5, green: 0.4, blue: 0.2)],
                                startPoint: .topLeading,
                                endPoint: .bottomTrailing
                            ),
                            lineWidth: 2
                        )
                        .padding(3)
                        .overlay(
                            RoundedRectangle(cornerRadius: 14)
                                .stroke(Color(red: 0.85, green: 0.7, blue: 0.35).opacity(0.3), lineWidth: 1)
                        )
                )
        )
    }

    private func wordsFor(ayah: Int) -> [QuranWord] {
        coordinator.words.filter { $0.ayah == ayah }
    }

    @ViewBuilder
    private func verseLine(ayahNumber: Int?, words: [QuranWord]) -> some View {
        HStack(spacing: 3) {
            ForEach(words) { word in
                let status = coordinator.wordStatuses[word.id] ?? .normal
                QuranWordItemView(word: word, status: status) {
                    coordinator.peekWord(word)
                }
            }

            if let num = ayahNumber {
                AyahBadgeView(ayahNumber: num)
            }
        }
        .frame(maxWidth: .infinity, alignment: .center)
    }
}

// Ornate Medina Surah Banner Header
public struct SurahHeaderFrame: View {
    let title: String
    let versesCount: Int

    public var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: 10)
                .fill(
                    LinearGradient(
                        colors: [Color(red: 0.18, green: 0.15, blue: 0.1), Color(red: 0.12, green: 0.1, blue: 0.06)],
                        startPoint: .top,
                        endPoint: .bottom
                    )
                )
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .stroke(Color(red: 0.85, green: 0.7, blue: 0.35), lineWidth: 1.5)
                )

            HStack {
                Text("آيَاتُهَا ٧")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(Color(red: 0.85, green: 0.7, blue: 0.35))

                Spacer()

                Text(title)
                    .font(.quranic(size: 26))
                    .foregroundColor(Color(red: 0.95, green: 0.82, blue: 0.45))
                    .shadow(color: Color(red: 0.85, green: 0.7, blue: 0.35).opacity(0.3), radius: 4)

                Spacer()

                Text("مَكِّيَّةٌ")
                    .font(.system(size: 11, weight: .bold))
                    .foregroundColor(Color(red: 0.85, green: 0.7, blue: 0.35))
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 8)
        }
        .frame(height: 52)
    }
}

// Word Item with accurate Quranic shaping and highlights
public struct QuranWordItemView: View {
    let word: QuranWord
    let status: WordRecitationStatus
    let onTap: () -> Void

    public var body: some View {
        Text(word.text_uthmani)
            .font(.quranic(size: 18))
            .foregroundColor(textColor)
            .padding(.horizontal, 2)
            .padding(.vertical, 1)
            .background(
                RoundedRectangle(cornerRadius: 5)
                    .fill(backgroundColor)
            )
            .blur(radius: status == .hidden ? 7 : 0)
            .opacity(status == .hidden ? 0.25 : 1.0)
            .animation(.easeInOut(duration: 0.2), value: status)
            .onTapGesture {
                onTap()
            }
    }

    private var textColor: Color {
        switch status {
        case .matched:
            return Color(red: 0.45, green: 0.95, blue: 0.55)
        case .mistake:
            return Color(red: 1.0, green: 0.4, blue: 0.4)
        case .prompted:
            return Color(red: 0.55, green: 0.85, blue: 1.0)
        default:
            return Color(red: 0.95, green: 0.95, blue: 0.96)
        }
    }

    private var backgroundColor: Color {
        switch status {
        case .matched:
            return Color.green.opacity(0.18)
        case .mistake:
            return Color.red.opacity(0.25)
        case .prompted:
            return Color.blue.opacity(0.3)
        case .active:
            return Color.yellow.opacity(0.25)
        default:
            return Color.clear
        }
    }
}

// Classical Ayah Number Circle Badge
public struct AyahBadgeView: View {
    let ayahNumber: Int

    public var body: some View {
        ZStack {
            Circle()
                .stroke(Color(red: 0.85, green: 0.7, blue: 0.35), lineWidth: 1.2)
                .frame(width: 22, height: 22)

            Text(toArabicNumerals(ayahNumber))
                .font(.system(size: 11, weight: .bold, design: .serif))
                .foregroundColor(Color(red: 0.85, green: 0.7, blue: 0.35))
        }
        .padding(.horizontal, 3)
    }

    private func toArabicNumerals(_ num: Int) -> String {
        let arabicDigits = ["٠", "١", "٢", "٣", "٤", "٥", "٦", "٧", "٨", "٩"]
        return String(num).map { char in
            if let digit = Int(String(char)), digit < arabicDigits.count {
                return arabicDigits[digit]
            }
            return String(char)
        }.joined()
    }
}
