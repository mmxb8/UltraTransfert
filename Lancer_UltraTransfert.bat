@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
if not exist "%~dp0launch_gui.py" (
  echo Archive incomplete. Extrayez tout le ZIP dans un nouveau dossier puis relancez.
  pause
  exit /b 1
)
if exist ".venv-run\Scripts\pythonw.exe" (
  start "" ".venv-run\Scripts\pythonw.exe" "%~dp0launch_gui.py"
  if errorlevel 1 (
    echo Impossible de lancer Python. Relancez Installer_Windows.bat.
    pause
    exit /b 1
  )
  exit /b 0
)
if exist ".venv-run\Scripts\python.exe" (
  ".venv-run\Scripts\python.exe" "%~dp0launch_gui.py"
  if errorlevel 1 pause
  exit /b
)
py -3 -c "import sys,tkinter; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0launch_gui.py"
  if errorlevel 1 pause
  exit /b
)
python -c "import sys,tkinter; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 (
  python "%~dp0launch_gui.py"
  if errorlevel 1 pause
  exit /b
)
echo Lancez Installer_Windows.bat pour installer Python avec tkinter.
pause
exit /b 1
