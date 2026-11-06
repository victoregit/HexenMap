@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0GenshinOverlay.exe" (
    start "" "%~dp0GenshinOverlay.exe" %*
) else (
    echo Executavel nao encontrado. Execute: python scripts/build_exe.py
    pause
)
