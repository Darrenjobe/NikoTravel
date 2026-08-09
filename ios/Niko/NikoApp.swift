import SwiftUI

@main
struct NikoApp: App {
    @StateObject private var location = LocationManager()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(location)
        }
    }
}
