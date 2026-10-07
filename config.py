# ==============================================================================
# AI Pothole Detection System - Configuration
# ==============================================================================
import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
DETECTIONS_DIR = os.path.join(BASE_DIR, "detections")
DATA_DIR = os.path.join(BASE_DIR, "data")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Ensure required directories exist
for directory in [MODELS_DIR, DETECTIONS_DIR, DATA_DIR]:
    os.makedirs(directory, exist_ok=True)

# Database
DB_PATH = os.path.join(DATA_DIR, "potholes.db")

# Model Configuration
# Primary target: custom pothole model (e.g., best.pt or pothole.pt)
# Fallback: yolov8n.pt (standard YOLO model for testing pipeline immediately)
CUSTOM_MODEL_PATH = os.path.join(MODELS_DIR, "pothole_yolov8.pt")
FALLBACK_MODEL_PATH = os.path.join(MODELS_DIR, "yolov8n.pt")

# Detection Parameters
CONFIDENCE_THRESHOLD = 0.35  # Minimum confidence to accept a detection (0.0 to 1.0)
IOU_THRESHOLD = 0.45         # Non-maximum suppression threshold

# Alert & Cooldown Settings
ALERT_COOLDOWN_SECONDS = 3.0  # Minimum seconds between repeated audio beeps / snapshot saves
AUDIO_BEEP_ENABLED = True     # Set to False to disable Windows beep sound
BEEP_FREQUENCY_LOW = 800      # Hz
BEEP_FREQUENCY_MED = 1200     # Hz
BEEP_FREQUENCY_HIGH = 1800    # Hz
BEEP_DURATION_MS = 250        # Duration of beep in milliseconds

# Estimated Severity Thresholds (Based on bounding box area % and perspective proximity)
# NOTE: Standard monocular cameras cannot physically measure pothole millimeter depth.
# This represents an estimated visual severity based on 2D footprint area and proximity.
SEVERITY_LOW_AREA_PCT = 0.010   # Under 1.0% hazard -> LOW
SEVERITY_MED_AREA_PCT = 0.035   # Over 3.5% hazard (or >= 3.5% area) -> HIGH
                                # Between 1.0% and 3.5% -> MEDIUM

# Severity Display Colors (BGR format for OpenCV)
COLOR_SEVERITY_LOW = (0, 220, 255)    # Yellow / Gold
COLOR_SEVERITY_MED = (0, 140, 255)    # Orange
COLOR_SEVERITY_HIGH = (0, 0, 255)     # Bright Red

# GPS Settings
# Set to True to use simulated route progression (advances lat/long as you drive/ride)
GPS_SIMULATION_ENABLED = True
DEFAULT_LATITUDE = 17.3850     # Project document GPS (e.g., Hyderabad 17.3850, 78.4867)
DEFAULT_LONGITUDE = 78.4867

# Flask Dashboard Settings
# Setting to "0.0.0.0" allows other laptops, phones, and devices on the same Wi-Fi/Hotspot to connect!
DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5000
