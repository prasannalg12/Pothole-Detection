# AI Pothole Detection & Hazard Alert System (RoadGuard AI)

A complete, production-ready computer vision prototype designed for road safety and municipal hazard tracking.

## 🌟 Architecture
```
Camera / Image / Video Stream
             ↓
     OpenCV Ingestion
             ↓
Ultralytics YOLO (2D Footprint Inference)
             ↓
     Pothole Detection
    ├── Bounding Box + "POTHOLE" Label
    ├── Detection Confidence %
    ├── Estimated Severity (LOW / MEDIUM / HIGH)
    └── ⚠ POTHOLE AHEAD Visual HUD Banner
             ↓
   Audio Alert Engine (Windows Beep + Cooldown Guard)
             ↓
   Geospatial Tagging (GPS Provider / Simulation)
             ↓
  SQLite Database Storage + Screenshot Evidence Archive
             ↓
   Flask Web Dashboard (Leaflet.js Map + Analytics Feed)
```

> [!NOTE]
> **Measurement Clarification**: Standard single-lens (monocular) vehicle cameras do not measure physical millimeter depth. In this system, severity is classified as **"Estimated Severity"** derived from the 2D pixel area and perspective footprint on the road surface. True physical depth measurement requires LiDAR, ultrasonic, or stereo-camera hardware.

---

## 📁 Project Folder Structure
```
PotholeDetection/
├── config.py                 # Core configurations, severity thresholds, alert cooldowns
├── detector.py               # Core detection engine (OpenCV + YOLO + HUD + Evidence Saver)
├── database.py               # SQLite database manager for detection history & metrics
├── alert_system.py           # Audio tone engine (winsound) with thread-safe cooldown
├── gps_tracker.py            # Geospatial coordinates provider & route simulation
├── dashboard.py              # Flask web dashboard backend server
├── run_detection.py          # Interactive CLI & parameter-driven launcher
├── generate_sample.py        # Generates synthetic test road image & seeds demo database
├── requirements.txt          # Python library specifications
├── README.md                 # Complete documentation & usage guide
├── models/                   # YOLO model weights directory
│   ├── download_model.py     # Model verification & auto-downloader
│   ├── pothole_yolov8.pt     # Custom trained pothole weights (drop here)
│   └── yolov8n.pt            # Baseline testing weights
├── detections/               # Auto-saved high-resolution snapshot evidence
├── data/                     # SQLite database (potholes.db) and test media
│   └── sample_road.jpg       # Synthetic test road image
├── static/                   # Dashboard assets
│   ├── css/style.css         # Modern dark-mode styling
│   └── js/app.js             # Leaflet.js map logic & real-time UI controls
└── templates/
    └── dashboard.html        # Interactive HTML5 dashboard layout
```

---

## 🛠️ Prerequisites & Installation

### 1. Requirements
- **Operating System**: Windows 11 (or Windows 10)
- **Editor**: Visual Studio Code (VS Code)
- **Python Version**: Python 3.10, 3.11, or 3.12 (64-bit)

### 2. Installation Commands
Open PowerShell or the integrated terminal in VS Code:
```powershell
# 1. Navigate to the project directory
cd "C:\Users\gpras\.gemini\antigravity\scratch\PotholeDetection"

# 2. (Optional but recommended) Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install all required dependencies
pip install -r requirements.txt
```

---

## 🧠 Obtaining the Pothole-Trained YOLO Model
The prototype includes automated fallback to `yolov8n.pt` so you can verify the entire pipeline immediately. To use a dedicated pothole detector trained on real road surface datasets:

