import Foundation

// How the JSON is laid out in a box: the biggest font at which every line, wrapped to the
// box's width, still fits its height. Same rules as the web screen (static/app.js).
// No SwiftUI here, so Tests/main.swift can run it on the Mac.

/// One line of the JSON. `value` is JSON text: "\"화요일\"" or 3.
struct Field: Equatable {
    var key: String
    var value: String
}

enum Ink { case punct, key, str }

/// A piece of text in one color. `clock` marks the live time, which the view draws itself.
struct Piece: Equatable {
    var text: String
    var ink: Ink
    var clock = false
}

/// One row on screen: words that are never split, indented by `indent` characters.
struct Row: Equatable {
    var indent: Int
    var words: [[Piece]]
}

struct Fit {
    var font: Double
    var rows: [Row]        // without the braces
    var rowHeight: Double
    var gap: Double        // space between rows
}

/// The rules that differ between a roomy box and a screen as narrow as a watch.
struct Rules {
    var keys: [String: String] = [:]         // shorter names for the keys
    var indent = 2                           // indent of a key, in characters
    var oneRow: Set<String> = ["weather"]    // never wrapped: the font gets smaller instead
    var under: Set<String> = []              // wrapped rows start under the value's first letter, not at the hang
    var shrinkStub = true                    // a stub left on a last row makes the font smaller
    var gap = 0.12                           // least space between rows, in units of font size
    var maxGap = 0.6                         // most space between rows; beyond it the JSON is centered

    /// The watch: everything gives way to a bigger font, and the rows spread over the whole height.
    static let compact = Rules(
        keys: ["time": "t", "date": "d", "weekday": "wd", "weather": "wx", "quote": "q", "count": "n", "timer": "tm"],
        indent: 0, oneRow: [], under: ["weather"], shrinkStub: false, gap: 0, maxGap: .infinity)
}

enum Layout {
    static let minFont = 8.0
    static let maxFont = 40.0
    static let charW = 0.62      // monospaced advance, in units of font size (slightly generous)
    static let textH = 1.2       // height of a row of text, in units of font size
    static let hang = 2          // further indent of the rows a long value wraps onto
    static let widow = 6.0       // fewer characters than this on the last row of a wrapped value is a stub
    static let clockUnits = 10.0 // "14:01:53" with its quotes

    /// Width of a string in monospaced-character units. Hangul, CJK and emoji are wider.
    static func units(_ text: String) -> Double {
        var n = 0.0
        for scalar in text.unicodeScalars {
            let c = scalar.value
            if c == 0xfe0f || c == 0x200d { continue }                                  // variation selector, joiner
            if c >= 0x1f000 || (0x2600...0x27bf).contains(c) { n += 1.8 }               // emoji, weather symbols
            else if c >= 0x1100 && c != 0x2026 && !(0x2190...0x21ff).contains(c) { n += 1.5 } // Hangul, CJK
            else { n += 1 }                                                             // ASCII, °, arrows
        }
        return n
    }

    /// A JSON line as words: the key with the start of its value, then the rest of the value
    /// cut at its spaces. A value that comes in lines of its own (the watch's timer) keeps them:
    /// each further line is one word, after an empty word that stands for the line break.
    static func words(_ field: Field, comma: Bool, rules: Rules = Rules()) -> [[Piece]] {
        let key = rules.keys[field.key] ?? field.key
        let head = [Piece(text: "\"\(key)\"", ink: .key), Piece(text: ": ", ink: .punct)]
        let tail = comma ? [Piece(text: ",", ink: .punct)] : []
        if field.key == "time" { return [head + [Piece(text: "", ink: .str, clock: true)] + tail] }
        let lines = field.value.components(separatedBy: "\n")
        var words = lines[0].components(separatedBy: " ").map { [Piece(text: $0, ink: .str)] }
        for line in lines.dropFirst() { words += [[], [Piece(text: line, ink: .str)]] }
        words[0].insert(contentsOf: head, at: 0)
        words[words.count - 1].append(contentsOf: tail)
        return words
    }

    static func units(_ word: [Piece]) -> Double {
        word.reduce(0) { $0 + ($1.clock ? clockUnits : units($1.text)) }
    }

