@echo off
REM Runs the app directly with installed Python (no build needed).
cd /d "%~dp0"
python -c "import tkinterdnd2" 2>nul || python -m pip install --user tkinterdnd2
start "" pythonw journal_checker.py %*
