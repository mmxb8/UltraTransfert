@echo off
setlocal DisableDelayedExpansion
cd /d "%~dp0"
set "setup_mode="
if /I "%~1"=="--offline" set "setup_mode=--offline"
if not "%~1"=="" if /I not "%~1"=="--offline" (
  echo Option inconnue. Utilisez seulement --offline pour une preparation sans reseau.
  exit /b 1
)
if not "%~2"=="" exit /b 1
py -3 -c "import sys,tkinter; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 goto with_launcher
python -c "import sys,tkinter; assert sys.version_info >= (3,10)" >nul 2>&1
if not errorlevel 1 goto with_python
if defined setup_mode (
  echo Preparation hors ligne impossible : Python 3.10+ avec tkinter doit deja etre installe.
  pause
  exit /b 1
)
where winget >nul 2>&1
if errorlevel 1 (
  echo Python 3.10+ avec tkinter est requis. Installez Python depuis python.org puis relancez Installer_Windows.bat.
  pause
  exit /b 1
)
winget install --exact --id Python.Python.3.13 --source winget --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto fail
echo Python installe. Fermez cette fenetre puis relancez Installer_Windows.bat.
pause
exit /b 0
:with_launcher
py -3 prepare_installation.py %setup_mode%
if errorlevel 1 goto fail
goto launch
:with_python
python prepare_installation.py %setup_mode%
if errorlevel 1 goto fail
:launch
call Lancer_UltraTransfert.bat
exit /b
:fail
echo Preparation non terminee. Verifiez la connexion Internet et les erreurs ci-dessus.
echo Les transferts locaux restent utilisables avec Python et tkinter sans le complement de partage.
pause
exit /b 1
