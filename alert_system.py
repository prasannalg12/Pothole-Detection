# ==============================================================================
# AI Pothole Detection System - Alert & Audio Engine
# ==============================================================================
import time
import threading
import sys
import cv2
import numpy as np
import config

try:
    import winsound
    HAS_WINSOUND = True
except ImportError:
    HAS_WINSOUND = False

class AlertSystem:
    """
    Manages audio alerts with rate-limiting cooldown and HUD overlay drawing.
    Prevents stutter by running audio playback in non-blocking background threads.
    """
    def __init__(self, cooldown=config.ALERT_COOLDOWN_SECONDS):
        self.cooldown = cooldown
        self.last_alert_time = 0.0
        self.lock = threading.Lock()
        self.is_muted = False

    def mute(self):
        """Silences any ongoing and future audio alerts."""
        self.is_muted = True

    def unmute(self):
        """Re-enables audio alerts."""
        self.is_muted = False

    def can_trigger(self):
        """Check if cooldown period has elapsed since last triggered alert."""
        if self.is_muted:
            return False
        return (time.time() - self.last_alert_time) >= self.cooldown

    def trigger_alert(self, severity="MEDIUM"):
        """
        Triggers an audio alert and updates cooldown timestamp.
        Returns True if alert actually fired, False if throttled by cooldown.
        """
        if self.is_muted:
            return False
        now = time.time()
        with self.lock:
            if (now - self.last_alert_time) < self.cooldown:
                return False
            self.last_alert_time = now

        # Run audio beep in a separate daemon thread to ensure zero video lag
        if config.AUDIO_BEEP_ENABLED and not self.is_muted:
            threading.Thread(target=self._play_beep, args=(severity,), daemon=True).start()

        return True

    def _play_beep(self, severity):
        """Asynchronously play a tone corresponding to severity level."""
        freq = config.BEEP_FREQUENCY_MED
        if severity == "HIGH":
            freq = config.BEEP_FREQUENCY_HIGH
        elif severity == "LOW":
            freq = config.BEEP_FREQUENCY_LOW

        if HAS_WINSOUND:
            try:
                # Windows built-in motherboard/speaker beep
                winsound.Beep(freq, config.BEEP_DURATION_MS)
            except Exception:
                pass
        else:
            # Fallback for systems without winsound
            sys.stdout.write('\a')
            sys.stdout.flush()

    def draw_warning_hud(self, frame, severity="MEDIUM", count=1, conf=0.96, lat=config.DEFAULT_LATITUDE, lon=config.DEFAULT_LONGITUDE):
        """
        Draws high-visibility '⚠ POTHOLE AHEAD' alert banner and the exact
        warning card layout matching the project specification document (PDF pages 1, 3, 4).
        """
        h, w, _ = frame.shape
        banner_height = 50
        
        # Color styling based on severity
        if severity == "HIGH":
            bg_color = (0, 0, 180)      # Crimson Red
            card_border = (0, 0, 255)
        elif severity == "MEDIUM":
            bg_color = (0, 120, 230)    # Amber / Orange
            card_border = (0, 140, 255)
        else:
            bg_color = (0, 180, 220)    # Golden Yellow
            card_border = (0, 220, 255)

        # 1. Top Warning Banner
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_height), bg_color, -1)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        warning_text = f"[!] WARNING: POTHOLE AHEAD! | SEVERITY: {severity}"
        if count > 1:
            warning_text += f" ({count} DETECTED)"

        cv2.putText(
            frame,
            warning_text,
            (20, 34),
            cv2.FONT_HERSHEY_DUPLEX,
            0.75,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )
        cv2.line(frame, (0, banner_height), (w, banner_height), (255, 255, 255), 2)

        # 2. Project Specification Warning Card (from PDF pages 1, 3, 4)
        card_w = min(270, int(w * 0.42))
        card_h = 130
        card_x = w - card_w - 20
        card_y = banner_height + 15

        card_overlay = frame.copy()
        cv2.rectangle(card_overlay, (card_x, card_y), (card_x + card_w, card_y + card_h), (20, 20, 25), -1)
        cv2.addWeighted(card_overlay, 0.82, frame, 0.18, 0, frame)
        cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + card_h), card_border, 2)

        # Card Title Header
        cv2.rectangle(frame, (card_x, card_y), (card_x + card_w, card_y + 30), bg_color, -1)
        cv2.putText(
            frame,
            "POTHOLE AHEAD",
            (card_x + int(card_w / 2) - 68, card_y + 21),
            cv2.FONT_HERSHEY_DUPLEX,
            0.52,
            (255, 255, 255),
            1,
            cv2.LINE_AA
        )

        # Card Body: Confidence %
        conf_val = int(conf * 100) if conf <= 1.0 else int(conf)
        cv2.putText(
            frame,
            f"[!] {conf_val}%",
            (card_x + int(card_w / 2) - 35, card_y + 58),
            cv2.FONT_HERSHEY_DUPLEX,
            0.68,
            (0, 140, 255) if severity != "HIGH" else (0, 0, 255),
            2,
            cv2.LINE_AA
        )

        # Card Body: Severity
        cv2.putText(
            frame,
            f"Severity: {severity}",
            (card_x + 16, card_y + 86),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.50,
            (240, 240, 240),
            1,
            cv2.LINE_AA
        )

        # Card Body: Location
        cv2.putText(
            frame,
            f"Location: {lat:.4f}, {lon:.4f}",
            (card_x + 16, card_y + 112),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (180, 210, 240),
            1,
            cv2.LINE_AA
        )

        return frame

alert_engine = AlertSystem()
