# Niko iOS app — setup

The Swift sources live in `ios/Niko/`. The Xcode project itself isn't checked
in (project files are machine-generated noise) — create it once locally:

## 1. Create the project

1. Xcode → **File → New → Project → iOS → App**
2. Product name **Niko**, interface SwiftUI, language Swift, no tests for now.
3. Save it anywhere *outside* this repo (or add the generated files to
   `.gitignore` if inside).
4. Delete the template `ContentView.swift`/`NikoApp.swift`, then drag the
   `ios/Niko/` folders (`Models`, `Services`, `Views`, plus `NikoApp.swift`
   and `ContentView.swift`) into the project navigator — check
   **"Copy items if needed" OFF** and reference them in place, so edits stay
   in the repo.

## 2. Configure

In the target's **Info** tab add:

| Key | Value |
|---|---|
| `NSLocationWhenInUseUsageDescription` | "Niko uses your location to answer questions about where you are and link places you review." |
| `NikoBaseURL` | `https://niko-backend.onrender.com` (or `http://localhost:8000` for dev) |
| `NikoAPIToken` | the same value as the backend's `API_TOKEN` |

For local dev against `http://localhost:8000`, also allow insecure loads for
localhost (App Transport Security exception) or just use the Render URL.

## 3. Run on your phone

1. Xcode → Settings → Accounts → sign in with your Apple developer account.
2. Target → Signing & Capabilities → select your team; Xcode manages the
   provisioning profile.
3. Plug in the phone (or pair over Wi-Fi), select it as the run destination,
   hit Run. First install requires trusting the developer cert on-device
   (Settings → General → VPN & Device Management).

**Before the trip:** distribute via TestFlight instead of a dev build — dev
provisioning profiles expire after 7 days on a free account and 1 year on a
paid one, but TestFlight builds run for 90 days and survive without the Mac.

## Voice input

The standard iOS keyboard's mic button provides dictation in every text field —
no speech framework, no permission prompt. That is the V1 voice story.
