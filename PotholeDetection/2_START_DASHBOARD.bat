@echo off
title AI Pothole Detection - Web Dashboard
cd /d "%~dp0"
echo ===================================================
echo Starting Web Dashboard on http://127.0.0.1:5000 ...
echo ===================================================
start http://127.0.0.1:5000
python dashboard.py
pause
