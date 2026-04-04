@echo off
:: Pedir permisos de administrador automáticamente
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Solicitando permisos de administrador...
    powershell -Command "Start-Process '%~f0' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"
echo Iniciando StreamMuter...
python stream_muter.py
pause
