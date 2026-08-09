import Foundation

/// JSON file cache — the offline story. Today/Places payloads are cached on
/// every successful fetch and served when the network is gone (ferries,
/// Mt Athos). Journal drafts queue here too (sync-on-reconnect is week-3 work).
enum CacheStore {
    private static var dir: URL {
        let d = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("niko", isDirectory: true)
        try? FileManager.default.createDirectory(at: d, withIntermediateDirectories: true)
        return d
    }

    static func save<T: Encodable>(_ value: T, key: String) {
        if let data = try? JSONEncoder().encode(value) {
            try? data.write(to: dir.appendingPathComponent("\(key).json"))
        }
    }

    static func load<T: Decodable>(_ type: T.Type, key: String) -> T? {
        guard let data = try? Data(contentsOf: dir.appendingPathComponent("\(key).json")) else {
            return nil
        }
        return try? JSONDecoder().decode(type, from: data)
    }
}
