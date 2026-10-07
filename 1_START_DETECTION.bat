@echo off
title AI Pothole Detection System - RoadGuard
cd /d "%~dp0"
echo ===================================================
echo Starting AI Pothole Detection Engine...
echo ===================================================
python run_detection.py
pause
