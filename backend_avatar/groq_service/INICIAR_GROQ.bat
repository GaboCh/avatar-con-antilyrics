@echo off
echo 🚀 Iniciando Servicio de Groq para Avatar...
cd /d "%~dp0"
call ..\entorno\Scripts\activate.bat
python app.py
pause
