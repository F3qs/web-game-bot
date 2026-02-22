"""
routines.py — wysokopoziomowe procedury bota (z humanizacją)
"""
import time, random, traceback
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import InvalidSessionIdException, NoSuchWindowException

from config import WALK_TIMEOUT, MAP_CHANGE_WAIT, LOOP_INTERVAL, AFTER_BATTLE_WAIT, NO_MOB_RETRIES, gauss_sleep, rsleep_range, rsleep
from game import connect, safe_js, wait_for_game_ready, get_current_map, get_hero_pos, walk_to, smart_walk_to, walk_map_path, find_nearest_mob, find_portal_to_next_map, change_map, find_walkable_neighbors, attack_mob, mob_exists, get_distance_to_mob, is_in_battle, wait_for_battle_end, unlock_movement, find_npc_on_map, talk_to_npc_by_id, wait_for_dialog, get_dialog_options, select_dialog_option_by_index, select_dialog_option_by_text, select_shop_in_dialog, wait_for_shop_open, close_shop_npc, NPC_TELEPORT_CITY_OPTIONS, check_for_death, go_to_homepage, return_to_game, human_move_and_click
from captcha import check_and_solve_captcha
from notifications import send_discord_notification

# ══════════════════════════════════════════════════════════════════════════════════
#  Stealth / Zmęczenie (Mikro-zachowania)
# ══════════════════════════════════════════════════════════════════════════════════

def random_micro_behavior(driver, gui):
    """Wykonuje losową, ludzką czynność niezwiązaną z expieniem."""
    rand = random.random()
    try:
            # Poruszanie lekko myszką po ekranie
            action = ActionChains(driver)
            for _ in range(random.randint(1, 4)):
                action.move_by_offset(random.randint(-50, 50), random.randint(-50, 50))
                action.pause(random.uniform(0.1, 0.4))
            action.perform()
    except: pass


# ══════════════════════════════════════════════════════════════════════════════════
#  Restock / Powrót
# ══════════════════════════════════════════════════════════════════════════════════

def get_free_bag_space(driver): return safe_js(driver, "return Gargonem.Core.Item.getFreeSpace();", default=-1)
def check_bags_full(driver): return get_free_bag_space(driver) == 0

def use_item_by_name(driver, item_name: str, gui=None):
    result = safe_js(driver, """
        var name = arguments[0]; var all = Gargonem.Core.Item.getAll();
        for (var id in all) {
            var it = all[id];
            if (it.loc === 'g' && it.name === name) { Gargonem.Core.Item.use(it); return {ok: true, name: it.name}; }
        }
        return {error: 'not_found'};
    """, item_name, default={'error': 'js_error'})
    if result.get('ok'):
        if gui: gui.log(f"[RESTOCK] Użyto: {result['name']}")
        return True
    return False

def sell_bag_contents(driver, bag_number: int, gui=None):
    if bag_number not in (1, 2, 3): return False
    try:
        bag_btn = driver.find_elements(By.CSS_SELECTOR, f'.grab-bag-{bag_number}')
        if not bag_btn: return False
        rsleep_range(0.4, 0.8)
        human_move_and_click(driver, bag_btn[0])
        
        rsleep_range(0.8, 1.5)
        accept_btn = driver.find_elements(By.CSS_SELECTOR, '.finalize-button .button')
        if not accept_btn: accept_btn = driver.find_elements(By.CSS_SELECTOR, '.finalize-button')
        if not accept_btn: return False
        
        rsleep_range(0.3, 0.7)
        human_move_and_click(driver, accept_btn[0])
        rsleep_range(1.0, 2.0)
        return True
    except: return False

