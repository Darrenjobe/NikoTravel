import Foundation

enum APIConfig {
    static var baseURL: String {
        if let s = Bundle.main.object(forInfoDictionaryKey: "HodegosBaseURL") as? String {
            return s.hasSuffix("/") ? String(s.dropLast()) : s
        }
        return "http://192.168.68.66:8000"
    }

    static var token: String {
        (Bundle.main.object(forInfoDictionaryKey: "HodegosAPIToken") as? String) ?? ""
    }
}

enum APIError: LocalizedError {
    case offline
    case server(Int)

    var errorDescription: String? {
        switch self {
        case .offline: return "No connection — Niko needs data to answer."
        case .server(let code): return "Server error (\(code)). Try again."
        }
    }
}

struct APIClient {
    static let shared = APIClient()

    private func url(_ path: String) -> URL {
        URL(string: APIConfig.baseURL + path)!
    }

    private func request<Body: Encodable, Response: Decodable>(
        _ path: String, method: String = "GET", body: Body? = nil
    ) async throws -> Response {
        var req = URLRequest(url: url(path))
        req.httpMethod = method
        req.timeoutInterval = 60
        req.setValue("Bearer \(APIConfig.token)", forHTTPHeaderField: "Authorization")
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONEncoder().encode(body)
        }
        let (data, response): (Data, URLResponse)
        do {
            (data, response) = try await URLSession.shared.data(for: req)
        } catch {
            throw APIError.offline
        }
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw APIError.server((response as? HTTPURLResponse)?.statusCode ?? 0)
        }
        return try JSONDecoder().decode(Response.self, from: data)
    }

    private func delete(_ path: String) async throws {
        var req = URLRequest(url: url(path))
        req.httpMethod = "DELETE"
        req.timeoutInterval = 60
        req.setValue("Bearer \(APIConfig.token)", forHTTPHeaderField: "Authorization")
        let (_, response): (Data, URLResponse)
        do {
            (_, response) = try await URLSession.shared.data(for: req)
        } catch {
            throw APIError.offline
        }
        guard let http = response as? HTTPURLResponse, (200..<300).contains(http.statusCode) else {
            throw APIError.server((response as? HTTPURLResponse)?.statusCode ?? 0)
        }
    }

    private struct Empty: Codable {}

    private func get<Response: Decodable>(_ path: String) async throws -> Response {
        try await request(path, body: Optional<Empty>.none)
    }

    // MARK: - Chat

    func chat(_ body: ChatRequest) async throws -> ChatResponse {
        try await request("/api/chat", method: "POST", body: body)
    }

    // MARK: - Journal

    func journalStart(mapsLink: String?) async throws -> JournalStartResponse {
        struct Body: Codable { let maps_link: String? }
        return try await request("/api/journal/start", method: "POST", body: Body(maps_link: mapsLink))
    }

    func journalMessage(entryId: String, message: String, lat: Double?, lon: Double?) async throws -> JournalMessageResponse {
        struct Body: Codable { let entry_id: String; let message: String; let lat: Double?; let lon: Double? }
        return try await request("/api/journal/message", method: "POST",
                                 body: Body(entry_id: entryId, message: message, lat: lat, lon: lon))
    }

    func journalConfirm(entryId: String, accepted: Bool) async throws -> JournalMessageResponse {
        struct Body: Codable { let entry_id: String; let accepted: Bool }
        return try await request("/api/journal/confirm", method: "POST",
                                 body: Body(entry_id: entryId, accepted: accepted))
    }

    func journalFinish(entryId: String) async throws -> [String: JournalEntry] {
        struct Body: Codable { let entry_id: String }
        return try await request("/api/journal/finish", method: "POST", body: Body(entry_id: entryId))
    }

    func journalDiscard(entryId: String) async throws {
        try await delete("/api/journal/\(entryId)")
    }

    func journalTranscript(entryId: String) async throws -> ConversationDetail {
        try await get("/api/journal/\(entryId)/transcript")
    }

    // MARK: - Today / Journey / Map

    func today() async throws -> TodayResponse { try await get("/api/today") }
    func places() async throws -> PlacesResponse { try await get("/api/places") }
    func insights() async throws -> InsightsResponse { try await get("/api/insights") }
    func mapPins() async throws -> PinsResponse { try await get("/api/map/pins") }
    func itinerary() async throws -> ItineraryResponse { try await get("/api/itinerary") }

    func events(lat: Double?, lon: Double?) async throws -> EventsResponse {
        var path = "/api/events"
        if let lat, let lon { path += "?lat=\(lat)&lon=\(lon)" }
        return try await get(path)
    }

    // MARK: - Conversations

    func conversations(type: String? = nil) async throws -> ConversationsResponse {
        let path = type.map { "/api/conversations?type=\($0)" } ?? "/api/conversations"
        return try await get(path)
    }

    func conversation(id: String) async throws -> ConversationDetail {
        try await get("/api/conversations/\(id)")
    }
}
