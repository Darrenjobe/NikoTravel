import SwiftUI

struct ContentView: View {
    @State private var recommendedPlaces: [Place] = []
    @State private var selectedTab = 0

    var body: some View {
        TabView(selection: $selectedTab) {
            HomeView()
                .tabItem { Label("Home", systemImage: "house.fill") }
                .tag(0)
            AskView(recommendedPlaces: $recommendedPlaces, selectedTab: $selectedTab)
                .tabItem { Label("Ask", systemImage: "bubble.left.fill") }
                .tag(1)
            JournalView()
                .tabItem { Label("Journal", systemImage: "square.and.pencil") }
                .tag(2)
            TripMapView(recommendedPlaces: $recommendedPlaces)
                .tabItem { Label("Map", systemImage: "map.fill") }
                .tag(3)
            TodayView()
                .tabItem { Label("Today", systemImage: "sun.max.fill") }
                .tag(4)
            JourneyView()
                .tabItem { Label("Journey", systemImage: "safari.fill") }
                .tag(5)
        }
        .tint(.hodAegean)
    }
}
