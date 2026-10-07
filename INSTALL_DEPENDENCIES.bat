@echo off
title Install AI Pothole Detection Dependencies
cd /d "%~dp0"
echo ===================================================
echo Installing Required Libraries...
echo ===================================================
pip install -r requirements.txt
echo.
echo ===================================================
echo Done! All libraries installed. You can close this.
echo ===================================================
pause
