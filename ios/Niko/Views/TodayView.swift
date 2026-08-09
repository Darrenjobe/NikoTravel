import SwiftUI

struct TodayView: View {
    @State private var today: TodayResponse?
    @State private var offline = false

    var body: some View {
        NavigationStack {
            List {
                if offline {
                    Label("Offline — showing your last synced guide", systemImage: "wifi.slash")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Section {
                    if let guide = today?.morningGuide {
                        ForEach(guide.stops) { stop in
                            VStack(alignment: .leading, spacing: 5) {
                                HStack {
                                    Text(stop.name).font(.subheadline.weight(.bold))
                                    Spacer()
                                    Text(stop.hours).font(.caption.weight(.semibold))
                                        .foregroundStyle(.green)
                                }
                                Text(stop.blurb).font(.footnote)
                                Text("💡 \(stop.tip)").font(.caption)
                                    .padding(8)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .background(.blue.opacity(0.08), in: RoundedRectangle(cornerRadius: 8))
                            }
                            .padding(.vertical, 2)
                        }
                        if let lunch = today?.morningGuide?.lunch {
                            Label(lunch, systemImage: "fork.knife").font(.footnote)
                        }
                    } else {
                        Text("Your morning guide lands at 7 AM.")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                } header: {
                    Label("Morning Guide", systemImage: "sun.max.fill")
                }

                Section {
                    if let recap = today?.eveningRecap {
                        Text(recap.narrative).font(.footnote)
                        ForEach(recap.entries) { entry in
                            VStack(alignment: .leading, spacing: 3) {
                                Text(entry.placeName ?? "Unconfirmed location")
                                    .font(.subheadline.weight(.semibold))
                                Text(entry.line ?? "").font(.caption).foregroundStyle(.secondary)
                                if let maps = entry.mapsUrl, let url = URL(string: maps) {
                                    Link("Google Maps ↗", destination: url).font(.caption.weight(.semibold))
                                }
                            }
                        }
                    } else {
                        Text("Tonight's recap lands at 8 PM — journal something today and it'll show up here.")
                            .font(.footnote).foregroundStyle(.secondary)
                    }
                } header: {
                    Label("Evening Recap", systemImage: "moon.stars.fill")
                }
            }
            .navigationTitle(title)
            .task { await load() }
            .refreshable { await load() }
        }
    }

    private var title: String {
        if let t = today, let day = t.tripDay {
            return "Day \(day) · \(t.region?.components(separatedBy: " (").first ?? "")"
        }
        return "Today"
    }

    private func load() async {
        do {
            let response = try await APIClient.shared.today()
            today = response
            offline = false
            CacheStore.save(response, key: "today")
        } catch {
            if let cached = CacheStore.load(TodayResponse.self, key: "today") {
                today = cached
                offline = true
            }
        }
    }
}
