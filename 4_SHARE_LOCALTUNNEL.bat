@echo off
title RoadGuard AI - Public Link via Localtunnel
cd /d "%~dp0"
echo =====================================================================
echo   RoadGuard AI - Alternative Public Tunnel (Localtunnel)
echo =====================================================================
echo.
npx localtunnel --port 5000
pause
