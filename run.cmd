@echo off
cd /d "%~dp0"
if exist "dist\0.1.1\DeskNest\DeskNest.exe" (
  start "" "dist\0.1.1\DeskNest\DeskNest.exe"
  exit /b
)
if exist ".runtime\pythonw.exe" (
  start "" ".runtime\pythonw.exe" "main.py"
  exit /b
)
if exist ".venv\Scripts\pythonw.exe" (
  start "" ".venv\Scripts\pythonw.exe" "main.py"
  exit /b
)
echo Python is not installed. See README.md or download the portable build.
pause
