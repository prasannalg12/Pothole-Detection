# ==============================================================================
# AI Pothole Detection System - Unified Web Dashboard Backend
# ==============================================================================
import os
import cv2
import time
import datetime
import threading
from flask import Flask, render_template, jsonify, send_from_directory, request, Response

import config
import database
import gps_tracker
from detector import PotholeDetector

app = Flask(
    __name__,
    template_folder=config.TEMPLATES_DIR,
    static_folder=config.STATIC_DIR
)

# Global detector instance
current_vehicle_mode = "Car Dashcam"
detector_instance = PotholeDetector(vehicle_mode=current_vehicle_mode)

# Camera streaming control
camera_lock = threading.Lock()
camera_active = False
video_cap = None

@app.route("/")
def index():
    """Renders the unified all-in-one dashboard."""
    stats = database.get_summary_stats()
    detections = database.get_all_detections(limit=50)
    return render_template(
        "dashboard.html",
        stats=stats,
        detections=detections,
        vehicle_mode=current_vehicle_mode
    )

@app.route("/api/stats")
def api_stats():
    """Returns JSON payload of system statistics."""
    stats = database.get_summary_stats()
    return jsonify(stats)

@app.route("/api/detections")
def api_detections():
    """Returns JSON list of all recent detections."""
    detections = database.get_all_detections(limit=100)
    return jsonify(detections)

@app.route("/api/set_vehicle_mode", methods=["POST"])
def api_set_vehicle_mode():
    """Toggles vehicle deployment mode (Car vs Bike)."""
    global current_vehicle_mode, detector_instance
    data = request.get_json() or {}
    mode = data.get("mode", "Car Dashcam")
    current_vehicle_mode = mode
    detector_instance.vehicle_mode = mode
    return jsonify({"status": "success", "mode": current_vehicle_mode})

@app.route("/api/silence_alarm", methods=["POST"])
def api_silence_alarm():
    """Silences any ongoing audio alert in the backend."""
    global detector_instance
    detector_instance.alert_engine.mute()
    return jsonify({"status": "silenced"})

@app.route("/api/unmute_alarm", methods=["POST"])
def api_unmute_alarm():
    """Unmutes audio alerts in the backend."""
    global detector_instance
    detector_instance.alert_engine.unmute()
    return jsonify({"status": "unmuted"})

@app.route("/api/detect_image", methods=["POST"])
def api_detect_image():
    """
    Handles image detection directly from web dashboard.
    Accepts uploaded file or runs on preloaded synthetic sample.
    """
    global detector_instance
    file = request.files.get("image")
    use_sample = request.form.get("use_sample", "false").lower() == "true"

    if use_sample or not file:
        sample_type = request.form.get("sample_type", "street")
        if sample_type == "highway":
            image_path = os.path.join(config.DATA_DIR, "road_highway.jpg")
        elif sample_type == "clean":
            image_path = os.path.join(config.DATA_DIR, "sample_clean_road.jpg")
        elif sample_type == "mixed":
            image_path = os.path.join(config.DATA_DIR, "sample_mixed_potholes.jpg")
        else:
            image_path = os.path.join(config.DATA_DIR, "real_road_pothole.jpg")
            if not os.path.exists(image_path):
                image_path = os.path.join(config.DATA_DIR, "sample_road.jpg")
        frame = cv2.imread(image_path)
    else:
        # Save uploaded file
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        upload_filename = f"upload_{timestamp}_{file.filename}"
        upload_path = os.path.join(config.DATA_DIR, upload_filename)
        file.save(upload_path)
        frame = cv2.imread(upload_path)

    if frame is None:
        return jsonify({"status": "error", "message": "Failed to decode image"}), 400

    # For web dashboard, audio is managed interactively in the browser UI
    annotated_frame, detections = detector_instance.detect_frame(frame, source_type="image", trigger_audio=False)
    
    # Save annotated result
    result_filename = f"web_result_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
    result_path = os.path.join(config.DETECTIONS_DIR, result_filename)
    cv2.imwrite(result_path, annotated_frame)

    lat, lon = gps_tracker.get_coordinates()
    max_severity = "NONE"
    if len(detections) > 0:
        max_severity = max(d["severity"] for d in detections)

    return jsonify({
        "status": "success",
        "result_image": f"/detections/{result_filename}",
        "count": len(detections),
        "max_severity": max_severity,
        "latitude": lat,
        "longitude": lon,
        "vehicle_mode": current_vehicle_mode,
        "detections": [{
            "severity": d["severity"],
            "conf": round(d["conf"] * 100, 1),
            "area_pct": round(d["area_pct"] * 100, 2)
        } for d in detections]
    })

