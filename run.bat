@echo off
REM MT5 Gold Trading System - Startup Script for Windows

echo ============================================================
echo   MT5 GOLD TRADING SYSTEM - Multi-Agent Analysis
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Check if in project directory
if not exist "main.py" (
    echo ERROR: Please run this script from the project directory
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt -q

echo.
echo ============================================================
echo   Running Analysis...
echo ============================================================
echo.

REM Run main analysis
python main.py %*

echo.
echo ============================================================
pause
