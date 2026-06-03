import customtkinter as ctk

FIELDS = ["temp", "feels_like", "humidity", "wind_speed", "pressure", "visibility", "clouds"]
FIELD_LABELS = {
    "temp": "Temperature (°)",
    "feels_like": "Feels Like (°)",
    "humidity": "Humidity (%)",
    "wind_speed": "Wind Speed (m/s)",
    "pressure": "Pressure (hPa)",
    "visibility": "Visibility (m)",
    "clouds": "Cloud Cover (%)",
}
OPERATORS = [">", ">=", "<", "<=", "=="]


class AlertRulesDialog(ctk.CTkToplevel):
    """Dialog for managing custom weather alert rules."""

    def __init__(self, master, app_config, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Custom Alert Rules")
        self.geometry("520x560")
        self.app_config = app_config
        self.attributes("-topmost", True)
        self.grab_set()
        self._setup_ui()
        self._refresh_list()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        ctk.CTkLabel(self, text="⚡ Custom Alert Rules",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 2))
        ctk.CTkLabel(self, text="Get notified when weather conditions cross your thresholds",
                     font=ctk.CTkFont(size=12), text_color="gray").pack()

        # Existing rules list
        ctk.CTkLabel(self, text="Active Rules",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(15, 4))
        self.rules_frame = ctk.CTkScrollableFrame(self, height=160)
        self.rules_frame.pack(fill="x", padx=20)

        # Separator
        ctk.CTkFrame(self, height=2, fg_color=("gray80", "gray30")).pack(fill="x", padx=20, pady=12)

        # Add-rule form
        ctk.CTkLabel(self, text="Add New Rule",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(0, 8))

        row1 = ctk.CTkFrame(self, fg_color="transparent")
        row1.pack(fill="x", padx=20)
        row1.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkLabel(row1, text="Field").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(row1, text="Operator").grid(row=0, column=1, sticky="w", padx=5)
        ctk.CTkLabel(row1, text="Threshold").grid(row=0, column=2, sticky="w")

        display_values = [FIELD_LABELS[f] for f in FIELDS]
        self._field_combo = ctk.CTkComboBox(row1, values=display_values, width=170)
        self._field_combo.set(display_values[0])
        self._field_combo.grid(row=1, column=0, sticky="ew", padx=(0, 5), pady=4)

        self._op_combo = ctk.CTkComboBox(row1, values=OPERATORS, width=80)
        self._op_combo.set(">")
        self._op_combo.grid(row=1, column=1, sticky="ew", padx=5, pady=4)

        self._threshold_entry = ctk.CTkEntry(row1, placeholder_text="e.g. 35")
        self._threshold_entry.grid(row=1, column=2, sticky="ew", padx=(5, 0), pady=4)

        ctk.CTkLabel(self, text="Notification Label").pack(anchor="w", padx=20, pady=(8, 3))
        self._label_entry = ctk.CTkEntry(self, placeholder_text="e.g. Heat Warning")
        self._label_entry.pack(fill="x", padx=20)

        self._error_lbl = ctk.CTkLabel(self, text="", text_color="red", font=ctk.CTkFont(size=12))
        self._error_lbl.pack()

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=12)
        ctk.CTkButton(btn_row, text="➕ Add Rule", command=self._add_rule).pack(side="left")
        ctk.CTkButton(btn_row, text="Close", command=self.destroy,
                      fg_color="transparent", border_width=1).pack(side="right")

    # ------------------------------------------------------------------
    def _refresh_list(self):
        for w in self.rules_frame.winfo_children():
            w.destroy()
        rules = self.app_config.get("alert_rules", [])
        if not rules:
            ctk.CTkLabel(self.rules_frame, text="No rules yet. Add one below.",
                         text_color="gray").pack(pady=12)
            return
        for i, rule in enumerate(rules):
            row = ctk.CTkFrame(self.rules_frame, corner_radius=8)
            row.pack(fill="x", pady=3, padx=5)
            fl = FIELD_LABELS.get(rule["field"], rule["field"])
            text = f"📢 {rule.get('label', 'Alert')}   —   {fl} {rule['operator']} {rule['threshold']}"
            ctk.CTkLabel(row, text=text, font=ctk.CTkFont(size=12),
                         anchor="w").pack(side="left", padx=10, pady=8, fill="x", expand=True)
            ctk.CTkButton(row, text="🗑", width=32, fg_color="transparent",
                          hover_color="#ff5e5e",
                          command=lambda idx=i: self._delete_rule(idx)).pack(side="right", padx=6)

    def _add_rule(self):
        self._error_lbl.configure(text="")
        display = self._field_combo.get()
        display_list = [FIELD_LABELS[f] for f in FIELDS]
        try:
            field = FIELDS[display_list.index(display)]
        except ValueError:
            field = FIELDS[0]

        operator = self._op_combo.get()
        label = self._label_entry.get().strip() or "Weather Alert"
        try:
            threshold = float(self._threshold_entry.get().strip())
        except ValueError:
            self._error_lbl.configure(text="⚠ Threshold must be a number")
            return

        rules = self.app_config.get("alert_rules", [])
        rules.append({"field": field, "operator": operator,
                      "threshold": threshold, "label": label})
        self.app_config.set("alert_rules", rules)
        self._threshold_entry.delete(0, "end")
        self._label_entry.delete(0, "end")
        self._refresh_list()

    def _delete_rule(self, index: int):
        rules = self.app_config.get("alert_rules", [])
        rules.pop(index)
        self.app_config.set("alert_rules", rules)
        self._refresh_list()
