@echo off
setlocal DisableDelayedExpansion
call "%~dp0Installer_Windows.bat" --offline
exit /b %errorlevel%
