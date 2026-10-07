# ==============================================================================
# RoadGuard AI - Public Worldwide Internet Tunnel Launcher
# Enables access from any laptop or mobile device on ANY network worldwide
# ==============================================================================
import os
import sys
import subprocess
import re
import time
import urllib.request

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLOUDFLARED_EXE = os.path.join(BASE_DIR, "cloudflared.exe")

def is_dashboard_running():
    try:
        urllib.request.urlopen("http://127.0.0.1:5000/api/stats", timeout=1.5)
        return True
    except Exception:
        return False

def main():
    print("=" * 70)
    print("   RoadGuard AI - Worldwide Internet Public Share Link")
    print("=" * 70)

    # 1. Start dashboard if not running
    if not is_dashboard_running():
        print("[INFO] Starting RoadGuard AI Dashboard server in background...")
        subprocess.Popen(
            [sys.executable, os.path.join(BASE_DIR, "dashboard.py")],
            creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
        )
        time.sleep(2.5)

    if not os.path.exists(CLOUDFLARED_EXE):
        print(f"[ERROR] cloudflared.exe was not found at: {CLOUDFLARED_EXE}")
        return

    print("[INFO] Creating secure encrypted HTTPS tunnel via Cloudflare...")
    print("[INFO] Zero sign-up, zero account required.")
    print("-" * 70)

    cmd = [CLOUDFLARED_EXE, "tunnel", "--url", "http://127.0.0.1:5000"]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace"
    )

    url_found = False
    for line in proc.stdout:
        match = re.search(r"https://[a-zA-Z0-9\-]+\.trycloudflare\.com", line)
        if match and not url_found:
            url_found = True
            public_url = match.group(0)
            print("\n" + "=" * 70)
            print("  SUCCESS! YOUR DASHBOARD IS ACCESSIBLE FROM ANYWHERE WORLDWIDE")
            print("=" * 70)
            print("\n  >> SHARE THIS LINK WITH ANYONE ON ANY LAPTOP OR PHONE:\n")
            print(f"     {public_url}\n")
            print("  * Anyone on ANY Wi-Fi network, mobile hotspot, or cellular 4G/5G can open it.")
            print("  * Keep this window open while sharing.")
            print("=" * 70 + "\n")
        elif not url_found:
            if "Registered tunnel connection" in line or "connection" in line.lower():
                print(f"  [Connecting] {line.strip()}")

    proc.wait()

if __name__ == "__main__":
    main()
