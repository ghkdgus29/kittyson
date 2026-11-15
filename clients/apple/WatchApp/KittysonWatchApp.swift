import SwiftUI
import WatchKit
import WidgetKit

@main
struct KittysonWatchApp: App {
    @WKApplicationDelegateAdaptor private var alarm: Alarm   // SwiftUI hands it to the views

    var body: some Scene {
        WindowGroup { Screen() }
    }
}

/// The watch face, as far as an app can be one: the card on the whole screen, with the
/// system's own clock hidden. The crown is the slider. Tap to count, or to run the timer.
/// The timer's lengths are an array of four, two to a row: a tap on a number starts it.
struct Screen: View {
    @Environment(\.scenePhase) private var phase
    @Environment(\.isLuminanceReduced) private var dimmed
    @EnvironmentObject private var alarm: Alarm
    @State private var snapshot = Server.cached()
    @State private var mode = Store.mode
    @State private var counter = Store.counter
    @State private var crown = 0.0
    @State private var setting: Int?         // the length the crown is setting, when it is not picking the mode
    @State private var touch = CGPoint.zero  // where the finger last came down

    var body: some View {
        // Every minute, and every second while the timer runs.
        TimelineView(.periodic(from: Clock(now: .now).midnight, by: alarm.timer.end == nil ? 60 : 1)) { time in
            Card(snapshot: snapshot, mode: mode, count: counter.count, timer: timerLine(at: time.date), now: time.date,
                 only: Screen.only[mode], inset: Screen.inset, compact: true)
                .ignoresSafeArea()
        }
        ._statusBarHidden()
        .onTapGesture(perform: tap)
        .onLongPressGesture(perform: hold)
        .simultaneousGesture(DragGesture(minimumDistance: 0, coordinateSpace: .global).onChanged { touch = $0.startLocation })
        .focusable()
        .digitalCrownRotation($crown, from: 0, through: Double((setting == nil ? Mode.allCases.count : Countdown.steps.count) - 1),
                              by: 1, sensitivity: .low, isContinuous: false, isHapticFeedbackEnabled: true)
        .onChange(of: crown) {
            let stop = Int(crown.rounded())
            if let setting {
                alarm.timer.slots[setting] = Countdown.steps[stop]
            } else {
                mode = Mode.allCases[stop]
                Store.mode = mode
            }
        }
        .task(id: phase) {
            guard phase == .active else { return }
            set(nil)
            await Server.refresh()
            snapshot = Server.cached()
            WidgetCenter.shared.reloadAllTimelines()
        }
    }

    /// Edge to edge, but for the top and bottom: there the screen's round corners would cut the braces.
    static let inset = EdgeInsets(top: 20, leading: 6, bottom: 20, trailing: 6)

    /// While counting or timing, only these lines, so the numbers are big enough to read mid-set.
    static let only: [Mode: [String]] = [.count: ["time", "timer", "count"], .timer: ["time", "timer", "set"]]

    /// The timer's line: always at its own stop, elsewhere only while it runs.
    private func timerLine(at now: Date) -> Field? {
        if let setting { return Field(key: "set", value: String(alarm.timer.slots[setting])) }
        if alarm.timer.end != nil { return Field(key: "timer", value: "\"\(alarm.timer.text(at: now, seconds: !dimmed))\"") }
        return mode == .timer ? Field(key: "timer", value: alarm.timer.picker) : nil
    }

    /// The length under the finger. With the braces the timer's screen has seven rows, and the
    /// array's two are the fourth and the fifth.
    private var slot: Int {
        let screen = WKInterfaceDevice.current().screenBounds.size
        let rows = screen.height - Screen.inset.top - Screen.inset.bottom
        return (touch.y < Screen.inset.top + rows * 4 / 7 ? 0 : 2) + (touch.x < screen.width / 2 ? 0 : 1)
    }

    private func tap() {
        if mode == .timer || alarm.timer.isOver(at: .now) {
            alarm.timer.tap(slot: setting ?? slot, window: 0.4)
            set(nil)
        } else if mode == .count {
            counter.tap(window: 0.4)
            Store.counter = counter
        } else {
            return
        }
        WKInterfaceDevice.current().play(.click)
    }

    /// A long press on a length of the waiting timer hands the crown to it, and another hands it back.
    private func hold() {
        guard mode == .timer, alarm.timer.end == nil else { return }
        set(setting == nil ? slot : nil)
        WKInterfaceDevice.current().play(.click)
    }

    private func set(_ slot: Int?) {
        setting = slot
        crown = Double(slot.map { Countdown.steps.firstIndex(of: alarm.timer.slots[$0]) ?? 0 } ?? Mode.allCases.firstIndex(of: mode) ?? 0)
    }
}
