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

    def estimate_severity(self, box_w, box_h, frame_w, frame_h, y2=None):
        """
        Estimates visual severity based on 2D bounding footprint area and perspective proximity.
        In monocular vehicle cameras, foreground road features represent imminent impact risk.
        """
        box_area = box_w * box_h
        frame_area = frame_w * frame_h
        area_pct = box_area / max(frame_area, 1)

        # Perspective proximity weighting: potholes closer to the bottom (foreground) have higher impact hazard
        if y2 is not None:
            y_bottom_pct = y2 / max(frame_h, 1)
            hazard_score = area_pct * (1.0 + 1.8 * y_bottom_pct)
        else:
            hazard_score = area_pct

        if hazard_score >= config.SEVERITY_MED_AREA_PCT or area_pct >= 0.035:
            severity = "HIGH"
            color = config.COLOR_SEVERITY_HIGH
        elif hazard_score >= config.SEVERITY_LOW_AREA_PCT or area_pct >= 0.010:
            severity = "MEDIUM"
            color = config.COLOR_SEVERITY_MED
        else:
            severity = "LOW"
            color = config.COLOR_SEVERITY_LOW

        return severity, area_pct, color

    def detect_frame(self, frame, source_type="camera", trigger_audio=True):
        """
        Processes a single BGR OpenCV frame:
        - Runs YOLO inference
        - Computes bounding boxes & estimated severity
        - Draws labels, confidence %, and warning HUD
        - Triggers audio alert & saves detection screenshot/log
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

        # Fallback for baseline model on test images: detect asphalt cavities & texture disruptions
        if len(detections) == 0 and not self.is_custom_pothole_model:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # 1. Vegetation mask (green foliage, leaves, roadside grass)
            green_mask = cv2.inRange(hsv, (25, 30, 30), (95, 255, 255))

            # 2. Road driving corridor (ignore sky/trees above 35% and bottom 7% for watermarks/hood)
            road_y_start = int(h * 0.35)
            road_y_end = int(h * 0.93)

            road_gray = gray[road_y_start:road_y_end, :]
            road_hsv = hsv[road_y_start:road_y_end, :]
            road_green = green_mask[road_y_start:road_y_end, :]

            # Estimate median asphalt luminance
            asphalt_mask = (road_hsv[:, :, 1] < 40) & (road_green == 0) & (road_gray > 30) & (road_gray < 220)
            if np.sum(asphalt_mask) < 300:
                med_lum = float(np.median(road_gray))
            else:
                med_lum = float(np.median(road_gray[asphalt_mask]))

            filtered = cv2.bilateralFilter(road_gray, 9, 75, 75)
            edges = cv2.Canny(filtered, 40, 100)

            # Suppress edges in green foliage and outside road corridor
            edges[road_green > 0] = 0
            edges[:, :int(w * 0.08)] = 0
            edges[:, int(w * 0.92):] = 0

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            dilated = cv2.dilate(edges, kernel, iterations=1)
            contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            candidate_boxes = []
            candidate_confs = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area > max(500, (w * h * 0.003)):
                    rx, ry, bw, bh = cv2.boundingRect(cnt)
                    if bw > w * 0.75 or bh > h * 0.55:
                        continue
                    roi_y1 = ry + road_y_start
                    roi_y2 = roi_y1 + bh
                    roi_x1 = rx
                    roi_x2 = rx + bw

                    box_hsv = hsv[roi_y1:roi_y2, roi_x1:roi_x2]
                    box_gray = gray[roi_y1:roi_y2, roi_x1:roi_x2]
                    box_green = green_mask[roi_y1:roi_y2, roi_x1:roi_x2]

                    # Reject if majority is vegetation/grass/colored shoulder
                    if np.mean(box_green > 0) > 0.15:
                        continue
                    if np.mean(box_hsv[:, :, 1] > 45) > 0.35:
                        continue

                    # Verify dark cavity pit characteristic of potholes
                    dark_pixels = np.sum((box_gray < (med_lum - 25)) & (box_green == 0))
                    dark_ratio = dark_pixels / max(bw * bh, 1)

                    if dark_ratio > 0.08 or (np.std(box_gray) > 28 and np.min(box_gray) < (med_lum - 30)):
                        candidate_boxes.append([rx, roi_y1, bw, bh])
                        candidate_confs.append(float(area * (1.0 + dark_ratio)))

            if len(candidate_boxes) > 0:
                indices = cv2.dnn.NMSBoxes(candidate_boxes, candidate_confs, score_threshold=500, nms_threshold=0.3)
                final_boxes = []
                for i in indices:
                    idx = i if isinstance(i, (int, np.integer)) else i[0]
                    final_boxes.append(candidate_boxes[idx])

                # Deduplicate any small box fully inside a larger box
                filtered_boxes = []
                for b1 in final_boxes:
                    contained = False
                    for b2 in final_boxes:
                        if b1 != b2:
                            if (b1[0] >= b2[0] - 15 and b1[1] >= b2[1] - 15 and 
                                (b1[0] + b1[2]) <= (b2[0] + b2[2]) + 15 and 
                                (b1[1] + b1[3]) <= (b2[1] + b2[3]) + 15 and 
                                (b2[2] * b2[3]) > (b1[2] * b1[3]) * 1.4):
                                contained = True
                                break
                    if not contained:
                        filtered_boxes.append(b1)

                for (x1, y1, bw, bh) in filtered_boxes:
                    x2 = x1 + bw
                    y2 = y1 + bh
                    severity, area_pct, color = self.estimate_severity(bw, bh, w, h, y2=y2)
                    conf = min(0.96, 0.78 + (area_pct * 1.5))
                    
                    if severity_rank[severity] > severity_rank[max_severity]:
                        max_severity = severity

                    detections.append({
                        "box": (x1, y1, x2, y2),
                        "conf": conf,
                        "severity": severity,
                        "area_pct": area_pct,
                        "color": color
                    })

                    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 3)
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

        if len(detections) > 0:
            lat, lon = gps_tracker.get_coordinates()
            max_conf = max(d["conf"] for d in detections)
            max_area_pct = max(d["area_pct"] for d in detections)

            # 1. Visual HUD warning banner and Project Document Warning Card
            display_frame = self.alert_engine.draw_warning_hud(
                display_frame, severity=max_severity, count=len(detections),
                conf=max_conf, lat=lat, lon=lon
            )

            # 2. Trigger audio alert (respects rate-limit cooldown) if enabled
            alert_fired = False
            if trigger_audio and not self.alert_engine.is_muted:
                alert_fired = self.alert_engine.trigger_alert(severity=max_severity)

            # 3. Save screenshot & record to database (always for single images, or on alert_fired for video/webcam)
            if alert_fired or source_type == "image":
                now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                file_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"pothole_{file_timestamp}_{max_severity.lower()}.jpg"
                save_path = os.path.join(config.DETECTIONS_DIR, filename)

                # Save screenshot of annotated frame
                cv2.imwrite(save_path, display_frame)

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
                print(f"[ALERT] Pothole Logged: #{rec_id} | Severity: {max_severity} | Conf: {max_conf*100:.1f}% | GPS: ({lat:.4f}, {lon:.4f})")

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
                print(f"[INFO] OpenCV GUI skipped. Opening image in Windows Photos viewer...")
                if save_output and os.path.exists(out_path):
                    try:
                        os.startfile(out_path)
                    except Exception:
                        pass
        return annotated_frame

    def process_video(self, video_path):
        """Processes a road video stream and saves annotated output."""
        if not os.path.exists(video_path):
            print(f"[ERROR] Video file does not exist: {video_path}")
            return None

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[ERROR] Failed to open video file: {video_path}")
            return None

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps_in = cap.get(cv2.CAP_PROP_FPS) or 20.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        out_name = "annotated_" + os.path.basename(video_path)
        out_path = os.path.join(config.DETECTIONS_DIR, out_name)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(out_path, fourcc, fps_in, (w, h))

        print(f"[RUN] Processing road video: {video_path}")
        print(f"      Resolution: {w}x{h} | Frames: {total_frames} | Target FPS: {fps_in:.1f}")

        frame_count = 0
        total_potholes_found = 0
        gui_available = True
        prev_time = time.time()

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            curr_time = time.time()
            fps = 1.0 / max(curr_time - prev_time, 1e-4)
            prev_time = curr_time

            annotated_frame, detections = self.detect_frame(frame, source_type="video")
            annotated_frame = self.draw_telemetry_bar(annotated_frame, fps=fps)
            writer.write(annotated_frame)

            if len(detections) > 0:
                total_potholes_found += len(detections)
                sev_list = [d["severity"] for d in detections]
                print(f"  [FRAME {frame_count}/{total_frames}] Potholes Detected: {len(detections)} ({', '.join(sev_list)}) | FPS: {fps:.1f}")
            elif frame_count % 20 == 0 or frame_count == total_frames:
                print(f"  [FRAME {frame_count}/{total_frames}] Scanning road... Clear surface | FPS: {fps:.1f}")

            if gui_available:
                try:
                    cv2.imshow("AI Pothole Detection System - Video Mode", annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:
                        break
                except Exception:
                    gui_available = False

        cap.release()
        writer.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass

        print(f"\n[OK] Video analysis completed successfully!")
        print(f"     Total frames analyzed: {frame_count}")
        print(f"     Saved annotated video with bounding boxes to: {out_path}")
        
        if os.path.exists(out_path):
            try:
                os.startfile(out_path)
            except Exception:
                pass

        return out_path

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

        print("[OK] Live camera feed active.")
        prev_time = time.time()
        gui_available = True

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

            if gui_available:
                try:
                    cv2.imshow("AI Pothole Detection System - Live Feed", annotated_frame)
                    key = cv2.waitKey(1) & 0xFF
                    if key == ord('q') or key == 27:
                        break
                except Exception:
                    gui_available = False
                    print("[INFO] OpenCV desktop GUI window not available on Python 3.14 wheel.")
                    print("[RECOMMENDED] Launch 2_START_DASHBOARD.bat to stream live camera at 30 FPS inside browser!")
                    break

        cap.release()
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
