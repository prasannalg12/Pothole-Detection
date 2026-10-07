@echo off
title Stop RoadGuard AI System
echo ===================================================
echo Stopping AI Pothole Detection & Dashboard processes...
echo ===================================================
taskkill /F /IM python.exe /T 2>nul
echo.
echo ===================================================
echo All RoadGuard AI processes have been stopped!
echo You can safely close this window.
echo ===================================================
pause
