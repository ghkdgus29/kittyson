import Foundation
import ImageIO
import UIKit

/// Text colors for the cat's photo, as /api/today gives them.
struct Theme: Codable, Equatable {
    var punct = "#ffffff"
    var key = "#9cdcfe"
    var str = "#ffd9a8"
    var halo = "#000000"
    var halo_alpha = 0.9
}

/// What the server last said: the lines in its own order, the colors, the photo.
struct Snapshot {
    var fields = ["time", "date", "weekday", "weather", "quote", "by"].map { Field(key: $0, value: "\"…\"") }
    var theme = Theme()
    var photo: UIImage?   // the picture itself: its file keeps one name, so only a new image redraws

    /// The lines to draw: the server's, with today's date from this device, the count when
    /// counting, and only the keys in `only` when the screen is too small for all of them.
    /// `short` (the watch): the weekday moves into the date's row, "26-11-24 화", and the timer's line
    /// takes that row while it runs. A row more would make every letter smaller.
    func lines(now: Date, timer: Field? = nil, count: Int? = nil, only: [String]? = nil, short: Bool = false) -> [Field] {
        let clock = Clock(now: now)
        var lines = fields.compactMap { field in
            switch field.key {
            case "date": timer ?? Field(key: "date", value: "\"\(short ? clock.shortDate : clock.date)\"")
            case "weekday": short ? nil : field
            default: field
            }
        }
        if let count { lines.append(Field(key: "count", value: String(count))) }
        if let only { lines = lines.filter { only.contains($0.key) } }
        return lines
    }
}

/// Talks to the kittyson server and keeps the last answer on disk, so there is always
/// something to draw. The address comes from Config/Local.xcconfig at build time.
enum Server {
    static let base = (Bundle.main.object(forInfoDictionaryKey: "KittysonServer") as? String) ?? "http://localhost:8000"
    static let retryAfter: TimeInterval = 15 * 60
    #if os(watchOS)
    static let photoPixels = 400   // widgets refuse big images, and the watch refuses them sooner
    #else
    static let photoPixels = 900
    #endif

    private static let folder: URL = {
        let fm = FileManager.default
        return fm.containerURL(forSecurityApplicationGroupIdentifier: Store.group)
            ?? fm.urls(for: .cachesDirectory, in: .userDomainMask)[0]
    }()

    private static func file(_ name: String) -> URL { folder.appendingPathComponent(name) }

    /// The last answer kept on disk.
    static func cached() -> Snapshot {
        var snapshot = Snapshot()
        if let data = try? Data(contentsOf: file("today.json")) {
            let fields = parse(data)
            if !fields.isEmpty { snapshot.fields = fields }
            if let cat = cat(data) { snapshot.theme = cat.theme }
        }
        snapshot.photo = UIImage(contentsOfFile: file("cat.jpg").path)
        return snapshot
    }

    /// The newest answer: asks the server unless it was asked within `retryAfter` (a widget
    /// redraws on every tap of the counter, and must not wait for the network each time).
    static func latest() async -> Snapshot {
        let now = Date.now.timeIntervalSince1970
        if now - Store.defaults.double(forKey: "lastTry") > retryAfter {
            Store.defaults.set(now, forKey: "lastTry")
            await refresh()
        }
        return cached()
    }

    /// Ask the server now and keep what it says. Whatever fails keeps its old file.
    static func refresh() async {
        guard let today = try? await get("/api/today"), !parse(today).isEmpty else { return }
        try? today.write(to: file("today.json"), options: .atomic)
        // The photo changes when the cat does, so it is fetched once for each cat.
        if let day = cat(today)?.day, Store.defaults.string(forKey: "catDay") != day,
           let jpg = try? await get("/cat/today.jpg?d=\(day)"), let small = shrink(jpg) {
            try? small.write(to: file("cat.jpg"), options: .atomic)
            Store.defaults.set(day, forKey: "catDay")
        }
    }

    private static func get(_ path: String) async throws -> Data {
        guard let url = URL(string: base + path) else { throw URLError(.badURL) }
        let request = URLRequest(url: url, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 8)
        let (data, response) = try await URLSession.shared.data(for: request)
        guard (response as? HTTPURLResponse)?.statusCode == 200 else { throw URLError(.badServerResponse) }
        return data
    }

    /// The "widget" of /api/today as lines, in the server's order.
    static func parse(_ data: Data) -> [Field] {
        guard let today = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let object = today["widget"] as? [String: Any],
              let raw = String(data: data, encoding: .utf8) else { return [] }
        // JSONSerialization forgets the order of the keys. The raw text still has it.
        func position(_ key: String) -> String.Index { raw.range(of: "\"\(key)\":")?.lowerBound ?? raw.endIndex }
        return object.keys.sorted { position($0) < position($1) }.map { Field(key: $0, value: jsonText(object[$0]!)) }
    }

    /// A value the way JSON writes it: strings in quotes, numbers bare.
    private static func jsonText(_ value: Any) -> String {
        let data = try? JSONSerialization.data(withJSONObject: value, options: [.fragmentsAllowed, .withoutEscapingSlashes])
        return data.flatMap { String(data: $0, encoding: .utf8) } ?? "null"
    }

    /// The "cat" of /api/today: the day its photo is of, and the colors that read well on it.
    /// nil while the server has no cat yet.
    private static func cat(_ data: Data) -> Cat? {
        (try? JSONDecoder().decode(Today.self, from: data))?.cat
    }

    private struct Today: Decodable { var cat: Cat? }
    private struct Cat: Decodable { var day: String; var theme: Theme }

    private static func shrink(_ jpg: Data) -> Data? {
        let options: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceThumbnailMaxPixelSize: photoPixels,
        ]
        guard let source = CGImageSourceCreateWithData(jpg as CFData, nil),
              let image = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else { return nil }
        let out = NSMutableData()
        guard let destination = CGImageDestinationCreateWithData(out, "public.jpeg" as CFString, 1, nil) else { return nil }
        CGImageDestinationAddImage(destination, image, [kCGImageDestinationLossyCompressionQuality: 0.85] as CFDictionary)
        return CGImageDestinationFinalize(destination) ? out as Data : nil
    }
}
