@echo off
cd /d "%~dp0"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -X utf8 scripts\lab_gui.py
) else (
  python -X utf8 scripts\lab_gui.py
)
