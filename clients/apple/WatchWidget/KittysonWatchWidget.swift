import SwiftUI
import WidgetKit

/// The way back to the app. watchOS returns to its own face after an hour unwatched, and
/// one tap on any of these, placed on that face or in the Smart Stack, opens kittyson again.
@main
struct KittysonWatchWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "KittysonWatchWidget", provider: Provider()) { entry in
            Complication(entry: entry)
                .containerBackground(for: .widget) { CatPhoto(image: entry.snapshot.photo) }
        }
        .configurationDisplayName("kittyson")
        .description("누르면 kittyson이 열립니다")
        .supportedFamilies([.accessoryCircular, .accessoryCorner, .accessoryInline, .accessoryRectangular])
    }
}

struct Complication: View {
    @Environment(\.widgetFamily) private var family
    var entry: Entry

    var body: some View {
        switch family {
        case .accessoryRectangular:
            JsonText(snapshot: entry.snapshot, now: entry.date, only: ["weather", "quote"], braces: false)
        case .accessoryInline:
            Label(weather, systemImage: "cat.fill")
        case .accessoryCorner:
            Image(systemName: "cat.fill").font(.title2).widgetLabel(weather)
        default:
            Image(systemName: "cat.fill").font(.title2)
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .background { AccessoryWidgetBackground() }
        }
    }

    /// The weather line without its quotes: ☀️ 15° ↑16 ↓7
    private var weather: String {
        let line = entry.snapshot.fields.first { $0.key == "weather" }
        return line?.value.trimmingCharacters(in: ["\""]) ?? "kittyson"
    }
}
