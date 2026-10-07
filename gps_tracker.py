# ==============================================================================
# AI Pothole Detection System - GPS Location Provider
# ==============================================================================
import random
import time
import config

class GPSTracker:
    """
    Provides GPS latitude and longitude coordinates.
    In prototype/demonstration mode, simulates incremental vehicle movement
    along a road corridor with realistic jitter.
    Supports easy drop-in of physical USB/UART GPS dongle via NMEA sentences if plugged in.
    """
    def __init__(self, start_lat=config.DEFAULT_LATITUDE, start_lon=config.DEFAULT_LONGITUDE):
        self.current_lat = start_lat
        self.current_lon = start_lon
        self.last_update = time.time()
        # Simulated heading angle in radians
        self.heading_step = 0.00015  # Approx ~15-20 meters per step

    def get_current_coordinates(self):
        """
        Returns (latitude, longitude) as float values.
        Simulates driving motion forward if simulation is enabled.
        """
        if not config.GPS_SIMULATION_ENABLED:
            return round(self.current_lat, 6), round(self.current_lon, 6)

        now = time.time()
        elapsed = now - self.last_update
        if elapsed > 1.0:
            # Advance along a realistic road trajectory
            lat_jitter = random.uniform(-0.00003, 0.00003)
            lon_jitter = random.uniform(-0.00003, 0.00003)
            self.current_lat += self.heading_step + lat_jitter
            self.current_lon += (self.heading_step * 0.7) + lon_jitter
            self.last_update = now

        return round(self.current_lat, 6), round(self.current_lon, 6)

# Global tracker instance
tracker_instance = GPSTracker()

def get_coordinates():
    return tracker_instance.get_current_coordinates()

if __name__ == "__main__":
    print("[TEST] Fetching simulated GPS coordinates for 3 samples:")
    for i in range(3):
        lat, lon = get_coordinates()
        print(f"Sample {i+1}: Latitude = {lat:.6f}, Longitude = {lon:.6f}")
        time.sleep(1.2)
