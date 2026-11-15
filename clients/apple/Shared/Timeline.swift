import WidgetKit

/// What a widget draws at one moment.
struct Entry: TimelineEntry {
    var date: Date
    var snapshot: Snapshot
}

/// Feeds both widgets. The clock runs by itself, so a new entry is needed only when the
/// text around it changes (see Clock.changes), and a new timeline every half hour.
struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> Entry {
        Entry(date: .now, snapshot: Snapshot())
    }

    func getSnapshot(in context: Context, completion: @escaping (Entry) -> Void) {
        completion(Entry(date: .now, snapshot: Server.cached()))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<Entry>) -> Void) {
        Task {
            let snapshot = await Server.latest()
            let now = Date.now
            let end = now.addingTimeInterval(30 * 60)
            let dates = [now] + Clock(now: now).changes.filter { $0 < end }
            completion(Timeline(entries: dates.map { Entry(date: $0, snapshot: snapshot) }, policy: .after(end)))
        }
    }
}
