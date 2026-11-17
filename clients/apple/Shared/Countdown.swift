import Foundation

/// The timer: four lengths to pick from and, once one is started, the moment it ends.
/// A tap on a length starts it. While it runs a double tap cancels it; once it is over, one tap puts it away.
struct Countdown: Codable, Equatable {
    static let steps = Array(1...60)  // the minutes the crown steps through

    var slots = [1, 5, 15, 30]        // the minutes to pick from
    var end: Date?                    // nil while it is not running
    var lastTap = Date.distantPast    // the last tap while it ran

    func isOver(at now: Date) -> Bool { end.map { $0 <= now } ?? false }

    /// `slot`: the length that was tapped, which matters only while no timer runs.
    /// `window`: two taps closer together than this many seconds are a double tap.
    mutating func tap(slot: Int = 0, at now: Date = .now, window: TimeInterval) {
        guard let end else {
            // It ends on a whole second. The screen redraws on whole seconds, each a little in
            // the past: counted from there, a fraction would show as a second too many.
            self.end = Date(timeIntervalSinceReferenceDate: now.timeIntervalSinceReferenceDate.rounded(.down) + Double(slots[slot]) * 60)
            return
        }
        if end <= now || now.timeIntervalSince(lastTap) <= window {
            self.end = nil
            lastTap = .distantPast
        } else {
            lastTap = now
        }
    }

    /// The time left: "14:32", or "14:--" where seconds cannot tick.
    func text(at now: Date, seconds: Bool = true) -> String {
        let left = max(Int((end ?? now).timeIntervalSince(now).rounded(.up)), 0)
        return seconds ? String(format: "%d:%02d", left / 60, left % 60) : "\(left / 60):--"
    }

    /// The lengths as a JSON array, two to a row: each number sits in the quarter of the screen that starts it.
    var picker: String {
        func row(_ a: Int, _ b: Int, last: Bool = false) -> String {
            "   " + "\(slots[a]),".padding(toLength: 7, withPad: " ", startingAt: 0) + "\(slots[b])" + (last ? "" : ",")
        }
        return "[\n\(row(0, 1))\n\(row(2, 3, last: true))\n]"
    }
}
