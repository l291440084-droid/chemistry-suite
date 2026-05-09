@echo off
echo === Chemistry Suite Windows Setup ===
echo.

cd /d "%~dp0"

echo [1/3] Creating Python virtual environment...
python -m venv ..\chemistry-suite-venv
if errorlevel 1 (
    echo ERROR: Failed to create venv. Make sure Python 3.10+ is installed.
    pause
    exit /b 1
)

echo [2/3] Installing Python dependencies...
call ..\chemistry-suite-venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install Python packages.
    pause
    exit /b 1
)

echo [3/3] Installing Node.js dependencies...
npm install
if errorlevel 1 (
    echo WARNING: npm install failed. Web components may not work.
    echo Make sure Node.js is installed.
)

echo.
echo === Setup complete! ===
echo Run 'run.bat' to start the application.
pause
