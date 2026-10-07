# ==============================================================================
# AI Pothole Detection System - Database Manager (SQLite)
# ==============================================================================
import sqlite3
import os
import config

def get_connection():
    """Create a thread-safe connection to the SQLite database."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the detections table schema if it does not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            severity TEXT NOT NULL,
            confidence REAL NOT NULL,
            box_area_pct REAL NOT NULL,
            image_path TEXT NOT NULL,
            latitude REAL,
            longitude REAL,
            vehicle_mode TEXT DEFAULT 'Car Dashcam',
            source_type TEXT DEFAULT 'camera'
        )
    """)
    conn.commit()
    conn.close()

def insert_detection(timestamp, severity, confidence, box_area_pct, image_path,
                     latitude=None, longitude=None, vehicle_mode="Car Dashcam", source_type="camera"):
    """
    Insert a newly identified pothole detection record.
    Returns the integer ID of the inserted record.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO detections 
        (timestamp, severity, confidence, box_area_pct, image_path, latitude, longitude, vehicle_mode, source_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, severity, confidence, box_area_pct, image_path, latitude, longitude, vehicle_mode, source_type))
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id

def get_all_detections(limit=200):
    """Retrieve all detection entries sorted by most recent first."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM detections
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def get_summary_stats():
    """Compute summary statistics for dashboard display."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) AS total FROM detections")
    total = cursor.fetchone()["total"] or 0
    
    cursor.execute("SELECT COUNT(*) AS count FROM detections WHERE severity = 'HIGH'")
    high_count = cursor.fetchone()["count"] or 0
    
    cursor.execute("SELECT COUNT(*) AS count FROM detections WHERE severity = 'MEDIUM'")
    med_count = cursor.fetchone()["count"] or 0
    
    cursor.execute("SELECT COUNT(*) AS count FROM detections WHERE severity = 'LOW'")
    low_count = cursor.fetchone()["count"] or 0
    
    cursor.execute("SELECT AVG(confidence) AS avg_conf FROM detections")
    avg_conf = cursor.fetchone()["avg_conf"]
    avg_conf = round(avg_conf * 100, 1) if avg_conf is not None else 0.0

    conn.close()
    return {
        "total": total,
        "high": high_count,
        "medium": med_count,
        "low": low_count,
        "avg_confidence": avg_conf
    }

def delete_detection(detection_id):
    """Delete a single detection entry by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detections WHERE id = ?", (detection_id,))
    conn.commit()
    conn.close()

def clear_all_detections():
    """Clear all records from database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM detections")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print(f"[OK] Database initialized successfully at: {config.DB_PATH}")
