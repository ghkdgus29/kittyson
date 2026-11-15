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
    var now: Date
    var only: [String]? = nil
    var inset = 16.0

    var body: some View {
        JsonText(snapshot: snapshot, mode: mode, count: count, now: now, only: only)
            .padding(inset)
            .background { CatPhoto(url: snapshot.photo).ignoresSafeArea() }
            .contentShape(Rectangle())
            .animation(.easeInOut(duration: 0.2), value: mode)
    }
}
