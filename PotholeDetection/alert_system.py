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

    def can_trigger(self):
        """Check if cooldown period has elapsed since last triggered alert."""
        return (time.time() - self.last_alert_time) >= self.cooldown

    def trigger_alert(self, severity="MEDIUM"):
        """
        Triggers an audio alert and updates cooldown timestamp.
        Returns True if alert actually fired, False if throttled by cooldown.
        """
        now = time.time()
        with self.lock:
            if (now - self.last_alert_time) < self.cooldown:
                return False
            self.last_alert_time = now

        # Run audio beep in a separate daemon thread to ensure zero video lag
        if config.AUDIO_BEEP_ENABLED:
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

    def draw_warning_hud(self, frame, severity="MEDIUM", count=1):
        """
        Draws a high-visibility '⚠ POTHOLE AHEAD' alert banner across the top of the frame.
        """
        h, w, _ = frame.shape
        banner_height = 65
        
        # Color styling based on severity
        if severity == "HIGH":
            bg_color = (0, 0, 180)      # Crimson Red
            text_color = (255, 255, 255)
        elif severity == "MEDIUM":
            bg_color = (0, 120, 230)    # Amber / Orange
            text_color = (255, 255, 255)
        else:
            bg_color = (0, 180, 220)    # Golden Yellow
            text_color = (20, 20, 20)

        # Create semi-transparent overlay banner
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, banner_height), bg_color, -1)
        # Blend overlay with original frame (alpha 0.85)
        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        # Draw warning text
        warning_text = f"[!] WARNING: POTHOLE AHEAD! | SEVERITY: {severity}"
        if count > 1:
            warning_text += f" ({count} DETECTED)"

        cv2.putText(
            frame,
            warning_text,
            (20, 42),
            cv2.FONT_HERSHEY_DUPLEX,
            0.85,
            text_color,
            2,
            cv2.LINE_AA
        )

        # Draw pulsing bottom border line on banner
        cv2.line(frame, (0, banner_height), (w, banner_height), (255, 255, 255), 2)
        return frame

alert_engine = AlertSystem()
