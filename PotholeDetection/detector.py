# ==============================================================================
# AI Pothole Detection System - Core Detection Engine
# ==============================================================================
import os
import cv2
import time
import datetime
import numpy as np
from ultralytics import YOLO

import config
import database
import alert_system
import gps_tracker

class PotholeDetector:
    """
    Main detection pipeline:
    1. Reads image/video/webcam stream via OpenCV.
    2. Runs inference using Ultralytics YOLO.
    3. Calculates visual bounding box area & estimated severity (LOW, MEDIUM, HIGH).
    4. Renders HUD annotations, confidence percentages, and warning banner.
    5. Dispatches non-blocking audio alerts with cooldown.
    6. Saves snapshot evidence and logs incident details (time, GPS, severity) to SQLite.
    """
    def __init__(self, model_path=None, conf_thresh=config.CONFIDENCE_THRESHOLD, vehicle_mode="Car Dashcam"):
        self.conf_thresh = conf_thresh
        self.vehicle_mode = vehicle_mode
        self.alert_engine = alert_system.alert_engine
        
        # Determine model path
        if model_path and os.path.exists(model_path):
            self.model_path = model_path
        elif os.path.exists(config.CUSTOM_MODEL_PATH):
            self.model_path = config.CUSTOM_MODEL_PATH
        elif os.path.exists(config.FALLBACK_MODEL_PATH):
            self.model_path = config.FALLBACK_MODEL_PATH
        else:
            # Fallback to loading standard weights
            self.model_path = "yolov8n.pt"

        print(f"[INIT] Loading YOLO model from: {self.model_path} ...")
        self.model = YOLO(self.model_path)
        
        # Check if model has a dedicated 'pothole' class
        self.class_names = self.model.names if hasattr(self.model, 'names') else {}
        self.is_custom_pothole_model = False
        if isinstance(self.class_names, dict):
            for idx, name in self.class_names.items():
                if "pothole" in str(name).lower() or "crack" in str(name).lower():
                    self.is_custom_pothole_model = True
                    break

        print(f"[INIT] Model loaded. Custom Pothole Weights Active: {self.is_custom_pothole_model}")
        print(f"[INIT] Active Vehicle Mode: {self.vehicle_mode}")

        # Initialize SQLite database
        database.init_db()

    def estimate_severity(self, box_w, box_h, frame_w, frame_h):
        """
        Estimates visual severity based on 2D bounding footprint area relative to frame size.
        NOTE: Standard monocular cameras cannot physically measure pothole millimeter depth.
        This provides an operational estimated severity metric for road hazard warning.
        """
        box_area = box_w * box_h
        frame_area = frame_w * frame_h
        area_pct = box_area / max(frame_area, 1)

        if area_pct >= config.SEVERITY_MED_AREA_PCT:
            severity = "HIGH"
            color = config.COLOR_SEVERITY_HIGH
        elif area_pct >= config.SEVERITY_LOW_AREA_PCT:
            severity = "MEDIUM"
            color = config.COLOR_SEVERITY_MED
        else:
            severity = "LOW"
            color = config.COLOR_SEVERITY_LOW

        return severity, area_pct, color

    def detect_frame(self, frame, source_type="camera"):
        """
        Processes a single BGR OpenCV frame:
        - Runs YOLO inference
        - Computes bounding boxes & estimated severity
        - Draws labels, confidence %, and warning HUD
        - Triggers audio alert & saves detection screenshot/log if cooldown permits
        """
        h, w, _ = frame.shape
        display_frame = frame.copy()

        # Run YOLO inference
        results = self.model.predict(
            source=frame,
            conf=self.conf_thresh,
            iou=config.IOU_THRESHOLD,
            verbose=False
        )

        detections = []
        max_severity = "LOW"
        severity_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

        if len(results) > 0 and len(results[0].boxes) > 0:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                cls_name = self.class_names.get(cls_id, str(cls_id))
                conf = float(box.conf[0].item())

                # If using custom pothole model, verify class; if fallback, accept detections
                if self.is_custom_pothole_model:
                    if "pothole" not in str(cls_name).lower():
                        continue

                # Bounding box coordinates (xyxy)
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = xyxy[0], xyxy[1], xyxy[2], xyxy[3]
                bw = max(x2 - x1, 1)
                bh = max(y2 - y1, 1)

                # Compute estimated severity
                severity, area_pct, color = self.estimate_severity(bw, bh, w, h)

                if severity_rank[severity] > severity_rank[max_severity]:
                    max_severity = severity

                detections.append({
                    "box": (x1, y1, x2, y2),
                    "conf": conf,
                    "severity": severity,
                    "area_pct": area_pct,
                    "color": color
                })

                # Draw bounding box
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 3)

                # Label background badge
                label_text = f"POTHOLE {conf*100:.1f}% [{severity}]"
                (label_w, label_h), baseline = cv2.getTextSize(
                    label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
                )
                label_y1 = max(y1 - label_h - 10, 0)
                label_y2 = y1
                cv2.rectangle(
                    display_frame,
                    (x1, label_y1),
                    (x1 + label_w + 10, label_y2),
                    color,
                    -1
                )
                cv2.putText(
                    display_frame,
                    label_text,
                    (x1 + 5, label_y2 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 255) if severity == "HIGH" else (0, 0, 0),
                    2,
                    cv2.LINE_AA
                )

        # If potholes were detected, draw top HUD warning & handle alert/saving
        if len(detections) > 0:
            # 1. Visual HUD warning banner
            display_frame = self.alert_engine.draw_warning_hud(
                display_frame, severity=max_severity, count=len(detections)
            )

            # 2. Trigger audio alert (respects rate-limit cooldown)
            alert_fired = self.alert_engine.trigger_alert(severity=max_severity)

            # 3. If cooldown permitted alert, save screenshot & record to database
            if alert_fired:
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                file_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"pothole_{file_timestamp}_{max_severity.lower()}.jpg"
                save_path = os.path.join(config.DETECTIONS_DIR, filename)

                # Save screenshot of annotated frame
                cv2.imwrite(save_path, display_frame)

                # Retrieve current GPS location
                lat, lon = gps_tracker.get_coordinates()

                # Get maximum confidence among detections
                max_conf = max(d["conf"] for d in detections)
                max_area_pct = max(d["area_pct"] for d in detections)

                # Store into SQLite
                rec_id = database.insert_detection(
                    timestamp=now_str,
                    severity=max_severity,
                    confidence=round(max_conf, 3),
                    box_area_pct=round(max_area_pct * 100, 2),
                    image_path=filename,
                    latitude=lat,
                    longitude=lon,
                    vehicle_mode=self.vehicle_mode,
                    source_type=source_type
                )
                print(f"[ALERT] Pothole Logged: #{rec_id} | Severity: {max_severity} | Conf: {max_conf*100:.1f}% | GPS: ({lat}, {lon})")

        return display_frame, detections

    def draw_telemetry_bar(self, frame, fps=0.0):
        """Draws bottom information status bar showing vehicle mode, GPS, and FPS."""
        h, w, _ = frame.shape
        bar_h = 35
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, h - bar_h), (w, h), (30, 30, 30), -1)
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        lat, lon = gps_tracker.get_coordinates()
        info_text = f"Mode: {self.vehicle_mode} | GPS: {lat:.4f}, {lon:.4f} | FPS: {fps:.1f} | 'q': Quit"
        cv2.putText(
            frame,
            info_text,
            (15, h - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (220, 220, 220),
            1,
            cv2.LINE_AA
        )
        return frame

    def process_image(self, image_path, save_output=True, show_window=True):
        """Processes a single road image input."""
        if not os.path.exists(image_path):
            print(f"[ERROR] Image file does not exist: {image_path}")
            return None

        frame = cv2.imread(image_path)
        if frame is None:
            print(f"[ERROR] Could not decode image: {image_path}")
            return None

        print(f"[RUN] Processing road image: {image_path}")
        annotated_frame, detections = self.detect_frame(frame, source_type="image")
        annotated_frame = self.draw_telemetry_bar(annotated_frame, fps=0.0)

        if save_output:
            out_name = "annotated_" + os.path.basename(image_path)
            out_path = os.path.join(config.DETECTIONS_DIR, out_name)
            cv2.imwrite(out_path, annotated_frame)
            print(f"[OK] Saved annotated result to: {out_path}")

        print(f"[RESULT] Found {len(detections)} pothole(s).")
        if show_window:
            try:
                cv2.imshow("AI Pothole Detection System - Image Mode", annotated_frame)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            except Exception as e:
                print(f"[INFO] GUI window skipped: {e}")
        return annotated_frame

    def process_video(self, video_path):
        """Processes a road video stream."""
        if not os.path.exists(video_path):
            print(f"[ERROR] Video file does not exist: {video_path}")
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[ERROR] Failed to open video file: {video_path}")
            return

        print(f"[RUN] Streaming road video: {video_path}")
        print("      Press 'q' or ESC in the video window to stop.")

        prev_time = time.time()
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                print("[INFO] Reached end of video file.")
                break

            curr_time = time.time()
            fps = 1.0 / max(curr_time - prev_time, 1e-4)
            prev_time = curr_time

            annotated_frame, _ = self.detect_frame(frame, source_type="video")
            annotated_frame = self.draw_telemetry_bar(annotated_frame, fps=fps)

            cv2.imshow("AI Pothole Detection System - Video Mode", annotated_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

        cap.release()
        cv2.destroyAllWindows()

    def process_webcam(self, camera_index=0):
        """Processes live camera feed from dashcam, USB cam, or bike handlebar/helmet mount."""
        print(f"[RUN] Initializing camera device at index: {camera_index}...")
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            print(f"[ERROR] Could not access camera index {camera_index}. Check permissions or USB connection.")
            return

        # Request standard 720p stream
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

        print("[OK] Live camera feed active. Press 'q' or ESC to quit.")
        prev_time = time.time()

        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Failed to capture video frame from camera.")
                break

            curr_time = time.time()
            fps = 1.0 / max(curr_time - prev_time, 1e-4)
            prev_time = curr_time

            annotated_frame, _ = self.detect_frame(frame, source_type="webcam")
            annotated_frame = self.draw_telemetry_bar(annotated_frame, fps=fps)

            cv2.imshow("AI Pothole Detection System - Live Feed", annotated_frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q') or key == 27:
                break

        cap.release()
        cv2.destroyAllWindows()
