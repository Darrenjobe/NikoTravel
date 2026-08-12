import SwiftUI

extension Color {
    static let hodPaper   = Color(red: 0.965, green: 0.949, blue: 0.914)
    static let hodCard    = Color(red: 1.000, green: 0.992, blue: 0.973)
    static let hodInk     = Color(red: 0.106, green: 0.102, blue: 0.090)
    static let hodMuted   = Color(red: 0.604, green: 0.580, blue: 0.510)
    static let hodAegean  = Color(red: 0.173, green: 0.373, blue: 0.486)
    static let hodTerra   = Color(red: 0.718, green: 0.357, blue: 0.227)
    static let hodOlive   = Color(red: 0.369, green: 0.443, blue: 0.275)
    static let hodCrimson = Color(red: 0.643, green: 0.290, blue: 0.220)
}

extension Font {
    static func hodDisplay(_ style: Font.TextStyle = .title2) -> Font {
        .system(style, design: .serif).weight(.semibold)
    }
    static func hodMeta(_ style: Font.TextStyle = .caption2) -> Font {
        .system(style, design: .monospaced).weight(.medium)
    }
}

struct HodLabel: View {
    let text: String
    var color: Color = .hodMuted
    var body: some View {
        Text(text.uppercased())
            .font(.hodMeta())
            .kerning(1.6)
            .foregroundStyle(color)
    }
}

struct HoursPill: View {
    let hours: String
    private var isWarning: Bool {
        let h = hours.lowercased()
        return ["closes", "closed", "last entry", "until 15", "sunset"].contains { h.contains($0) }
    }
    var body: some View {
        Text(hours)
            .font(.caption.weight(.semibold))
            .padding(.horizontal, 9).padding(.vertical, 4)
            .background((isWarning ? Color.hodCrimson : .hodOlive).opacity(0.12), in: Capsule())
            .foregroundStyle(isWarning ? Color.hodCrimson : .hodOlive)
            .accessibilityLabel("Hours: \(hours)")
    }
}

struct HodScreen: ViewModifier {
    var tint: Color = .hodAegean
    func body(content: Content) -> some View {
        content
            .scrollContentBackground(.hidden)
            .background(Color.hodPaper)
            .tint(tint)
    }
}

extension View {
    func hodScreen(tint: Color = .hodAegean) -> some View { modifier(HodScreen(tint: tint)) }
}
