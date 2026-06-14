@echo off
cd /d "%~dp0chat_program"

echo Starting MiddAI...
echo.
echo Make sure MiddAI_open_first.bat has already prepared LM Studio.
echo LM Studio API should be running at:
echo http://127.0.0.1:1234
echo.
echo MiddAI will open at:
echo http://127.0.0.1:5000
echo.
echo Keep this window open while using MiddAI.
echo Close this window or press Ctrl+C to stop the MiddAI chat server.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Could not find .venv\Scripts\python.exe
    echo Make sure this file is inside the MiddAI folder.
    pause
    exit /b 1
)

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:5000'"

".venv\Scripts\python.exe" chat.py

pause
