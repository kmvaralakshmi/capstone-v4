@echo off
cd /d "%~dp0"
python scripts\run_pipeline.py --skip-download
pause
