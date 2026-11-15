import SwiftUI
import WatchKit
import WidgetKit

@main
struct KittysonWatchApp: App {
    var body: some Scene {
        WindowGroup { Screen() }
    }
}

/// The watch face, as far as an app can be one: the card on the whole screen, with the
/// system's own clock hidden. The crown is the slider. Tap to count.
struct Screen: View {
    @Environment(\.scenePhase) private var phase
    @State private var snapshot = Server.cached()
    @State private var mode = Store.mode
    @State private var counter = Store.counter
    @State private var crown = 0.0

    var body: some View {
        TimelineView(.everyMinute) { time in
            Card(snapshot: snapshot, mode: mode, count: counter.count, now: time.date,
                 only: mode == .count ? Screen.counting : nil, inset: 6)
        }
        ._statusBarHidden()
        .onTapGesture(perform: tap)
        .focusable()
        .digitalCrownRotation($crown, from: 0, through: 2, by: 1, sensitivity: .low,
                              isContinuous: false, isHapticFeedbackEnabled: true)
        .onChange(of: crown) {
            mode = Mode.allCases[Int(crown.rounded())]
            Store.mode = mode
        }
        .task(id: phase) {
            guard phase == .active else { return }
            crown = Double(Mode.allCases.firstIndex(of: mode) ?? 0)
            await Server.refresh()
            snapshot = Server.cached()
            WidgetCenter.shared.reloadAllTimelines()
        }
    }

    /// While counting, only these lines, so the number is big enough to read mid-set.
    static let counting = ["time", "count"]

    private func tap() {
        guard mode == .count else { return }
        counter.tap(window: 0.4)
        Store.counter = counter
        WKInterfaceDevice.current().play(.click)
    }
}
