@echo off
REM 더블클릭용 발표 데모 런처 — 창이 닫히지 않게 -NoExit 유지
chcp 65001 >nul
powershell -ExecutionPolicy Bypass -NoExit -File "%~dp0DEMO.ps1" %*
