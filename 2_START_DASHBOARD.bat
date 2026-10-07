@echo off
title RoadGuard AI - Web Dashboard (Multi-Laptop Network Access)
cd /d "%~dp0"
echo =================================================================
echo   RoadGuard AI Pothole Detection Dashboard
echo   Starting server with multi-device network access...
echo =================================================================
echo.
echo   This Laptop: http://127.0.0.1:5000
echo   Other Laptops/Phones: Connect to the same Wi-Fi/Hotspot!
echo   (Your exact shareable network link will appear below)
echo.
echo =================================================================
start http://127.0.0.1:5000
python dashboard.py
pause
