import SwiftUI
import WidgetKit

@main
struct KittysonApp: App {
    var body: some Scene {
        WindowGroup { Screen() }
    }
}

/// The same card as the widget. The app is here to carry the widget and the watch app,
/// and to fetch a fresh cat when it is opened.
struct Screen: View {
    @Environment(\.scenePhase) private var phase
    @State private var snapshot = Server.cached()

    var body: some View {
        TimelineView(.everyMinute) { time in
            Card(snapshot: snapshot, now: time.date)
        }
        .aspectRatio(1, contentMode: .fit)
        .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
        .padding(20)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.black)
        .preferredColorScheme(.dark)
        .task(id: phase) {
            guard phase == .active else { return }
            await Server.refresh()
            snapshot = Server.cached()
            WidgetCenter.shared.reloadAllTimelines()
        }
    }
}
