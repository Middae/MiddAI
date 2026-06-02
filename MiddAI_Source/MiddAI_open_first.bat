@echo off
cd /d "%~dp0"

echo MiddAI first step: prepare LM Studio.
echo.
echo This will use LM Studio's lms command to download/load a model and start
echo the LM Studio local API server on http://127.0.0.1:1234
echo.
echo Make sure LM Studio is installed and has been opened at least once.
echo.

set "PYTHON_EXE=%~dp0chat_program\.venv\Scripts\python.exe"

if not exist "%PYTHON_EXE%" (
    echo Could not find chat_program\.venv\Scripts\python.exe
    echo Make sure this file is inside the MiddAI folder.
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%~dp0lmstudio_setup\setup_lmstudio.py"

echo.
pause
