import SwiftUI

struct JourneyView: View {
    @State private var section = 0
    @State private var placesResponse: PlacesResponse?
    @State private var insights: [Insight] = []

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                Picker("Section", selection: $section) {
                    Text("Places").tag(0)
                    Text("Insights").tag(1)
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)

                if section == 0 { placesList } else { insightsList }
            }
            .navigationTitle("Journey")
            .navigationBarTitleDisplayMode(.inline)
            .task { await load() }
            .refreshable { await load() }
        }
    }

    private var placesList: some View {
        List {
            if let prefs = placesResponse?.preferences,
               !(prefs.likes.isEmpty && prefs.dislikes.isEmpty) {
                Section("What Niko's learned") {
                    PreferenceChips(likes: prefs.likes, dislikes: prefs.dislikes)
                }
            }
            Section {
                ForEach(placesResponse?.entries ?? []) { entry in
                    NavigationLink {
                        EntryDetailView(entry: entry)
                    } label: {
                        VStack(alignment: .leading, spacing: 3) {
                            HStack {
                                Text(entry.placeName ?? "Unconfirmed location")
                                    .font(.subheadline.weight(.semibold))
                                Spacer()
                                Text(sentimentEmoji(entry.sentiment))
                            }
                            Text(entry.line ?? "").font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
                if placesResponse?.entries.isEmpty ?? true {
                    Text("Journal entries land here.").font(.footnote).foregroundStyle(.secondary)
                }
            }
        }
    }

    private var insightsList: some View {
        List {
            Section(footer: Text("Generated once or twice a day whenever you've logged 2+ moments in the last 24 hours.")) {
                ForEach(insights) { insight in
                    HStack(alignment: .top, spacing: 10) {
                        Text(insight.emoji ?? "✨").font(.title3)
                        VStack(alignment: .leading, spacing: 3) {
                            Text(insight.text).font(.footnote)
                            if let tag = insight.tag {
                                Text(tag.uppercased()).font(.caption2.weight(.semibold))
                                    .foregroundStyle(.secondary)
                            }
                        }
                    }
                }
                if insights.isEmpty {
                    Text("No insights yet — they show up after a day of journaling and questions.")
                        .font(.footnote).foregroundStyle(.secondary)
                }
            }
        }
    }

    private func load() async {
        if let p = try? await APIClient.shared.places() {
            placesResponse = p
            CacheStore.save(p, key: "places")
        } else if let cached = CacheStore.load(PlacesResponse.self, key: "places") {
            placesResponse = cached
        }
        if let i = try? await APIClient.shared.insights() {
            insights = i.insights
        }
    }
}

func sentimentEmoji(_ sentiment: String?) -> String {
    switch sentiment {
    case "loved": return "😍"
    case "mixed": return "🙂"
    case "skip": return "😕"
    default: return "▫️"
    }
}

struct PreferenceChips: View {
    let likes: [String]
    let dislikes: [String]

    var body: some View {
        FlowChips(items:
            likes.map { ("Likes: \($0)", Color.green) } +
            dislikes.map { ("Dislikes: \($0)", Color.red) }
        )
    }
}

struct FlowChips: View {
    let items: [(String, Color)]

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack {
                ForEach(items.indices, id: \.self) { i in
                    Text(items[i].0)
                        .font(.caption.weight(.semibold))
                        .padding(.horizontal, 10).padding(.vertical, 5)
                        .background(items[i].1.opacity(0.12), in: Capsule())
                        .foregroundStyle(items[i].1)
                }
            }
        }
    }
}

struct EntryDetailView: View {
    let entry: JournalEntry

    var body: some View {
        List {
            Section("Niko's summary") {
                Text(entry.summary ?? "—").font(.footnote)
            }
            Section("Best / Worst") {
                Label(entry.best ?? "—", systemImage: "hand.thumbsup.fill")
                    .font(.footnote).foregroundStyle(.green)
                Label(entry.worst ?? "—", systemImage: "hand.thumbsdown.fill")
                    .font(.footnote).foregroundStyle(.red)
            }
            if let maps = entry.mapsUrl, let url = URL(string: maps) {
                Link("Open in Google Maps ↗", destination: url)
                    .font(.subheadline.weight(.semibold))
            } else {
                Label("Unconfirmed location — no link", systemImage: "mappin.slash")
                    .font(.footnote).foregroundStyle(.secondary)
            }
        }
        .navigationTitle(entry.placeName ?? "Entry")
        .navigationBarTitleDisplayMode(.inline)
    }
}
