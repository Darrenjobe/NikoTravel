# Ὁδηγός iOS app — setup

**Naming:** the app is **Ὁδηγός** (Greek for "guide", *o-dhi-GOS*). Greek
script is used everywhere the user sees the name; code identifiers use the
Latin transliteration **Hodegos**. **Niko** is the in-app assistant persona —
it stays in assistant copy ("Ask Niko", "What Niko's learned") and never
appears as an identifier.

The Swift sources live in `ios/Hodegos/`. The Xcode project itself isn't
checked in (project files are machine-generated noise) — create it once
locally:

## 1. Create the project

1. Xcode → **File → New → Project → iOS → App**
2. Product name **Hodegos** (ASCII — the display name is set separately in
   step 2), interface SwiftUI, language Swift, no tests for now.
3. Save it anywhere *outside* this repo (or add the generated files to
   `.gitignore` if inside).
4. Delete the template `ContentView.swift`/`HodegosApp.swift`, then drag the
   `ios/Hodegos/` folders (`Models`, `Services`, `Views`, plus
   `HodegosApp.swift` and `ContentView.swift`) into the project navigator —
   check **"Copy items if needed" OFF** and reference them in place, so edits
   stay in the repo.

> Keep the target, module, and bundle identifier ASCII (`Hodegos`,
> `com.yourname.hodegos`). Non-ASCII product/module names cause friction in
> bundle IDs, schemes, and command-line tooling — the Greek name is applied
> purely as a display name below.

## 2. Configure

In the target's **Info** tab add:

| Key | Value |
|---|---|
| `CFBundleDisplayName` | `Ὁδηγός` — the home-screen name under the icon |
| `NSLocationWhenInUseUsageDescription` | "Ὁδηγός uses your location to answer questions about where you are and to link places you review." |
| `HodegosBaseURL` | `https://hodegos-backend.onrender.com` (see below for local dev) |
| `HodegosAPIToken` | the same value as the backend's `API_TOKEN` |

### Pointing the app at a backend on your Mac

`localhost` on the phone means *the phone*, not your Mac — you need the Mac's
network address, and the backend must be bound to `0.0.0.0` (see
`backend/README.md` → Testing from your phone).

Set `HodegosBaseURL` to the Mac's **Bonjour name**, not its IP — the IP changes
whenever DHCP reassigns it, the `.local` name doesn't:

```
http://Johns-MacBook-Pro.local:8000
```

Two iOS restrictions will otherwise make this fail silently, both **dev-only —
remove them before shipping to TestFlight with the Render URL**:

| Key | Value | Why |
|---|---|---|
| `NSAppTransportSecurity` → `NSAllowsLocalNetworking` (Boolean) | `YES` | App Transport Security blocks plaintext `http://`. This exception permits it for `.local` and unqualified hostnames only — far narrower than `NSAllowsArbitraryLoads`, which disables ATS everywhere. |
| `NSLocalNetworkUsageDescription` (String) | "Ὁδηγός connects to the development backend running on your Mac." | iOS 14+ requires consent before an app touches the local network. Without this string the connection fails with no prompt and no useful error. |

iOS shows the local-network prompt **once**; if you tap Deny it won't ask
again. Re-enable under Settings → Privacy & Security → Local Network.

Because `NSAllowsLocalNetworking` only covers `.local` and unqualified names,
using a raw `192.168.x.x` IP would additionally require `NSAllowsArbitraryLoads`
— another reason to use the Bonjour name.

Once the backend is on Render, `HodegosBaseURL` becomes the HTTPS URL and
neither key is needed.

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
