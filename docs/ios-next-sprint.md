# Ὁδηγός iOS — implementing the new backend features

Hand-off doc for the SwiftUI side. Everything described here is **already
live on the backend** and verified; nothing below is blocked.

Naming, unchanged: **Ὁδηγός** is the app, `Hodegos` is for identifiers, and
**Nikos** is the assistant persona (renamed from "Niko" — the Swift strings
are still the old name; see §7).

Base URL and token come from `Info.plist` (`HodegosBaseURL`,
`HodegosAPIToken`) as they do today.

---

## 0. Do these two first — they are blocking and they are bugs

### 0.1 `/api/itinerary` currently fails to decode, silently

`ItineraryDay.stops` is typed `[GuideStop]`, and `GuideStop` requires
`hours` and `tip`. The itinerary endpoint returns stops with **only**
`name` and `blurb` — confirmed against the live payload:

```
stop keys: ['blurb', 'name']
```

So decoding throws, `try?` in `HomeView.load()` swallows it, and
`upcomingDays` is permanently empty. Home's "Upcoming" section has never
rendered. This is not a backend gap — the itinerary markdown genuinely has no
opening hours; only the LLM-generated morning guide does.

Give itinerary days their own types in `Models/Models.swift`:

```swift
struct ItineraryResponse: Codable { let days: [ItineraryDay] }

struct ItineraryDay: Codable, Identifiable {
    let date: String
    let tripDay: Int
    let region: String?
    let stops: [ItineraryStop]
    let dining: [DiningOption]

    var id: String { date }

    enum CodingKeys: String, CodingKey {
        case date, region, stops, dining
        case tripDay = "trip_day"
    }
}

struct ItineraryStop: Codable, Identifiable {
    let name: String
    let blurb: String
    var id: String { name }
}

struct DiningOption: Codable, Identifiable {
    let meal: String            // "Breakfast" | "Lunch" | "Dinner"
    let options: [String]
    var id: String { meal }
}
```

`region` and `dining` are also returned today and currently dropped on the
floor. The Itinerary screen (§3) needs both.

Do **not** change `GuideStop` to make its fields optional — that would weaken
the Today view, where `hours` and `tip` are always present.

### 0.2 `APIError` lost its auth cases

`APIError` is back to `.offline` / `.server(Int)`. The 401 diagnostics were
restored server-side in `74197c7`, but the client can no longer distinguish
them, so a token problem in Greece reads as "Server error (401)". Restore:

```swift
enum APIError: LocalizedError {
    case offline
    case missingToken
    case unauthorized
    case server(Int)

    var errorDescription: String? {
        switch self {
        case .offline:       return "No connection — Nikos needs data to answer."
        case .missingToken:  return "No API token set. Add HodegosAPIToken to Info.plist."
        case .unauthorized:  return "Token rejected. Check HodegosAPIToken matches the server."
        case .server(let c): return "Server error (\(c)). Try again."
        }
    }
}
```

In `request` / `delete`, throw `.missingToken` when `APIConfig.token` is
empty before sending, and map `401` to `.unauthorized`.

> This file has now been overwritten twice by an older Xcode working copy.
> **Pull before opening Xcode.**

---

## 1. `APIClient` — one new helper, five new endpoints

Query parameters already work: `url(_:)` is string-based, so
`"/api/x?q=\(v)"` is fine. `delete(_:)` exists and discards the response
body, which suits every DELETE below.

The one genuine gap is **raw bytes** — `request` always decodes JSON, and
`/api/tts` returns `audio/mpeg`. Add alongside it:

