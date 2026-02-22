import requests
import json

def send_discord_notification(webhook_url, message, title="Powiadomienie Bota", color=0x1f8b4c):
    if not webhook_url: return
    data = {"embeds": [{"title": title, "description": message, "color": color, "footer": {"text": "Margonem Bot"}}]}
    try:
        result = requests.post(webhook_url, data=json.dumps(data), headers={"Content-Type": "application/json"})
        result.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[Discord] Błąd: {e}")