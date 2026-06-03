import customtkinter as ctk


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_search, on_add_location, on_show_settings,
                 on_show_dashboard, on_remove_location,
                 on_show_commute, on_show_alert_rules, on_toggle_overlay,
                 config, api_client, **kwargs):
        super().__init__(master, width=300, corner_radius=0, **kwargs)
        self.on_search = on_search
        self.on_add_location = on_add_location
        self.on_show_settings = on_show_settings
        self.on_show_dashboard = on_show_dashboard
        self.on_remove_location = on_remove_location
        self.on_show_commute = on_show_commute
        self.on_show_alert_rules = on_show_alert_rules
        self.on_toggle_overlay = on_toggle_overlay
        self.app_config = config
        self.api_client = api_client

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1)   # locations scroll expands
        self._alerts_visible = True
        self._setup_ui()

    # ------------------------------------------------------------------ setup
    def _setup_ui(self):
        # Logo
        ctk.CTkLabel(self, text="Weather Pro",
                     font=ctk.CTkFont(size=24, weight="bold")).grid(
            row=0, column=0, padx=20, pady=(18, 4))

        # Appearance mode toggle (Light / Dark / Auto)
        mode_seg = ctk.CTkSegmentedButton(
            self, values=["Light", "Dark", "Auto"],
            command=self._on_mode_change, width=260, height=28,
        )
        mode_seg.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        saved_mode = self.app_config.get("appearance_mode", "System")
        mode_seg.set("Auto" if saved_mode == "System" else saved_mode)
        self._mode_seg = mode_seg

        # Search bar
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        self.city_entry = ctk.CTkEntry(
            search_frame, placeholder_text="Enter city name…")
        self.city_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.city_entry.bind("<Return>", lambda e: self.trigger_search())
        self.city_entry.bind("<KeyRelease>", self._on_key_release)
        self.search_btn = ctk.CTkButton(
            search_frame, text="🔍", width=40, command=self.trigger_search)
        self.search_btn.pack(side="left")

        # Saved locations header
        ctk.CTkLabel(self, text="Saved Locations",
                     font=ctk.CTkFont(size=14, weight="bold")).grid(
            row=3, column=0, padx=20, pady=(10, 0), sticky="w")

        self.locations_scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent")
        self.locations_scroll.grid(
            row=4, column=0, padx=10, pady=5, sticky="nsew")

        # Alerts collapsible panel
        self.alerts_header = ctk.CTkButton(
            self, text="✅ No Active Alerts ▼",
            fg_color="transparent", border_width=1,
            border_color=("gray70", "gray30"),
            text_color=("gray10", "gray90"), height=28,
            command=self._toggle_alerts,
        )
        self.alerts_header.grid(row=5, column=0, padx=20, pady=(5, 0), sticky="ew")

        self.alerts_panel = ctk.CTkScrollableFrame(
            self, fg_color="transparent", height=80)
        self.alerts_panel.grid(
            row=6, column=0, padx=10, pady=(0, 5), sticky="ew")

        # Add location button
        ctk.CTkButton(
            self, text="➕ Add Current Location",
            command=self.on_add_location,
        ).grid(row=7, column=0, padx=20, pady=(5, 3), sticky="ew")

        # Settings + Dashboard row
        row_a = ctk.CTkFrame(self, fg_color="transparent")
        row_a.grid(row=8, column=0, padx=20, pady=3, sticky="ew")
        row_a.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            row_a, text="⚙️ Settings", command=self.on_show_settings,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ctk.CTkButton(
            row_a, text="🌍 Dashboard", command=self.on_show_dashboard,
            fg_color="#3a7bd5", hover_color="#3a6073",
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # Commute + Alert Rules row
        row_b = ctk.CTkFrame(self, fg_color="transparent")
        row_b.grid(row=9, column=0, padx=20, pady=3, sticky="ew")
        row_b.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            row_b, text="🚗 Commute", command=self.on_show_commute,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
        ).grid(row=0, column=0, sticky="ew", padx=(0, 3))
        ctk.CTkButton(
            row_b, text="🔔 Alert Rules", command=self.on_show_alert_rules,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
        ).grid(row=0, column=1, sticky="ew", padx=(3, 0))

        # Widget overlay toggle
        self.overlay_btn = ctk.CTkButton(
            self, text="📟 Show Widget Overlay",
            command=self.on_toggle_overlay,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"),
        )
        self.overlay_btn.grid(row=10, column=0, padx=20, pady=3, sticky="ew")

        # Status label
        self.status_label = ctk.CTkLabel(
            self, text="Ready", font=ctk.CTkFont(size=12), text_color="gray")
        self.status_label.grid(row=11, column=0, padx=20, pady=(0, 10))

        self.update_locations_list()

    # ------------------------------------------------------------------ mode toggle
    def _on_mode_change(self, mode: str):
        ctk_mode = "System" if mode == "Auto" else mode
        ctk.set_appearance_mode(ctk_mode)
        self.app_config.set("appearance_mode", ctk_mode)

    # ------------------------------------------------------------------ alerts
    def _toggle_alerts(self):
        self._alerts_visible = not self._alerts_visible
        if self._alerts_visible:
            self.alerts_panel.grid()
        else:
            self.alerts_panel.grid_remove()

    def update_alerts(self, alerts: list):
        for w in self.alerts_panel.winfo_children():
            w.destroy()
        n = len(alerts)
        arrow = "▼" if self._alerts_visible else "▶"
        if n == 0:
            self.alerts_header.configure(text=f"✅ No Active Alerts {arrow}")
        else:
            self.alerts_header.configure(text=f"⚠️ Alerts ({n}) {arrow}")
        for alert in alerts:
            level = alert.get("level", "info")
            color = {"danger": "#b02020", "warning": "#b07020"}.get(level, "#205080")
            ctk.CTkLabel(
                self.alerts_panel, text=alert.get("message", ""),
                fg_color=color, corner_radius=6,
                font=ctk.CTkFont(size=11), text_color="white",
                wraplength=240, justify="left",
            ).pack(fill="x", padx=5, pady=2)

    # ------------------------------------------------------------------ locations
    def update_locations_list(self):
        for w in self.locations_scroll.winfo_children():
            w.destroy()
        for i, loc in enumerate(self.app_config.get("saved_locations", [])):
            row = ctk.CTkFrame(self.locations_scroll, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkButton(
                row, text=loc["name"], anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray70", "gray30"),
                command=lambda n=loc["name"]: self.trigger_search(n),
            ).pack(side="left", fill="x", expand=True)
            ctk.CTkButton(
                row, text="❌", width=30,
                fg_color="transparent", hover_color="#ff5e5e",
                command=lambda idx=i: self.on_remove_location(idx),
            ).pack(side="right")

    # ------------------------------------------------------------------ misc
    def set_status(self, text: str):
        self.status_label.configure(text=text)

    def set_overlay_btn_text(self, visible: bool):
        txt = "📟 Hide Widget Overlay" if visible else "📟 Show Widget Overlay"
        self.overlay_btn.configure(text=txt)

    def trigger_search(self, city: str = ""):
        if city:
            self.city_entry.delete(0, "end")
            self.city_entry.insert(0, city)
        city = self.city_entry.get().strip()
        self.on_search(city)

    # ------------------------------------------------------------------ autofill
    def _on_key_release(self, event):
        if event.keysym in ("Return", "Up", "Down", "Left", "Right", "Escape"):
            return
        query = self.city_entry.get().strip()
        if len(query) < 3:
            self._close_autofill()
            return
        if hasattr(self, "_af_timer"):
            self.after_cancel(self._af_timer)
        self._af_timer = self.after(
            400,
            lambda: self.api_client.fetch_autofill(query, self._show_autofill))

    def _show_autofill(self, data: list):
        self._close_autofill()
        if not data:
            return
        self.autofill_frame = ctk.CTkFrame(
            self, fg_color=("gray95", "gray15"),
            corner_radius=8, border_width=1,
            border_color=("gray75", "gray25"))
        # find search_frame
        sf = [w for w in self.grid_slaves(row=2, column=0)]
        parent = sf[0] if sf else self
        self.autofill_frame.place(in_=parent, relx=0, rely=1.0,
                                   relwidth=1.0, y=5)
        self.autofill_frame.lift()
        for item in data:
            parts = [p for p in [item.get("name"), item.get("state", ""),
                                 item.get("country", "")] if p]
            full = ", ".join(parts)
            disp = full if len(full) <= 30 else full[:28] + "…"
            ctk.CTkButton(
                self.autofill_frame, text=disp, anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray85", "gray25"),
                corner_radius=6, height=32,
                command=lambda t=full: self._select_autofill(t),
            ).pack(fill="x", padx=6, pady=3)
        self.bind_all("<Button-1>", self._check_autofill_click, add="+")

    def _select_autofill(self, text: str):
        self.trigger_search(text)
        self._close_autofill()

    def _close_autofill(self):
        if hasattr(self, "autofill_frame") and self.autofill_frame.winfo_exists():
            self.autofill_frame.destroy()

    def _check_autofill_click(self, event):
        if hasattr(self, "autofill_frame") and self.autofill_frame.winfo_exists():
            x, y = self.winfo_pointerxy()
            widget = self.winfo_containing(x, y)
            cur = widget
            inside = False
            while cur:
                if cur in (self.autofill_frame, self.city_entry):
                    inside = True
                    break
                cur = cur.master
            if not inside:
                self._close_autofill()
