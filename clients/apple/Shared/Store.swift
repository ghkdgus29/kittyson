import Foundation

/// The stops of the watch's crown: cat + JSON, timer, set counter, cat first (JSON faint).
enum Mode: String, CaseIterable {
    case json, timer, count, photo
}

/// The watch app's mode, count and timer, and the app group an app shares with its widget.
enum Store {
    static let group = "group.com.ghkdgus29.kittyson"
    static let defaults = UserDefaults(suiteName: group) ?? .standard

    static var mode: Mode {
        get { Mode(rawValue: defaults.string(forKey: "mode") ?? "") ?? .json }
        set { defaults.set(newValue.rawValue, forKey: "mode") }
    }

    static var counter: Counter {
        get { defaults.data(forKey: "counter").flatMap { try? JSONDecoder().decode(Counter.self, from: $0) } ?? Counter() }
        set { defaults.set(try? JSONEncoder().encode(newValue), forKey: "counter") }
    }

    static var timer: Countdown {
        get { defaults.data(forKey: "timer").flatMap { try? JSONDecoder().decode(Countdown.self, from: $0) } ?? Countdown() }
        set { defaults.set(try? JSONEncoder().encode(newValue), forKey: "timer") }
    }
}
