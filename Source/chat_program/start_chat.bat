@echo off
cd /d "%~dp0"

echo Starting MiddAI...
echo.
echo Make sure LM Studio is already running its local server at:
echo http://127.0.0.1:1234
echo.
echo Keep this window open while using the chat.
echo Close this window or press Ctrl+C to stop the chat server.
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Could not find .venv\Scripts\python.exe
    echo Make sure this file is inside the MiddAI\chat_program folder.
    pause
    exit /b 1
)

start "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 2; Start-Process 'http://127.0.0.1:5000'"

".venv\Scripts\python.exe" chat.py

pause
