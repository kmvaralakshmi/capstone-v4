@echo off
cd /d "%~dp0"
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Setup complete. Use start_backend.bat to open the dashboard.
pause
