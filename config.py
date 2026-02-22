"""
config.py — stałe oraz klasa BotConfig (wspólny stan między GUI a wątkiem bota)
"""
import threading
import json
import os
import time
import random

# ── Stałe (nie zmieniane z GUI) ─────────────────────────────────────────────────
REMOTE_DEBUG_PORT = 9222
LOOP_INTERVAL     = 1.0
WALK_TIMEOUT      = 30
STUCK_THRESHOLD   = 3
UNSTUCK_RETRIES   = 3
BATTLE_TIMEOUT    = 60
AFTER_BATTLE_WAIT = 0.5 
MAP_CHANGE_WAIT   = 3
NO_MOB_RETRIES    = 3
SETTINGS_FILE     = "settings.json"

# ── Pomocnicze funkcje czasu (Gauss) ──────────────────────────────────────
def gauss_sleep(mu, sigma):
    """Opóźnienie oparte na rozkładzie Gaussa dla bardziej ludzkich przerw."""
    delay = random.gauss(mu, sigma)
    time.sleep(max(0.1, delay))

def rsleep_range(lo, hi):
    """Zwykłe losowe opóźnienie w zakresie."""
    time.sleep(random.uniform(lo, hi))

def rsleep(base, variance=0.2):
    """Opóźnienie bazowe + wariancja"""
    time.sleep(max(0.1, base + random.uniform(-variance, variance)))

# ══════════════════════════════════════════════════════════════════════════════════
#  BotConfig
# ══════════════════════════════════════════════════════════════════════════════════
class BotConfig:
    def __init__(self):
        self._lock = threading.Lock()

        self._min_lvl = 1
        self._max_lvl = 300
        self._min_group = 1
        self._max_group = 10
        self._map_keywords = []

        self.map_timers = {}

        self.running     = True
        self.paused      = False
        self.kills       = 0
        self.status      = "Oczekiwanie…"
        self.current_map = ""
        self.deaths      = 0

        self.restock_enabled       = False
        self.restock_teleport      = "Zwój teleportacji na Kwieciste Przejście"
        self.restock_npc           = "Tunia Frupotius"
        self.restock_shop_map      = "Dom Tunii"
        self.restock_sell_sequence = "1,1,2"
        self._restock_in_progress  = False

        self.restock_return_method    = "npc_teleport"
        self.restock_return_scroll    = "Góralski pergamin"
        self.restock_return_walk_path = ""

        self.npc_teleport_npc_name    = "Zakonnik Planu Astralnego"
        self.npc_teleport_npc_map     = "Straż Thuzal"
        self.npc_teleport_city        = "Ithan"
        self.npc_teleport_walk_to_npc = ""
        self.npc_teleport_after_path  = ""
        self._npc_teleport_in_progress = False
        self._npc_teleport_pending     = False

        self.death_return_path = ""
        self.discord_enabled = False
        self.discord_webhook_url = ""

    def update_map_timer(self, map_name):
        if not map_name: return
        with self._lock:
            self.map_timers[map_name] = time.time()

    def get_map_last_visit(self, map_name):
        with self._lock:
            for key, val in self.map_timers.items():
                if map_name in key or key in map_name:
                    return val
            return 0.0

    @property
    def min_lvl(self):
        with self._lock: return self._min_lvl
    @min_lvl.setter
    def min_lvl(self, v):
        with self._lock: self._min_lvl = int(v)

    @property
    def max_lvl(self):
        with self._lock: return self._max_lvl
    @max_lvl.setter
    def max_lvl(self, v):
        with self._lock: self._max_lvl = int(v)

    @property
    def min_group(self):
        with self._lock: return self._min_group
    @min_group.setter
    def min_group(self, v):
        with self._lock: self._min_group = int(v)

    @property
    def max_group(self):
        with self._lock: return self._max_group
    @max_group.setter
    def max_group(self, v):
        with self._lock: self._max_group = int(v)

    @property
    def map_keywords(self):
        with self._lock: return list(self._map_keywords)
    @map_keywords.setter
    def map_keywords(self, v):
        with self._lock: self._map_keywords = list(v)

    def save(self):
        data = {
            "min_lvl": self._min_lvl, "max_lvl": self._max_lvl,
            "min_group": self._min_group, "max_group": self._max_group,
            "map_keywords": self._map_keywords,
            "restock_enabled": self.restock_enabled,
            "restock_teleport": self.restock_teleport,
            "restock_npc": self.restock_npc,
            "restock_shop_map": self.restock_shop_map,
            "restock_sell_sequence": self.restock_sell_sequence,
            "restock_return_method": self.restock_return_method,
            "restock_return_scroll": self.restock_return_scroll,
            "restock_return_walk_path": self.restock_return_walk_path,
            "npc_teleport_npc_name": self.npc_teleport_npc_name,
            "npc_teleport_npc_map": self.npc_teleport_npc_map,
            "npc_teleport_city": self.npc_teleport_city,
            "npc_teleport_walk_to_npc": self.npc_teleport_walk_to_npc,
            "npc_teleport_after_path": self.npc_teleport_after_path,
            "death_return_path": self.death_return_path,
            "discord_enabled": self.discord_enabled,
            "discord_webhook_url": self.discord_webhook_url,
        }
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisu ustawień: {e}")

    def load(self):
        if not os.path.exists(SETTINGS_FILE): return
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            self._min_lvl = data.get("min_lvl", 1)
            self._max_lvl = data.get("max_lvl", 300)
            self._min_group = data.get("min_group", 1)
            self._max_group = data.get("max_group", 10)
            self._map_keywords = data.get("map_keywords", [])
            self.restock_enabled = data.get("restock_enabled", False)
            self.restock_teleport = data.get("restock_teleport", "")
            self.restock_npc = data.get("restock_npc", "")
            self.restock_shop_map = data.get("restock_shop_map", "")
            self.restock_sell_sequence = data.get("restock_sell_sequence", "1,1,2")
            self.restock_return_method = data.get("restock_return_method", "npc_teleport")
            self.restock_return_scroll = data.get("restock_return_scroll", "")
            self.restock_return_walk_path = data.get("restock_return_walk_path", "")
            self.npc_teleport_npc_name = data.get("npc_teleport_npc_name", "Zakonnik Planu Astralnego")
            self.npc_teleport_npc_map = data.get("npc_teleport_npc_map", "Straż Thuzal")
            self.npc_teleport_city = data.get("npc_teleport_city", "Ithan")
            self.npc_teleport_walk_to_npc = data.get("npc_teleport_walk_to_npc", "")
            self.npc_teleport_after_path = data.get("npc_teleport_after_path", "")
            self.death_return_path = data.get("death_return_path", "")
            self.discord_enabled = data.get("discord_enabled", False)
            self.discord_webhook_url = data.get("discord_webhook_url", "")
        except Exception as e:
            print(f"Błąd odczytu ustawień: {e}")