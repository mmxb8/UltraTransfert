@echo off
setlocal
cd /d "%~dp0"
if not exist reports mkdir reports
py -3 -m venv .venv-build
if errorlevel 1 goto fail
".venv-build\Scripts\python.exe" -m pip install -r requirements-windows-build.txt
if errorlevel 1 goto fail
".venv-build\Scripts\python.exe" -m pip freeze > reports\windows-build-dependencies.txt
".venv-build\Scripts\python.exe" build_windows.py > reports\windows-portable-build.log 2>&1
if errorlevel 1 goto fail
echo Paquet portable construit et controle dans dist.
echo Le controle ne remplace pas les essais manuels Windows et RDP.
pause
exit /b 0
:fail
echo Construction echouee. Aucun nouveau paquet valide n'est annonce.
echo Consultez reports\windows-portable-build.log et les messages ci-dessus.
pause
exit /b 1
