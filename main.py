"""
main.py — punkt startowy bota Margonem
"""
from config import BotConfig
from gui    import BotGUI, HAS_KEYBOARD

if __name__ == "__main__":
    config = BotConfig()
    config.load()
    gui = BotGUI(config)

    if not HAS_KEYBOARD:
        gui.log("UWAGA: Brak biblioteki 'keyboard' — hotkey F6 nie działa.")
    else:
        gui.log(f"Hotkey {BotGUI.HOTKEY} → pokaż / ukryj okno.")

    gui.log("Wczytano ustawienia. Kliknij ▶ Start aby uruchomić bota.\n")
    gui.run()