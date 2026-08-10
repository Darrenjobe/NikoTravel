import SwiftUI

@main
struct HodegosApp: App {
    @StateObject private var location = LocationManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(location)
        }
    }
}
