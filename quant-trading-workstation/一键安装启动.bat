@echo off
chcp 65001
title QuantTrading Workstation - Setup
cd /d "%~dp0"

echo ============================================
echo   QuantTrading Workstation
echo   Setup + Launch
echo ============================================
echo.

echo [1/3] Checking Python...
python --version
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Install Python 3.11+ from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during install.
    pause
    exit /b 1
)
echo.

echo [2/3] Installing dependencies...
cd /d "%~dp0server"
python -m pip install -r requirements.txt --quiet --disable-pip-version-check
if %errorlevel% neq 0 (
    echo [WARN] Trying Tsinghua mirror...
    python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple --quiet
)
cd /d "%~dp0"
echo [OK] Done
echo.

echo [3/3] Starting server...
taskkill /F /IM python.exe
timeout /t 2 /nobreak
cd /d "%~dp0server"
start "" pythonw -m uvicorn main:app --host 127.0.0.1 --port 8001 --log-level warning
cd /d "%~dp0"
timeout /t 4 /nobreak
start http://127.0.0.1:8001

echo.
echo ============================================
echo   Setup complete! http://127.0.0.1:8001
echo   Daily use: double-click start.bat
echo ============================================
pause
