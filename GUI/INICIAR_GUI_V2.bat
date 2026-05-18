@echo off
echo 🚀 Iniciando Interfaz Automática V2 (con TikTok)...
cd /d "%~dp0"
:: Subimos un nivel para encontrar el entorno virtual
call ..\entorno\Scripts\activate.bat
:: Ejecutamos el script que está en la carpeta scripts
python scripts\auto_swap_gui_v2.py
pause
