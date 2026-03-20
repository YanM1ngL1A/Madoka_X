@echo off
setlocal

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" "run_ui.py"
) else (
    python "run_ui.py"
)

if errorlevel 1 (
    echo.
    echo Failed to start the UI. Make sure Python is installed or .venv is available.
    pause
)