```swift
private func requestData<Body: Encodable>(
    _ path: String, method: String = "POST", body: Body? = nil
) async throws -> (Data, HTTPURLResponse) {
    var req = URLRequest(url: url(path))
    req.httpMethod = method
    req.timeoutInterval = 120          // synthesis is slower than a JSON call
    req.setValue("Bearer \(APIConfig.token)", forHTTPHeaderField: "Authorization")
    if let body {
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONEncoder().encode(body)
    }
    let (data, response): (Data, URLResponse)
    do { (data, response) = try await URLSession.shared.data(for: req) }
    catch { throw APIError.offline }
    guard let http = response as? HTTPURLResponse else { throw APIError.server(0) }
    guard (200..<300).contains(http.statusCode) else {
        throw http.statusCode == 401 ? APIError.unauthorized
                                     : APIError.server(http.statusCode)
    }
    return (data, http)
}
```

Then:

```swift
// MARK: - Map search & saved places

func searchPlaces(q: String, lat: Double?, lon: Double?) async throws -> PlacesSearchResponse {
    var path = "/api/places/search?q=\(q.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
    if let lat, let lon { path += "&lat=\(lat)&lon=\(lon)" }
    return try await get(path)
}

func savedPlaces() async throws -> SavedPlacesResponse { try await get("/api/saved") }
func savePlace(_ place: Place) async throws -> SavedAck {
    try await request("/api/saved", method: "POST", body: place)
}
func unsavePlace(placeId: String) async throws { try await delete("/api/saved/\(placeId)") }

// MARK: - Models

func models(refresh: Bool = false) async throws -> ModelsResponse {
    try await get("/api/models" + (refresh ? "?refresh=true" : ""))
}
func setModel(chat: String? = nil, job: String? = nil) async throws -> ModelSelectionAck {
    struct Body: Codable { let chat_model: String?; let job_model: String? }
    return try await request("/api/models", method: "POST", body: Body(chat_model: chat, job_model: job))
}
func resetModels() async throws { try await delete("/api/models") }

// MARK: - Speech

/// Returns MP3 bytes plus whether the server served them from its cache.
func speak(_ text: String) async throws -> (Data, Bool) {
    struct Body: Codable { let text: String }
    let (data, http) = try await requestData("/api/tts", body: Body(text: text))
    return (data, http.value(forHTTPHeaderField: "X-Hodegos-Cached") == "1")
}
```

`Place` already encodes with the right snake_case keys, so it can be POSTed
to `/api/saved` unchanged.

New response models:

```swift
struct PlacesSearchResponse: Codable { let places: [Place] }
struct SavedPlacesResponse: Codable { let places: [Place] }
struct SavedAck: Codable { let ok: Bool; let saved: Bool }

struct ModelsResponse: Codable {
    let models: [ModelInfo]
    let source: String              // live | cache | stale-cache | fallback
    let note: String?
    let chatModel: String
    let jobModel: String
    enum CodingKeys: String, CodingKey {
        case models, source, note
        case chatModel = "chat_model"
        case jobModel  = "job_model"
    }
}

struct ModelInfo: Codable, Identifiable {
    let id: String
    let displayName: String
    let maxInputTokens: Int?
    let maxOutputTokens: Int?
    enum CodingKeys: String, CodingKey {
        case id
        case displayName     = "display_name"
        case maxInputTokens  = "max_input_tokens"
        case maxOutputTokens = "max_output_tokens"
    }
}

struct ModelSelectionAck: Codable {
    let chatModel: String
    let jobModel: String
    let warnings: [String]
    enum CodingKeys: String, CodingKey {
        case warnings
        case chatModel = "chat_model"
        case jobModel  = "job_model"
    }
}
```

---

## 2. Map — search, save, filter

All three land in `Views/MapView.swift`. Do them in this order; each depends
on the previous.

### 2.1 Replace `MKLocalSearch` with the backend

`search()` currently uses `MKLocalSearch`, which returns **no Place ID and no
`maps_url`** — so it synthesizes `placeId: "\(lat),\(lon)"` and passes
`mapsUrl: nil`. That is why search results can't open a Google business page
the way journal pins and recommendations can, and it leaves nothing stable to
save against.

`GET /api/places/search` wraps the same Google Places call the concierge uses,
so a searched result and a recommended one are the same object:

