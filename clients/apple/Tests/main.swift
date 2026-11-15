// Checks of the parts that need no device. Run from clients/apple:
//   swiftc Shared/Counter.swift Shared/Layout.swift Tests/main.swift -o /tmp/kittyson-check && /tmp/kittyson-check

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

// ---- Layout ----

let fields = [
    Field(key: "time", value: "\"14:01:53\""),
    Field(key: "date", value: "\"2026-11-15\""),
    Field(key: "weekday", value: "\"일요일\""),
    Field(key: "weather", value: "\"☀️ 15° ↑16 ↓7\""),
    Field(key: "quote", value: "\"펼친 노트 한 장이 월요일의 발걸음을 가볍게 한다\""),
]

let large = Layout.fit(fields, width: 338 - 24, height: 354 - 24)
let weatherRows = large.rows.filter { $0.words[0][0].text == "\"weather\"" }
check(large.font >= 14 && large.font <= 20, "Large widget font is \(large.font)pt")
check(weatherRows.count == 1 && weatherRows[0].words.count == 4, "weather stays on one row")
check(large.rows.count == 6 || large.rows.count == 7, "the quote wraps onto \(large.rows.count - 4) rows")
check(large.rows.last?.indent == Layout.hang, "wrapped rows hang deeper")
let used = Double(large.rows.count + 2) * large.rowHeight + Double(large.rows.count + 3) * large.gap
check(used <= 330.5, "rows and gaps fit the height (\(used) of 330)")

let narrow = Layout.fit([Field(key: "weather", value: "\"☀️ 15° ↑16 ↓7\"")], width: 150, height: 300)
check(narrow.rows.count == 1 && narrow.font < 12, "a narrow box shrinks the font instead of wrapping weather (\(narrow.font)pt)")

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
check(at(0, 5).changes.count == 4 && at(14, 1).changes.count == 1, "coming changes of the prefix and the date")

print(failed == 0 ? "all good" : "\(failed) failed")
exit(failed == 0 ? 0 : 1)
