"""
captcha.py — detekcja i rozwiązywanie captchy z humanizacją i opóźnieniami
"""
import time, re, random
from selenium.webdriver.common.by import By

from config import rsleep_range
from game import safe_js, human_move_and_click

PRE_CAPTCHA_POLL = 0.5

def _quick_captcha_visible(driver) -> bool:
    try:
        return driver.execute_script("""
            var cw = document.querySelector('.captcha-window');
            if (cw && cw.style.display !== 'none') return true;
            var pre = document.querySelector('.pre-captcha');
            if (pre && pre.children.length > 0) return true;
            return false;
        """)
    except Exception: return False

def detect_pre_captcha(driver):
    return safe_js(driver, """
        var pre = document.querySelector('.pre-captcha');
        if (pre && pre.children.length > 0) {
            var t = pre.querySelector('.captcha-pre-info__time');
            return t ? parseInt(t.textContent) : 0;
        }
        return null;
    """, default=None)

def wait_for_pre_captcha(driver, gui=None, timeout=120):
    for _ in range(timeout * 2):
        if detect_pre_captcha(driver) is None: return
        time.sleep(PRE_CAPTCHA_POLL)

def wait_for_captcha_appear(driver, gui=None, timeout=15):
    for _ in range(timeout * 2):
        res = safe_js(driver, """
            var el = document.querySelector('.captcha-window');
            if (el && el.style.display !== 'none') {
                var b = el.querySelectorAll('.captcha__buttons .button, .captcha__buttons .btn');
                if (b.length > 0) return b.length;
            }
            return null;
        """, default=None)
        if res: return True
        time.sleep(0.5)
    return False

def click_pre_captcha_solve_now(driver) -> bool:
    try:
        selectors = ['.pre-captcha .button', '.pre-captcha .btn', '.captcha-pre-info__button .button']
        btns = []
        for sel in selectors:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            if found: btns.extend(found)

        for btn in btns:
            if not btn.is_displayed(): continue
            txt = btn.text.lower()
            if any(kw in txt for kw in ("rozwiąz", "rozwiąż", "scan", "zeskanuj")):
                rsleep_range(0.5, 1.2)
                # Używamy humanizacji myszy zamiast prostego click
                human_move_and_click(driver, btn)
                return True
        return False
    except Exception: return False

def click_correct_captcha_buttons(driver) -> dict:
    try:
        selectors = ['.captcha-window .captcha__buttons .button.small.green', '.captcha-window .captcha__buttons .button']
        buttons = []
        for sel in selectors:
            found = driver.find_elements(By.CSS_SELECTOR, sel)
            buttons = [b for b in found if b.is_displayed()]
            if buttons: break

        clicked, correct_texts = 0, []
        for btn in buttons:
            text = btn.text.strip()
            if re.match(r'^\*[^*]+\*$', text):
                if "pressed" in (btn.get_attribute("class") or ""): continue
                
                # Używamy humanizacji myszy
                rsleep_range(0.5, 1.2)
                human_move_and_click(driver, btn)
                clicked += 1
                correct_texts.append(text)
                rsleep_range(0.5, 1.0)

        return {'clicked': clicked, 'total': len(buttons), 'correct_texts': correct_texts}
    except Exception as e:
        return {'clicked': 0, 'total': 0, 'error': str(e)}

def click_captcha_confirm(driver) -> bool:
    try:
        selectors = ['.captcha-window .captcha__confirm .button.small.green', '.captcha-window .captcha__confirm .button', '.captcha__confirm .button']
        for sel in selectors:
            btns = [b for b in driver.find_elements(By.CSS_SELECTOR, sel) if b.is_displayed()]
            if btns:
                rsleep_range(0.5, 1.2)
                human_move_and_click(driver, btns[0])
                return True
        return False
    except Exception: return False

def check_and_solve_captcha(driver, gui=None) -> bool:
    if not _quick_captcha_visible(driver): return False

    if gui: gui.log("[CAPTCHA] Wykryto! Oczekuję przed rozwiązaniem...")

    # STEALTH: Symulacja ludzkiego czasu reakcji i czytania. Bot nie rzuca się od razu.
    rsleep_range(2.5, 4.5)

    if detect_pre_captcha(driver) is not None:
        if click_pre_captcha_solve_now(driver):
            if gui: gui.log("[CAPTCHA] Kliknięto 'Rozwiąż teraz'")
            time.sleep(1)
        else:
            wait_for_pre_captcha(driver, gui)
            time.sleep(1)

    wait_for_captcha_appear(driver, gui)
    
    # Kolejny naturalny przestój na "zapoznanie się z pytaniem"
    rsleep_range(2.0, 3.5)

    res = click_correct_captcha_buttons(driver)
    if res['clicked'] > 0:
        if gui: gui.log(f"[CAPTCHA] Zaznaczono {res['clicked']} odpowiedzi.")
        rsleep_range(0.8, 1.5)
        if click_captcha_confirm(driver):
            if gui: gui.log("[CAPTCHA] Potwierdzono ✓")
    else:
        if gui: gui.log("[CAPTCHA] Brak pasujących odpowiedzi.")

    rsleep_range(1.5, 3.0)
    return True