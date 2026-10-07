@echo off
title RoadGuard AI - Public Worldwide Internet Link (Cloudflare Tunnel)
cd /d "%~dp0"
echo =====================================================================
echo   RoadGuard AI - Public Worldwide Internet Shareable Link
echo =====================================================================
echo.
echo   [1/2] Checking dashboard server status...
start http://127.0.0.1:5000
echo   [2/2] Launching secure Cloudflare Tunnel for port 5000...
echo.
echo   ===================================================================
echo   LOOK FOR YOUR PUBLIC LINK BELOW (e.g., https://...trycloudflare.com)
echo   Copy and send that link to anyone on ANY laptop or phone!
echo   ===================================================================
echo.
.\cloudflared.exe tunnel --url http://127.0.0.1:5000
pause
