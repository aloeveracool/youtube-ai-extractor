@echo off
chcp 65001 > nul
title GitHub 저장소 업로드

echo ========================================================
echo     YouTube AI Extractor - GitHub 저장소 업로드
echo ========================================================
echo.
echo [1] 저장소(aloeveracool/youtube-ai-extractor)로 푸시 시작...
echo.

cd /d "%~dp0"
git push -u origin main

echo.
echo ========================================================
echo [완료] 업로드가 완료되었습니다! 
echo 이제 Render 대시보드(https://dashboard.render.com)에서
echo 빌드가 자동으로 진행됩니다.
echo ========================================================
echo.
pause
