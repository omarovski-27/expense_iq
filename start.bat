@echo off
title ExpenseIQ Launcher
echo Starting ExpenseIQ...
echo.
start "ExpenseIQ Backend" cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn main:app --reload --port 8000"
echo Backend starting...
timeout /t 3 /nobreak > nul
start "ExpenseIQ Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host"
echo Frontend starting...
timeout /t 5 /nobreak > nul
start "" "http://localhost:5173"
echo.
echo All services started.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:5173
echo.
pause