```swift
private func search() async {
    guard !searchText.isEmpty else { return }
    let coord = location.coordinate
    guard let res = try? await APIClient.shared.searchPlaces(
        q: searchText, lat: coord?.latitude, lon: coord?.longitude) else { return }
    searchResults = res.places
    if let first = res.places.first, let lat = first.lat, let lon = first.lon {
        position = .region(.init(center: .init(latitude: lat, longitude: lon),
                                 latitudinalMeters: 1500, longitudinalMeters: 1500))
    }
}
```

`MapDetailCard`'s existing "Open in Google Maps ↗" link starts working for
search results with **no change to that view** — the results now carry a real
`maps_url`.

Location bias matters: pass the user's coordinate so "taverna" means *near
me*, not somewhere in Ohio.

### 2.2 Saved layer and the heart

State and loading, following the existing fetch-then-fall-back-to-cache shape
already in `load()`:

```swift
@State private var savedPlaces: [Place] = []
@State private var showSaved = true

private func loadSaved() async {
    if let res = try? await APIClient.shared.savedPlaces() {
        savedPlaces = res.places
        CacheStore.save(res, key: "saved")
    } else if let cached = CacheStore.load(SavedPlacesResponse.self, key: "saved") {
        savedPlaces = cached.places
    }
}
```

Render as a fourth `Annotation` layer gated on `showSaved`, using
`PinDot(color: .hodOlive)`. **Dedupe by `place_id`** against recommendations
and search results, preferring saved styling, so a place that is both doesn't
draw two overlapping pins.

Extend `MapDetailCard` — its header is already
`Text(title) / Spacer() / close button`, so the heart slots between the spacer
and the close:

```swift
struct MapDetailCard: View {
    let title: String
    let subtitle: String
    let mapsUrl: String?
    var isSaved: Bool = false
    var onToggleSave: (() -> Void)? = nil     // nil = not saveable
    let onClose: () -> Void
    ...
    HStack {
        Text(title).font(.hodDisplay(.title3))
        Spacer()
        if let onToggleSave {
            Button(action: onToggleSave) {
                Image(systemName: isSaved ? "heart.fill" : "heart")
                    .foregroundStyle(Color.hodTerra)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(isSaved ? "Remove from saved" : "Save this place")
        }
        Button(action: onClose) { Image(systemName: "xmark.circle.fill") }
            .foregroundStyle(.secondary)
    }
}
```

Pass `onToggleSave: nil` for journal pins — a `MapPin` has no `place_id`, so
there is nothing to key a save on.

**Toggle optimistically**, then call the API, and revert on failure:

```swift
private func toggleSave(_ place: Place) {
    guard let pid = place.placeId else { return }
    let wasSaved = savedPlaces.contains { $0.placeId == pid }
    if wasSaved { savedPlaces.removeAll { $0.placeId == pid } }
    else        { savedPlaces.insert(place, at: 0) }
    Task {
        do {
            if wasSaved { try await APIClient.shared.unsavePlace(placeId: pid) }
            else        { _ = try await APIClient.shared.savePlace(place) }
            CacheStore.save(SavedPlacesResponse(places: savedPlaces), key: "saved")
        } catch {
            if wasSaved { savedPlaces.insert(place, at: 0) }
            else        { savedPlaces.removeAll { $0.placeId == pid } }
        }
    }
}
```

A heart that waits on a network round-trip feels broken on hotel Wi-Fi. Both
backend calls are idempotent — POST is `INSERT OR REPLACE`, and DELETE of an
absent id succeeds — so a retry or a double-tap is safe.

### 2.3 Filter submenu

Replace the two `Toggle`s in `legend` with one filter button opening a `Menu`:

```swift
Menu {
    Toggle("My places",       isOn: $showMine)
    Toggle("Recommendations", isOn: $showRecs)
    Toggle("Saved",           isOn: $showSaved)
} label: {
    Image(systemName: "line.3.horizontal.decrease.circle")
        .padding(8)
        .background(.regularMaterial, in: Circle())
        .foregroundStyle(Color.hodAegean)
}
```

