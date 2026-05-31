@echo off
title ExpenseIQ
echo ============================================
echo            ExpenseIQ Dashboard
echo ============================================
echo.
echo Your expenses live in the cloud (where the Telegram bot saves them).
echo This window just opens your dashboard to view them.
echo.
echo Starting your dashboard...
echo.

REM Wake the cloud in the BACKGROUND so it warms while the dashboard boots.
REM We do NOT wait for it - the dashboard retries on its own if the server
REM is still waking. With the keep-warm job running it is usually already
REM awake, so there is nothing to wait for.
start "" /B curl -s --max-time 90 -o nul https://expense-iq-ypan.onrender.com/health

REM Launch the dashboard and open it in the browser right away.
start "ExpenseIQ Frontend" cmd /k "cd /d %~dp0frontend && npm run dev -- --host"
timeout /t 4 /nobreak > nul
start "" "http://localhost:5173"
echo.
echo ============================================
echo  Dashboard opening in your browser.
echo  Keep this window open while you use the app.
echo  Close it (or press a key) when you are done.
echo ============================================
echo.
pause
