@echo off
echo Starting ExpenseIQ...
start cmd /k "cd /d %~dp0backend && .venv\Scripts\activate && uvicorn main:app --reload --port 8000"
timeout /t 3 /nobreak > nul
start cmd /k "cd /d %~dp0frontend && npm run dev"
timeout /t 4 /nobreak > nul
start "" "http://localhost:5173"
echo ExpenseIQ is running. Close this window when done.
