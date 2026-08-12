import Foundation

// MARK: - Chat

struct ChatRequest: Codable {
    let message: String
    let lat: Double?
    let lon: Double?
    let memoryMode: Bool
    let timestamp: String

    enum CodingKeys: String, CodingKey {
        case message, lat, lon, timestamp
        case memoryMode = "memory_mode"
    }
}

struct ChatResponse: Codable {
    let reply: String
    let places: [Place]
    let sources: [String?]
}

struct Place: Codable, Identifiable, Hashable {
    let placeId: String?
    let name: String?
    let address: String?
    let lat: Double?
    let lon: Double?
    let category: String?
    let rating: Double?
    let ratingCount: Int?
    let mapsUrl: String?

    var id: String { placeId ?? name ?? UUID().uuidString }

    enum CodingKeys: String, CodingKey {
        case name, address, lat, lon, category, rating
        case placeId = "place_id"
        case ratingCount = "rating_count"
        case mapsUrl = "maps_url"
    }
}

struct ChatMessage: Identifiable {
    let id = UUID()
    let role: Role
    let text: String
    var places: [Place] = []
    var sources: [String] = []

    enum Role { case user, niko }
}

// MARK: - Journal

struct JournalStartResponse: Codable {
    let entryId: String
    let reply: String
    enum CodingKeys: String, CodingKey {
        case reply
        case entryId = "entry_id"
    }
}

struct JournalMessageResponse: Codable {
    let reply: String
    let candidate: Place?
}

struct JournalEntry: Codable, Identifiable {
    let id: String
    let createdAt: Double
    let placeName: String?
    let mapsUrl: String?
    let lat: Double?
    let lon: Double?
    let sentiment: String?
    let line: String?
    let summary: String?
    let best: String?
    let worst: String?

    enum CodingKeys: String, CodingKey {
        case id, lat, lon, sentiment, line, summary, best, worst
        case createdAt = "created_at"
        case placeName = "place_name"
        case mapsUrl = "maps_url"
    }
}

// MARK: - Today / Journey / Map

struct TodayResponse: Codable {
    let tripDay: Int?
    let date: String
    let region: String?
    let morningGuide: MorningGuide?
    let eveningRecap: EveningRecap?

    enum CodingKeys: String, CodingKey {
        case date, region
        case tripDay = "trip_day"
        case morningGuide = "morning_guide"
        case eveningRecap = "evening_recap"
    }
}

struct MorningGuide: Codable {
    let stops: [GuideStop]
    let lunch: String
}

struct GuideStop: Codable, Identifiable {
    let name: String
    let hours: String
    let blurb: String
    let tip: String
    var id: String { name }
}

struct EveningRecap: Codable {
    let narrative: String
    let entries: [RecapEntry]
}

struct RecapEntry: Codable, Identifiable {
    let placeName: String?
    let sentiment: String?
    let line: String?
    let mapsUrl: String?
    var id: String { (placeName ?? "?") + (line ?? "") }

    enum CodingKeys: String, CodingKey {
        case sentiment, line
        case placeName = "place_name"
        case mapsUrl = "maps_url"
    }
}

struct PlacesResponse: Codable {
    let entries: [JournalEntry]
    let preferences: Preferences
}

struct Preferences: Codable {
    let likes: [String]
    let dislikes: [String]
}

struct InsightsResponse: Codable {
    let insights: [Insight]
}

struct Insight: Codable, Identifiable {
    let id: String
    let emoji: String?
    let text: String
    let tag: String?
}

struct PinsResponse: Codable {
    let pins: [MapPin]
}

struct MapPin: Codable, Identifiable {
    let id: String
    let placeName: String?
    let lat: Double
    let lon: Double
    let sentiment: String?
    let line: String?
    let mapsUrl: String?

    enum CodingKeys: String, CodingKey {
        case id, lat, lon, sentiment, line
        case placeName = "place_name"
        case mapsUrl = "maps_url"
    }
}
