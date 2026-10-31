@echo off
chcp 65001 >nul
title VocabMatrix Local Server
echo ========================================================
echo   Starting VocabMatrix Local Web Server on Port 8080
echo ========================================================
cd /d "%~dp0"
python server.py 8080
pause
