# ==============================================================================
# AI Pothole Detection System - Test Sample & Mock Data Generator
# ==============================================================================
import os
import cv2
import numpy as np
import datetime
import config
import database

def generate_synthetic_pothole_image():
    """
    Synthesizes a realistic asphalt road perspective image with road markings
    and surface potholes for instant testing without needing external files.
    """
    os.makedirs(config.DATA_DIR, exist_ok=True)
    sample_path = os.path.join(config.DATA_DIR, "sample_road.jpg")

    width, height = 1280, 720
    # Create dark asphalt base
    road = np.full((height, width, 3), (48, 50, 52), dtype=np.uint8)

    # Add realistic asphalt noise texture
    noise = np.random.normal(0, 12, (height, width, 3)).astype(np.int16)
    road = np.clip(road.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    # Draw perspective road lane markings (yellow center dashes, white shoulder)
    # Left shoulder line
    cv2.line(road, (200, height), (500, int(height * 0.45)), (230, 230, 230), 8, cv2.LINE_AA)
    # Right shoulder line
    cv2.line(road, (1080, height), (780, int(height * 0.45)), (230, 230, 230), 8, cv2.LINE_AA)
    # Center dashed yellow line
    for y in range(int(height * 0.45), height, 70):
        t1 = (y - int(height * 0.45)) / (height - int(height * 0.45))
        t2 = min(1.0, t1 + 0.05)
        x_center1 = int(640 + (t1 - 0.5) * 60)
        x_center2 = int(640 + (t2 - 0.5) * 60)
        y2 = min(height, y + 40)
        cv2.line(road, (x_center1, y), (x_center2, y2), (0, 215, 255), 6, cv2.LINE_AA)

    # Draw simulated pothole 1 (High Severity - larger, foreground)
    center1 = (520, 560)
    axes1 = (130, 70)
    # Shadow/interior cavity
    cv2.ellipse(road, center1, axes1, 15, 0, 360, (18, 18, 20), -1, cv2.LINE_AA)
    # Textured cracks around rim
    cv2.ellipse(road, center1, (axes1[0] + 12, axes1[1] + 8), 15, 0, 360, (75, 78, 82), 3, cv2.LINE_AA)
    # Rough jagged inner rim
    inner_pts = np.array([
        [410, 545], [450, 585], [520, 610], [600, 580],
        [630, 530], [580, 510], [470, 515]
    ], np.int32)
    cv2.fillPoly(road, [inner_pts], (10, 10, 12), cv2.LINE_AA)

    # Draw simulated pothole 2 (Medium Severity - mid-distance)
    center2 = (760, 430)
    axes2 = (70, 35)
    cv2.ellipse(road, center2, axes2, -10, 0, 360, (22, 22, 25), -1, cv2.LINE_AA)
    cv2.ellipse(road, center2, (axes2[0] + 6, axes2[1] + 4), -10, 0, 360, (80, 80, 85), 2, cv2.LINE_AA)

    # Save to disk
    cv2.imwrite(sample_path, road)
    print(f"[OK] Generated synthetic test road image at: {sample_path}")
    return sample_path

def seed_demo_database():
    """
    Populates SQLite database with 4 initial sample detection records
    so the web dashboard map and metrics are immediately populated for demonstration.
    """
    database.init_db()
    stats = database.get_summary_stats()
    if stats["total"] > 0:
        print("[INFO] Database already contains records. Skipping seed.")
        return

    print("[INFO] Seeding initial demonstration records into SQLite database...")
    sample_img = generate_synthetic_pothole_image()
    sample_filename = os.path.basename(sample_img)
    
    # Copy sample image to detections folder as demo snapshots
    demo_snapshots = [
        "demo_pothole_high_01.jpg",
        "demo_pothole_med_02.jpg",
        "demo_pothole_low_03.jpg",
        "demo_pothole_high_04.jpg"
    ]
    img_data = cv2.imread(sample_img)
    for snap in demo_snapshots:
        target = os.path.join(config.DETECTIONS_DIR, snap)
        if not os.path.exists(target):
            cv2.imwrite(target, img_data)

    records = [
        ("2026-10-06 10:14:22", "HIGH", 0.92, 8.4, demo_snapshots[0], 19.0760, 72.8777, "Car Dashcam", "video"),
        ("2026-10-06 10:18:05", "MEDIUM", 0.84, 4.2, demo_snapshots[1], 19.0785, 72.8802, "Car Dashcam", "video"),
        ("2026-10-06 10:22:40", "LOW", 0.76, 1.8, demo_snapshots[2], 19.0812, 72.8835, "Bike Helmet/Handlebar", "camera"),
        ("2026-10-06 10:29:15", "HIGH", 0.95, 9.1, demo_snapshots[3], 19.0850, 72.8870, "Car Dashcam", "camera")
    ]

    for rec in records:
        database.insert_detection(*rec)

    print("[OK] Successfully seeded 4 realistic demonstration records with GPS locations!")

if __name__ == "__main__":
    generate_synthetic_pothole_image()
    seed_demo_database()
