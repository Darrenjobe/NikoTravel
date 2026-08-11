import Foundation

/// Thin async client for the Ὁδηγός backend. Configure the base URL and token
/// in Info.plist (see ios/README.md) or edit the defaults below for dev.
enum APIConfig {
    static var baseURL: URL {
        if let s = Bundle.main.object(forInfoDictionaryKey: "HodegosBaseURL") as? String,
           let url = URL(string: s) { return url }
        return URL(string: "http://127.0.0.1:8000")!
    }

    static var token: String {
        (Bundle.main.object(forInfoDictionaryKey: "HodegosAPIToken") as? String) ?? ""
    }
}

enum APIError: LocalizedError {
    case offline
    case missingToken
    case unauthorized
    case server(Int)

    var errorDescription: String? {
        switch self {
        case .offline:
            return "No connection — Niko needs data to answer."
        case .missingToken:
            return "HodegosAPIToken is missing from Info.plist. Add it with "
                 + "the same value as the backend's API_TOKEN."
        case .unauthorized:
            return "Unauthorized (401). HodegosAPIToken doesn't match the "
                 + "backend's API_TOKEN — check the server log for details."
        case .server(let code):
            return "Server error (\(code)). Try again."
        }
    }
}

struct APIClient {
    static let shared = APIClient()

    private func request<Body: Encodable, Response: Decodable>(
        _ path: String, method: String = "GET", body: Body? = nil
    ) async throws -> Response {
        // Fail with a clear message rather than sending "Bearer " and
        // puzzling over a 401.
        guard !APIConfig.token.isEmpty else { throw APIError.missingToken }

        var req = URLRequest(url: APIConfig.baseURL.appendingPathComponent(path))
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
        guard let http = response as? HTTPURLResponse else { throw APIError.server(0) }
        if http.statusCode == 401 { throw APIError.unauthorized }
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.server(http.statusCode)
        }
        return try JSONDecoder().decode(Response.self, from: data)
    }

    private struct Empty: Codable {}

    private func get<Response: Decodable>(_ path: String) async throws -> Response {
        try await request(path, body: Optional<Empty>.none)
    }

    // MARK: - Endpoints

    func chat(_ body: ChatRequest) async throws -> ChatResponse {
        try await request("/api/chat", method: "POST", body: body)
    }

    func journalStart(mapsLink: String?) async throws -> JournalStartResponse {
        struct Body: Codable { let maps_link: String? }
        //return try await request("/api/journal/start", method: "POST", body: Body(maps_link: mapsLink))
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

    func today() async throws -> TodayResponse { try await get("/api/today") }
    func places() async throws -> PlacesResponse { try await get("/api/places") }
    func insights() async throws -> InsightsResponse { try await get("/api/insights") }
    func mapPins() async throws -> PinsResponse { try await get("/api/map/pins") }
}