    /// Break one JSON line into rows no wider than `cap` characters. nil when a single word
    /// is too wide, or when the last row is a stub and a smaller font is the cure for that.
    /// `under`: the rows it wraps onto start under the value's first letter.
    static func wrap(_ words: [[Piece]], cap: Double, rules: Rules = Rules(), under: Bool = false) -> [Row]? {
        // The key, the colon and the value's opening quote come before that letter.
        let hang = Double(rules.indent) + (under ? units(Array(words[0].prefix(2))) + 1 : Double(Layout.hang))
        var rows: [Row] = []
        var used = 0.0
        var broken = false   // the value breaks the line here itself
        for word in words {
            if word.isEmpty { broken = true; continue }
            let n = units(word)
            if !rows.isEmpty, !broken, used + 1 + n <= cap {
                rows[rows.count - 1].words.append(word)
                used += 1 + n
                continue
            }
            // A line of the value's own brings its own indent.
            let start = rows.isEmpty || broken ? Double(rules.indent) : hang
            if start + n > cap { return nil }
            rows.append(Row(indent: Int(start), words: [word]))
            used = start + n
            broken = false
        }
        guard rows.count > 1, used - hang < widow, !words.contains([]) else { return rows }
        if rules.shrinkStub { return nil }
        // Otherwise the word before the stub comes down to keep it company.
        let above = rows.count - 2
        if rows[above].words.count > 1, used + 1 + units(rows[above].words.last!) <= cap {
            rows[above + 1].words.insert(rows[above].words.removeLast(), at: 0)
        }
        return rows
    }

    static func fit(_ fields: [Field], width: Double, height: Double, braces: Bool = true, rules: Rules = Rules()) -> Fit {
        let all = fields.enumerated().map { words($1, comma: $0 < fields.count - 1, rules: rules) }
        let extra = braces ? 2 : 0

        func result(_ font: Double, _ rows: [Row]) -> Fit {
            let count = Double(rows.count + extra)
            let rowHeight = (font * textH).rounded()
            // Height the rows leave over is shared out between them, up to a point.
            let spare = (height - count * rowHeight) / (count + 1)
            return Fit(font: font, rows: rows, rowHeight: rowHeight, gap: min(max(spare, font * rules.gap), font * rules.maxGap))
        }

        for font in stride(from: maxFont, through: minFont, by: -0.5) {
            var rows: [Row] = []
            var ok = true
            for (field, words) in zip(fields, all) {
                guard let wrapped = wrap(words, cap: width / (font * charW), rules: rules, under: rules.under.contains(field.key)),
                      wrapped.count == 1 || !rules.oneRow.contains(field.key) else { ok = false; break }
                rows += wrapped
            }
            let count = Double(rows.count + extra)
            if ok, count * (font * textH).rounded() + (count + 1) * font * rules.gap <= height { return result(font, rows) }
        }
        // Nothing fits: smallest font, one row per key, and the view squeezes what is still too long.
        return result(minFont, all.map { Row(indent: rules.indent, words: $0) })
    }
}

/// The device's clock, for the two values the device fills in itself: "time" and "date".
struct Clock {
    let now: Date

    var midnight: Date { Calendar.current.startOfDay(for: now) }

    var date: String { now.formatted(Date.ISO8601FormatStyle(timeZone: .current).year().month().day()) }

    /// "time" is a live timer counting from midnight. It drops leading zeros (14:01:53,
    /// 9:01:53, 12:34, 5:03), so this is the text to put in front of it.
    var prefix: String {
        let parts = Calendar.current.dateComponents([.hour, .minute], from: now)
        let hour = parts.hour ?? 0, minute = parts.minute ?? 0
        if hour >= 10 { return "" }
        if hour >= 1 { return "0" }
        return minute >= 10 ? "00:" : "00:0"
    }

    /// "14:01", for a dimmed screen where seconds cannot tick.
    var minute: String {
        let parts = Calendar.current.dateComponents([.hour, .minute], from: now)
        return String(format: "%02d:%02d", parts.hour ?? 0, parts.minute ?? 0)
    }

    /// The coming moments at which `prefix` or `date` changes.
    var changes: [Date] {
        let tomorrow = Calendar.current.date(byAdding: .day, value: 1, to: midnight) ?? midnight.addingTimeInterval(86400)
        return ([10, 60, 600].map { midnight.addingTimeInterval($0 * 60) } + [tomorrow]).filter { $0 > now }
    }
}
