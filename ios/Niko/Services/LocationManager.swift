import CoreLocation
import Foundation

/// Coarse "where am I" for context chips and place resolution. Reduced
/// accuracy is plenty — we bias searches within a couple of kilometers.
final class LocationManager: NSObject, ObservableObject, CLLocationManagerDelegate {
    @Published var coordinate: CLLocationCoordinate2D?
    @Published var placeName: String?

    private let manager = CLLocationManager()
    private let geocoder = CLGeocoder()

    override init() {
        super.init()
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters
        manager.requestWhenInUseAuthorization()
        manager.startMonitoringSignificantLocationChanges()
        manager.requestLocation()
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let loc = locations.last else { return }
        coordinate = loc.coordinate
        geocoder.reverseGeocodeLocation(loc) { [weak self] placemarks, _ in
            if let p = placemarks?.first {
                self?.placeName = [p.subLocality ?? p.locality, p.locality != p.subLocality ? p.locality : nil]
                    .compactMap { $0 }.joined(separator: ", ")
            }
        }
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {}
}
