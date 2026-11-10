@echo off
setlocal
set "PYINSTALLER_RESET_ENVIRONMENT=1"
start "" /D "%~dp0" "%~dp0HexenMapLauncher.exe"
endlocal
