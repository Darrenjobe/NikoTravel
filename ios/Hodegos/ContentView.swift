import SwiftUI

struct ContentView: View {
    // Recommendation pins handed off from Ask → Map
    @State private var recommendedPlaces: [Place] = []
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            AskView(recommendedPlaces: $recommendedPlaces, selectedTab: $selectedTab)
                .tabItem { Label("Ask", systemImage: "bubble.left.fill") }
                .tag(0)
            JournalView()
                .tabItem { Label("Journal", systemImage: "square.and.pencil") }
                .tag(1)
            TripMapView(recommendedPlaces: $recommendedPlaces)
                .tabItem { Label("Map", systemImage: "map.fill") }
                .tag(2)
            TodayView()
                .tabItem { Label("Today", systemImage: "sun.max.fill") }
                .tag(3)
            JourneyView()
                .tabItem { Label("Journey", systemImage: "safari.fill") }
                .tag(4)
        }
    }
}
