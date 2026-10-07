@echo off
REM Builds a single JournalChecker.exe (no Python needed on target PCs).
REM Requires Python 3.9+ from python.org on THIS machine.
cd /d "%~dp0"
python -m pip install --upgrade pyinstaller tkinterdnd2 || goto :error
python -m PyInstaller --noconfirm --onefile --windowed --name JournalChecker --collect-all tkinterdnd2 journal_checker.py || goto :error
echo.
echo Done: dist\JournalChecker.exe
pause
exit /b 0
:error
echo Build failed.
pause
exit /b 1
