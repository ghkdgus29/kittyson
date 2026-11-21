import SwiftUI
import WidgetKit

@main
struct KittysonApp: App {
    var body: some Scene {
        WindowGroup { Screen() }
    }
}

/// The same card as the widget, and under it how to use kittyson. The app is here to carry
/// the widget and the watch app, and to fetch a fresh cat when it is opened.
struct Screen: View {
    @Environment(\.scenePhase) private var phase
    @State private var snapshot = Server.cached()

    var body: some View {
        ScrollView {
            VStack(spacing: 32) {
                TimelineView(.everyMinute) { time in
                    Card(snapshot: snapshot, now: time.date)
                }
                .aspectRatio(1, contentMode: .fit)
                .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
                Guide().padding(.horizontal, 4)
            }
            .padding(20)
        }
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
