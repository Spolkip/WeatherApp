import customtkinter as ctk
from utils import get_icon


class CommutePlanner(ctk.CTkToplevel):
    """Shows side-by-side weather comparison for two cities (origin → destination)."""

    def __init__(self, master, api_client, app_config, icon_cache, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Commute Weather Planner")
        self.geometry("720x530")
        self.api_client = api_client
        self.app_config = app_config
        self.icon_cache = icon_cache
        self._results: dict = {}
        self.attributes("-topmost", True)
        self.grab_set()
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self):
        ctk.CTkLabel(self, text="🚗 Commute Weather Planner",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 3))
        ctk.CTkLabel(self, text="Compare weather at your origin and destination",
                     font=ctk.CTkFont(size=12), text_color="gray").pack()

        # Input row
        inp = ctk.CTkFrame(self, fg_color="transparent")
        inp.pack(fill="x", padx=24, pady=14)
        inp.grid_columnconfigure((0, 2), weight=1)
        inp.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(inp, text="Origin City").grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(inp, text="Destination City").grid(row=0, column=2, sticky="w")

        self.origin_entry = ctk.CTkEntry(inp, placeholder_text="e.g. London")
        self.origin_entry.grid(row=1, column=0, sticky="ew", padx=(0, 6), pady=4)

        ctk.CTkLabel(inp, text="→", font=ctk.CTkFont(size=22)).grid(row=1, column=1, padx=8)

        self.dest_entry = ctk.CTkEntry(inp, placeholder_text="e.g. Paris")
        self.dest_entry.grid(row=1, column=2, sticky="ew", padx=(6, 0), pady=4)

        self.check_btn = ctk.CTkButton(self, text="🔍 Check Weather", command=self._check)
        self.check_btn.pack(pady=4)

        self.status_lbl = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=12), text_color="gray")
        self.status_lbl.pack()

        # Results panels (side by side)
        panels = ctk.CTkFrame(self, fg_color="transparent")
        panels.pack(fill="both", expand=True, padx=20, pady=8)
        panels.grid_columnconfigure((0, 1), weight=1)
        panels.grid_rowconfigure(0, weight=1)

        self.origin_panel = self._make_panel(panels, "📍 Origin")
        self.origin_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 6))

        self.dest_panel = self._make_panel(panels, "📍 Destination")
        self.dest_panel.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

    def _make_panel(self, parent, title: str) -> ctk.CTkFrame:
        panel = ctk.CTkFrame(parent, corner_radius=14)
        panel.title_lbl = ctk.CTkLabel(  # type: ignore[attr-defined]
            panel, text=title, font=ctk.CTkFont(size=15, weight="bold"))
        panel.title_lbl.pack(pady=(14, 2))  # type: ignore[attr-defined]

        panel.city_lbl = ctk.CTkLabel(panel, text="—",  # type: ignore[attr-defined]
                                      font=ctk.CTkFont(size=13), text_color="gray")
        panel.city_lbl.pack()  # type: ignore[attr-defined]

        panel.icon_lbl = ctk.CTkLabel(panel, text="", width=80, height=80)  # type: ignore[attr-defined]
        panel.icon_lbl.pack(pady=4)  # type: ignore[attr-defined]

        panel.temp_lbl = ctk.CTkLabel(panel, text="--°",  # type: ignore[attr-defined]
                                      font=ctk.CTkFont(size=44, weight="bold"))
        panel.temp_lbl.pack()  # type: ignore[attr-defined]

        panel.desc_lbl = ctk.CTkLabel(panel, text="",  # type: ignore[attr-defined]
                                      font=ctk.CTkFont(size=13), text_color="gray")
        panel.desc_lbl.pack(pady=2)  # type: ignore[attr-defined]

        panel.details_lbl = ctk.CTkLabel(panel, text="",  # type: ignore[attr-defined]
                                         font=ctk.CTkFont(size=12), text_color="gray",
                                         justify="center")
        panel.details_lbl.pack(pady=(0, 14))  # type: ignore[attr-defined]
        return panel

    # ------------------------------------------------------------------
    def _check(self):
        origin = self.origin_entry.get().strip()
        dest = self.dest_entry.get().strip()
        if not origin or not dest:
            self.status_lbl.configure(text="⚠ Please enter both cities", text_color="orange")
            return
        if not self.app_config.get("api_key"):
            self.status_lbl.configure(text="API key not configured", text_color="red")
            return

        self._results = {}
        self.check_btn.configure(state="disabled")
        self.status_lbl.configure(text="Fetching weather…", text_color="gray")

        def on_success(key: str, data: dict):
            self._results[key] = data
            self.after(0, lambda: self._update_panel(
                self.origin_panel if key == "origin" else self.dest_panel, data))
            if len(self._results) == 2:
                self.after(0, self._compare)
                self.after(0, lambda: self.check_btn.configure(state="normal"))

        def on_err(which: str, msg: str):
            self.after(0, lambda: self.status_lbl.configure(
                text=f"Error fetching {which}: {msg}", text_color="red"))
            self.after(0, lambda: self.check_btn.configure(state="normal"))

        self.api_client.fetch_weather(origin,
            lambda d: on_success("origin", d),
            lambda e: on_err("origin", e))
        self.api_client.fetch_weather(dest,
            lambda d: on_success("dest", d),
            lambda e: on_err("dest", e))

    def _update_panel(self, panel, data: dict):
        cw = data["current"]
        loc = data["location"]
        units = self.app_config.get("units", "metric")
        unit_str = "°C" if units == "metric" else "°F"
        speed_unit = "m/s" if units == "metric" else "mph"

        city = loc.get("name", cw["name"])
        country = cw.get("sys", {}).get("country", "")
        temp = round(cw["main"]["temp"])
        feels = round(cw["main"]["feels_like"])
        desc = cw["weather"][0]["description"].title()
        humidity = cw["main"]["humidity"]
        wind = cw["wind"]["speed"]
        pop_next = round(data["forecast"]["list"][0].get("pop", 0) * 100)

        panel.city_lbl.configure(text=f"{city}, {country}")  # type: ignore[attr-defined]
        panel.temp_lbl.configure(text=f"{temp}{unit_str}")    # type: ignore[attr-defined]
        panel.desc_lbl.configure(text=desc)                   # type: ignore[attr-defined]
        panel.details_lbl.configure(                          # type: ignore[attr-defined]
            text=f"Feels like {feels}{unit_str}\n"
                 f"💧 {humidity}%   🌬️ {wind} {speed_unit}\n"
                 f"🌧️ Rain chance: {pop_next}%")

        icon = get_icon(cw["weather"][0]["icon"], (80, 80), self.icon_cache)
        if icon:
            panel.icon_lbl.configure(image=icon)  # type: ignore[attr-defined]

    def _compare(self):
        o = self._results["origin"]["current"]
        d = self._results["dest"]["current"]
        diff = d["main"]["temp"] - o["main"]["temp"]
        if abs(diff) > 3:
            warmer = "Destination" if diff > 0 else "Origin"
            self.status_lbl.configure(
                text=f"✅ Done  •  {warmer} is {abs(diff):.1f}° warmer — pack accordingly!",
                text_color=("gray30", "gray70"))
        else:
            self.status_lbl.configure(text="✅ Similar temperatures at both locations",
                                      text_color=("gray30", "gray70"))
