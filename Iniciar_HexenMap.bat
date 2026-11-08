@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0HexenMap.exe" (
    start "" "%~dp0HexenMap.exe" %*
) else (
    echo Executavel nao encontrado. Execute: python scripts/build_exe.py
    pause
)
