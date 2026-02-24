"""
gui.py — interfejs graficzny bota (customtkinter)
"""
import threading
import tkinter as tk
import customtkinter as ctk

try:
    import keyboard as kb
    HAS_KEYBOARD = True
except ImportError:
    HAS_KEYBOARD = False

from config import BotConfig
from margoworld import (
    fetch_expowiska_list, fetch_expowisko_details,
    fetch_world_map_list, search_world_maps,
)
from game import connect
from routines import bot_loop, npc_teleport_routine

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class BotGUI:
    HOTKEY = "F6"

    def __init__(self, config: BotConfig):
        self.cfg = config

        self.root = ctk.CTk()
        self.root.title("Margonem Bot")
        self.root.geometry("640x820")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # ════════════════════════════════════════════════════
        #  GÓRNY PASEK
        # ════════════════════════════════════════════════════
        frm_top = ctk.CTkFrame(self.root, fg_color="transparent")
        frm_top.pack(fill="x", padx=10, pady=(10, 0))

        # Sterowanie
        frm_btns, inner_btns = self._create_labelframe(frm_top, "Sterowanie")
        frm_btns.pack(side="left", padx=(0, 10), fill="y")
        
        self.btn_run = ctk.CTkButton(inner_btns, text="▶ START", font=("Segoe UI", 13, "bold"), width=110, height=32, fg_color="#2b8a3e", hover_color="#237032", command=self._toggle_run)
        self.btn_run.grid(row=0, column=0, padx=5, pady=5)
        
        self.btn_pause = ctk.CTkButton(inner_btns, text="⏸ Pauza", width=110, height=32, state="disabled", command=self._toggle_pause)
        self.btn_pause.grid(row=0, column=1, padx=5, pady=5)

        lbl_hk = ctk.CTkLabel(inner_btns, text=f"Hotkey: {self.HOTKEY}", text_color="gray", font=("Segoe UI", 11, "italic"))
        lbl_hk.grid(row=1, column=0, columnspan=2, pady=(0, 5))

        # Status
        frm_st, inner_st = self._create_labelframe(frm_top, "Status")
        frm_st.pack(side="left", fill="both", expand=True)

        self.lbl_status = ctk.CTkLabel(inner_st, text="Status: Oczekiwanie…", font=("Segoe UI", 13, "bold"), text_color="#3498db")
        self.lbl_status.grid(row=0, column=0, padx=10, pady=(2, 0), sticky="w")
        self.lbl_map = ctk.CTkLabel(inner_st, text="Mapa: —", font=("Segoe UI", 12))
        self.lbl_map.grid(row=1, column=0, padx=10, sticky="w")
        self.lbl_kills = ctk.CTkLabel(inner_st, text="Zabito: 0", font=("Segoe UI", 12))
        self.lbl_kills.grid(row=2, column=0, padx=10, pady=(0, 2), sticky="w")

        # ════════════════════════════════════════════════════
        #  LOG
        # ════════════════════════════════════════════════════
        frm_log, inner_log = self._create_labelframe(self.root, "Konsola (Log)")
        frm_log.pack(fill="x", padx=10, pady=(10, 0))

        self.log_widget = ctk.CTkTextbox(inner_log, height=110, font=("Consolas", 12))
        self.log_widget.pack(fill="both", expand=True)
        self.log_widget.configure(state="disabled")

        # ════════════════════════════════════════════════════
        #  ZAKŁADKI (TABS)
        # ════════════════════════════════════════════════════
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_exp  = self.tabview.add("🗡 Expowisko")
        self.tab_rs   = self.tabview.add("🛒 Powroty & Restock")
        self.tab_mw   = self.tabview.add("🗺 Trasy")
        self.tab_sch  = self.tabview.add("⏰ Harmonogram")
        self.tab_brw  = self.tabview.add("🌐 Przeglądarka")
        self.tab_set  = self.tabview.add("⚙️ Ustawienia")

        self._build_tab_expowisko(self.tab_exp, config)
        self._build_tab_restock(self.tab_rs, config)
        self._build_tab_margoworld(self.tab_mw)
        self._build_tab_schedule(self.tab_sch, config)
        self._build_tab_browser(self.tab_brw, config)
        self._build_tab_settings(self.tab_set, config)

        if HAS_KEYBOARD: kb.add_hotkey(self.HOTKEY, self._hotkey_toggle, suppress=False)

        self.bot_thread = None
        self._refresh_status()

    # ══════════════════════════════════════════════════════════
    #  Narzędzia GUI
    # ══════════════════════════════════════════════════════════
    def _create_labelframe(self, parent, title):
        frm = ctk.CTkFrame(parent)
        lbl = ctk.CTkLabel(frm, text=title, font=("Segoe UI", 13, "bold"))
        lbl.pack(anchor="w", padx=10, pady=(5,0))
        inner = ctk.CTkFrame(frm, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=5, pady=5)
        return frm, inner

    # ══════════════════════════════════════════════════════════
    #  Budowanie Zakładek
    # ══════════════════════════════════════════════════════════
    def _build_tab_expowisko(self, tab, config):
        frm_mw, in_mw = self._create_labelframe(tab, "Expowiska (MargoWorld)")
        frm_mw.pack(fill="x", padx=5, pady=(5, 5))

        self._expowiska_list = []
        self._expowiska_filtered = []  # przechowuje aktualnie widoczne wpisy

        # Górny pasek: szukaj + przycisk + status
        frm_exp_top = ctk.CTkFrame(in_mw, fg_color="transparent")
        frm_exp_top.pack(fill="x", padx=5, pady=(5, 0))

        ctk.CTkLabel(frm_exp_top, text="Szukaj:").pack(side="left", padx=(0, 4))
        self.var_exp_search = tk.StringVar()
        self.var_exp_search.trace_add("write", self._on_exp_search_changed)
        ctk.CTkEntry(frm_exp_top, textvariable=self.var_exp_search, width=200).pack(side="left", padx=(0, 10))

        self.btn_load_exp = ctk.CTkButton(frm_exp_top, text="⬇ Załaduj listę", width=130, command=self._load_expowiska)
        self.btn_load_exp.pack(side="left", padx=(0, 8))

        self.lbl_exp_status = ctk.CTkLabel(frm_exp_top, text="(nie pobrano)", text_color="gray", font=("Segoe UI", 11))
        self.lbl_exp_status.pack(side="left")

        # Scrollowalna lista expowisk
        frm_lb = ctk.CTkFrame(in_mw, fg_color="transparent")
        frm_lb.pack(fill="x", padx=5, pady=(4, 5))

        self.lb_exp = tk.Listbox(
            frm_lb, height=7, font=("Consolas", 12),
            selectmode="single",
            bg="#2b2b2b", fg="#ffffff",
            selectbackground="#1f538d",
            borderwidth=0, highlightthickness=0,
            activestyle="none",
        )
        sb_exp = tk.Scrollbar(frm_lb, orient="vertical", command=self.lb_exp.yview)
        self.lb_exp.configure(yscrollcommand=sb_exp.set)
        self.lb_exp.pack(side="left", fill="both", expand=True)
        sb_exp.pack(side="right", fill="y")
        self.lb_exp.bind("<Double-Button-1>", lambda e: self._on_exp_selected_lb())
        self.lb_exp.bind("<Return>", lambda e: self._on_exp_selected_lb())

        ctk.CTkLabel(in_mw, text="↑ Dwuklik lub Enter = zastosuj expowisko", text_color="gray", font=("Segoe UI", 11, "italic")).pack(anchor="w", padx=5, pady=(0, 4))

        frm_set, in_set = self._create_labelframe(tab, "Filtrowanie Mobów")
        frm_set.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(in_set, text="Min LVL:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.var_min = tk.IntVar(value=config.min_lvl)
        ctk.CTkEntry(in_set, textvariable=self.var_min, width=50).grid(row=0, column=1, padx=5, pady=5)
        
        ctk.CTkLabel(in_set, text="Max LVL:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.var_max = tk.IntVar(value=config.max_lvl)
        ctk.CTkEntry(in_set, textvariable=self.var_max, width=50).grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(in_set, text="Min GRP:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.var_min_grp = tk.IntVar(value=config.min_group)
        ctk.CTkEntry(in_set, textvariable=self.var_min_grp, width=50).grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(in_set, text="Max GRP:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.var_max_grp = tk.IntVar(value=config.max_group)
        ctk.CTkEntry(in_set, textvariable=self.var_max_grp, width=50).grid(row=1, column=3, padx=5, pady=5)

        ctk.CTkButton(in_set, text="Zastosuj parametry", command=self._apply_levels).grid(row=0, column=4, rowspan=2, padx=15, pady=5)

        self.var_avoid_elites = tk.BooleanVar(value=config.avoid_elites)
        ctk.CTkCheckBox(in_set, text="Unikaj Elit oraz Elit II", variable=self.var_avoid_elites, command=self._apply_levels).grid(row=2, column=0, columnspan=4, padx=5, pady=5, sticky="w")

        frm_map, in_map = self._create_labelframe(tab, "Rotacja map expowiska (jedna mapa na linię)")
        frm_map.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.txt_maps = ctk.CTkTextbox(in_map, font=("Consolas", 12))
        self.txt_maps.pack(fill="both", expand=True, padx=5, pady=5)
        self.txt_maps.insert("0.0", "\n".join(config.map_keywords))
        
        ctk.CTkButton(in_map, text="Zastosuj mapy", command=self._apply_maps).pack(pady=5)

    def _build_tab_restock(self, tab, config):
        # Sekcja ŚMIERĆ
        frm_death, in_death = self._create_labelframe(tab, "☠️ Powrót po śmierci")
        frm_death.pack(fill="x", padx=5, pady=(5, 5))

        ctk.CTkLabel(in_death, text="Nick postaci:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.var_preferred_char = tk.StringVar(value=getattr(config, 'preferred_character', ''))
        ctk.CTkEntry(in_death, textvariable=self.var_preferred_char, width=200,
                     placeholder_text="np. Hate My Life").grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ctk.CTkLabel(in_death, text="(postać wybierana po wylogowaniu)", text_color="gray",
                     font=("Segoe UI", 11)).grid(row=0, column=2, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(in_death, text="Trasa map:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.var_death_path = tk.StringVar(value=config.death_return_path)
        ctk.CTkEntry(in_death, textvariable=self.var_death_path, width=440).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(in_death, text="(od miasta do expowiska)", text_color="gray", font=("Segoe UI", 11)).grid(row=2, column=1, padx=5, sticky="w")

        # Sekcja RESTOCK
        self.var_restock = tk.BooleanVar(value=config.restock_enabled)
        ctk.CTkCheckBox(tab, text="✅  Włącz auto-restock gdy torby pełne", variable=self.var_restock).pack(anchor="w", padx=15, pady=(10, 0))

        frm_sell, in_sell = self._create_labelframe(tab, "1. Sprzedaż u NPC")
        frm_sell.pack(fill="x", padx=5, pady=(5, 5))

        ctk.CTkLabel(in_sell, text="TP do sklepu:").grid(row=0, column=0, padx=5, pady=3, sticky="e")
        self.var_rs_teleport = tk.StringVar(value=config.restock_teleport)
        ctk.CTkEntry(in_sell, textvariable=self.var_rs_teleport, width=420).grid(row=0, column=1, columnspan=3, padx=5, pady=3, sticky="ew")

        ctk.CTkLabel(in_sell, text="NPC (nick):").grid(row=1, column=0, padx=5, pady=3, sticky="e")
        self.var_rs_npc = tk.StringVar(value=config.restock_npc)
        ctk.CTkEntry(in_sell, textvariable=self.var_rs_npc, width=180).grid(row=1, column=1, padx=5, pady=3, sticky="w")
        
        ctk.CTkLabel(in_sell, text="Mapa:").grid(row=1, column=2, padx=5, pady=3, sticky="e")
        self.var_rs_map = tk.StringVar(value=config.restock_shop_map)
        ctk.CTkEntry(in_sell, textvariable=self.var_rs_map, width=140).grid(row=1, column=3, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(in_sell, text="Torby (np. 1,1,2):").grid(row=2, column=0, padx=5, pady=3, sticky="e")
        self.var_rs_bags = tk.StringVar(value=config.restock_sell_sequence)
        ctk.CTkEntry(in_sell, textvariable=self.var_rs_bags, width=100).grid(row=2, column=1, padx=5, pady=3, sticky="w")

        # Zakonnik
        NPC_CITIES = ["Ithan", "Torneg", "Werbin", "Karka-han", "Eder", "Nithal", "Trupia Przełęcz [Tuzmer]", "Thuzal"]

        frm_tp, in_tp = self._create_labelframe(tab, "2. Powrót na expowisko")
        frm_tp.pack(fill="x", padx=5, pady=5)

        ctk.CTkLabel(in_tp, text="Metoda:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.var_return_method = tk.StringVar(value=config.restock_return_method)
        frm_rb = ctk.CTkFrame(in_tp, fg_color="transparent")
        frm_rb.grid(row=0, column=1, columnspan=3, sticky="w", pady=5)
        for t, v in [("Zakonnik", "npc_teleport"), ("Zwój", "scroll"), ("Pieszo", "walk")]:
            ctk.CTkRadioButton(frm_rb, text=t, variable=self.var_return_method, value=v).pack(side="left", padx=10)

        ctk.CTkLabel(in_tp, text="Zakonnik Mapa:").grid(row=1, column=0, padx=5, pady=3, sticky="e")
        self.var_tp_map = tk.StringVar(value=config.npc_teleport_npc_map)
        ctk.CTkEntry(in_tp, textvariable=self.var_tp_map, width=160).grid(row=1, column=1, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(in_tp, text="Miasto (TP):").grid(row=1, column=2, padx=5, pady=3, sticky="e")
        self.var_tp_city = tk.StringVar(value=config.npc_teleport_city)
        ctk.CTkComboBox(in_tp, variable=self.var_tp_city, values=NPC_CITIES, width=160).grid(row=1, column=3, padx=5, pady=3, sticky="w")

        ctk.CTkLabel(in_tp, text="Trasa (do NPC):").grid(row=2, column=0, padx=5, pady=3, sticky="e")
        self.var_tp_walk_to_npc = tk.StringVar(value=getattr(config, 'npc_teleport_walk_to_npc', ""))
        ctk.CTkEntry(in_tp, textvariable=self.var_tp_walk_to_npc, width=420).grid(row=2, column=1, columnspan=3, padx=5, pady=3, sticky="ew")

        ctk.CTkLabel(in_tp, text="Trasa (po TP):").grid(row=3, column=0, padx=5, pady=3, sticky="e")
        self.var_tp_after = tk.StringVar(value=config.npc_teleport_after_path)
        ctk.CTkEntry(in_tp, textvariable=self.var_tp_after, width=420).grid(row=3, column=1, columnspan=3, padx=5, pady=3, sticky="ew")
        
        ctk.CTkLabel(in_tp, text="Zwój/Pieszo tras:").grid(row=4, column=0, padx=5, pady=3, sticky="e")
        self.var_rs_return = tk.StringVar(value=config.restock_return_scroll)
        self.var_rs_walk_path = tk.StringVar(value=config.restock_return_walk_path)
        frm_mix = ctk.CTkFrame(in_tp, fg_color="transparent")
        frm_mix.grid(row=4, column=1, columnspan=3, sticky="ew", pady=3)
        ctk.CTkEntry(frm_mix, textvariable=self.var_rs_return, width=180).pack(side="left", padx=(5,10))
        ctk.CTkEntry(frm_mix, textvariable=self.var_rs_walk_path, width=230).pack(side="left")

        frm_btns = ctk.CTkFrame(tab, fg_color="transparent")
        frm_btns.pack(pady=10)
        ctk.CTkButton(frm_btns, text="💾 Zapisz powroty i restock", fg_color="#c0392b", hover_color="#922b21", command=self._apply_restock).pack(side="left", padx=10)
        ctk.CTkButton(frm_btns, text="🚀 Test TP Zakonnika", command=self._trigger_npc_teleport).pack(side="left", padx=10)

    def _build_tab_schedule(self, tab, config):
        """Zakładka harmonogramu — okna czasowe aktywności bota."""
        # Nagłówek
        ctk.CTkLabel(tab, text="Ustal kiedy bot ma być aktywny. Poza oknami bot wychodzi na stronę główną i czeka.",
                     font=("Segoe UI", 11, "italic"), text_color="gray", wraplength=560).pack(padx=10, pady=(8, 4), anchor="w")

        # Włącz/wyłącz
        frm_top = ctk.CTkFrame(tab, fg_color="transparent")
        frm_top.pack(fill="x", padx=10, pady=(0, 4))

        self.var_sch_enabled = tk.BooleanVar(value=config.schedule_enabled)
        ctk.CTkCheckBox(frm_top, text="✅  Włącz harmonogram", variable=self.var_sch_enabled).pack(side="left", padx=5)

        ctk.CTkLabel(frm_top, text="Losowe przesunięcie ±", text_color="gray").pack(side="left", padx=(20, 2))
        self.var_sch_offset = tk.IntVar(value=config.schedule_random_offset)
        ctk.CTkEntry(frm_top, textvariable=self.var_sch_offset, width=45).pack(side="left")
        ctk.CTkLabel(frm_top, text="min (anty-detekcja)", text_color="gray").pack(side="left", padx=(2, 0))

        # Lista okien
        frm_list, in_list = self._create_labelframe(tab, "Okna aktywności")
        frm_list.pack(fill="both", expand=True, padx=10, pady=5)

        self.lb_sch = tk.Listbox(
            in_list, height=8, font=("Consolas", 13),
            selectmode="single",
            bg="#2b2b2b", fg="#ffffff",
            selectbackground="#1f538d",
            borderwidth=0, highlightthickness=0,
            activestyle="none",
        )
        sb_sch = tk.Scrollbar(in_list, orient="vertical", command=self.lb_sch.yview)
        self.lb_sch.configure(yscrollcommand=sb_sch.set)
        self.lb_sch.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        sb_sch.pack(side="right", fill="y", pady=5, padx=(0, 5))

        # Wczytaj istniejące okna
        self._sch_windows = list(config.schedule_windows)
        self._sch_refresh_listbox()

        # Formularz dodawania
        frm_add, in_add = self._create_labelframe(tab, "Dodaj okno")
        frm_add.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(in_add, text="Od:").grid(row=0, column=0, padx=(5, 2), pady=6, sticky="e")
        self.var_sch_start = tk.StringVar(value="08:00")
        ent_start = ctk.CTkEntry(in_add, textvariable=self.var_sch_start, width=70)
        ent_start.grid(row=0, column=1, padx=2, pady=6)
        ctk.CTkLabel(in_add, text="Do:").grid(row=0, column=2, padx=(12, 2), pady=6, sticky="e")
        self.var_sch_end = tk.StringVar(value="22:00")
        ctk.CTkEntry(in_add, textvariable=self.var_sch_end, width=70).grid(row=0, column=3, padx=2, pady=6)
        ctk.CTkLabel(in_add, text="(format HH:MM, okno przez północ np. 22:00–06:00 też działa)",
                     text_color="gray", font=("Segoe UI", 10)).grid(row=0, column=4, padx=8, pady=6, sticky="w")

        frm_btns2 = ctk.CTkFrame(tab, fg_color="transparent")
        frm_btns2.pack(pady=6)
        ctk.CTkButton(frm_btns2, text="➕ Dodaj okno", width=120, command=self._sch_add_window).pack(side="left", padx=6)
        ctk.CTkButton(frm_btns2, text="🗑 Usuń zaznaczone", width=140, fg_color="#5a3030", hover_color="#7a2020",
                      command=self._sch_remove_window).pack(side="left", padx=6)
        ctk.CTkButton(frm_btns2, text="💾 Zapisz harmonogram", width=160, fg_color="#1a4a6e", hover_color="#1a3a5e",
                      command=self._sch_save).pack(side="left", padx=6)

    def _sch_refresh_listbox(self):
        self.lb_sch.delete(0, "end")
        if not self._sch_windows:
            self.lb_sch.insert("end", "  (brak okien — bot działa bez harmonogramu)")
            return
        for i, w in enumerate(self._sch_windows):
            s = w.get("start", "??:??")
            e = w.get("end", "??:??")
            # Pokaz czy okno przekracza polnoc
            note = "  ⟳ przez północ" if s > e else ""
            self.lb_sch.insert("end", f"  {i+1:>2}.  {s}  →  {e}{note}")

    def _sch_add_window(self):
        start = self.var_sch_start.get().strip()
        end   = self.var_sch_end.get().strip()
        # Walidacja
        import re
        pat = r"^([01]?\d|2[0-3]):[0-5]\d$"
        if not re.match(pat, start) or not re.match(pat, end):
            self.log("[HARMONOGRAM] Nieprawidłowy format czasu. Użyj HH:MM (np. 08:00).")
            return
        if start == end:
            self.log("[HARMONOGRAM] Godzina startu i końca nie może być taka sama.")
            return
        self._sch_windows.append({"start": start, "end": end})
        self._sch_refresh_listbox()
        self.log(f"[HARMONOGRAM] Dodano okno: {start} → {end}")

    def _sch_remove_window(self):
        idxs = self.lb_sch.curselection()
        if not idxs or not self._sch_windows:
            return
        i = idxs[0]
        if i < len(self._sch_windows):
            removed = self._sch_windows.pop(i)
            self._sch_refresh_listbox()
            self.log(f"[HARMONOGRAM] Usunięto okno: {removed['start']} → {removed['end']}")

    def _sch_save(self):
        self.cfg.schedule_enabled       = self.var_sch_enabled.get()
        self.cfg.schedule_windows       = list(self._sch_windows)
        try:
            self.cfg.schedule_random_offset = max(0, int(self.var_sch_offset.get()))
        except ValueError:
            self.cfg.schedule_random_offset = 5
        self.cfg.save()
        state = "WŁĄCZONY" if self.cfg.schedule_enabled else "wyłączony"
        self.log(f"[HARMONOGRAM] Zapisano. Stan: {state}. Okien: {len(self._sch_windows)}.")

    # ══════════════════════════════════════════════════════════════════════════
    #  ZAKŁADKA: 🌐 Przeglądarka
    # ══════════════════════════════════════════════════════════════════════════
    def _build_tab_browser(self, tab, config: "BotConfig"):
        # ── Wybór przeglądarki ────────────────────────────────────────────────
        frm_btype, in_btype = self._create_labelframe(tab, "Wybór przeglądarki")
        frm_btype.pack(fill="x", padx=5, pady=(5, 5))

        ctk.CTkLabel(in_btype, text="Typ przeglądarki:", font=("Segoe UI", 12)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.var_browser_type = tk.StringVar(value=config.browser_type)
        frm_radio = ctk.CTkFrame(in_btype, fg_color="transparent")
        frm_radio.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        for i, (label, val) in enumerate([("🌐 Chrome", "chrome"), ("🦁 Brave", "brave"), ("🔷 Edge", "edge")]):
            ctk.CTkRadioButton(frm_radio, text=label, variable=self.var_browser_type, value=val,
                               command=self._on_browser_type_changed).grid(row=0, column=i, padx=8)

        ctk.CTkLabel(in_btype, text="Ścieżka do exe\n(puste = auto):", font=("Segoe UI", 11), text_color="gray").grid(row=1, column=0, padx=10, pady=(0,5), sticky="w")
        self.var_browser_path = tk.StringVar(value=config.browser_binary_path)
        ent_path = ctk.CTkEntry(in_btype, textvariable=self.var_browser_path, width=340, placeholder_text="np. C:\\Brave\\brave.exe  (zostaw puste = auto)")
        ent_path.grid(row=1, column=1, padx=5, pady=(0,5), sticky="w")

        # Podpowiedź ze ścieżką auto-detect
        self.lbl_auto_path = ctk.CTkLabel(in_btype, text="", font=("Segoe UI", 10, "italic"), text_color="#888888")
        self.lbl_auto_path.grid(row=2, column=1, padx=5, pady=(0,8), sticky="w")
        self._update_path_hint()

        # ── Moduły Anti-Fingerprint ──────────────────────────────────────────
        frm_sf, in_sf = self._create_labelframe(tab, "Moduły Anti-Fingerprint (CDP)")
        frm_sf.pack(fill="x", padx=5, pady=(0, 5))

        self.var_sf_webgl    = tk.BooleanVar(value=config.stealth_webgl)
        self.var_sf_canvas   = tk.BooleanVar(value=config.stealth_canvas)
        self.var_sf_audio    = tk.BooleanVar(value=config.stealth_audio)
        self.var_sf_webrtc   = tk.BooleanVar(value=config.stealth_webrtc)
        self.var_sf_timezone = tk.BooleanVar(value=config.stealth_timezone)

        checks = [
            (self.var_sf_webgl,    "🎮 WebGL",        "Podmień GPU vendor/renderer (Intel Iris OpenGL Engine)"),
            (self.var_sf_canvas,   "🖼️ Canvas",        "Dodaj mikroszum do fingerprinta canvas — każde przejście inne"),
            (self.var_sf_audio,    "🔊 AudioContext",  "Szum na próbkach Web Audio API"),
            (self.var_sf_webrtc,   "🔌 WebRTC",        "Blokuj wyciek prawdziwego IP przez ICE/STUN"),
            (self.var_sf_timezone, "🕐 Timezone",      "Wymuś Europe/Warsaw zamiast systemowej strefy"),
        ]
        for row, (var, label, tip) in enumerate(checks):
            ctk.CTkCheckBox(in_sf, text=label, variable=var, font=("Segoe UI", 12)).grid(row=row, column=0, padx=10, pady=3, sticky="w")
            ctk.CTkLabel(in_sf, text=tip, font=("Segoe UI", 10), text_color="#666666").grid(row=row, column=1, padx=(0, 10), pady=3, sticky="w")

        # ── Konfiguracja WebGL ───────────────────────────────────────────────
        frm_wgl, in_wgl = self._create_labelframe(tab, "Parametry WebGL (widoczne dla strony)")
        frm_wgl.pack(fill="x", padx=5, pady=(0, 5))

        presets = {
            # Windows — Intel (zintegrowana karta, bardzo popularna)
            "Intel UHD 630 (Windows)":   ("Google Inc. (Intel)",  "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            "Intel UHD 770 (Windows)":   ("Google Inc. (Intel)",  "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            # Windows — NVIDIA (popularne modele — nie Twój model!)
            "NVIDIA GTX 1650 (Windows)": ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            "NVIDIA RTX 3060 (Windows)": ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            # Windows — AMD
            "AMD RX 580 (Windows)":      ("Google Inc. (AMD)",    "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11)"),
            # macOS — tylko jeśli ktoś potrzebuje
            "Intel Iris (macOS)":        ("Intel Inc.",           "Intel Iris OpenGL Engine"),
        }
        ctk.CTkLabel(in_wgl, text="Preset:", font=("Segoe UI", 12)).grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.var_wgl_preset = tk.StringVar(value="-- własny --")
        combo_preset = ctk.CTkOptionMenu(in_wgl, values=["-- własny --"] + list(presets.keys()),
                                          variable=self.var_wgl_preset, width=250,
                                          command=lambda v: self._apply_webgl_preset(v, presets))
        combo_preset.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(in_wgl, text="Vendor:", font=("Segoe UI", 12)).grid(row=1, column=0, padx=10, pady=(0,5), sticky="w")
        self.var_webgl_vendor = tk.StringVar(value=config.webgl_vendor)
        ctk.CTkEntry(in_wgl, textvariable=self.var_webgl_vendor, width=300).grid(row=1, column=1, padx=5, pady=(0,5), sticky="w")

        ctk.CTkLabel(in_wgl, text="Renderer:", font=("Segoe UI", 12)).grid(row=2, column=0, padx=10, pady=(0,8), sticky="w")
        self.var_webgl_renderer = tk.StringVar(value=config.webgl_renderer)
        ctk.CTkEntry(in_wgl, textvariable=self.var_webgl_renderer, width=300).grid(row=2, column=1, padx=5, pady=(0,8), sticky="w")

        # ── Info ─────────────────────────────────────────────────────────────
        frm_info, in_info = self._create_labelframe(tab, "ℹ️ Jak uruchomić Brave z Debug Port")
        frm_info.pack(fill="x", padx=5, pady=(0, 5))
        info_text = (
            'Uruchom Brave przed botem z flagą:\n'
            '"brave.exe" --remote-debugging-port=9222 --user-data-dir=C:\\BraveProfile\n\n'
            'Lub Chrome:\n'
            '"chrome.exe" --remote-debugging-port=9222 --user-data-dir=C:\\ChromeProfile'
        )
        ctk.CTkTextbox(in_info, height=80, font=("Consolas", 11), state="normal").pack(fill="x", padx=5, pady=5)
        # Wstaw tekst do textbox
        txt_info = in_info.winfo_children()[-1]
        txt_info.insert("0.0", info_text)
        txt_info.configure(state="disabled")

        # ── Przycisk zapisu ──────────────────────────────────────────────────
        ctk.CTkButton(tab, text="💾 Zapisz ustawienia przeglądarki", height=32,
                      command=self._save_browser_settings).pack(pady=(5, 10))

    def _build_tab_settings(self, tab, config):
        frm_dsc, in_dsc = self._create_labelframe(tab, "Discord Webhook")
        frm_dsc.pack(fill="x", padx=5, pady=5)

        self.var_dsc_enabled = tk.BooleanVar(value=config.discord_enabled)
        ctk.CTkCheckBox(in_dsc, text="Włącz powiadomienia Discord", variable=self.var_dsc_enabled).pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(in_dsc, text="Webhook URL (Główny - Zgony, przerwy, bot itp.):").pack(anchor="w", padx=10, pady=(5,0))
        self.var_dsc_url = tk.StringVar(value=config.discord_webhook_url)
        ctk.CTkEntry(in_dsc, textvariable=self.var_dsc_url, width=400).pack(fill="x", padx=10, pady=5)

        self.var_dsc_pm = tk.BooleanVar(value=config.discord_private_messages)
        ctk.CTkCheckBox(in_dsc, text="Wysyłaj wiadomości prywatne (z gry) na Discord", variable=self.var_dsc_pm).pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(in_dsc, text="Webhook URL (TYLKO na Prywatne Wiadomości):").pack(anchor="w", padx=10, pady=(5,0))
        self.var_dsc_pm_url = tk.StringVar(value=getattr(config, 'discord_webhook_pm_url', ''))
        ctk.CTkEntry(in_dsc, textvariable=self.var_dsc_pm_url, width=400, placeholder_text="Zostaw puste, by wysyłać na główny Webhook").pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(in_dsc, text="💾 Zapisz ustawienia Discord", command=self._save_discord_settings).pack(pady=10)

    def _save_discord_settings(self):
        self.cfg.discord_enabled = self.var_dsc_enabled.get()
        self.cfg.discord_webhook_url = self.var_dsc_url.get().strip()
        self.cfg.discord_private_messages = self.var_dsc_pm.get()
        self.cfg.discord_webhook_pm_url = self.var_dsc_pm_url.get().strip()
        self.cfg.save()
        self.log(f"[USTAWIENIA] Zapisano konfigurację Discord.")

    def _save_discord_settings(self):
        self.cfg.discord_enabled = self.var_dsc_enabled.get()
        self.cfg.discord_webhook_url = self.var_dsc_url.get().strip()
        self.cfg.discord_private_messages = self.var_dsc_pm.get()
        self.cfg.save()
        self.log(f"[USTAWIENIA] Zapisano konfigurację Discord.")

    def _on_browser_type_changed(self):
        self._update_path_hint()

    def _update_path_hint(self):
        import sys, os
        btype = getattr(self, 'var_browser_type', None)
        if not btype: return
        from game import _detect_binary
        path = _detect_binary(btype.get())
        if path:
            exists = "✅ znaleziono" if os.path.exists(path) else "❌ nie znaleziono"
            self.lbl_auto_path.configure(text=f"Auto: {path}  [{exists}]")
        else:
            self.lbl_auto_path.configure(text="Auto: (ChromeDriver wykryje automatycznie)")

    def _apply_webgl_preset(self, name, presets):
        if name in presets:
            vendor, renderer = presets[name]
            self.var_webgl_vendor.set(vendor)
            self.var_webgl_renderer.set(renderer)

    def _save_browser_settings(self):
        self.cfg.browser_type        = self.var_browser_type.get()
        self.cfg.browser_binary_path = self.var_browser_path.get().strip()
        self.cfg.stealth_webgl       = self.var_sf_webgl.get()
        self.cfg.stealth_canvas      = self.var_sf_canvas.get()
        self.cfg.stealth_audio       = self.var_sf_audio.get()
        self.cfg.stealth_webrtc      = self.var_sf_webrtc.get()
        self.cfg.stealth_timezone    = self.var_sf_timezone.get()
        self.cfg.webgl_vendor        = self.var_webgl_vendor.get().strip()
        self.cfg.webgl_renderer      = self.var_webgl_renderer.get().strip()
        self.cfg.save()
        self.log(f"[PRZEGLĄDARKA] Zapisano. Typ: {self.cfg.browser_type} | WebGL: {self.cfg.webgl_vendor}")

    def _build_tab_margoworld(self, tab):
        ctk.CTkLabel(tab, text="Wyszukaj nazwy map do skopiowania do trasy (po przecinku)", font=("Segoe UI", 12, "italic"), text_color="gray").pack(padx=10, pady=(10, 5), anchor="w")

        frm_search = ctk.CTkFrame(tab, fg_color="transparent")
        frm_search.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(frm_search, text="Szukaj mapy:").pack(side="left", padx=(0, 5))
        self.var_map_search = tk.StringVar()
        self.var_map_search.trace_add("write", self._on_map_search_changed)
        ctk.CTkEntry(frm_search, textvariable=self.var_map_search, width=220).pack(side="left", padx=5)
        self.btn_mw_load = ctk.CTkButton(frm_search, text="⬇ Pobierz listę", command=self._load_world_maps)
        self.btn_mw_load.pack(side="left", padx=10)
        self.lbl_mw_status = ctk.CTkLabel(frm_search, text="(nie pobrano)", text_color="gray")
        self.lbl_mw_status.pack(side="left", padx=5)

        frm_res, in_res = self._create_labelframe(tab, "Wyniki")
        frm_res.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Standardowy tk.Listbox dobrze sformatowany dla trybu ciemnego
        self.lb_maps = tk.Listbox(in_res, height=12, font=("Consolas", 12), selectmode="extended",
                                  bg="#2b2b2b", fg="#ffffff", selectbackground="#1f538d", borderwidth=0, highlightthickness=0)
        
        sb = tk.Scrollbar(in_res, orient="vertical", command=self.lb_maps.yview)
        self.lb_maps.configure(yscrollcommand=sb.set)
        self.lb_maps.pack(side="left", fill="both", expand=True, padx=(5, 0), pady=5)
        sb.pack(side="right", fill="y", pady=5, padx=(0, 5))
        self.lb_maps.bind("<Double-Button-1>", self._on_map_double_click)

        frm_path, in_path = self._create_labelframe(tab, "Budowa Trasy")
        frm_path.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(in_path, text="Trasa:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.var_built_path = tk.StringVar()
        ctk.CTkEntry(in_path, textvariable=self.var_built_path, width=480).grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        frm_pbtn = ctk.CTkFrame(in_path, fg_color="transparent")
        frm_pbtn.grid(row=1, column=0, columnspan=2, pady=5)
        ctk.CTkButton(frm_pbtn, text="➕ Dodaj", width=80, command=self._mw_add_selected).pack(side="left", padx=5)
        ctk.CTkButton(frm_pbtn, text="🗑 Wyczyść", width=80, command=lambda: self.var_built_path.set("")).pack(side="left", padx=5)

    # ══════════════════════════════════════════════════════════
    #  Zdarzenia
    # ══════════════════════════════════════════════════════════
    def _apply_levels(self):
        try:
            mn, mx = self.var_min.get(), self.var_max.get()
            if mn > mx: mn, mx = mx, mn
            self.cfg.min_lvl, self.cfg.max_lvl = mn, mx
            
            mn_g, mx_g = self.var_min_grp.get(), self.var_max_grp.get()
            if mn_g > mx_g: mn_g, mx_g = mx_g, mn_g
            self.cfg.min_group, self.cfg.max_group = mn_g, mx_g

            self.cfg.avoid_elites = self.var_avoid_elites.get()

            self.cfg.save()
            self.log(f"Zapisano: Lvl {mn}-{mx}, Grupa {mn_g}-{mx_g}, Unikaj Elit: {self.cfg.avoid_elites}")
        except Exception as e:
            self.log(f"Błąd konfiguracji level/grupa: {e}")

    def _apply_maps(self):
        raw = self.txt_maps.get("0.0", "end").strip()
        maps = [l.strip() for l in raw.splitlines() if l.strip()]
        if not maps: return self.log("Lista map pusta!")
        self.cfg.map_keywords = maps
        self.cfg.save()
        self.log(f"Zapisano mapy ({len(maps)})")

    def _load_expowiska(self):
        self.btn_load_exp.configure(state="disabled")
        self.lbl_exp_status.configure(text="Pobieranie…", text_color="orange")
        self.log("Pobieram z MargoWorld…")
        def _w():
            try:
                data = fetch_expowiska_list()
                self._expowiska_list = data
                self._expowiska_filtered = data
                self.root.after(0, lambda: self._fill_exp_listbox(data))
                self.root.after(0, lambda: self.lbl_exp_status.configure(
                    text=f"✓ {len(data)} expowisk", text_color="green"))
                self.root.after(0, lambda: self.log(f"Załadowano {len(data)} expowisk!"))
            except Exception as e:
                self.root.after(0, lambda: self.lbl_exp_status.configure(text="Błąd!", text_color="red"))
                self.root.after(0, lambda: self.log(f"Błąd: {e}"))
            finally:
                self.root.after(0, lambda: self.btn_load_exp.configure(state="normal"))
        threading.Thread(target=_w, daemon=True).start()

    def _fill_exp_listbox(self, data):
        self.lb_exp.delete(0, "end")
        self._expowiska_filtered = data
        for e in data:
            lvl = e.get("level", 0)
            label = f"[{lvl:>3} lvl]  {e['name']}" if lvl else f"         {e['name']}"
            self.lb_exp.insert("end", label)

    def _on_exp_search_changed(self, *_):
        q = self.var_exp_search.get().strip().lower()
        filtered = [e for e in self._expowiska_list if q in e["name"].lower()] if q else self._expowiska_list
        self._fill_exp_listbox(filtered)

    def _on_exp_selected_lb(self):
        idxs = self.lb_exp.curselection()
        if not idxs:
            return
        exp = self._expowiska_filtered[idxs[0]]
        self.log(f"Pobieram detale dla: {exp['name']}…")
        def _w():
            try:
                details = fetch_expowisko_details(exp["url"])
                self.root.after(0, lambda: self._apply_exp_details(exp, details))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Błąd detali: {e}"))
        threading.Thread(target=_w, daemon=True).start()

    def _apply_exp_details(self, exp, details):
        if details["min_lvl"] > 0:
            self.var_min.set(details["min_lvl"]); self.var_max.set(details["max_lvl"])
            self.cfg.min_lvl = details["min_lvl"]; self.cfg.max_lvl = details["max_lvl"]
        if details["maps"]:
            self.txt_maps.delete("0.0", "end")
            self.txt_maps.insert("0.0", "\n".join(details["maps"]))
            self.cfg.map_keywords = details["maps"]
        self.cfg.save()
        self.log(f"Zastosowano: {exp['name']}")

    def _apply_restock(self):
        self.cfg.restock_enabled = self.var_restock.get()
        self.cfg.restock_teleport = self.var_rs_teleport.get().strip()
        self.cfg.restock_npc = self.var_rs_npc.get().strip()
        self.cfg.restock_shop_map = self.var_rs_map.get().strip()
        self.cfg.restock_sell_sequence = self.var_rs_bags.get().strip()
        self.cfg.restock_return_method = self.var_return_method.get()
        self.cfg.restock_return_scroll = self.var_rs_return.get().strip()
        self.cfg.restock_return_walk_path = self.var_rs_walk_path.get().strip()
        
        # Nowe powroty ze śmierci
        self.cfg.death_return_path = self.var_death_path.get().strip()
        self.cfg.preferred_character = self.var_preferred_char.get().strip()

        # NPC
        self.cfg.npc_teleport_npc_name = "Zakonnik Planu Astralnego"
        self.cfg.npc_teleport_npc_map = self.var_tp_map.get().strip()
        self.cfg.npc_teleport_city = self.var_tp_city.get().strip()
        self.cfg.npc_teleport_walk_to_npc = self.var_tp_walk_to_npc.get().strip()
        self.cfg.npc_teleport_after_path = self.var_tp_after.get().strip()
        self.cfg.save()
        self.log("Zapisano ustawienia powrotów i restocku!")

    def _trigger_npc_teleport(self):
        self._apply_restock()
        if not (self.bot_thread and self.bot_thread.is_alive()):
            self.log("[NPC-TP] Startuję sam teleport…")
            threading.Thread(target=lambda: npc_teleport_routine(connect(self.cfg), self.cfg, self), daemon=True).start()
        else:
            self.log("[NPC-TP] Teleport dodany do kolejki.")
            self.cfg._npc_teleport_pending = True

    def _load_world_maps(self):
        self.btn_mw_load.configure(state="disabled")
        self.lbl_mw_status.configure(text="Pobieranie…", text_color="orange")
        def _w():
            try:
                data = fetch_world_map_list(force=True)
                self.root.after(0, lambda: self._fill_maps([m["name"] for m in data]))
                self.root.after(0, lambda: self.lbl_mw_status.configure(text=f"✓ {len(data)} map", text_color="green"))
            except Exception as e:
                self.root.after(0, lambda: self.lbl_mw_status.configure(text="Błąd!", text_color="red"))
            finally:
                self.root.after(0, lambda: self.btn_mw_load.configure(state="normal"))
        threading.Thread(target=_w, daemon=True).start()

    def _fill_maps(self, names):
        self.lb_maps.delete(0, "end")
        for n in names: self.lb_maps.insert("end", n)

    def _on_map_search_changed(self, *_):
        q = self.var_map_search.get().strip().lower()
        res = search_world_maps(q, limit=200)
        self._fill_maps([m["name"] for m in res])

    def _on_map_double_click(self, event=None):
        self._mw_add_selected()

    def _mw_add_selected(self):
        idx = self.lb_maps.curselection()
        if not idx: return
        sel = [self.lb_maps.get(i) for i in idx]
        cur = self.var_built_path.get().strip()
        self.var_built_path.set((cur + ", " if cur else "") + ", ".join(sel))

    def _toggle_run(self):
        if self.bot_thread and self.bot_thread.is_alive():
            self.cfg.running = False
            self.btn_run.configure(text="▶ START", fg_color="#2b8a3e", hover_color="#237032")
            self.btn_pause.configure(state="disabled")
            self.log("Zatrzymuję bota…")
        else:
            self.cfg.running = True
            self.cfg.paused = False
            self.btn_run.configure(text="⏹ STOP", fg_color="#c0392b", hover_color="#922b21")
            self.btn_pause.configure(state="normal", text="⏸ Pauza")
            self.bot_thread = threading.Thread(target=bot_loop, args=(self.cfg, self), daemon=True)
            self.bot_thread.start()
            self.log("Bot uruchomiony!")

    def _toggle_pause(self):
        if self.cfg.paused:
            self.cfg.paused = False
            self.btn_pause.configure(text="⏸ Pauza")
            self.log("Wznowiono.")
        else:
            self.cfg.paused = True
            self.btn_pause.configure(text="▶ Wznów")
            self.log("Wstrzymano (pauza).")

    def _hotkey_toggle(self):
        self.root.after(0, self._toggle_visibility)

    def _toggle_visibility(self):
        if self.root.state() == "withdrawn":
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
        else:
            self.root.withdraw()

    def _on_close(self):
        self.root.withdraw()

    def log(self, msg: str):
        def _i():
            self.log_widget.configure(state="normal")
            self.log_widget.insert("end", msg + "\n")
            self.log_widget.see("end")
            self.log_widget.configure(state="disabled")
        self.root.after(0, _i)

    def _refresh_status(self):
        self.lbl_status.configure(text=f"Status: {self.cfg.status}")
        self.lbl_map.configure(text=f"Mapa: {self.cfg.current_map or '—'}")
        self.lbl_kills.configure(text=f"Zabito: {self.cfg.kills}")
        if self.bot_thread and not self.bot_thread.is_alive() and self.cfg.running:
            self.btn_run.configure(text="▶ START", fg_color="#2b8a3e", hover_color="#237032")
            self.btn_pause.configure(state="disabled")
        self.root.after(500, self._refresh_status)

    def run(self):
        self.root.mainloop()
        self.cfg.running = False
