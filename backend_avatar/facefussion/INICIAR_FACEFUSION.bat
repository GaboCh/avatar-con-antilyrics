@echo off
echo 🎭 Iniciando Servicio de FaceFusion (FaceSwap)...
cd /d "%~dp0"
call ..\entorno\Scripts\activate.bat
python app.py
pause
