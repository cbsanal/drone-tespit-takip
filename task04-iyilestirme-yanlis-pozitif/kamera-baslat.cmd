@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -u scripts\kamera.py --droidcam %*
) else (
  "..\task04-model-egitimi\.venv\Scripts\python.exe" -u scripts\kamera.py --droidcam %*
)
pause
