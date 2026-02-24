@echo off
title Brave - Instancja 2 (port 9223)

echo ╔══════════════════════════════════════════╗
echo ║  INSTANCJA 2  ^|  Port 9223  ^|  Konto 2  ║
echo ╚══════════════════════════════════════════╝
echo.

:: WAŻNE: Instancja 2 MUSI mieć osobny folder user-data-dir!
:: Nie można uruchomić dwóch Brave z tym samym folderem profilu.
:: Ten folder zostanie automatycznie utworzony przy pierwszym uruchomieniu.
:: Zaloguj się tam na drugie konto Margonem.
set "USER_DATA_2=C:\Users\Nowy uzytkownik\AppData\Local\BraveSoftware\Brave-Browser-Bot2\User Data"

start "" "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe" ^
    --remote-debugging-port=9223 ^
    --user-data-dir="%USER_DATA_2%" ^
    --profile-directory="Default" ^
    --disable-blink-features=AutomationControlled ^
    --disable-backgrounding-occluded-windows ^
    --disable-background-timer-throttling ^
    --disable-renderer-backgrounding ^
    --disable-features=CalculateNativeWinOcclusion ^
    --disable-hang-monitor ^
    --disable-ipc-flooding-protection ^
    --disable-client-side-phishing-detection ^
    --no-first-run ^
    --no-default-browser-check ^
    --disable-popup-blocking ^
    --disable-infobars ^
    --start-maximized ^
    --log-level=3 ^
    --window-size=1920,1080 ^
    "https://jaruna.margonem.pl/"

echo [INFO] Czekam na port 9223...
timeout /t 4 /nobreak >nul
netstat -ano | findstr ":9223 " >nul 2>&1
if %errorlevel% == 0 (echo [OK] Instancja 2 gotowa!) else (echo [INFO] Port 9223 jeszcze nie gotowy.)
echo.
echo UWAGA: Jesli to pierwsze uruchomienie instancji 2,
echo zaloguj sie na drugie konto Margonem w tym oknie Brave.
echo.
pause
