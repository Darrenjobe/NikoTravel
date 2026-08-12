# Hodegos — visual handoff (Native + Greek palette)

Two new files, then eight small edits. No layout, navigation, or networking changes;
every native control stays a native control.

## 1. Add
- `ios/Hodegos/Theme.swift` — palette, serif/mono fonts, `HodLabel`, `HoursPill`, `.hodScreen()`
- `ios/Hodegos/Components.swift` — themed `MessageBubble`, `CandidateCard`, `PinDot`, `FlowChips`

Delete the old `MessageBubble` (AskView.swift), `CandidateCard` (JournalView.swift),
`PinDot` + `FlowChips` (MapView.swift / JourneyView.swift) — the new ones have identical
initialisers, so no call site changes.

## 2. Edits

### ContentView.swift
Nothing required. Optional: `.tint(.hodAegean)` on the `TabView`.

### AskView.swift
- `VStack(spacing: 0) { … }` → add `.hodScreen()` after `.navigationTitle("Ask Niko")`.
- Location chip: `.foregroundStyle(.tint)` → `.foregroundStyle(Color.hodAegean)`.
- Empty state: `Text("Ask me anything out here").font(.headline)` → `.font(.hodDisplay(.title2))`;
  starter buttons `.tint(.hodAegean)`.
- `memoryBar`: `.tint(.blue)` → `.tint(.hodAegean)`.
- `inputBar`: send glyph `.foregroundStyle(Color.hodAegean)`.

### JournalView.swift
- `.tint(.orange)` → `.tint(.hodTerra)`.
- Confirmed-place strip: `.background(.orange.opacity(0.12))` → `.background(Color.hodTerra.opacity(0.12))`,
  and `Text(confirmedPlace).font(.hodDisplay(.headline)).foregroundStyle(Color.hodTerra)`.
- `MessageBubble(message: msg, onShowMap: { _ in }, accent: .hodTerra)` — pass the terracotta accent.
- Add `.hodScreen(tint: .hodTerra)` alongside the existing modifiers.

### MapView.swift
- `legend`: `.tint(.orange)` → `.tint(.hodTerra)`, `.tint(.blue)` → `.tint(.hodAegean)`.
- Annotations: `PinDot(color: .orange)` → `.hodTerra`; `PinDot(color: .blue)` → `.hodAegean`.
- `MapDetailCard`: title `.font(.hodDisplay(.title3))`; keep `.regularMaterial`.
- Recommendation subtitle already reads `address · ★ rating` — unchanged.

### TodayView.swift
- Wrap the `List` with `.hodScreen()`.
- Stop rows: `Text(stop.name).font(.hodDisplay(.headline))`; replace the green hours `Text`
  with `HoursPill(hours: stop.hours)` (handles the §5.4 "style warnings differently" rule).
- Tip inset: `.background(.blue.opacity(0.08))` → `Color.hodAegean.opacity(0.08)`.
- Section headers: `Label("Morning Guide", …)` → `HodLabel(text: "Morning guide")`.
- Offline row: `.foregroundStyle(Color.hodCrimson)`, keep `wifi.slash`.

### JourneyView.swift
- `.hodScreen()` on the `VStack`.
- Entry rows: place name `.font(.hodDisplay(.headline))`; use `.hodMuted` when `placeName == nil`
  so "Unconfirmed location" reads as a placeholder without hiding it.
- `PreferenceChips`: `Color.green` → `.hodOlive`, `Color.red` → `.hodCrimson`.
- `EntryDetailView`: `Section("Niko's summary")` header → `HodLabel(text: "Niko's summary")`;
  best `.hodOlive`, worst `.hodCrimson`; leave the "Unconfirmed location — no link" row as is.
- `sentimentEmoji` unchanged — emoji stays the non-colour signal for accessibility.

## 3. Accessibility notes
- Serif is applied via `.system(_:design:.serif)`, so Dynamic Type still scales; test at XL.
- Every accent carries a second signal: sentiment emoji, layer chip text, `HoursPill` wording.
- `HodLabel` kerns uppercase mono at caption2 — do not go below it.
