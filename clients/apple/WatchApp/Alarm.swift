import SwiftUI
import WatchKit

/// The timer and the alarm at its end. The alarm is a session the system starts at that
/// moment, whether or not the app is on screen; it then taps the wrist until it is stopped.
final class Alarm: NSObject, ObservableObject, WKApplicationDelegate, WKExtendedRuntimeSessionDelegate {
    @Published var timer = Store.timer {
        didSet {
            Store.timer = timer
            if timer.end != oldValue.end { schedule() }
        }
    }
    private var session: WKExtendedRuntimeSession?

    /// Only one session can be scheduled at a time, so the old one goes first.
    private func schedule() {
        let old = session
        session = nil
        old?.invalidate()
        guard let end = timer.end, end > .now else { return }
        let session = WKExtendedRuntimeSession()
        session.delegate = self
        session.start(at: end)
        self.session = session
    }

    /// The system started the app for an alarm that was set before the app last quit.
    func handle(_ extendedRuntimeSession: WKExtendedRuntimeSession) {
        session = extendedRuntimeSession
        extendedRuntimeSession.delegate = self
        if timer.end == nil { extendedRuntimeSession.invalidate() }
    }

    func extendedRuntimeSessionDidStart(_ session: WKExtendedRuntimeSession) {
        session.notifyUser(hapticType: .notification) { _ in 2 }
    }

    func extendedRuntimeSessionWillExpire(_ session: WKExtendedRuntimeSession) {}

    /// The session is gone: stopped from the system's alert, left ringing for half an hour, or
    /// refused by the system. The timer goes with it, as a timer that cannot ring is a trap.
    func extendedRuntimeSession(_ session: WKExtendedRuntimeSession,
                                didInvalidateWith reason: WKExtendedRuntimeSessionInvalidationReason, error: Error?) {
        if let error { print("alarm:", error) }
        guard session === self.session else { return }
        self.session = nil
        timer.end = nil
    }
}
