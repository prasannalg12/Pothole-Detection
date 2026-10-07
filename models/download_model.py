# ==============================================================================
# AI Pothole Detection System - Model Setup & Verifier
# ==============================================================================
import os
import sys
import urllib.request

# Add parent directory to path to import config
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import config

def verify_or_download_models():
    """
    Checks for custom pothole model weights. If not found, downloads standard
    YOLOv8 nano weights so the system can initialize and run immediately.
    """
    os.makedirs(config.MODELS_DIR, exist_ok=True)

    print("=" * 65)
    print("   AI Pothole Detection - Model Verification")
    print("=" * 65)

    if os.path.exists(config.CUSTOM_MODEL_PATH):
        print(f"[OK] Found custom trained pothole model at:\n     {config.CUSTOM_MODEL_PATH}")
        return config.CUSTOM_MODEL_PATH

    print(f"[INFO] Custom pothole weights not detected at: {config.CUSTOM_MODEL_PATH}")
    print("       To achieve maximum pothole accuracy in real production:")
    print("       1. Download a trained pothole YOLOv8 model (.pt) from:")
    print("          - GitHub / Roboflow Universe / Kaggle (search 'pothole yolov8')")
    print("       2. Rename the file to: pothole_yolov8.pt")
    print(f"       3. Place it inside: {config.MODELS_DIR}\n")

    # Download / verify standard YOLOv8 nano as fallback
    fallback = config.FALLBACK_MODEL_PATH
    if not os.path.exists(fallback):
        print("[INFO] Downloading baseline YOLOv8 Nano weights for immediate testing...")
        url = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8n.pt"
        try:
            urllib.request.urlretrieve(url, fallback)
            print(f"[OK] Downloaded baseline weights: {fallback}")
        except Exception as e:
            print(f"[WARN] Automatic download failed ({e}). Ultralytics will attempt auto-download on first run.")
    else:
        print(f"[OK] Found baseline YOLOv8 model at:\n     {fallback}")

    return fallback

if __name__ == "__main__":
    verify_or_download_models()
