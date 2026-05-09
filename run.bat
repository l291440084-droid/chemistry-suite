@echo off
cd /d "%~dp0"
if exist "..\chemistry-suite-venv\Scripts\activate.bat" (
    call ..\chemistry-suite-venv\Scripts\activate.bat
)
python main.py
pause
