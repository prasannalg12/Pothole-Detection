# ==============================================================================
# AI Pothole Detection System - Flask Web Dashboard
# ==============================================================================
import os
from flask import Flask, render_template, jsonify, send_from_directory, request
import config
import database

app = Flask(
    __name__,
    template_folder=config.TEMPLATES_DIR,
    static_folder=config.STATIC_DIR
)

@app.route("/")
def index():
    """Renders the main dashboard page."""
    stats = database.get_summary_stats()
    detections = database.get_all_detections(limit=50)
    return render_template("dashboard.html", stats=stats, detections=detections)

@app.route("/api/stats")
def api_stats():
    """Returns JSON payload of system statistics."""
    stats = database.get_summary_stats()
    return jsonify(stats)

@app.route("/api/detections")
def api_detections():
    """Returns JSON list of all recent detections for dynamic map markers & table."""
    detections = database.get_all_detections(limit=100)
    return jsonify(detections)

@app.route("/api/detections/<int:detection_id>", methods=["DELETE"])
def api_delete_detection(detection_id):
    """Deletes a detection entry."""
    database.delete_detection(detection_id)
    return jsonify({"status": "success", "message": f"Record #{detection_id} removed"})

@app.route("/detections/<path:filename>")
def serve_detection_image(filename):
    """Serves captured pothole screenshot files directly from detections folder."""
    return send_from_directory(config.DETECTIONS_DIR, filename)

def start_server():
    """Starts the Flask development server."""
    database.init_db()
    print("=" * 65)
    print("    AI Pothole Detection - Web Dashboard")
    print(f"    URL: http://{config.DASHBOARD_HOST}:{config.DASHBOARD_PORT}")
    print("    Press CTRL+C to stop the dashboard server.")
    print("=" * 65)
    app.run(
        host=config.DASHBOARD_HOST,
        port=config.DASHBOARD_PORT,
        debug=False
    )

if __name__ == "__main__":
    start_server()
