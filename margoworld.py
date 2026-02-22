"""
margoworld.py — pobieranie danych z margoworld.pl
"""
import urllib.request, ssl, re

MARGOWORLD_BASE       = "https://margoworld.pl"
MARGOWORLD_EXP        = MARGOWORLD_BASE + "/npc/exp"
MARGOWORLD_WORLD_LIST = MARGOWORLD_BASE + "/world/list"

_world_map_cache: list = []

def _fetch_html(url: str) -> str:
    try: ctx = ssl.create_default_context()
    except: ctx = ssl._create_unverified_context()
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
    with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="replace")

def fetch_expowiska_list() -> list:
    html = _fetch_html(MARGOWORLD_EXP)
    pattern = r'href="(/tags/view/exp-[^"]+)"[^>]*>\s*([^<]+?)\s*</a>'
    results, seen = [], set()
    for m in re.finditer(pattern, html):
        path, text = m.group(1), m.group(2).strip()
        if path in seen: continue
        seen.add(path)
        lvl_m = re.search(r'\((\d+)\s*lvl\)', text)
        results.append({"name": text, "level": int(lvl_m.group(1)) if lvl_m else 0, "url": MARGOWORLD_BASE + path, "slug": path.split("/")[-1]})
    results.sort(key=lambda x: x["level"])
    return results

def fetch_expowisko_details(url: str) -> dict:
    html = _fetch_html(url)
    maps = []
    for m in re.finditer(r'href="/world/view/[^"]*"[^>]*>\s*([^<]+?)\s*</a>', html):
        name = m.group(1).strip()
        if name and name not in maps: maps.append(name)
    mobs, mob_levels = [], []
    for m in re.finditer(r'/npc/view/\d+/(.+?)-(\d+)lvl', html):
        lvl = int(m.group(2))
        mobs.append({"name": m.group(1).replace('-', ' ').title(), "lvl": lvl})
        mob_levels.append(lvl)
    return {"maps": maps, "min_lvl": min(mob_levels) if mob_levels else 0, "max_lvl": max(mob_levels) if mob_levels else 0, "mobs": mobs}

def fetch_world_map_list(force: bool = False) -> list:
    global _world_map_cache
    if _world_map_cache and not force: return _world_map_cache
    html = _fetch_html(MARGOWORLD_WORLD_LIST)
    results, seen = [], set()
    for m in re.finditer(r'href="/world/view/(\d+)/([^"]+)"[^>]*>\s*([^<]+?)\s*</a>', html):
        name = m.group(3).strip()
        if name in seen: continue
        seen.add(name)
        map_id = int(m.group(1))
        results.append({"name": name, "map_id": map_id, "url": MARGOWORLD_BASE + f"/world/view/{map_id}/{m.group(2)}"})
    results.sort(key=lambda x: x["name"].lower())
    _world_map_cache = results
    return results

def search_world_maps(query: str, limit: int = 200) -> list:
    maps = _world_map_cache if _world_map_cache else fetch_world_map_list()
    q = query.lower().strip()
    if not q: return maps[:limit]
    starts = [m for m in maps if m["name"].lower().startswith(q)]
    contains = [m for m in maps if q in m["name"].lower() and not m["name"].lower().startswith(q)]
    return (starts + contains)[:limit]