def generate_video_stream():
    """Generator for live webcam feed with real-time YOLO detection overlay."""
    global camera_active, video_cap, detector_instance
    cap = cv2.VideoCapture(0)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    
    while camera_active:
        success, frame = cap.read()
        if not success:
            break

        annotated_frame, _ = detector_instance.detect_frame(frame, source_type="webcam")
        annotated_frame = detector_instance.draw_telemetry_bar(annotated_frame)

        ret, buffer = cv2.imencode(".jpg", annotated_frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

    cap.release()

@app.route("/video_feed")
def video_feed():
    """Video streaming route for live camera detection."""
    global camera_active
    camera_active = True
    return Response(
        generate_video_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/api/stop_camera", methods=["POST"])
def api_stop_camera():
    """Stops the camera streaming generator."""
    global camera_active
    camera_active = False
    return jsonify({"status": "success", "message": "Camera stopped"})

# ------------------------------------------------------------------------------
# Video File Streaming (Pre-recorded Road Video Inference)
# ------------------------------------------------------------------------------
video_file_active = False
active_video_path = os.path.join(config.DATA_DIR, "road_test.mp4")

def generate_video_file_stream(file_path):
    """Streams a pre-recorded road video with real-time YOLO detection overlay."""
    global video_file_active, detector_instance
    cap = cv2.VideoCapture(file_path)
    fps_in = cap.get(cv2.CAP_PROP_FPS) or 20.0
    delay = 1.0 / max(fps_in, 10.0)

    while video_file_active and cap.isOpened():
        success, frame = cap.read()
        if not success:
            # Loop video smoothly
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

        annotated_frame, _ = detector_instance.detect_frame(frame, source_type="video", trigger_audio=False)
        annotated_frame = detector_instance.draw_telemetry_bar(annotated_frame, fps=fps_in)

        ret, buffer = cv2.imencode(".jpg", annotated_frame)
        if not ret:
            continue

        frame_bytes = buffer.tobytes()
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")
        time.sleep(delay)

    cap.release()

@app.route("/video_file_feed")
def video_file_feed():
    """Stream MJPEG feed of recorded road video."""
    global video_file_active, active_video_path
    video_file_active = True
    return Response(
        generate_video_file_stream(active_video_path),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/api/start_video_file", methods=["POST"])
def api_start_video_file():
    """Starts video file detection playback."""
    global video_file_active, active_video_path
    data = request.get_json() or {}
    use_sample = data.get("use_sample", True)
    active_video_path = os.path.join(config.DATA_DIR, "road_test.mp4")
    video_file_active = True
    return jsonify({"status": "success", "video": active_video_path})

@app.route("/api/upload_video", methods=["POST"])
def api_upload_video():
    """Uploads a custom road video file and sets it for playback."""
    global video_file_active, active_video_path
    file = request.files.get("video")
    if not file:
        return jsonify({"status": "error", "message": "No video file uploaded"}), 400

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    upload_filename = f"upload_video_{timestamp}_{file.filename}"
    upload_path = os.path.join(config.DATA_DIR, upload_filename)
    file.save(upload_path)
    active_video_path = upload_path
    video_file_active = True
    return jsonify({"status": "success", "filename": upload_filename})

@app.route("/api/stop_video_file", methods=["POST"])
def api_stop_video_file():
    """Stops the video file playback."""
    global video_file_active
    video_file_active = False
    return jsonify({"status": "success", "message": "Video playback stopped"})

@app.route("/api/detections/<int:detection_id>", methods=["DELETE"])
def api_delete_detection(detection_id):
    """Deletes a detection entry."""
    database.delete_detection(detection_id)
    return jsonify({"status": "success", "message": f"Record #{detection_id} removed"})

@app.route("/api/shutdown", methods=["POST"])
def api_shutdown():
    """Gracefully stops the dashboard server."""
    def kill():
        time.sleep(0.5)
        os._exit(0)
    threading.Thread(target=kill, daemon=True).start()
    return jsonify({"status": "success", "message": "Dashboard server shutting down..."})

@app.route("/detections/<path:filename>")
def serve_detection_image(filename):
    """Serves captured pothole screenshot files directly from detections folder."""
    return send_from_directory(config.DETECTIONS_DIR, filename)

def get_local_ip():
    """Returns local IPv4 network address of this computer."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def start_server():
    """Starts the Flask server with multi-device network support."""
    database.init_db()
    local_ip = get_local_ip()
    port = config.DASHBOARD_PORT
    print("=" * 68)
    print("    RoadGuard AI - All-in-One Detection & Geospatial Dashboard")
    print("=" * 68)
    print("  [LOCAL ACCESS - This Laptop]:")
    print(f"     http://127.0.0.1:{port}")
    print(f"     http://localhost:{port}")
    print("")
    print("  [NETWORK ACCESS - Other Laptops / Phones on Same Wi-Fi]:")
    print(f"     http://{local_ip}:{port}")
    print("=" * 68)
    print("  [INFO] Share the Network URL above so others can open it!")
    print("=" * 68)

    app.run(
        host=config.DASHBOARD_HOST,
        port=port,
        debug=False
    )

if __name__ == "__main__":
    start_server()
