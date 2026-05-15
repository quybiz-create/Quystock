@echo off
title QuyStock
cd /d C:\StockAlert

:: Kiem tra server da chay chua
netstat -an | find "5000" | find "LISTENING" >nul 2>&1
if %errorlevel%==0 (
    start chrome http://localhost:5000
    exit
)

:: Chay server ngam
start /min cmd /c python server.py

:: Cho server khoi dong
timeout /t 4 /nobreak >nul

:: Mo Chrome
start chrome http://localhost:5000