@echo off
echo ============================================================
echo 3D RAG Visualization - Starting Web Server
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Check if embedding-data.json exists
if not exist "embedding-data.json" (
    echo WARNING: embedding-data.json not found
    echo Running: python extract_embeddings.py
    echo.
    python extract_embeddings.py
    echo.
)

REM Start the server
echo Starting server...
python start_server.py

pause