1. **Option A (Roboflow Universe)**:
   - Visit [Roboflow Universe](https://universe.roboflow.com/search?q=pothole)
   - Search for **"Pothole Detection YOLOv8"**
   - Download the model weights (`best.pt`)
2. **Option B (Kaggle)**:
   - Search Kaggle for **"Pothole Detection YOLOv8 best.pt"**
3. **Placing the Model**:
   - Rename your downloaded model file to: `pothole_yolov8.pt`
   - Copy it into the `models/` directory:
     `PotholeDetection/models/pothole_yolov8.pt`
   - The system will automatically detect and prioritize it!

---

## 🚀 Running the Project

### Step 1: Start the Detection Engine
You can launch the detection engine interactively or via commands:

#### Option A: Interactive Menu (Recommended for Beginners)
```powershell
python run_detection.py
```
This presents a menu to choose your vehicle mount (Car vs. Bike) and your input source (Image, Video, Webcam, or Synthetic Sample).

#### Option B: Direct Command Line Options
- **Test with Synthetic Sample**:
  ```powershell
  python run_detection.py --source sample
  ```
- **Single Road Image**:
  ```powershell
  python run_detection.py --source image --path "data/sample_road.jpg"
  ```
- **Road Video**:
  ```powershell
  python run_detection.py --source video --path "path/to/road_video.mp4"
  ```
- **Live Laptop / USB Dashcam**:
  ```powershell
  python run_detection.py --source webcam --camera 0
  ```

---

### Step 2: Start the Web Dashboard
Open a second terminal window and run:
```powershell
python dashboard.py
```
Open your web browser and go to:
👉 **`http://127.0.0.1:5000`**

You will see:
- Real-time KPI summary (Total, High, Medium, Low severity counts)
- Leaflet OpenStreetMap displaying colored incident pins
- Incident history table with confidence % and clickable screenshot evidence
- Filter controls and modal inspection

---

## 🚗 Car vs. 🏍️ Bike Deployment Demonstration

| Feature | Car Front / Windshield Dashcam | Bike Helmet / Handlebar Phone Mount |
| :--- | :--- | :--- |
| **Mounting Position** | Suction mount behind rearview mirror, angled ~15° downward toward road. | Handlebar clamp or chin-mount helmet bracket. |
| **Field of View (FOV)** | Wide, stable horizon; higher perspective (~1.2m – 1.5m off ground). | More dynamic tilt; lower perspective (~0.9m – 1.4m off ground). |
| **Vibration Handling** | Car suspension dampens small bumps; relatively smooth video frames. | Handlebar absorbs direct road vibration; helmet mount provides natural head stabilization. |
| **Alert Notification** | Audio beep through car cabin speakers / laptop speakers. | Audio beep through Bluetooth helmet intercom / phone speaker. |
| **Severity Perception** | A medium pothole may cause tire damage or suspension wear. | A medium/high pothole presents an immediate loss-of-balance or crash risk for two-wheelers. |
| **Software Adaptation** | Select Option `[1] Car Dashcam` in `run_detection.py`. Tagged in DB logs. | Select Option `[2] Bike Helmet/Handlebar` in `run_detection.py`. Tagged in DB logs. |

---

## ⚙️ How Severity is Estimated
- **LOW Severity**: Bounding box takes up `< 2.5%` of the frame area. Minor shallow dips or hairline road fissures.
- **MEDIUM Severity**: Bounding box takes up `2.5% – 7.0%` of the frame area. Moderate pothole requiring steering adjustment.
- **HIGH Severity**: Bounding box takes up `> 7.0%` of the frame area or spans immediate foreground. Critical crater presenting imminent vehicle damage or fall hazard.

---

## 🔧 Troubleshooting Common Errors

1. **`ModuleNotFoundError: No module named 'cv2'` or `'ultralytics'`**:
   - Solution: Ensure virtual environment is activated and run:
     `pip install -r requirements.txt`
2. **`Camera index 0 failed to open`**:
   - Solution: Check Windows 11 Camera Privacy Settings: *Settings > Privacy & Security > Camera > Let desktop apps access your camera*. If using an external USB camera, try `--camera 1`.
3. **`Execution Policy Error on Activate.ps1`**:
   - Solution: Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` in PowerShell.
4. **Beep sound not heard**:
   - Ensure system audio is turned on. On Windows, `winsound.Beep` utilizes default audio output.
