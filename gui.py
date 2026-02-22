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

        self.tab_exp = self.tabview.add("🗡 Expowisko")
        self.tab_rs = self.tabview.add("🛒 Powroty & Restock")
        self.tab_mw = self.tabview.add("🗺 Trasy")

        self._build_tab_expowisko(self.tab_exp, config)
        self._build_tab_restock(self.tab_rs, config)
        self._build_tab_margoworld(self.tab_mw)

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
        self.combo_exp = ctk.CTkComboBox(in_mw, state="readonly", width=300, command=self._on_exp_selected)
        self.combo_exp.set("← kliknij 'Załaduj listę'")
        self.combo_exp.pack(side="left", padx=(5, 5), pady=5, fill="x", expand=True)
        
        self.btn_load_exp = ctk.CTkButton(in_mw, text="Załaduj listę", command=self._load_expowiska)
        self.btn_load_exp.pack(side="right", padx=(5, 5), pady=5)

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
        
        ctk.CTkLabel(in_death, text="Trasa map:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.var_death_path = tk.StringVar(value=config.death_return_path)
        ctk.CTkEntry(in_death, textvariable=self.var_death_path, width=440).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkLabel(in_death, text="(od miasta do expowiska)", text_color="gray", font=("Segoe UI", 11)).grid(row=1, column=1, padx=5, sticky="w")

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

            self.cfg.save()
            self.log(f"Zapisano: Lvl {mn}-{mx}, Grupa {mn_g}-{mx_g}")
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
        self.log("Pobieram z MargoWorld…")
        def _w():
            try:
                data = fetch_expowiska_list()
                self._expowiska_list = data
                names = [e["name"] for e in data]
                self.root.after(0, lambda: self.combo_exp.configure(values=names))
                self.root.after(0, lambda: self.combo_exp.set("Wybierz expowisko…"))
                self.root.after(0, lambda: self.log(f"Załadowano {len(data)} expowisk!"))
            except Exception as e:
                self.root.after(0, lambda: self.log(f"Błąd: {e}"))
            finally:
                self.root.after(0, lambda: self.btn_load_exp.configure(state="normal"))
        threading.Thread(target=_w, daemon=True).start()

    def _on_exp_selected(self, value):
        idx = [e["name"] for e in self._expowiska_list].index(value)
        exp = self._expowiska_list[idx]
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
            threading.Thread(target=lambda: npc_teleport_routine(connect(), self.cfg, self), daemon=True).start()
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