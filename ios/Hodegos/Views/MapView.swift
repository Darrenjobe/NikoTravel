import MapKit
import SwiftUI

struct TripMapView: View {
    @Binding var recommendedPlaces: [Place]

    @State private var journalPins: [MapPin] = []
    @State private var selectedPin: MapPin?
    @State private var selectedRec: Place?
    @State private var showMine = true
    @State private var showRecs = true
    @State private var searchText = ""
    @State private var searchResults: [Place] = []
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
                            PinDot(color: .hodTerra)
                                .onTapGesture { selectedPin = pin; selectedRec = nil }
                        }
                    }
                }
                if showRecs {
                    ForEach(recommendedPlaces.filter { $0.lat != nil && $0.lon != nil }) { place in
                        Annotation(place.name ?? "Suggested",
                                   coordinate: .init(latitude: place.lat!, longitude: place.lon!)) {
                            PinDot(color: .hodAegean)
                                .onTapGesture { selectedRec = place; selectedPin = nil }
                        }
                    }
                }
                ForEach(searchResults.filter { $0.lat != nil && $0.lon != nil }) { place in
                    Annotation(place.name ?? "Result",
                               coordinate: .init(latitude: place.lat!, longitude: place.lon!)) {
                        PinDot(color: .hodOlive)
                            .onTapGesture { selectedRec = place; selectedPin = nil }
                    }
                }
            }
            .safeAreaInset(edge: .top) { legend }
            .safeAreaInset(edge: .bottom) { detailCard }
            .navigationTitle("Map")
            .navigationBarTitleDisplayMode(.inline)
            .searchable(text: $searchText, prompt: "Search restaurants, museums…")
            .onSubmit(of: .search) { Task { await search() } }
            .onChange(of: searchText) { if searchText.isEmpty { searchResults = [] } }
            .task { await load() }
            .refreshable { await load() }
        }
    }

    private var legend: some View {
        HStack(spacing: 8) {
            Toggle(isOn: $showMine) { Label("My places", systemImage: "circle.fill") }
                .toggleStyle(.button).tint(.hodTerra).font(.caption.weight(.semibold))
            Toggle(isOn: $showRecs) { Label("Recommendations", systemImage: "circle.fill") }
                .toggleStyle(.button).tint(.hodAegean).font(.caption.weight(.semibold))
            Spacer()
            Button {
                position = .userLocation(
                    fallback: .region(.init(center: .init(latitude: 37.9715, longitude: 23.7267),
                                           latitudinalMeters: 3000, longitudinalMeters: 3000)))
            } label: {
                Image(systemName: "location.fill")
                    .padding(8)
                    .background(.regularMaterial, in: Circle())
                    .foregroundStyle(Color.hodAegean)
            }
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

    private func search() async {
        guard !searchText.isEmpty else { return }
        let req = MKLocalSearch.Request()
        req.naturalLanguageQuery = searchText
        guard let results = try? await MKLocalSearch(request: req).start() else { return }
        searchResults = results.mapItems.compactMap { item in
            guard let name = item.name else { return nil }
            return Place(
                placeId: "\(item.placemark.coordinate.latitude),\(item.placemark.coordinate.longitude)",
                name: name,
                address: item.placemark.thoroughfare,
                lat: item.placemark.coordinate.latitude,
                lon: item.placemark.coordinate.longitude,
                category: item.pointOfInterestCategory?.rawValue,
                rating: nil,
                ratingCount: nil,
                mapsUrl: nil
            )
        }
        if let first = searchResults.first, let lat = first.lat, let lon = first.lon {
            position = .region(.init(center: .init(latitude: lat, longitude: lon),
                                    latitudinalMeters: 1500, longitudinalMeters: 1500))
        }
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
                Text(title).font(.hodDisplay(.title3))
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
                    .foregroundStyle(Color.hodAegean)
            }
        }
        .padding()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16))
        .padding()
    }
}
