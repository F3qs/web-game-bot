import time, random, traceback, re
from selenium_stealth import stealth
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import (
    JavascriptException, WebDriverException,
    InvalidSessionIdException, NoSuchWindowException,
)

from config import (
    REMOTE_DEBUG_PORT, WALK_TIMEOUT, STUCK_THRESHOLD,
    UNSTUCK_RETRIES, BATTLE_TIMEOUT, MAP_CHANGE_WAIT,
    rsleep, rsleep_range, gauss_sleep
)

GAME_SERVER_URL = "jaruna.margonem.pl" 

# ══════════════════════════════════════════════════════════════════════════════════
#  Połączenie i Nawigacja z Selenium-Stealth
# ══════════════════════════════════════════════════════════════════════════════════

def connect():
    global GAME_SERVER_URL
    opts = Options()
    opts.add_experimental_option("debuggerAddress", f"127.0.0.1:{REMOTE_DEBUG_PORT}")
    
    drv = webdriver.Chrome(options=opts)
    
    # Aplikowanie stealth (maskowanie automatyzacji)
    stealth(drv,
        languages=["pl-PL", "pl"],
        vendor="Google Inc.",
        platform="Win32",
        webgl_vendor="Intel Inc.",
        renderer="Intel Iris OpenGL Engine",
        fix_hairline=True,
    )

    game_handle = None
    for handle in drv.window_handles:
        drv.switch_to.window(handle)
        if "margonem.pl" in drv.current_url and "www." not in drv.current_url:
            game_handle = handle
            import urllib.parse
            GAME_SERVER_URL = urllib.parse.urlparse(drv.current_url).netloc
            break
    if game_handle:
        drv.switch_to.window(game_handle)
    
    print("Zastosowano kamuflaż (selenium-stealth).")
    return drv

def go_to_homepage(driver):
    try: driver.get("https://www.margonem.pl/")
    except: pass

def return_to_game(driver):
    try:
        if GAME_SERVER_URL not in driver.current_url:
            driver.get(f"https://{GAME_SERVER_URL}/")
    except: pass


# ══════════════════════════════════════════════════════════════════════════════════
#  Humanizacja myszy
# ══════════════════════════════════════════════════════════════════════════════════

