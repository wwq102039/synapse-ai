@echo off
chcp 65001 >nul
echo ============================================
echo   Synapse AI - Neural Brain Studio
echo ============================================
echo.
echo Starting Synapse AI server...
echo Open http://localhost:8765 in your browser
echo Press Ctrl+C to stop
echo.
cd /d "%~dp0"
call conda activate synapse-ai 2>nul
if errorlevel 1 (
    echo [WARN] conda not found, trying direct Python...
    set PYTHON_PATH=%USERPROFILE%\.conda\envs\synapse-ai\python.exe
    if exist "%PYTHON_PATH%" (
        "%PYTHON_PATH%" -m uvicorn backend.main:app --host 0.0.0.0 --port 8765 --reload
    ) else (
        python -m uvicorn backend.main:app --host 0.0.0.0 --port 8765 --reload
    )
) else (
    python -m uvicorn backend.main:app --host 0.0.0.0 --port 8765 --reload
)
pause
