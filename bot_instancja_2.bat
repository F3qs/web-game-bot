@echo off
title Bot - Instancja 2 (port 9223 / settings_2.json)

echo ╔══════════════════════════════════════════════════════╗
echo ║  BOT INSTANCJA 2  ^|  Port: 9223  ^|  settings_2.json ║
echo ╚══════════════════════════════════════════════════════╝
echo.

:: Sprawdź czy Brave na porcie 9223 jest uruchomiony
netstat -ano | findstr ":9223 " >nul 2>&1
if %errorlevel% neq 0 (
    echo [BLAD] Brave na porcie 9223 nie jest uruchomiony!
    echo Najpierw uruchom: brave_instancja_2.bat
    echo.
    pause
    exit /b 1
)
echo [OK] Brave na porcie 9223 - gotowy.
echo.

:: Sprawdź czy settings_2.json istnieje
if not exist "%~dp0settings_2.json" (
    echo [BLAD] Nie znaleziono pliku settings_2.json!
    echo Skopiuj settings.json jako settings_2.json i skonfiguruj druga instancje.
    pause
    exit /b 1
)
echo [OK] settings_2.json - znaleziony.
echo.

:: Przejdź do folderu ze skryptami
cd /d "%~dp0"

:: Uruchom bota instancja 2
python main.py --instance 2
if %errorlevel% neq 0 (
    echo.
    echo [BLAD] Bot zakonczyl sie z bledem. Sprawdz powyzszy log.
)
pause
