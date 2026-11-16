@echo off
title AURA - Autonomous Desktop Agent & Execution Harness
cd /d "%~dp0"

echo [AURA] Launching Cognitive Agent and Execution Harness...
python -u main.py
if %ERRORLEVEL% NEQ 0 (
    "C:\Users\arpit\AppData\Local\Programs\Python\Python312\python.exe" -u main.py
)
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AURA] Process terminated with exit code %ERRORLEVEL%.
    pause
)
