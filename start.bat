@echo off
REM campusfound - one-click start for Windows. Needs Python 3.10+ (python.org, tick "Add to PATH").
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.10 or newer from https://www.python.org/downloads/ and tick "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Setting up for the first time. This takes a minute...
  python -m venv .venv
)

".venv\Scripts\python.exe" -m pip install --quiet --disable-pip-version-check -r requirements.txt
if errorlevel 1 (
  echo Installing packages failed. Check your internet connection and try again.
  pause
  exit /b 1
)

".venv\Scripts\python.exe" run.py %*
pause
