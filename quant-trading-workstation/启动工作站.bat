@echo off
chcp 65001
cd /d "%~dp0"
cd /d "%~dp0server"
start "" pythonw -m uvicorn main:app --host 127.0.0.1 --port 8001 --log-level warning
cd /d "%~dp0"
timeout /t 4 /nobreak
start http://127.0.0.1:8001
echo.
echo QuantTrading Workstation started: http://127.0.0.1:8001
timeout /t 2 /nobreak