def restock_routine(driver, cfg, gui=None) -> bool:
    if cfg._restock_in_progress: return False
    cfg._restock_in_progress = True
    if gui: gui.log("\n[RESTOCK] Torby pełne! Rozpoczynam restock…")
    cfg.status = "Restock — teleport…"
    success = False

    try:
        if not use_item_by_name(driver, cfg.restock_teleport, gui): return False
        rsleep(2.0)
        wait_for_game_ready(driver, timeout=15)
        
        cfg.status = "Restock — idę do sklepu…"
        shop_map = cfg.restock_shop_map
        if shop_map.lower() not in get_current_map(driver).lower():
            portals = find_portal_to_next_map(driver, [shop_map])
            if portals:
                smart_walk_to(driver, portals[0]['x'], portals[0]['y'], timeout=WALK_TIMEOUT + 5, gui=gui)
                time.sleep(MAP_CHANGE_WAIT)
                wait_for_game_ready(driver, timeout=15)

        cfg.status = "Restock — szukam NPC…"
        npc = find_npc_on_map(driver, cfg.restock_npc)
        if not npc: time.sleep(2); npc = find_npc_on_map(driver, cfg.restock_npc)
        if not npc: return False

        hero = get_hero_pos(driver)
        if abs(hero['x'] - npc['x']) + abs(hero['y'] - npc['y']) > 1:
            if not smart_walk_to(driver, npc['x'], npc['y'], timeout=WALK_TIMEOUT, gui=gui): return False
            rsleep(0.5)

        cfg.status = "Restock — rozmowa z NPC…"
        talk_to_npc_by_id(driver, npc['id'])
        rsleep(1.0)
        if not wait_for_dialog(driver, timeout=10): return False

        shop_ok = (select_shop_in_dialog(driver) or select_dialog_option_by_text(driver, "sprzedaż") or select_dialog_option_by_text(driver, "co masz"))
        if not shop_ok: return False
        rsleep(1.5)
        if not wait_for_shop_open(driver, timeout=10): return False

        cfg.status = "Restock — sprzedaję…"
        sell_seq = [int(s.strip()) for s in cfg.restock_sell_sequence.split(",") if s.strip().isdigit()]
        for bag_num in sell_seq:
            sell_bag_contents(driver, bag_num, gui)
            rsleep(2.0)

        close_shop_npc(driver)
        rsleep(2.0)

        cfg.status = "Restock — powrót na expo…"
        method = cfg.restock_return_method
        if method == "npc_teleport": npc_teleport_routine(driver, cfg, gui)
        elif method == "scroll":
            if use_item_by_name(driver, cfg.restock_return_scroll, gui):
                rsleep(2.0)
                wait_for_game_ready(driver, timeout=15)
        else: walk_map_path(driver, cfg, gui, cfg.restock_return_walk_path, tag="RESTOCK-POWRÓT")

        cfg.status = "Aktywny"
        success = True
        return True
    except: return False
    finally:
        cfg._restock_in_progress = False
        if not success: cfg.status = "Aktywny"


def npc_teleport_routine(driver, cfg, gui=None) -> bool:
    if cfg._npc_teleport_in_progress: return False
    cfg._npc_teleport_in_progress = True
    cfg.status = "NPC Teleport…"

    try:
        walk_to_npc = getattr(cfg, 'npc_teleport_walk_to_npc', '').strip()
        if walk_to_npc: walk_map_path(driver, cfg, gui, walk_to_npc, tag="NPC-TP")
            
        npc = find_npc_on_map(driver, cfg.npc_teleport_npc_name)
        if not npc: time.sleep(2); npc = find_npc_on_map(driver, cfg.npc_teleport_npc_name)
        if not npc: return False

        hero = get_hero_pos(driver)
        if abs(hero['x'] - npc['x']) + abs(hero['y'] - npc['y']) > 1:
            if not smart_walk_to(driver, npc['x'], npc['y'], timeout=WALK_TIMEOUT, gui=gui): return False
            rsleep(0.5)

        talk_to_npc_by_id(driver, npc['id'])
        rsleep(1.0)
        if not wait_for_dialog(driver, timeout=10): return False

        ok = (select_dialog_option_by_index(driver, 1) or select_dialog_option_by_text(driver, "teleportować"))
        if not ok: return False
        rsleep(1.2)
        if not wait_for_dialog(driver, timeout=10): return False

        city = cfg.npc_teleport_city
        city_num = NPC_TELEPORT_CITY_OPTIONS.get(city)
        selected = select_dialog_option_by_index(driver, city_num) if city_num else False
        if not selected: selected = select_dialog_option_by_text(driver, city.split()[0])
        if not selected: return False

        rsleep(1.5)
        wait_for_game_ready(driver, timeout=20)
        time.sleep(1.0)

        after_path = getattr(cfg, 'npc_teleport_after_path', '').strip()
        if after_path: walk_map_path(driver, cfg, gui, after_path, tag="NPC-TP→EXP")

        cfg.status = "Aktywny"
        return True
    except: return False
    finally:
        cfg._npc_teleport_in_progress = False
        cfg._npc_teleport_pending = False


