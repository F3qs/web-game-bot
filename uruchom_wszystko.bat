@echo off
title Margonem Bot - Uruchom WSZYSTKO
cd /d "%~dp0"

echo ╔══════════════════════════════════════════════════════════╗
echo ║          MARGONEM BOT — URUCHAMIANIE OBUINSTANCJI        ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
echo Ten skrypt uruchomi:
echo   1. Brave instancja 1 (port 9222)
echo   2. Brave instancja 2 (port 9223)
echo   3. Bot instancja 1
echo   4. Bot instancja 2
echo.
echo UWAGA: Obydwa konta Margonem musza byc juz zalogowane
echo w swoich profilach Brave!
echo.
choice /C TN /M "Kontynuowac? (T=Tak / N=Anuluj)"
if errorlevel 2 exit /b 0

echo.
echo [KROK 1/4] Uruchamiam Brave - Instancja 1 (port 9222)...
start "" "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" ^
    --remote-debugging-port=9222 ^
    --user-data-dir="C:\Users\Nowy uzytkownik\AppData\Local\BraveSoftware\Brave-Browser\User Data" ^
    --profile-directory="Default" ^
    --disable-blink-features=AutomationControlled ^
    --disable-backgrounding-occluded-windows ^
    --disable-background-timer-throttling ^
    --disable-renderer-backgrounding ^
    --disable-features=CalculateNativeWinOcclusion ^
    --disable-hang-monitor ^
    --no-first-run --no-default-browser-check ^
    --disable-popup-blocking --disable-infobars ^
    --log-level=3 ^
    "https://jaruna.margonem.pl/"

echo [KROK 2/4] Uruchamiam Brave - Instancja 2 (port 9223)...
start "" "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" ^
    --remote-debugging-port=9223 ^
    --user-data-dir="C:\Users\Nowy uzytkownik\AppData\Local\BraveSoftware\Brave-Browser-Bot2\User Data" ^
    --profile-directory="Default" ^
    --disable-blink-features=AutomationControlled ^
    --disable-backgrounding-occluded-windows ^
    --disable-background-timer-throttling ^
    --disable-renderer-backgrounding ^
    --disable-features=CalculateNativeWinOcclusion ^
    --disable-hang-monitor ^
    --no-first-run --no-default-browser-check ^
    --disable-popup-blocking --disable-infobars ^
    --log-level=3 ^
    "https://jaruna.margonem.pl/"

echo.
echo [INFO] Czekam 6 sekund az oba Brave sie zaladuja...
timeout /t 6 /nobreak >nul

:: Weryfikacja portów
set "OK1=0" & set "OK2=0"
netstat -ano | findstr ":9222 " >nul 2>&1 && set "OK1=1"
netstat -ano | findstr ":9223 " >nul 2>&1 && set "OK2=1"

if "%OK1%"=="1" (echo [OK] Port 9222 aktywny) else (echo [UWAGA] Port 9222 nie odpowiada!)
if "%OK2%"=="1" (echo [OK] Port 9223 aktywny) else (echo [UWAGA] Port 9223 nie odpowiada!)
echo.

echo [KROK 3/4] Uruchamiam Bot - Instancja 1...
start "Bot Instancja 1" cmd /k "cd /d "%~dp0" && python main.py --instance 1"

timeout /t 2 /nobreak >nul

echo [KROK 4/4] Uruchamiam Bot - Instancja 2...
start "Bot Instancja 2" cmd /k "cd /d "%~dp0" && python main.py --instance 2"

echo.
echo ╔══════════════════════════════════════════════════════════╗
echo ║  Gotowe! Oba boty uruchomione w osobnych oknach.        ║
echo ║  Instancja 1: F6  ^|  Instancja 2: F7  (ukryj/pokaz)   ║
echo ╚══════════════════════════════════════════════════════════╝
echo.
pause
