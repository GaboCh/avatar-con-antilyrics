@echo off
echo 🤖 Iniciando Servicio de LLM (Original)...
cd /d "%~dp0"
call ..\entorno\Scripts\activate.bat
python app.py
pause
