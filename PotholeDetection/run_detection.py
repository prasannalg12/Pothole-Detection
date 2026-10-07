# ==============================================================================
# AI Pothole Detection System - Main Application Launcher
# ==============================================================================
import os
import sys
import argparse
from detector import PotholeDetector
import config

def interactive_menu():
    """Beginner-friendly interactive prompt when no CLI arguments are supplied."""
    print("=" * 65)
    print("    AI POTHOLE DETECTION & HAZARD ALERT SYSTEM")
    print("=" * 65)
    print("Select Vehicle Mounting Setup:")
    print("  [1] Car Front Windshield / Dashcam")
    print("  [2] Bike Helmet / Handlebar Phone Mount")
    vehicle_choice = input("Enter choice (1 or 2, default: 1): ").strip()
    vehicle_mode = "Bike Helmet/Handlebar" if vehicle_choice == "2" else "Car Dashcam"

    print("\nSelect Input Source:")
    print("  [1] Single Road Image")
    print("  [2] Road Video File")
    print("  [3] Live Webcam / USB Dashcam")
    print("  [4] Run Self-Test with Synthetic Road Sample")
    source_choice = input("Enter choice (1-4): ").strip()

    detector = PotholeDetector(vehicle_mode=vehicle_mode)

    if source_choice == "1":
        default_img = os.path.join(config.DATA_DIR, "sample_road.jpg")
        print(f"\nEnter image path (Press ENTER for default: {default_img}):")
        user_path = input("Path: ").strip()
        img_path = user_path if user_path else default_img
        detector.process_image(img_path)

    elif source_choice == "2":
        default_vid = os.path.join(config.DATA_DIR, "road_test.mp4")
        print(f"\nEnter video path (Press ENTER for default: {default_vid}):")
        user_path = input("Path: ").strip()
        vid_path = user_path if user_path else default_vid
        detector.process_video(vid_path)

    elif source_choice == "3":
        cam_idx = input("\nEnter camera index (default 0 for laptop webcam / USB cam): ").strip()
        index = int(cam_idx) if cam_idx.isdigit() else 0
        detector.process_webcam(camera_index=index)

    elif source_choice == "4":
        # Generate sample and run
        import generate_sample
        sample_path = generate_sample.generate_synthetic_pothole_image()
        detector.process_image(sample_path)

    else:
        print("[!] Invalid option. Exiting.")

def parse_cli():
    """Command-line argument parser for direct command line execution."""
    parser = argparse.ArgumentParser(description="AI Pothole Detection & Alert System")
    parser.add_argument("--source", choices=["image", "video", "webcam", "sample"],
                        help="Input source type: 'image', 'video', 'webcam', or 'sample'")
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

    # If no source argument was provided, launch the interactive menu
    if not args.source:
        interactive_menu()
        return

    vehicle_mode = "Bike Helmet/Handlebar" if args.mode == "bike" else "Car Dashcam"
    detector = PotholeDetector(conf_thresh=args.conf, vehicle_mode=vehicle_mode)

    if args.source == "image":
        img_path = args.path if args.path else os.path.join(config.DATA_DIR, "sample_road.jpg")
        detector.process_image(img_path)

    elif args.source == "video":
        vid_path = args.path if args.path else os.path.join(config.DATA_DIR, "road_test.mp4")
        detector.process_video(vid_path)

    elif args.source == "webcam":
        detector.process_webcam(camera_index=args.camera)

    elif args.source == "sample":
        import generate_sample
        sample_path = generate_sample.generate_synthetic_pothole_image()
        detector.process_image(sample_path)

if __name__ == "__main__":
    main()
