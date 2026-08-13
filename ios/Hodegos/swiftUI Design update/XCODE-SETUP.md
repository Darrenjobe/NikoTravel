# From zero to Ὁδηγός on your phone

Ordered so you get a running app before you touch any styling. Roughly 45 minutes
to step 5; the theme is the last 20.

## 1. Create the project (once)

Xcode → **File → New → Project → iOS → App**

| Field | Value |
|---|---|
| Product Name | `Hodegos` (ASCII — the Greek name is a *display* name, step 3) |
| Interface | SwiftUI |
| Language | Swift |
| Storage | None |
| Tests | Off |

Save it **outside** the NikoTravel repo (or gitignore the generated `.xcodeproj`).
Set the minimum deployment target to **iOS 17.0** (target → General → Minimum Deployments) —
the code uses `MapCameraPosition`, `UserAnnotation`, and the two-argument `onChange`.

## 2. Bring in the source

Delete Xcode's template `ContentView.swift` and `HodegosApp.swift` (Move to Trash).

Drag from the repo into the project navigator:

```
ios/Hodegos/HodegosApp.swift
ios/Hodegos/ContentView.swift
ios/Hodegos/Models/
ios/Hodegos/Services/
ios/Hodegos/Views/
```

In the drop sheet: **"Copy items if needed" OFF**, "Create groups", target `Hodegos` checked.
Referencing in place means Xcode edits and `git diff` stay in sync.

Build now (⌘B). It should compile against nothing but Foundation/SwiftUI/MapKit/CoreLocation —
there are no packages to add, ever.

## 3. Info.plist keys

Target → **Info** tab → add four rows. Names below are what `APIClient.swift` and
`LocationManager` actually read — the older spec draft calls them `Nikos*`, ignore that.

| Key | Type | Value |
|---|---|---|
| `CFBundleDisplayName` | String | `Ὁδηγός` |
| `NSLocationWhenInUseUsageDescription` | String | Ὁδηγός uses your location to answer questions about where you are and to link places you review. |
| `HodegosBaseURL` | String | `https://hodegos-backend.onrender.com` |
| `HodegosAPIToken` | String | same string as the backend's `API_TOKEN` |

The token is a secret: put it in a `.xcconfig` that is gitignored, or type it straight into
the local project — never commit it.

If you point at `http://localhost:8000` for dev, add App Transport Security →
`NSAllowsLocalNetworking = YES`. Simpler: just use the Render URL.

## 4. Run it

1. Simulator first (⌘R). Location: Features → Location → Custom → 37.9715, 23.7267 (Athens),
   so the location chip and lat/lon actually populate.
2. Then the phone: Xcode → Settings → Accounts → sign in; target → Signing & Capabilities →
   your team; plug in, select the device, Run. Trust the cert on-device under
   Settings → General → VPN & Device Management.

Sanity check before styling: Ask a question and get a reply; Today loads; Map shows pins.
If Ask returns "No connection — Nikos needs data to answer." the base URL or token is wrong —
that error is `APIError.offline`, thrown for *any* URLSession failure, not just airplane mode.

## 5. Apply the theme

Add `swift/Theme.swift` and `swift/Components.swift` from this project to the target
(same drag-in, "Copy items if needed" ON this time — they don't live in the repo yet).

Then delete the four originals they replace, or you'll get redeclaration errors:

- `MessageBubble` — bottom of `Views/AskView.swift`
- `CandidateCard` — bottom of `Views/JournalView.swift`
- `PinDot` — bottom of `Views/MapView.swift`
- `FlowChips` — bottom of `Views/JourneyView.swift`

Now work through `swift/HANDOFF.md` §2, one view at a time, building after each. Every edit
is a modifier or a colour swap — no structural changes — so a broken build means a typo, not
a design problem.

Order matters least here, but Ask first gives you the fastest visual read on whether the
palette is landing.

## 6. TestFlight

App Store Connect → new app, bundle ID `com.yourname.hodegos`. In Xcode: Product → Archive →
Distribute App → TestFlight. Add yourself as an internal tester; the build is usable ~10 minutes
after processing and lasts 90 days.

Do this **at least a week before departure** — first-time App Store Connect setup has a habit of
surfacing an export-compliance or privacy-manifest question you don't want to meet on Sept 4.

## Gotchas worth knowing up front

- **`journalFinish` returns `[String: JournalEntry]`**, not a bare entry — the backend wraps it
  in `{"entry": …}`. Existing code discards the result, so it doesn't bite until you use it.
- **`ChatResponse.sources` is `[String?]`** and gets `compactMap`'d at the call site. Keep that.
- **Serif + Dynamic Type**: `Font.hodDisplay` uses `.system(_:design:.serif)`, so it scales.
  Test at XL (Simulator → Settings → Accessibility → Display & Text Size).
- **No third-party packages.** If a Swift Package looks tempting, the answer for V1 is no.
