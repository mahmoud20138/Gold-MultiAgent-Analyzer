@echo off
REM ============================================================
REM  UNIFIED EXECUTOR — ICT Multi-Agent Trade Launcher
REM  Session: trading_20260305_194417
REM ============================================================

title ICT Unified Executor

echo.
echo  ================================================================
echo   UNIFIED EXECUTOR  ^|  ICT Multi-Agent Scan Processor
echo   Session: trading_20260305_194417
echo  ================================================================
echo.
echo  Config:
echo    MAGIC_NUMBER  : 202603
echo    MAX_LOT       : 0.1
echo    MAX_POSITIONS : 5  (2 legacy already open)
echo    MIN_SCORE     : 5
echo    MAX_DAILY_LOSS: 3%%
echo    MONITOR_INT   : 30s
echo.
echo  Legacy positions (AMZNm + MSFTm) are tracked but NOT modified.
echo.

REM Activate venv and run
set "VENV=%~dp0venv\Scripts\python.exe"
set "SCRIPT=%~dp0unified_executor.py"

if not exist "%VENV%" (
    echo  [ERROR] venv Python not found at: %VENV%
    echo  Please ensure the venv is set up correctly.
    pause
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo  [ERROR] Script not found at: %SCRIPT%
    pause
    exit /b 1
)

echo  Starting executor...
echo  Press Ctrl+C in the console to stop the monitoring loop.
echo.

"%VENV%" "%SCRIPT%"

echo.
echo  ================================================================
echo   Executor exited.
echo  ================================================================
pause