All three default **on**. `Menu` gives native multi-toggle behaviour with no
custom popover. Keep the find-my-location button to its right; the legend row
goes from two wide pill toggles to two icons, which is also a better use of
space over a map.

Pin colours, for the legend and any future key: journaled `.hodTerra`,
recommendations `.hodAegean`, saved `.hodOlive`, search results `.hodMuted`.

---

## 3. Itinerary screen

`GET /api/itinerary` returns the **whole trip** — all 21 days, Sept 5–25.
(It used to default to "today onward", which silently dropped past days; that
was fixed backend-side.) Pass `?start=&days=` only for a window.

New `Views/ItineraryView.swift`:

- `List` grouped by `region`, one `Section` per region, header = region name
  plus its date span via `HodLabel`.
- Row per day: "Day 7 · Sept 11" plus the stop count.
- Tap → detail listing `stops` (name in `.hodDisplay`, blurb in `.caption`)
  and `dining` grouped by meal.
- `.hodScreen()`, `Color.hodCard` row backgrounds, matching `TodayView`.

Entry point: a `NavigationLink` in `SidebarMenuView` (in `HomeView.swift`),
in a new **Trip** section above **Connection**. That view is presented as a
`.sheet` and already wraps its `List` in a `NavigationStack`, so the push
works with no restructuring.

**Cache it** under key `"itinerary"`, loading cache first then refreshing —
same order as `HomeView.load()`. This is the screen that has to work through
Mt Athos (Sept 20–23, minimal connectivity).

Fixing §0.1 also makes Home's "Upcoming" section start rendering for free.

---

## 4. Speech

`POST /api/tts` returns **MP3 bytes**, not JSON. Any text the app is showing
can be spoken: an Ask answer, a journal reply, a recommendation, the morning
guide.

```swift
import AVFoundation

@MainActor
final class SpeechPlayer: ObservableObject {
    @Published var speakingId: UUID?          // which bubble is playing
    @Published var isLoading = false
    private var player: AVAudioPlayer?

    func toggle(_ text: String, id: UUID) async {
        if speakingId == id { stop(); return }
        stop()
        isLoading = true
        defer { isLoading = false }
        guard let (data, _) = try? await APIClient.shared.speak(text) else { return }
        try? AVAudioSession.sharedInstance().setCategory(.playback, mode: .spokenAudio)
        try? AVAudioSession.sharedInstance().setActive(true)
        player = try? AVAudioPlayer(data: data)
        player?.play()
        speakingId = id
    }

    func stop() {
        player?.stop(); player = nil; speakingId = nil
    }
}
```

UI: a small speaker button on each Nikos message bubble in `Components.swift`
— `speaker.wave.2` / `speaker.wave.2.fill` while playing, a `ProgressView`
while loading. Same treatment on the morning guide card and evening digest.

Things worth knowing:

- **The server strips markdown before synthesis.** Send the raw reply text;
  don't pre-clean it. `POST /api/tts/preview` returns exactly what the voice
  will be given, and costs nothing — useful while tuning.
- **Greek script is intentional.** The configured voice is a Greek speaker and
  the Greek characters drive correct pronunciation. Never transliterate before
  sending.
- **`X-Hodegos-Cached: 1`** means the server had it already; replaying the
  same guide is free.
- **503 vs 502.** 503 = `ELEVENLABS_API_KEY` not configured; don't retry, and
  hide the speaker button. 502 = ElevenLabs failed (quota, transient); a retry
  is reasonable. Both are distinguishable via `.server(code)`.
- Set `AVAudioSession` to `.playback` or audio won't play with the ringer
  switch silenced — the common "it works on my desk, not in my pocket" bug.
- Consider `TTS_OUTPUT_FORMAT=mp3_22050_32` server-side over eSIM: roughly 4×
  smaller for spoken word.

