import Foundation

/// The set counter. One tap adds one, a double tap takes one off, a triple tap resets.
/// The number changes on every tap of a gesture, counted from where it stood before the first.
struct Counter: Codable, Equatable {
    var count = 0
    var before = 0                    // the count before the current gesture's first tap
    var taps = 0                      // taps in the current gesture
    var lastTap = Date.distantPast

    /// `window`: taps closer together than this many seconds are one gesture.
    mutating func tap(at now: Date = .now, window: TimeInterval) {
        if now.timeIntervalSince(lastTap) > window { taps = 0 }
        if taps == 0 { before = count }
        taps += 1
        count = taps == 1 ? before + 1 : taps == 2 ? max(before - 1, 0) : 0
        lastTap = now
    }
}
