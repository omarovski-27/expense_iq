@echo off
title ExpenseIQ
echo ============================================
echo            ExpenseIQ Dashboard
echo ============================================
echo.
echo Your expenses live in the cloud (where the Telegram bot saves them).
echo This window just opens your dashboard to view them.
echo.
echo [1/2] Waking up the cloud server...
echo       (can take up to a minute if it has been idle)
curl -s --max-time 90 -o nul -w "      Server responded: HTTP %%{http_code}\n" https://expense-iq-ypan.onrender.com/health
echo.
echo [2/2] Opening your dashboard...
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
