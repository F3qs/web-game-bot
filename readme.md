# 🗡️ Web Game Bot (Margonem)

Profesjonalny, zautomatyzowany bot do gry przeglądarkowej stworzony w języku Python. Wykorzystuje `selenium-stealth` w celu omijania detekcji oraz posiada nowoczesny, czytelny interfejs graficzny (GUI) zbudowany z użyciem biblioteki `customtkinter`.

## ✨ Główne funkcje

- **🤖 Inteligentny Pathfinding:** Wykorzystanie algorytmu BFS do omijania przeszkód i optymalnego poruszania się po mapie.
- **🛡️ Moduł Anty-Captcha:** Automatyczne wykrywanie zabezpieczeń i rozwiązywanie captchy w grze z zachowaniem ludzkich opóźnień.
- **🏃 Humanizacja ruchów:** Symulacja "ludzkiego" zachowania myszki (mikrodrgania, losowy offset) w celu ominięcia zabezpieczeń anty-bot.
- **🛒 Zaawansowany Auto-Restock:** System automatycznego powrotu do miasta po zapełnieniu toreb, sprzedaży u wybranego NPC i powrotu na łowisko (obsługa Zwojów, Zakonnika Planu Astralnego oraz chodzenia pieszego).
- **🗺️ Integracja z MargoWorld:** Bezpośrednie pobieranie danych o mapach, expowiskach i poziomach potworów z poziomu interfejsu GUI.
- **💬 Powiadomienia Discord:** Opcjonalne alerty o statusie bota (np. o zgonie postaci, powrotach czy napotkaniu captchy) wysyłane bezpośrednio na serwer Discord przez Webhook.

## 🛠️ Wymagania

- [Python 3.8+](https://www.python.org/downloads/)
- Przeglądarka Google Chrome

## 🚀 Instalacja

1. Sklonuj repozytorium na swój dysk:
   ```bash
   git clone https://github.com/F3qs/web-game-bot.git
   cd web-game-bot