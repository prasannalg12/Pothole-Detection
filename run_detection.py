# ==============================================================================
# AI Pothole Detection System - Main Application Launcher
# ==============================================================================
import os
import sys
import argparse
from detector import PotholeDetector
import config

def interactive_menu():
    """Beginner-friendly interactive prompt using real road images."""
    print("=" * 65)
    print("    AI POTHOLE DETECTION & HAZARD ALERT SYSTEM")
    print("    Presentation & Working Prototype (Car + Bike)")
    print("=" * 65)
    print("Select Vehicle Mounting Setup:")
    print("  [1] Car Front Windshield / Dashcam")
    print("  [2] Bike Helmet / Handlebar Phone Mount")
    vehicle_choice = input("Enter choice (1 or 2, default: 1): ").strip()
    vehicle_mode = "Bike Helmet/Handlebar" if vehicle_choice == "2" else "Car Dashcam"

    print("\nSelect Input Source:")
    print("  [1] Mixed Craters Road Photo (Detects Low + High Severity)")
    print("  [2] Highway Road Photo (Project Document Page 3 - High Severity)")
    print("  [3] Clean Road Photo (Zero Potholes - Verify Safe Road)")
    print("  [4] Custom Road Image File (Enter your own path)")
    print("  [5] Road Video File (Runs on test driving video or custom .mp4)")
    print("  [6] Live Webcam / USB Dashcam")
    source_choice = input("Enter choice (1-6, default: 1): ").strip()

    detector = PotholeDetector(vehicle_mode=vehicle_mode)

    if source_choice == "1" or source_choice == "":
        img_path = os.path.join(config.DATA_DIR, "sample_mixed_potholes.jpg")
        detector.process_image(img_path)

    elif source_choice == "2":
        img_path = os.path.join(config.DATA_DIR, "road_highway.jpg")
        detector.process_image(img_path)

    elif source_choice == "3":
        img_path = os.path.join(config.DATA_DIR, "sample_clean_road.jpg")
        detector.process_image(img_path)

    elif source_choice == "4":
        print("\nEnter custom image file path:")
        user_path = input("Path: ").strip()
        img_path = user_path if user_path else os.path.join(config.DATA_DIR, "sample_mixed_potholes.jpg")
        detector.process_image(img_path)

    elif source_choice == "5":
        default_vid = os.path.join(config.DATA_DIR, "road_test.mp4")
        print(f"\nEnter video path (Press ENTER for default: {default_vid}):")
        user_path = input("Path: ").strip()
        vid_path = user_path if user_path else default_vid
        detector.process_video(vid_path)

    elif source_choice == "6":
        cam_idx = input("\nEnter camera index (default 0 for laptop webcam / USB cam): ").strip()
        index = int(cam_idx) if cam_idx.isdigit() else 0
        detector.process_webcam(camera_index=index)

    else:
        print("[!] Defaulting to Mixed Craters Road Photo...")
        img_path = os.path.join(config.DATA_DIR, "sample_mixed_potholes.jpg")
        detector.process_image(img_path)

def parse_cli():
    """Command-line argument parser for direct command line execution."""
    parser = argparse.ArgumentParser(description="AI Pothole Detection & Alert System")
    parser.add_argument("--source", choices=["image", "video", "webcam", "sample", "highway", "clean", "mixed"],
                        help="Input source: 'image', 'video', 'webcam', 'sample', 'highway', 'clean', or 'mixed'")
    parser.add_argument("--path", type=str, default=None,
                        help="File path to the image or video")
    parser.add_argument("--camera", type=int, default=0,
                        help="Camera device index (default: 0)")
    parser.add_argument("--mode", choices=["car", "bike"], default="car",
                        help="Vehicle deployment mode: 'car' or 'bike'")
    parser.add_argument("--conf", type=float, default=config.CONFIDENCE_THRESHOLD,
                        help="YOLO detection confidence threshold (0.1 to 0.9)")
    return parser.parse_args()

def main():
    args = parse_cli()

    if not args.source:
        interactive_menu()
        return

    vehicle_mode = "Bike Helmet/Handlebar" if args.mode == "bike" else "Car Dashcam"
    detector = PotholeDetector(conf_thresh=args.conf, vehicle_mode=vehicle_mode)

    if args.source == "image":
        img_path = args.path if args.path else os.path.join(config.DATA_DIR, "sample_mixed_potholes.jpg")
        detector.process_image(img_path)

    elif args.source == "highway":
        img_path = os.path.join(config.DATA_DIR, "road_highway.jpg")
        detector.process_image(img_path)

    elif args.source == "clean":
        img_path = os.path.join(config.DATA_DIR, "sample_clean_road.jpg")
        detector.process_image(img_path)

    elif args.source == "mixed" or args.source == "sample":
        img_path = os.path.join(config.DATA_DIR, "sample_mixed_potholes.jpg")
        detector.process_image(img_path)

    elif args.source == "video":
        vid_path = args.path if args.path else os.path.join(config.DATA_DIR, "road_test.mp4")
        detector.process_video(vid_path)

    elif args.source == "webcam":
        detector.process_webcam(camera_index=args.camera)

if __name__ == "__main__":
    main()
