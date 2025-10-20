@echo off
title Hybrid Health Check
color 0A
echo.
echo  ==============================================
echo     ??  Running Hybrid Health Diagnostics...
echo  ==============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass ^
  -Command "& 'C:\Users\JMiniPC\OneDrive\Projects\FantasyFootball\Run-Health.ps1' --pipeline"
echo.
echo  ==============================================
echo     ?  Hybrid Health Check complete.
echo     Log file saved under:
echo     data\processed\hybrid_health_pc_*.log
echo  ==============================================
echo.
pause
