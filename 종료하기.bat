@echo off
chcp 65001 > nul
echo ===================================================
echo     YouTube AI Extractor 서버를 종료합니다...
echo ===================================================
echo.

for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8500 ^| findstr LISTENING') do (
    taskkill /F /PID %%a 2>nul
)

echo.
echo [완료] 서버가 안전하게 종료되었습니다.
timeout /t 2 > nul
