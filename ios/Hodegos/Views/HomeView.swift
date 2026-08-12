import SwiftUI

struct HomeView: View {
    @State private var today: TodayResponse?
    @State private var showMenu = false

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 28) {
                    VStack(alignment: .leading, spacing: 6) {
                        Text("Ὁδηγός")
                            .font(.hodDisplay(.largeTitle))
                            .foregroundStyle(Color.hodInk)
                        Text("Your Greek travel companion")
                            .font(.subheadline)
                            .foregroundStyle(Color.hodMuted)
                    }
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.top, 8)

                    if let guide = today?.morningGuide, !guide.stops.isEmpty {
                        VStack(alignment: .leading, spacing: 12) {
                            HodLabel(text: "Today's Stops")
                            ForEach(guide.stops) { stop in
                                HStack(alignment: .top, spacing: 12) {
                                    Image(systemName: "mappin.circle.fill")
                                        .foregroundStyle(Color.hodAegean)
                                        .font(.title3)
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(stop.name).font(.hodDisplay(.headline))
                                        Text(stop.blurb)
                                            .font(.caption)
                                            .foregroundStyle(Color.hodMuted)
                                        HoursPill(hours: stop.hours)
                                    }
                                }
                                .padding(14)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.hodCard, in: RoundedRectangle(cornerRadius: 14))
                                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.hodInk.opacity(0.07)))
                            }
                        }
                    } else {
                        VStack(alignment: .leading, spacing: 8) {
                            HodLabel(text: "Today")
                            Text("Your morning guide lands at 7 AM — check back then for today's stops and tips.")
                                .font(.footnote)
                                .foregroundStyle(Color.hodMuted)
                        }
                        .padding(14)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(Color.hodCard, in: RoundedRectangle(cornerRadius: 14))
                        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.hodInk.opacity(0.07)))
                    }

                    if let recap = today?.eveningRecap {
                        VStack(alignment: .leading, spacing: 12) {
                            HodLabel(text: "Evening Digest")
                            Text(recap.narrative)
                                .font(.footnote)
                                .foregroundStyle(Color.hodInk)
                                .padding(14)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.hodCard, in: RoundedRectangle(cornerRadius: 14))
                                .overlay(RoundedRectangle(cornerRadius: 14).stroke(Color.hodInk.opacity(0.07)))
                        }
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        HodLabel(text: "Quick Tips")
                        Label("Ask Nikos anything — history, food, hours, directions", systemImage: "bubble.left.fill")
                            .font(.footnote).foregroundStyle(Color.hodAegean)
                        Label("Journal a place right after you visit for the best summary", systemImage: "square.and.pencil")
                            .font(.footnote).foregroundStyle(Color.hodTerra)
                        Label("Pull down on any screen to refresh from the server", systemImage: "arrow.clockwise")
                            .font(.footnote).foregroundStyle(Color.hodMuted)
                    }
                }
                .padding()
            }
            .hodScreen()
            .navigationTitle(today.flatMap { t in t.tripDay.map { "Day \($0)" } } ?? "Home")
            .navigationBarTitleDisplayMode(.large)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showMenu = true } label: {
                        Image(systemName: "line.3.horizontal")
                            .foregroundStyle(Color.hodAegean)
                    }
                }
            }
            .sheet(isPresented: $showMenu) {
                SidebarMenuView()
            }
            .task { await load() }
        }
    }

    private func load() async {
        if let cached = CacheStore.load(TodayResponse.self, key: "today") {
            today = cached
        }
        if let fresh = try? await APIClient.shared.today() {
            today = fresh
            CacheStore.save(fresh, key: "today")
        }
    }
}

struct SidebarMenuView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List {
                Section {
                    Label("Set HodegosBaseURL in Info.plist to point to your server", systemImage: "server.rack")
                        .font(.footnote).foregroundStyle(.secondary)
                    Label("Set HodegosAPIToken in Info.plist — never commit it to git", systemImage: "key.fill")
                        .font(.footnote).foregroundStyle(.secondary)
                } header: {
                    HodLabel(text: "Connection")
                }

                Section {
                    Label("Offline mode uses the last data synced from the server", systemImage: "wifi.slash")
                        .font(.footnote).foregroundStyle(.secondary)
                    Label("Location is used for nearby context and journaling", systemImage: "location.fill")
                        .font(.footnote).foregroundStyle(.secondary)
                    Label("Pull down on any screen to force a refresh", systemImage: "arrow.clockwise")
                        .font(.footnote).foregroundStyle(.secondary)
                } header: {
                    HodLabel(text: "How It Works")
                }

                Section {
                    Label("Version 1.0 — built for travel, not tourism", systemImage: "globe")
                        .font(.footnote).foregroundStyle(.secondary)
                } header: {
                    HodLabel(text: "About")
                }
            }
            .scrollContentBackground(.hidden)
            .background(Color.hodPaper)
            .tint(.hodAegean)
            .navigationTitle("Menu")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                        .foregroundStyle(Color.hodAegean)
                }
            }
        }
    }
}
