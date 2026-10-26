@echo off
title AURA - Autonomous Desktop Agent & Execution Harness
cd /d "%~dp0"

echo [AURA] Launching Cognitive Agent and Execution Harness...
"D:\Apps\Anaconda\python.exe" -u main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [AURA] Process terminated with exit code %ERRORLEVEL%.
    pause
)