def human_move_and_click(driver, element):
    """Uhumanizowane kliknięcie: mikro-ruchy + losowy punkt + opóźnienie."""
    try:
        action = ActionChains(driver)
        
        # 1. Symulacja mikrodrgań i "szukania" kursorem
        for _ in range(random.randint(1, 4)):
            action.move_by_offset(random.randint(-15, 15), random.randint(-15, 15))
            action.pause(random.uniform(0.01, 0.05))
            
        # 2. Skierowanie się na element (środek)
        action.move_to_element(element)
        
        # 3. Dodanie losowego offsetu wewnątrz wymiarów elementu
        width = element.size.get('width', 10)
        height = element.size.get('height', 10)
        off_x = random.randint( -width//3, width//3 )
        off_y = random.randint( -height//3, height//3 )
        action.move_by_offset(off_x, off_y)
        
        # 4. Przerwa na "zdecydowanie się" na klik
        action.pause(random.uniform(0.1, 0.35))
        action.click().perform()
    except Exception as e:
        # Fallback
        try: element.click()
        except: pass


# ══════════════════════════════════════════════════════════════════════════════════
#  JS helpers & Game Info
# ══════════════════════════════════════════════════════════════════════════════════

def safe_js(driver, script, *args, default=None):
    for _ in range(10):
        try: return driver.execute_script(script, *args)
        except (JavascriptException, WebDriverException): gauss_sleep(0.5, 0.1)
        except (InvalidSessionIdException, NoSuchWindowException): raise
    return default

def wait_for_game_ready(driver, timeout=30):
    for _ in range(timeout):
        ready = safe_js(driver, "return (typeof Engine !== 'undefined' && Engine.hero && Engine.hero.d && Engine.map && Engine.map.d && Engine.map.d.name) ? true : false;", default=False)
        if ready: return True
        time.sleep(1)
    return False

def unlock_movement(driver):
    safe_js(driver, "try { Engine.hero.stop = false; } catch(e) {}")

def get_hero_pos(driver):
    return safe_js(driver, "return {x: Engine.hero.d.x, y: Engine.hero.d.y};", default={'x': -1, 'y': -1})

def get_current_map(driver):
    return safe_js(driver, "return Engine.map.d.name;", default="")

def check_for_death(driver):
    return safe_js(driver, """
        var el = document.querySelector('.dazed-time');
        if (!el || el.offsetParent === null) return null;
        var text = el.textContent.trim();
        if (!text) return null;
        var mins = 0, secs = 0;
        var mMatch = text.match(/(\\d+)\\s*min/);
        var sMatch = text.match(/(\\d+)\\s*s/);
        if (mMatch) mins = parseInt(mMatch[1]);
        if (sMatch) secs = parseInt(sMatch[1]);
        if (mins === 0 && secs === 0) return null;
        return (mins * 60) + secs;
    """)

# ══════════════════════════════════════════════════════════════════════════════════
#  Pathfinding (BFS)
# ══════════════════════════════════════════════════════════════════════════════════

def bfs_distance(driver, sx, sy, tx, ty, max_steps=200):
    return safe_js(driver, """
        var sx = arguments[0], sy = arguments[1], tx = arguments[2], ty = arguments[3], maxSteps = arguments[4];
        if (sx === tx && sy === ty) return 0;
        var md = Engine.map.d, w = md.x, h = md.y;
        var col = (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.Collision) ? Gargonem.Core.Collision.getCols() : null;
        if (!col) return Math.abs(tx - sx) + Math.abs(ty - sy);
        var key = function(x, y) { return y * w + x; };
        var visited = {}; visited[key(sx, sy)] = true;
        var queue = [{x: sx, y: sy, d: 0}]; var head = 0;
        var dirs = [[-1,0],[1,0],[0,-1],[0,1]];
        while (head < queue.length) {
            var cur = queue[head++];
            if (cur.d >= maxSteps) break;
            for (var i = 0; i < dirs.length; i++) {
                var nx = cur.x + dirs[i][0], ny = cur.y + dirs[i][1];
                if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                var k = key(nx, ny);
                if (visited[k]) continue;
                var idx = ny * w + nx;
                if (nx === tx && ny === ty) return cur.d + 1;
                if (idx < 0 || idx >= col.length || col[idx] !== '0') continue;
                visited[k] = true; queue.push({x: nx, y: ny, d: cur.d + 1});
            }
        }
        return -1;
    """, sx, sy, tx, ty, max_steps, default=-1)

def find_walkable_neighbors(driver, cx, cy, radius=3):
    return safe_js(driver, """
        var cx = arguments[0], cy = arguments[1], r = arguments[2];
        var md = Engine.map.d; var w = md.x, h = md.y;
        var col = (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.Collision) ? Gargonem.Core.Collision.getCols() : null;
        if (!col) return [];
        var npcs = (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.Npc) ? Gargonem.Core.Npc.getAll() : {};
        var res = [];
        for (var dy = -r; dy <= r; dy++) {
            for (var dx = -r; dx <= r; dx++) {
                if (dx === 0 && dy === 0) continue;
                var nx = cx + dx, ny = cy + dy;
                if (nx < 0 || ny < 0 || nx >= w || ny >= h) continue;
                var idx = ny * w + nx;
                if (idx >= 0 && idx < col.length && col[idx] === '0') {
                    var blocked = false;
                    for (var nid in npcs) { var nn = npcs[nid]; if (nn.x === nx && nn.y === ny) { blocked = true; break; } }
                    if (!blocked) res.push({x: nx, y: ny, dist: Math.abs(dx) + Math.abs(dy)});
                }
            }
        }
        res.sort(function(a, b) { return a.dist - b.dist; });
        return res;
    """, cx, cy, radius, default=[])

def walk_to(driver, x, y):
    unlock_movement(driver)
    safe_js(driver, """
        if (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.GoTo) {
            Gargonem.Core.GoTo.goTo(arguments[0], arguments[1]);
        } else { Engine.hero.autoGoTo({x: arguments[0], y: arguments[1]}); }
    """, x, y)

def _quick_captcha_visible(driver):
    try:
        return driver.execute_script("""
            var pres = document.querySelectorAll('.pre-captcha');
            for (var i = 0; i < pres.length; i++) { if (pres[i].children.length > 0) return true; }
            var cws = document.querySelectorAll('.captcha-window');
            for (var j = 0; j < cws.length; j++) {
                var s = window.getComputedStyle(cws[j]);
                if (s.display !== 'none' && s.visibility !== 'hidden') return true;
            }
            return false;
        """)
    except Exception: return False

def smart_walk_to(driver, target_x, target_y, timeout=WALK_TIMEOUT, gui=None, check_fn=None):
    from captcha import check_and_solve_captcha
    walk_to(driver, target_x, target_y)
    last_x, last_y = -999, -999
    stuck_ticks, unstuck_attempts = 0, 0

    for _ in range(timeout + UNSTUCK_RETRIES * 4):
        time.sleep(1)
        unlock_movement(driver)

        if _quick_captcha_visible(driver):
            check_and_solve_captcha(driver, gui)
            walk_to(driver, target_x, target_y)

        if check_fn:
            result = check_fn(driver)
            if result == 'arrived': return True
            if result == 'abort': return False

        pos = get_hero_pos(driver)
        hx, hy = pos['x'], pos['y']

        if abs(hx - target_x) + abs(hy - target_y) <= 1: return True
        if hx == last_x and hy == last_y: stuck_ticks += 1
        else: stuck_ticks = 0
        last_x, last_y = hx, hy

        if stuck_ticks >= STUCK_THRESHOLD:
            unstuck_attempts += 1
            if unstuck_attempts > UNSTUCK_RETRIES: return False
            neighbors = find_walkable_neighbors(driver, hx, hy, radius=4)
            picked = None
            if neighbors:
                best_score = 99999
                for n in neighbors[:12]:
                    score = abs(n['x'] - target_x) + abs(n['y'] - target_y)
                    if score < best_score: best_score = score; picked = n
            if picked:
                walk_to(driver, picked['x'], picked['y'])
                for _ in range(5):
                    time.sleep(1)
                    p2 = get_hero_pos(driver)
                    if abs(p2['x'] - picked['x']) + abs(p2['y'] - picked['y']) <= 1: break
                walk_to(driver, target_x, target_y)
            else:
                rx, ry = hx + random.choice([-2, -1, 1, 2]), hy + random.choice([-2, -1, 1, 2])
                walk_to(driver, rx, ry)
                time.sleep(2)
                walk_to(driver, target_x, target_y)
            stuck_ticks = 0
    return False

# ══════════════════════════════════════════════════════════════════════════════════
#  Moby i walka
# ══════════════════════════════════════════════════════════════════════════════════

def find_nearest_mob(driver, min_lvl, max_lvl, min_group=1, max_group=10):
    candidates = safe_js(driver, """
        var minLvl = parseInt(arguments[0]), maxLvl = parseInt(arguments[1]);
        var minGrp = parseInt(arguments[2]), maxGrp = parseInt(arguments[3]);
        var hd = Engine.hero.d;
        var npcs = (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.Npc) ? Gargonem.Core.Npc.getAll() : {};
        function isMobAttackable(n) {
            if (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.Npc && Gargonem.Core.Npc.isAttackable) {
                return Gargonem.Core.Npc.isAttackable(n);
            }
            return (n.type == 2 || n.type == 3);
        }
        function getGroupId(n) {
            if (n.d && typeof n.d.grp !== 'undefined' && n.d.grp !== null) return parseInt(n.d.grp);
            if (typeof n.grp !== 'undefined' && n.grp !== null) return parseInt(n.grp);
            return 0;
        }
        var groupCounts = {};
        for (var id in npcs) {
            var n = npcs[id];
            var gid = getGroupId(n);
            if (!isNaN(gid) && gid > 0) {
                if (!groupCounts[gid]) groupCounts[gid] = 0;
                groupCounts[gid]++;
            }
        }
        var result = [];
        for (var id in npcs) {
            var n = npcs[id];
            if (!isMobAttackable(n)) continue;
            var mobLvl = parseInt(n.lvl);
            if (isNaN(mobLvl)) continue;
            if (mobLvl < minLvl || mobLvl > maxLvl) continue;
            var currentGroupSize = 1;
            var gid = getGroupId(n);
            if (!isNaN(gid) && gid > 0 && groupCounts[gid]) { currentGroupSize = groupCounts[gid]; }
            if (currentGroupSize < minGrp || currentGroupSize > maxGrp) continue;
            result.push({
                id: id, nick: n.nick, lvl: mobLvl, grp: currentGroupSize, 
                x: n.x, y: n.y, mdist: Math.abs(n.x - hd.x) + Math.abs(n.y - hd.y)
            });
        }
        result.sort(function(a, b) { 
            if (a.mdist === b.mdist) return a.id - b.id;
            return a.mdist - b.mdist; 
        });
        return result.slice(0, 10);
    """, min_lvl, max_lvl, min_group, max_group, default=[])

    if not candidates: return None

    hero_pos = get_hero_pos(driver)
    hx, hy = hero_pos['x'], hero_pos['y']
    best, best_dist = None, 99999

    for mob in candidates:
        d = bfs_distance(driver, hx, hy, mob['x'], mob['y'], max_steps=200)
        if d == -1: continue
        if d < best_dist:
            best_dist = d
            best = mob
            best['dist'] = d
    return best

def attack_mob(driver, mob_id):
    """Próba fizycznego ataku, w razie błędu fallback do wywołania JS."""
    unlock_movement(driver)
    try:
        # Próba znalezienia grafiki potwora
        mob_el = driver.find_element(By.ID, f"npc-{mob_id}")
        if mob_el.is_displayed():
            human_move_and_click(driver, mob_el)
            return
    except:
        pass
    
    # Bezpieczniejszy fallback, jeśli mob był częściowo poza ekranem
    safe_js(driver, '_g("fight&a=attack&id=-" + arguments[0] + "&ff=1");', mob_id)

def mob_exists(driver, mob_id):
    return safe_js(driver, "if (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.Npc) { return !!Gargonem.Core.Npc.getByID(arguments[0]); } return false;", mob_id, default=False)

def get_distance_to_mob(driver, mob_id):
    return safe_js(driver, "var m = (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.Npc) ? Gargonem.Core.Npc.getByID(arguments[0]) : null; if (!m) return -1; var hd = Engine.hero.d; return Math.abs(m.x - hd.x) + Math.abs(m.y - hd.y);", mob_id, default=-1)

def is_in_battle(driver):
    return safe_js(driver, "if (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.Fight) { return !!Gargonem.Core.Fight.isActive(); } return false;", default=False)

def wait_for_battle_end(driver, timeout=BATTLE_TIMEOUT, gui=None):
    from captcha import check_and_solve_captcha
    for _ in range(timeout):
        if not is_in_battle(driver): return True
        if _quick_captcha_visible(driver):
            check_and_solve_captcha(driver, gui)
        time.sleep(1)
    return False

# ══════════════════════════════════════════════════════════════════════════════════
#  Portale / Zmiana mapy i NPC Helpers
# ══════════════════════════════════════════════════════════════════════════════════

def find_portal_to_next_map(driver, keywords):
    portals = safe_js(driver, """
        var keywords = arguments[0];
        var currentMap = Engine.map.d.name;
        var hd = Engine.hero.d;
        var results = [];
        if (typeof Gargonem !== 'undefined' && Gargonem.Core && Gargonem.Core.GW) {
            var gws = Gargonem.Core.GW.get();
            var seen = {};
            for (var i = 0; i < gws.length; i++) {
                var gw = gws[i];
                var targetName = Gargonem.Core.TownName.get(gw.id);
                if (!targetName || targetName === currentMap) continue;
                var match = false;
                for (var j = 0; j < keywords.length; j++) {
                    if (targetName.toLowerCase().indexOf(keywords[j].toLowerCase()) !== -1) { match = true; break; }
                }
                if (!match) continue;
                var key = gw.id + '';
                var mdist = Math.abs(gw.x - hd.x) + Math.abs(gw.y - hd.y);
                if (!seen[key] || mdist < seen[key].mdist) {
                    seen[key] = {mapId: gw.id, mapName: targetName, x: gw.x, y: gw.y, mdist: mdist};
                }
            }
            for (var k in seen) results.push(seen[k]);
        }
        return results;
    """, keywords, default=[])

    if not portals: return []
    hero_pos = get_hero_pos(driver)
    hx, hy = hero_pos['x'], hero_pos['y']
    reachable = []
    
    for p in portals:
        d = bfs_distance(driver, hx, hy, p['x'], p['y'], max_steps=300)
        p['dist'] = d if d != -1 else p['mdist'] * 1.5 
        reachable.append(p)

    reachable.sort(key=lambda p: p['dist'])
    return reachable

def change_map(driver, portal, gui=None, min_lvl=None, max_lvl=None, min_group=1, max_group=10):
    old_map = get_current_map(driver)
    def _check(drv):
        if get_current_map(drv) != old_map: return 'arrived'
        if min_lvl is not None and max_lvl is not None:
            if find_nearest_mob(drv, min_lvl, max_lvl, min_group, max_group): return 'abort'
        return None

    arrived = smart_walk_to(driver, portal['x'], portal['y'], timeout=WALK_TIMEOUT + 10, gui=gui, check_fn=_check)
    current = get_current_map(driver)
    if current and current != old_map:
        wait_for_game_ready(driver)
        return True
    if arrived:
        time.sleep(3)
        current = get_current_map(driver)
        if current and current != old_map:
            wait_for_game_ready(driver)
            return True
    if min_lvl is not None and max_lvl is not None:
        if find_nearest_mob(driver, min_lvl, max_lvl, min_group, max_group):
            return 'mob_found'
    return False

def walk_map_path(driver, cfg, gui, path_str: str, tag: str = "TRASA") -> bool:
    path_maps = [m.strip() for m in path_str.split(',') if m.strip()]
    if not path_maps: return True
    for i, target_map in enumerate(path_maps):
        if target_map.lower() in get_current_map(driver).lower(): continue
        reached = False
        for attempt in range(3):
            portals = find_portal_to_next_map(driver, [target_map])
            if not portals:
                time.sleep(1.5)
                continue
            res = change_map(driver, portals[0], gui, min_lvl=cfg.min_lvl, max_lvl=cfg.max_lvl, min_group=getattr(cfg, 'min_group', 1), max_group=getattr(cfg, 'max_group', 10))
            if res is True:
                rsleep(MAP_CHANGE_WAIT)
                wait_for_game_ready(driver, timeout=15)
                reached = True
                break
            elif res == 'mob_found':
                time.sleep(0.5)
                if target_map.lower() in get_current_map(driver).lower(): reached = True
                break
            time.sleep(1.0)
        if not reached: return False
    return True

def find_npc_on_map(driver, npc_name):
    return safe_js(driver, "var npc = Gargonem.Core.Npc.getByName(arguments[0]); if (!npc) return null; return {id: npc.id.toString(), nick: npc.nick, x: npc.x, y: npc.y};", npc_name, default=None)

def talk_to_npc_by_id(driver, npc_id): safe_js(driver, "Gargonem.Core.Talk.talkTo(arguments[0].toString());", npc_id)

def wait_for_dialog(driver, timeout=10):
    for _ in range(timeout * 2):
        if safe_js(driver, "var t = Gargonem.Core.Talk.get(); return (t && t.options && t.options.length > 0) ? true : false;", default=False): return True
        time.sleep(0.5)
    return False

def get_dialog_options(driver): return safe_js(driver, "var t = Gargonem.Core.Talk.get(); if (!t || !t.options) return []; var r = []; for (var i = 0; i < t.options.length; i++) { r.push({index: i+1, text: (t.options[i].text || t.options[i].label || t.options[i].name || '').trim()}); } return r;", default=[])

def select_dialog_option_by_index(driver, option_index): return safe_js(driver, "var idx = arguments[0] - 1; var t = Gargonem.Core.Talk.get(); if (!t || !t.options || idx < 0 || idx >= t.options.length) return false; Gargonem.Core.Talk.selectOption(t.options[idx]); return true;", option_index, default=False)

def select_dialog_option_by_text(driver, text_substring): return safe_js(driver, "var sub = arguments[0].toLowerCase(); var t = Gargonem.Core.Talk.get(); if (!t || !t.options) return false; for (var i = 0; i < t.options.length; i++) { var opt = t.options[i]; var label = (opt.text || opt.label || opt.name || '').toLowerCase(); if (label.indexOf(sub) !== -1) { Gargonem.Core.Talk.selectOption(opt); return true; } } return false;", text_substring, default=False)

def select_shop_in_dialog(driver): return safe_js(driver, "return Gargonem.Core.Talk.selectOptionByFlag(32);", default=False)

def wait_for_shop_open(driver, timeout=10):
    for _ in range(timeout * 2):
        if safe_js(driver, "var s = Gargonem.Core.Shop.get(); return (s && s.open) ? true : false;", default=False): return True
        time.sleep(0.5)
    return False

def close_shop_npc(driver): safe_js(driver, "Gargonem.Core.Shop.shopClose();")

NPC_TELEPORT_CITY_OPTIONS = {
    "Ithan": 1, "Torneg": 2, "Werbin": 3, "Karka-han": 4, 
    "Eder": 5, "Nithal": 6, "Trupia Przełęcz [Tuzmer]": 7, "Thuzal": 8,
}