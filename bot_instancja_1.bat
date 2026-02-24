@echo off
title Bot - Instancja 1 (port 9222 / settings.json)

echo ╔════════════════════════════════════════════════════╗
echo ║  BOT INSTANCJA 1  ^|  Port: 9222  ^|  settings.json ║
echo ╚════════════════════════════════════════════════════╝
echo.

:: Sprawdź czy Chrome na porcie 9222 jest uruchomiony
netstat -ano | findstr ":9222 " >nul 2>&1
if %errorlevel% neq 0 (
    echo [BLAD] Brave na porcie 9222 nie jest uruchomiony!
    echo Najpierw uruchom: Chrome_instancja_1.bat
    echo.
    pause
    exit /b 1
)
echo [OK] Chrome na porcie 9222 - gotowy.
echo.

:: Przejdź do folderu ze skryptami (tam gdzie jest main.py)
cd /d "%~dp0"

:: Uruchom bota instancja 1
python main.py --instance 1
if %errorlevel% neq 0 (
    echo.
    echo [BLAD] Bot zakonczyl sie z bledem. Sprawdz powyzszy log.
)
pause