# ══════════════════════════════════════════════════════════════════════════════════
#  Główna pętla bota
# ══════════════════════════════════════════════════════════════════════════════════

def bot_loop(cfg, gui):
    driver = connect()
    no_mob_count = 0
    if cfg.discord_enabled: send_discord_notification(cfg.discord_webhook_url, "Bot uruchomiony.", "START")
        
    while cfg.running:
        try:
            # --- ZGON ---
            death_time = check_for_death(driver)
            if death_time is not None:
                cfg.deaths += 1
                cfg.status = f"Zgon! Odrodzenie: {death_time}s"
                gui.log(f"☠️ Zgon. Odrodzenie za {death_time} sekund.")
                if cfg.discord_enabled:
                    send_discord_notification(cfg.discord_webhook_url, f"Postać zginęła! Powrót za **{death_time // 60}m {death_time % 60}s**.\nLiczba śmierci: **{cfg.deaths}**.", "💀 Zgon!", color=0xde2121)
                
                # Ochrona przed detekcją i wylogowaniem - czekamy na stronie głównej
                go_to_homepage(driver)
                wait_duration = death_time + random.uniform(15, 45)
                end_t = time.time() + wait_duration
                while time.time() < end_t and cfg.running: time.sleep(1)
                if not cfg.running: break
                    
                return_to_game(driver)
                wait_for_game_ready(driver, timeout=60)
                
                if getattr(cfg, 'death_return_path', '').strip():
                    walk_map_path(driver, cfg, gui, cfg.death_return_path, tag="ŚMIERĆ-POWRÓT")
                continue

            # --- CAPTCHA ---
            if check_and_solve_captcha(driver, gui):
                cfg.status = "CAPTCHA rozwiązana"
                if cfg.discord_enabled: send_discord_notification(cfg.discord_webhook_url, "Rozwiązano CAPTCHA.", "CAPTCHA", color=0xf2a01e)
                continue

            # --- PAUZA / TP ---
            if cfg.paused: time.sleep(0.5); continue
            if cfg._npc_teleport_pending and not cfg._npc_teleport_in_progress:
                npc_teleport_routine(driver, cfg, gui)
                cfg.current_map = get_current_map(driver)
                cfg.update_map_timer(cfg.current_map)
                continue

            # --- WALKA ---
            if is_in_battle(driver):
                cfg.status = "Walka…"
                wait_for_battle_end(driver, gui=gui)
                time.sleep(AFTER_BATTLE_WAIT)
                no_mob_count = 0
                continue
            unlock_movement(driver)

            # --- SZUKANIE MOBA ---
            mob = find_nearest_mob(driver, cfg.min_lvl, cfg.max_lvl, min_group=cfg.min_group, max_group=cfg.max_group)
            
            if not mob:
                no_mob_count += 1
                cfg.status = f"Brak mobów ({no_mob_count}/{NO_MOB_RETRIES})"
                
                if no_mob_count >= NO_MOB_RETRIES:
                    current_map_name = get_current_map(driver)
                    cfg.update_map_timer(current_map_name)
                    
                    portals = find_portal_to_next_map(driver, cfg.map_keywords)
                    if portals:
                        closest = portals[0]
                        if closest['dist'] == 0:
                            hp = get_hero_pos(driver)
                            nb = find_walkable_neighbors(driver, hp['x'], hp['y'], radius=2)
                            if nb: walk_to(driver, nb[0]['x'], nb[0]['y'])
                            else: walk_to(driver, hp['x']+1, hp['y'])
                            rsleep_range(1.0, 1.5)
                            portals = find_portal_to_next_map(driver, cfg.map_keywords)

                    if portals:
                        def score_portal(p): return cfg.get_map_last_visit(p['mapName'])
                        portals.sort(key=score_portal)
                        best_portal = portals[0]
                        
                        cfg.status = f"Idę do: {best_portal['mapName']}"
                        result = change_map(driver, best_portal, gui, min_lvl=cfg.min_lvl, max_lvl=cfg.max_lvl, min_group=cfg.min_group, max_group=cfg.max_group)
                                            
                        if result is True:
                            rsleep(MAP_CHANGE_WAIT)
                            new_map = get_current_map(driver)
                            cfg.current_map = new_map
                            cfg.update_map_timer(new_map)
                            no_mob_count = 0
                        elif result == 'mob_found': no_mob_count = 0
                    else:
                        rsleep(5, 2.0)
                        no_mob_count = NO_MOB_RETRIES - 1 
                else: rsleep(LOOP_INTERVAL)
                continue

            # --- ATAK ---
            no_mob_count = 0
            mob_id = mob['id']
            cfg.status = f"Cel: {mob['nick']} ({mob['grp']})"
            
            if get_distance_to_mob(driver, mob_id) > 1:
                last_better_mob_check = 0
                def _check_mob(drv):
                    nonlocal last_better_mob_check
                    if not cfg.running: return 'abort'
                    current_dist = get_distance_to_mob(drv, mob_id)
                    if current_dist == -1: return 'abort' 
                    if current_dist <= 1: return 'arrived'
                    if current_dist > 3 and (time.time() - last_better_mob_check > 0.8):
                        last_better_mob_check = time.time()
                        better = find_nearest_mob(drv, cfg.min_lvl, cfg.max_lvl, min_group=cfg.min_group, max_group=cfg.max_group)
                        if better and better['id'] != mob_id:
                            b_dist = better.get('dist', better.get('mdist', 999))
                            if b_dist < (current_dist - 2): return 'abort' 
                    return None

                if not smart_walk_to(driver, mob['x'], mob['y'], timeout=WALK_TIMEOUT, gui=gui, check_fn=_check_mob):
                    continue

            if not mob_exists(driver, mob_id): continue

            # Ludzkie atakowanie (fizyczne kliknięcie, jeśli to możliwe)
            attack_mob(driver, mob_id)
            cfg.kills += 1
            rsleep_range(0.8, 1.5) 
            
            # --- RESTOCK ---
            if cfg.restock_enabled and not cfg._restock_in_progress:
                if check_bags_full(driver):
                    restock_routine(driver, cfg, gui)
                    cfg.current_map = get_current_map(driver)
                    cfg.update_map_timer(cfg.current_map)

            rsleep_range(0.2, 0.5)

        except KeyboardInterrupt: break
        except (InvalidSessionIdException, NoSuchWindowException):
            gui.log("Utracono połączenie z przeglądarką. Próbuję połączyć się ponownie...")
            gauss_sleep(5, 1)
            try: driver = connect()
            except: pass
        except Exception as e:
            traceback.print_exc()
            gauss_sleep(2, 0.5)

    cfg.status = "Zatrzymany"
    if cfg.discord_enabled: send_discord_notification(cfg.discord_webhook_url, "Bot został zatrzymany.", "STOP", color=0x9c2323)
    gui.log("Bot zatrzymany.")