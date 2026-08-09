import MapKit
import SwiftUI

struct TripMapView: View {
    @Binding var recommendedPlaces: [Place]

    @State private var journalPins: [MapPin] = []
    @State private var selectedPin: MapPin?
    @State private var selectedRec: Place?
    @State private var showMine = true
    @State private var showRecs = true
    @State private var position: MapCameraPosition = .userLocation(
        fallback: .region(.init(center: .init(latitude: 37.9715, longitude: 23.7267),
                                latitudinalMeters: 3000, longitudinalMeters: 3000)))

    var body: some View {
        NavigationStack {
            Map(position: $position) {
                UserAnnotation()
                if showMine {
                    ForEach(journalPins) { pin in
                        Annotation(pin.placeName ?? "Entry",
                                   coordinate: .init(latitude: pin.lat, longitude: pin.lon)) {
                            PinDot(color: .orange)
                                .onTapGesture { selectedPin = pin; selectedRec = nil }
                        }
                    }
                }
                if showRecs {
                    ForEach(recommendedPlaces.filter { $0.lat != nil && $0.lon != nil }) { place in
                        Annotation(place.name ?? "Suggested",
                                   coordinate: .init(latitude: place.lat!, longitude: place.lon!)) {
                            PinDot(color: .blue)
                                .onTapGesture { selectedRec = place; selectedPin = nil }
                        }
                    }
                }
            }
            .safeAreaInset(edge: .top) { legend }
            .safeAreaInset(edge: .bottom) { detailCard }
            .navigationTitle("Map")
            .navigationBarTitleDisplayMode(.inline)
            .task { await load() }
            .refreshable { await load() }
        }
    }

    private var legend: some View {
        HStack(spacing: 8) {
            Toggle(isOn: $showMine) { Label("My places", systemImage: "circle.fill") }
                .toggleStyle(.button).tint(.orange).font(.caption.weight(.semibold))
            Toggle(isOn: $showRecs) { Label("Recommendations", systemImage: "circle.fill") }
                .toggleStyle(.button).tint(.blue).font(.caption.weight(.semibold))
            Spacer()
        }
        .padding(.horizontal)
    }

    @ViewBuilder
    private var detailCard: some View {
        if let pin = selectedPin {
            MapDetailCard(title: pin.placeName ?? "Journal entry",
                          subtitle: pin.line ?? "",
                          mapsUrl: pin.mapsUrl) { selectedPin = nil }
        } else if let rec = selectedRec {
            MapDetailCard(title: rec.name ?? "Suggested",
                          subtitle: [rec.address, rec.rating.map { "★ \($0)" }]
                              .compactMap { $0 }.joined(separator: " · "),
                          mapsUrl: rec.mapsUrl) { selectedRec = nil }
        }
    }

    private func load() async {
        if let response = try? await APIClient.shared.mapPins() {
            journalPins = response.pins
            CacheStore.save(response, key: "pins")
        } else if let cached = CacheStore.load(PinsResponse.self, key: "pins") {
            journalPins = cached.pins
        }
    }
}

struct PinDot: View {
    let color: Color
    var body: some View {
        Circle()
            .fill(color)
            .frame(width: 18, height: 18)
            .overlay(Circle().stroke(.white, lineWidth: 2.5))
            .shadow(radius: 2)
    }
}

struct MapDetailCard: View {
    let title: String
    let subtitle: String
    let mapsUrl: String?
    let onClose: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(title).font(.headline)
                Spacer()
                Button { onClose() } label: { Image(systemName: "xmark.circle.fill") }
                    .foregroundStyle(.secondary)
            }
            if !subtitle.isEmpty {
                Text(subtitle).font(.subheadline).foregroundStyle(.secondary)
            }
            if let mapsUrl, let url = URL(string: mapsUrl) {
                Link("Open in Google Maps ↗", destination: url)
                    .font(.subheadline.weight(.semibold))
            }
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .padding()
    }
}
