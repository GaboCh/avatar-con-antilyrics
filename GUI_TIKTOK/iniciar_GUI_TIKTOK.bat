@echo off
chcp 65001 >nul
setlocal

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "AVATAR=%ROOT%\.."
set "PYTHON=%AVATAR%\entorno\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [ERROR] No se encontro el entorno virtual.
    echo         Ejecuta primero: instalar.bat
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   GUI TIKTOK - TikTok Favoritos ^> Anticopyright ^> YouTube
echo ============================================================
echo.
"%PYTHON%" "%ROOT%\scripts\tiktok_youtube_gui.py"
pause
