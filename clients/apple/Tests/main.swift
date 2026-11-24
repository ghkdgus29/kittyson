// Checks of the parts that need no device. Run from clients/apple:
//   swiftc Shared/Counter.swift Shared/Countdown.swift Shared/Layout.swift Tests/main.swift -o /tmp/kittyson-check && /tmp/kittyson-check

import Foundation

var failed = 0
func check(_ ok: Bool, _ what: String) {
    print(ok ? "ok   " : "FAIL ", what)
    if !ok { failed += 1 }
}

// ---- Counter ----

func counted(_ gestures: [Int], from start: Int = 0) -> Int {
    var counter = Counter(count: start)
    var now = Date(timeIntervalSince1970: 1_000_000)
    for taps in gestures {
        now += 10                       // a new gesture, well after the last one
        for _ in 0..<taps {
            now += 0.15
            counter.tap(at: now, window: 0.4)
        }
    }
    return counter.count
}

check(counted([1]) == 1, "one tap adds one")
check(counted([1, 1, 1]) == 3, "three separate taps add three")
check(counted([2], from: 3) == 2, "a double tap takes one off")
check(counted([2]) == 0, "a double tap never goes below zero")
check(counted([3], from: 7) == 0, "a triple tap resets")
check(counted([4], from: 7) == 0, "more taps stay at zero")
check(counted([1, 1, 2, 1]) == 2, "1 + 1 - 1 + 1")

// ---- Countdown ----

let noon = Date(timeIntervalSince1970: 1_000_000)
var timer = Countdown()
check(timer.picker == "[\n   1,     5,\n   15,    30\n]", "a waiting timer shows its lengths, two to a row")
timer.tap(slot: 2, at: noon + 0.7, window: 0.4)
check(timer.end == noon + 900, "a tap on a length starts it, to end on a whole second")
check(timer.text(at: noon) == "15:00", "seen from the second it started in, the whole time is left")
check(timer.text(at: noon + 27.5) == "14:33" && timer.text(at: noon + 27.5, seconds: false) == "14:--", "time left, with and without seconds")
timer.tap(at: noon + 60, window: 0.4)
timer.tap(at: noon + 70, window: 0.4)
check(timer.end != nil, "single taps leave a running timer alone")
timer.tap(at: noon + 70.2, window: 0.4)
check(timer.end == nil, "a double tap cancels it")
timer.tap(slot: 0, at: noon + 100, window: 0.4)
check(!timer.isOver(at: noon + 159) && timer.isOver(at: noon + 160) && timer.text(at: noon + 200) == "0:00", "over after a minute")
timer.tap(at: noon + 200, window: 0.4)
check(timer.end == nil, "one tap puts a finished timer away")

// ---- Layout ----

let fields = [
    Field(key: "time", value: "\"14:01:53\""),
    Field(key: "date", value: "\"2026-11-15\""),
    Field(key: "weekday", value: "\"일요일\""),
    Field(key: "weather", value: "\"☀️ 15° ↑16 ↓7\""),
    Field(key: "quote", value: "\"나는 폭풍이 두렵지 않다. 내 배를 모는 법을 배우고 있으니까\""),  // about as long as the server lets one be
    Field(key: "by", value: "\"루이자 메이 올컷\""),                                         // and so is the name
]

let large = Layout.fit(fields, width: 338 - 24, height: 354 - 24)
let weatherRows = large.rows.filter { $0.words[0][0].text == "\"weather\"" }
check(large.font >= 14 && large.font <= 20, "Large widget font is \(large.font)pt")
check(weatherRows.count == 1 && weatherRows[0].words.count == 4, "weather stays on one row")
check(large.rows.count == 7 || large.rows.count == 8, "the quote wraps onto \(large.rows.count - 5) rows")
check(large.rows[large.rows.count - 2].indent == Rules().indent + Layout.hang, "wrapped rows hang deeper")
check(large.rows.last?.words[0][0].text == "\"by\"", "the name has the last row to itself")
let used = Double(large.rows.count + 2) * large.rowHeight + Double(large.rows.count + 3) * large.gap
check(used <= 330.5, "rows and gaps fit the height (\(used) of 330)")

let narrow = Layout.fit([Field(key: "weather", value: "\"☀️ 15° ↑16 ↓7\"")], width: 150, height: 300)
check(narrow.rows.count == 1 && narrow.font < 12, "a narrow box shrinks the font instead of wrapping weather (\(narrow.font)pt)")

// The 46 mm watch: 208 x 248 pt, less the watch app's insets. There the weekday shares the date's row.
let watchFields = [fields[0], Field(key: "date", value: "\"26-11-15 일\"")] + fields[3...]
let watch = Layout.fit(watchFields, width: 196, height: 208, rules: .compact)
let watchUsed = Double(watch.rows.count + 2) * watch.rowHeight + Double(watch.rows.count + 3) * watch.gap
check(watch.font >= 15, "compact: the watch font is \(watch.font)pt")
check(watch.rows.count == 8, "compact: the quote takes three rows and the name one (\(watch.rows.count) rows in all)")
check(watch.rows[0].indent == 0 && watch.rows[0].words[0][0].text == "\"t\"", "compact: short keys at the left edge")
check(watch.rows.allSatisfy { $0.indent == 0 || $0.words.count > 1 }, "compact: no row is a lone word")
let arrows = watch.rows.first { $0.words[0][0].text == "↑16" }
check(arrows?.indent == 7 && arrows?.words.count == 2, "compact: the weather wraps to under its icon")
check(abs(watchUsed - 208) < 0.5, "compact: rows spread over the whole height (\(watchUsed) of 208)")

let picking = Layout.fit([fields[0], Field(key: "timer", value: Countdown().picker)], width: 196, height: 208, rules: .compact)
check(picking.font > watch.font && picking.rows.count == 5, "compact: the timer's lengths take three rows more, at \(picking.font)pt")
check(picking.rows[2] == Row(indent: 0, words: [[Piece(text: "   1,     5,", ink: .str)]]), "a line of the value's own is one row, spaces and all")
check(picking.rows[4].words[0][0].text == "]" && picking.rows[4].indent == 0, "the array closes at the key's indent")

let counting = Layout.fit(fields + [Field(key: "count", value: "3")], width: 314, height: 330)
check(counting.rows.last?.words[0].last?.text == "3", "count is the last line, with no comma")

// ---- Clock ----

var calendar = Calendar.current
func at(_ hour: Int, _ minute: Int) -> Clock {
    Clock(now: calendar.date(from: DateComponents(year: 2026, month: 11, day: 15, hour: hour, minute: minute, second: 30))!)
}
check(at(14, 1).prefix == "" && at(9, 1).prefix == "0" && at(0, 12).prefix == "00:" && at(0, 5).prefix == "00:0", "timer prefixes")
check(at(14, 1).minute == "14:01" && at(0, 5).minute == "00:05", "time without seconds")
check(at(14, 1).date == "2026-11-15", "date is \(at(14, 1).date)")
check(at(14, 1).shortDate == "26-11-15 일", "the watch's date is \(at(14, 1).shortDate)")
check(at(0, 5).changes.count == 4 && at(14, 1).changes.count == 1, "coming changes of the prefix and the date")

print(failed == 0 ? "all good" : "\(failed) failed")
exit(failed == 0 ? 0 : 1)