---

## 5. Model picker (Settings)

Chat and jobs are set independently, and the choice persists on the server —
so it survives redeploys and applies wherever the app runs. Default is now
`claude-sonnet-5` for both.

A **Models** section in `SidebarMenuView`, or a small `SettingsView`:

- `GET /api/models` → `models[]` already filtered to ones the app can run on.
- Two `Picker`s bound to `chat_model` and `job_model`.
- Show `source`: `live` / `cache` / `stale-cache` / `fallback`. When it's
  `fallback` the list is a built-in guess, not the account's real catalog —
  say so rather than presenting it as fact.
- Surface `warnings[]` from the POST response; a non-empty array means the
  choice was accepted but couldn't be verified.
- A "Reset to default" row calling `resetModels()`.

Pull-to-refresh should call `models(refresh: true)` — the server caches the
catalog for 24 h otherwise.

---

## 6. `CacheStore` durability

`CacheStore` writes to `.cachesDirectory`, which iOS may evict under storage
pressure. That's wrong for the itinerary, saved places, and the day's guide —
exactly the data needed when there's no signal. Change `dir` to
`.applicationSupportDirectory` (excluded from iCloud backup if you prefer).

One line, and it belongs with this work rather than the Week-3 offline pass,
because §2.2 and §3 both add offline-critical caches.

> `docs/FRONTEND_STATE.md` describes `CacheStore` as "UserDefaults-backed".
> It writes JSON files. Worth correcting while you're in there.

---

## 7. Persona rename: Niko → Nikos

The backend and all docs now say **Nikos**. The Swift side still says "Niko"
in six user-visible places:

| File | What |
|---|---|
| `Services/APIClient.swift` | `.offline` message |
| `Views/HomeView.swift` | "Ask Nikos anything…" quick tip |
| `Views/HistoryView.swift` | empty-state copy |
| `Views/JourneyView.swift` | "Niko's learned", "Niko's summary" |
| `Models/Models.swift` | `enum Role { case user, niko }` |
| `Views/AskView.swift` | `.niko` usages |

The enum case is an internal identifier — rename to `.nikos` for consistency
or leave it; just don't leave the *strings* split, since the assistant now
introduces itself as Nikos in every prompt.

---

## 8. Suggested order

1. §0.1 + §0.2 — bug fixes, unblock everything (~30 min)
2. §1 — `APIClient` surface (~30 min)
3. §2.1 → §2.2 → §2.3 — the map, in that order
4. §3 — Itinerary screen
5. §4 — speech
6. §5, §6, §7 — settings, cache durability, rename

§3 is independent of §2 and makes a good parallel or fallback task.

---

## 9. Verifying against the real backend

Point `HodegosBaseURL` at the Mac or the Render URL, then:

1. **Search** "taverna" → pins appear → tap one → **Open in Google Maps ↗**
   opens the real business page. This is the thing `MKLocalSearch` could not
   do; if the link is missing, §2.1 didn't land.
2. **Heart** a result → fills → force-quit → relaunch → still filled and still
   pinned. Tap again → gone after refresh.
3. **Filter** → all three on by default; each toggle removes only its layer; a
   place that is both saved and recommended draws one pin.
4. **Menu → Itinerary** → 21 days grouped by region, stops *and* dining
   populated. Airplane mode → still renders from cache.
5. **Speak** a reply containing Greek → audio plays, Greek is pronounced as
   Greek, no "asterisk asterisk" or emoji read aloud. Tap again → replays
   instantly (server cache).
6. **Models** → switch chat to Opus → `GET /api/models/current` on the server
   reflects it → restart the app → still selected.
7. Blank `HodegosAPIToken` → error reads "No API token set", not
   "Server error (401)".

If search returns nothing, check the server's startup log for
`✓ GOOGLE_PLACES_API_KEY` — search degrades to an empty list rather than
erroring, so a missing key looks exactly like a client bug.
