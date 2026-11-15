import SwiftUI

/// The JSON as text, in the biggest font that fits the space it is given.
struct JsonText: View {
    @Environment(\.isLuminanceReduced) private var dimmed
    var snapshot: Snapshot
    var mode = Mode.json
    var count = 0
    var now: Date
    var only: [String]? = nil   // the keys to show, when there is no room for all of them
    var braces = true

    var body: some View {
        let fields = snapshot.lines(now: now, count: mode == .count ? count : nil, only: only)
        let halo = Color(hex: snapshot.theme.halo).opacity(mode == .photo ? 0 : snapshot.theme.halo_alpha)
        GeometryReader { box in
            let fit = Layout.fit(fields, width: box.size.width, height: box.size.height, braces: braces)
            VStack(alignment: .leading, spacing: fit.gap) {
                if braces { brace("{", fit) }
                ForEach(Array(fit.rows.enumerated()), id: \.offset) { _, row in
                    text(row).frame(height: fit.rowHeight)
                }
                if braces { brace("}", fit) }
            }
            .font(.system(size: fit.font, design: .monospaced))
            .lineLimit(1)
            .minimumScaleFactor(0.5)
            .shadow(color: halo, radius: fit.font * 0.08)
            .shadow(color: halo, radius: fit.font * 0.3)
            .frame(width: box.size.width, height: box.size.height, alignment: .leading)
        }
        .opacity(mode == .photo ? 0.2 : 1)
    }

    private func brace(_ brace: String, _ fit: Fit) -> some View {
        Text(brace).foregroundStyle(color(.punct)).frame(height: fit.rowHeight)
    }

    private func text(_ row: Row) -> Text {
        var text = Text(String(repeating: " ", count: row.indent))
        for (i, word) in row.words.enumerated() {
            if i > 0 { text = Text("\(text) ") }
            for piece in word { text = Text("\(text)\(colored(piece))") }
        }
        return text
    }

    private func colored(_ piece: Piece) -> Text {
        guard piece.clock else { return Text(verbatim: piece.text).foregroundStyle(color(piece.ink)) }
        let clock = Clock(now: now)
        // With the wrist down the watch redraws once a minute, so no seconds then.
        if dimmed { return Text(verbatim: "\"\(clock.minute)\"").foregroundStyle(color(piece.ink)) }
        // The system keeps a timer text running by itself, in a widget too.
        return Text("\"\(clock.prefix)\(Text(clock.midnight, style: .timer))\"").foregroundStyle(color(piece.ink))
    }

    private func color(_ ink: Ink) -> Color {
        switch ink {
        case .punct: Color(hex: snapshot.theme.punct)
        case .key: Color(hex: snapshot.theme.key)
        case .str: Color(hex: snapshot.theme.str)
        }
    }
}

extension Color {
    /// "#9cdcfe"
    init(hex: String) {
        let n = UInt32(hex.dropFirst(), radix: 16) ?? 0xffffff
        self.init(red: Double(n >> 16 & 0xff) / 255, green: Double(n >> 8 & 0xff) / 255, blue: Double(n & 0xff) / 255)
    }
}
