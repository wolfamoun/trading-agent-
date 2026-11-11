@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if errorlevel 1 (
  echo Python 3.11+ is required. Install it from https://www.python.org/downloads/windows/
  pause
  exit /b 1
)

py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if errorlevel 1 (
  echo Please install Python 3.11 or newer, then run this file again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 goto :failed

".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :failed

if not exist ".env" copy ".env.example" ".env" >nul

start "Fieldnote FX server" cmd /k ".venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000"
timeout /t 2 /nobreak >nul
start "" "http://127.0.0.1:8000"
echo Fieldnote FX is opening in your browser.
echo Keep the server window open. Close it to stop the app.
echo To enable the AI chat, add a new GROQ_API_KEY in the .env file and restart.
pause
exit /b 0

:failed
echo Setup failed. Check the message above, then run this file again.
pause
exit /b 1
