import SwiftUI
import WidgetKit

/// The watch's face on the home screen: the cat and the JSON, nothing to operate.
/// A tap opens the app.
@main
struct KittysonWidget: Widget {
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: "KittysonWidget", provider: Provider()) { entry in
            JsonText(snapshot: entry.snapshot, now: entry.date)
                .padding(14)
                .containerBackground(for: .widget) { CatPhoto(url: entry.snapshot.photo) }
        }
        .configurationDisplayName("kittyson")
        .description("오늘의 고양이와 JSON")
        .supportedFamilies([.systemLarge])
        .contentMarginsDisabled()
    }
}
