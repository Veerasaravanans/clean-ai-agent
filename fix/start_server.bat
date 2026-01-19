@echo off
REM start_server.bat - Windows startup script

echo ========================================
echo AI AGENT FRAMEWORK - STARTUP
echo ========================================
echo.

REM Activate virtual environment
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Warning: Virtual environment not found
)

echo.
echo Clearing Python cache...
python -c "import shutil; import pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"

echo.
echo Testing imports...
python test_imports.py

if errorlevel 1 (
    echo.
    echo ========================================
    echo IMPORT TEST FAILED!
    echo Please check the error above.
    echo ========================================
    pause
    exit /b 1
)

echo.
echo ========================================
echo Starting server...
echo ========================================
echo.

python start_server.py