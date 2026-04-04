@echo off
echo ========================================
echo   StreamMuter - Instalador
echo ========================================
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python no encontrado.
    echo Descargalo en https://python.org y asegurate de marcar "Add to PATH"
    pause
    exit /b 1
)

echo [OK] Python encontrado
echo.
echo Instalando dependencias...
echo.

pip install pycaw keyboard pystray Pillow comtypes obsws-python win10toast

echo.
echo ========================================
echo   Instalacion completada!
echo ========================================
echo.
echo Ahora edita config.json con:
echo   - El .exe de tu juego
echo   - Tu hotkey preferida (default: F9)
echo   - Configuracion de OBS si la necesitas
echo.
echo Para correr: ejecuta START.bat (como Administrador)
echo.
pause
