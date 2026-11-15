import SwiftUI

/// Today's cat, filling whatever space it is given. A plain dark color until the first photo arrives.
struct CatPhoto: View {
    var url: URL?

    var body: some View {
        Color(hex: "#2b2b33")
            .overlay {
                if let url, let image = UIImage(contentsOfFile: url.path) {
                    Image(uiImage: image).resizable().scaledToFill()
                }
            }
            .clipped()
    }
}

/// The JSON over the cat: the whole screen of the two apps. Only the watch has modes.
struct Card: View {
    var snapshot: Snapshot
    var mode = Mode.json
    var count = 0
    var timer: Field? = nil
    var now: Date
    var only: [String]? = nil
    var inset = EdgeInsets(top: 16, leading: 16, bottom: 16, trailing: 16)
    var compact = false         // a screen as narrow as a watch

    var body: some View {
        // On a watch the letters are small, so the photo steps back behind them.
        let veil = Color(hex: snapshot.theme.halo).opacity(compact && mode != .photo ? 0.35 : 0)
        JsonText(snapshot: snapshot, mode: mode, count: count, timer: timer, now: now, only: only, compact: compact)
            .padding(inset)
            .background { CatPhoto(url: snapshot.photo).overlay(veil).ignoresSafeArea() }
            .contentShape(Rectangle())
            .animation(.easeInOut(duration: 0.2), value: mode)
    }
}
