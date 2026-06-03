import customtkinter as ctk
import tkinter as tk
import math
from utils import format_time, get_icon
from ui.custom_widgets import (GradientFrame, AQIGauge, WindCompass,
                               MinMaxTempBar, LoadingSpinner, MoonPhaseWidget,
                               SunriseArcWidget)
import mplcursors
from ui.map_view import MapView
from datetime import datetime, timedelta
import pytz
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class MainView(ctk.CTkScrollableFrame):
    def __init__(self, master, config, icon_cache, on_unit_toggle=None, on_tm_fetch=None, **kwargs):
        super().__init__(master, corner_radius=0, fg_color="transparent", **kwargs)
        self.app_config = config
        self.icon_cache = icon_cache
        self._on_unit_toggle = on_unit_toggle
        self._on_tm_fetch = on_tm_fetch
        self._last_data = None
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._setup_ui()
        self.advanced_visible = False
        self.toggle_advanced()   # start collapsed

    # ------------------------------------------------------------------ setup
    def _setup_ui(self):
        # ── Current weather card ──────────────────────────────────────────
        self.current_card = GradientFrame(self, corner_radius=15)
        self.current_card.grid(row=0, column=0, columnspan=2,
                               padx=20, pady=(20, 10), sticky="nsew")

        self.current_icon_label = ctk.CTkLabel(
            self.current_card, text="", width=120, height=120, bg_color="transparent")
        self.current_icon_label.pack(side="left", padx=20, pady=20)

        self.current_details_frame = ctk.CTkFrame(
            self.current_card, fg_color="transparent")
        self.current_details_frame.pack(
            side="left", fill="both", expand=True, padx=20, pady=20)

        self.city_label = ctk.CTkLabel(
            self.current_details_frame, text="City, Country",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="white", bg_color="transparent")
        self.city_label.pack(anchor="w")

        self.temp_label = ctk.CTkLabel(
            self.current_details_frame, text="--°",
            font=ctk.CTkFont(size=64, weight="bold"),
            text_color="white", bg_color="transparent")
        self.temp_label.pack(anchor="w")

        self.desc_label = ctk.CTkLabel(
            self.current_details_frame, text="Description",
            font=ctk.CTkFont(size=18),
            text_color="white", bg_color="transparent")
        self.desc_label.pack(anchor="w")

        # Historical comparison label (updates async after fetch)
        self.historical_label = ctk.CTkLabel(
            self.current_details_frame, text="",
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray75"), bg_color="transparent")
        self.historical_label.pack(anchor="w", pady=(2, 0))

        # °C/°F toggle + copy button row
        card_btns = ctk.CTkFrame(self.current_details_frame, fg_color="transparent")
        card_btns.pack(anchor="w", pady=(10, 0))

        unit_cmd = self._on_unit_toggle if self._on_unit_toggle else lambda: None
        self.unit_toggle_btn = ctk.CTkButton(
            card_btns, text="°C / °F", width=78, height=26,
            fg_color="transparent", border_width=1, border_color=("gray60", "gray50"),
            text_color="white", hover_color=("gray60", "gray50"),
            font=ctk.CTkFont(size=12), command=unit_cmd)
        self.unit_toggle_btn.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            card_btns, text="📋 Copy", width=72, height=26,
            fg_color="transparent", border_width=1, border_color=("gray60", "gray50"),
            text_color="white", hover_color=("gray60", "gray50"),
            font=ctk.CTkFont(size=12), command=self._copy_to_clipboard,
        ).pack(side="left")

        # Right-click context menu on card canvas
        self.current_card.canvas.bind("<Button-3>", self._show_context_menu, add="+")
        self.current_card.bind("<Button-3>", self._show_context_menu, add="+")

        # ── Hourly strip ─────────────────────────────────────────────────
        self.hourly_frame = ctk.CTkScrollableFrame(
            self, orientation="horizontal", height=150, fg_color="transparent")
        self.hourly_frame.grid(row=1, column=0, columnspan=2,
                               padx=20, pady=10, sticky="ew")

        # ── 5-day forecast ───────────────────────────────────────────────
        ctk.CTkLabel(self, text="5-Day Forecast",
                     font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=2, column=0, columnspan=2, padx=20, pady=(20, 5), sticky="w")

        self.forecast_container = ctk.CTkFrame(self, fg_color="transparent")
        self.forecast_container.grid(row=3, column=0, columnspan=2,
                                     padx=20, pady=(0, 10), sticky="ew")

        # ── Advanced toggle ───────────────────────────────────────────────
        self.adv_btn = ctk.CTkButton(
            self, text="Show Advanced Information ▼",
            command=self.toggle_advanced,
            fg_color="transparent", border_width=1,
            text_color=("gray10", "gray90"))
        self.adv_btn.grid(row=4, column=0, columnspan=2, pady=10)

        # ── Advanced container ────────────────────────────────────────────
        self.adv_container = ctk.CTkFrame(self, fg_color="transparent")
        self.adv_container.grid(row=5, column=0, columnspan=2, sticky="nsew")
        self.adv_container.grid_columnconfigure(0, weight=1)
        self.adv_container.grid_columnconfigure(1, weight=1)

        # Detail cards — 5 columns × 2 rows = 10 cards
        self.details_grid = ctk.CTkFrame(self.adv_container, fg_color="transparent")
        self.details_grid.grid(row=0, column=0, columnspan=2,
                               padx=20, pady=(10, 20), sticky="nsew")
        for i in range(5):
            self.details_grid.grid_columnconfigure(i, weight=1)

        self.detail_widgets: dict = {}
        self.detail_labels: list = []

        for i in range(10):
            card = ctk.CTkFrame(self.details_grid, corner_radius=10)
            card.grid(row=i // 5, column=i % 5, padx=5, pady=5, sticky="nsew")

            title_lbl = ctk.CTkLabel(
                card, text="", font=ctk.CTkFont(size=12, weight="bold"),
                text_color="gray")
            title_lbl.pack(pady=(10, 0))

            if i == 1:       # Wind
                cw = WindCompass(card)
                cw.pack(pady=5)
                self.detail_widgets["wind"] = cw
                val_lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=14))
                val_lbl.pack(pady=(0, 10))
            elif i == 5:     # Sun Cycle — graphical arc
                cw = SunriseArcWidget(card)
                cw.pack(pady=3)
                self.detail_widgets["sun"] = cw
                val_lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=10),
                                       text_color="gray")
                val_lbl.pack(pady=(0, 4))
            elif i == 6:     # AQI
                cw = AQIGauge(card)
                cw.pack(pady=5)
                self.detail_widgets["aqi"] = cw
                val_lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=14))
                val_lbl.pack(pady=(0, 10))
            elif i == 7:     # Moon Phase
                cw = MoonPhaseWidget(card)
                cw.pack(pady=5)
                self.detail_widgets["moon"] = cw
                val_lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=14))
                val_lbl.pack(pady=(0, 10))
            else:
                val_lbl = ctk.CTkLabel(card, text="", font=ctk.CTkFont(size=16))
                val_lbl.pack(pady=(15, 10))

            self.detail_labels.append((title_lbl, val_lbl))

        # ── Map view ──────────────────────────────────────────────────────
        self.map_view = MapView(self.adv_container, self.app_config, height=300)
        self.map_view.grid(row=1, column=0, padx=(20, 10), pady=10, sticky="nsew")

        # ── Tabbed graph view (Temperature + Precipitation) ───────────────
        self.graph_tabview = ctk.CTkTabview(
            self.adv_container, corner_radius=15, height=320)
        self.graph_tabview.grid(row=1, column=1, padx=(10, 20), pady=10, sticky="nsew")

        self.graph_tabview.add("🌡️ Temperature")
        self.graph_tabview.add("🌧️ Precipitation")

        temp_tab = self.graph_tabview.tab("🌡️ Temperature")
        self.fig, self.ax = plt.subplots(figsize=(5, 2.8), dpi=100)
        self.fig.patch.set_alpha(0)
        self.ax.patch.set_alpha(0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=temp_tab)
        self.canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        precip_tab = self.graph_tabview.tab("🌧️ Precipitation")
        self.fig2, self.ax2 = plt.subplots(figsize=(5, 2.8), dpi=100)
        self.fig2.patch.set_alpha(0)
        self.ax2.patch.set_alpha(0)
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=precip_tab)
        self.canvas2.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # ── Time Machine UI ───────────────────────────────────────────────
        self.tm_container = ctk.CTkFrame(self.adv_container, corner_radius=10)
        self.tm_container.grid(row=2, column=0, columnspan=2, padx=20, pady=(10, 20), sticky="ew")
        
        self.tm_header = ctk.CTkLabel(
            self.tm_container, text="🕰️ Time Machine (Slide to view past weather)", 
            font=ctk.CTkFont(size=14, weight="bold"))
        self.tm_header.pack(pady=(10, 5))
        
        self.tm_slider = ctk.CTkSlider(self.tm_container, from_=0, to=3650, number_of_steps=3650, command=self._on_tm_slide)
        self.tm_slider.set(0)
        self.tm_slider.pack(fill="x", padx=40, pady=5)
        self.tm_slider.bind("<ButtonRelease-1>", self._on_tm_release)
        
        self.tm_date_lbl = ctk.CTkLabel(self.tm_container, text="Live Data (Today)", font=ctk.CTkFont(size=12))
        self.tm_date_lbl.pack(pady=(0, 10))

        self.tm_result_card = GradientFrame(self.tm_container, corner_radius=10, height=100)
        self.tm_result_card.colors = ("#3a7bd5", "#3a6073")
        
        self.tm_result_title = ctk.CTkLabel(self.tm_result_card, text="", font=ctk.CTkFont(size=16, weight="bold"), text_color="white", bg_color="transparent")
        self.tm_result_title.pack(pady=(10, 5))
        
        self.tm_result_details = ctk.CTkLabel(self.tm_result_card, text="", font=ctk.CTkFont(size=14), text_color="white", bg_color="transparent")
        self.tm_result_details.pack(pady=(0, 10))

    # ------------------------------------------------------------------ time machine
    def _on_tm_slide(self, value):
        days_ago = int(value)
        if days_ago == 0:
            self.tm_date_lbl.configure(text="Live Data (Today)", text_color=("gray10", "gray90"))
            self.tm_result_card.pack_forget()
        else:
            target_date = datetime.now() - timedelta(days=days_ago)
            self.tm_date_lbl.configure(text=f"Target: {target_date.strftime('%Y-%m-%d')} ({days_ago} days ago)", text_color="#4a90e2")

    def _on_tm_release(self, event):
        days_ago = int(self.tm_slider.get())
        if days_ago == 0:
            self.tm_result_card.pack_forget()
            return
            
        target_date = datetime.now() - timedelta(days=days_ago)
        date_str = target_date.strftime('%Y-%m-%d')
        self.tm_date_lbl.configure(text=f"Fetching data for {date_str}...")
        
        if self._on_tm_fetch:
            self._on_tm_fetch(date_str)
            
    def update_time_machine(self, data: dict):
        unit_str = "°C" if self.app_config.get("units") == "metric" else "°F"
        speed_unit = "m/s" if self.app_config.get("units") == "metric" else "mph"
        
        self.tm_date_lbl.configure(text=f"Historical Data: {data['date']}", text_color=("gray10", "gray90"))
        
        t_max = round(data['t_max'])
        t_min = round(data['t_min'])
        precip = data['precip']
        wind = data['wind']
        
        self.tm_result_title.configure(text=f"Average: {round((t_max + t_min) / 2)}{unit_str}")
        self.tm_result_details.configure(
            text=f"High: {t_max}{unit_str}   Low: {t_min}{unit_str}   |   🌧️ Precip: {precip}mm   |   🌬️ Wind Max: {wind}{speed_unit}"
        )
        
        self.tm_result_card.pack(fill="x", padx=20, pady=(0, 10))
        self.tm_result_card._draw_gradient()

    # ------------------------------------------------------------------ toggle
    def toggle_advanced(self):
        self.advanced_visible = not self.advanced_visible
        if self.advanced_visible:
            self.adv_container.grid()
            self.adv_btn.configure(text="Hide Advanced Information ▲")
        else:
            self.adv_container.grid_remove()
            self.adv_btn.configure(text="Show Advanced Information ▼")

    # ------------------------------------------------------------------ loading
    def show_loading(self):
        if not hasattr(self, "loading_overlay"):
            bg_color = "#e0e0e0" if ctk.get_appearance_mode() == "Light" else "#1a1a1a"
            self.loading_overlay = ctk.CTkFrame(self, fg_color=bg_color, corner_radius=0)
            center = ctk.CTkFrame(self.loading_overlay, fg_color="transparent")
            center.place(relx=0.5, rely=0.5, anchor="center")
            self.spinner = LoadingSpinner(center, bg_color=bg_color)
            self.spinner.pack(pady=10)
            ctk.CTkLabel(center, text="Fetching Weather Data…",
                         font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        self.loading_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.loading_overlay.lift()
        self.spinner.start()

    def hide_loading(self):
        if hasattr(self, "loading_overlay") and self.loading_overlay.winfo_exists():
            self.spinner.stop()
            self.loading_overlay.place_forget()

    # ------------------------------------------------------------------ public
    def set_historical_temp(self, avg_temp: int):
        """Called from main.py when historical data arrives."""
        unit_str = "°C" if self.app_config.get("units") == "metric" else "°F"
        self.historical_label.configure(
            text=f"↕ Same day last year: {avg_temp}{unit_str}")

    # ------------------------------------------------------------------ animation
    def _animate_card_in(self, target_colors: tuple, frame: int = 0, total: int = 8, anim_id: int = 0):
        if not self.winfo_exists():
            return
        if frame == 0:
            self._current_anim_id = getattr(self, "_current_anim_id", 0) + 1
            anim_id = self._current_anim_id
        elif getattr(self, "_current_anim_id", 0) != anim_id:
            return  # a newer animation started
            
        if frame >= total:
            self.current_card.colors = target_colors
            self.current_card._draw_gradient()
            return
        ratio = frame / total
        c1 = _lerp_hex("#555555", target_colors[0], ratio)
        c2 = _lerp_hex("#333333", target_colors[1], ratio)
        self.current_card.colors = (c1, c2)
        self.current_card._draw_gradient()
        self.after(28, lambda: self._animate_card_in(target_colors, frame + 1, total, anim_id))

    # ------------------------------------------------------------------ clipboard
    def _copy_to_clipboard(self):
        if not self._last_data:
            return
        cw = self._last_data["current"]
        loc = self._last_data["location"]
        units = self.app_config.get("units", "metric")
        unit_str = "°C" if units == "metric" else "°F"
        speed_unit = "m/s" if units == "metric" else "mph"
        text = (
            f"🌤️ Weather for {loc['name']}\n"
            f"🌡️ {round(cw['main']['temp'])}{unit_str} "
            f"(feels {round(cw['main']['feels_like'])}{unit_str})\n"
            f"☁️ {cw['weather'][0]['description'].title()}\n"
            f"💧 Humidity: {cw['main']['humidity']}%\n"
            f"🌬️ Wind: {cw['wind']['speed']} {speed_unit}"
        )
        self.clipboard_clear()
        self.clipboard_append(text)

    def _show_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="📋 Copy Weather Summary",
                         command=self._copy_to_clipboard)
        if self._on_unit_toggle:
            menu.add_separator()
            unit_str = "°F" if self.app_config.get("units") == "metric" else "°C"
            menu.add_command(label=f"🔄 Switch to {unit_str}",
                             command=self._on_unit_toggle)
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    # ------------------------------------------------------------------ update
    def update_data(self, data: dict):
        self._last_data = data
        cw = data["current"]
        fc = data["forecast"]
        loc = data["location"]
        aqi = data["air_quality"]
        units = self.app_config.get("units", "metric")
        unit_str = "°C" if units == "metric" else "°F"
        speed_unit = "m/s" if units == "metric" else "mph"

        # Main card labels
        self.city_label.configure(
            text=f"{cw['name']}, {cw.get('sys', {}).get('country', '')}")
        self.temp_label.configure(
            text=f"{round(cw['main']['temp'])}{unit_str}")
        self.desc_label.configure(
            text=f"{cw['weather'][0]['description'].title()}, "
                 f"Feels like {round(cw['main']['feels_like'])}{unit_str}")

        icon = get_icon(cw["weather"][0]["icon"], (120, 120), self.icon_cache)
        if icon:
            self.current_icon_label.configure(image=icon)

        # Card colour + fade-in animation
        desc_l = cw["weather"][0]["description"].lower()
        if "clear" in desc_l or "sun" in desc_l:
            target = ("#FFD194", "#70E1F5");  text_color = "black"
        elif "rain" in desc_l or "drizzle" in desc_l:
            target = ("#3a7bd5", "#3a6073");  text_color = "white"
        elif "cloud" in desc_l or "overcast" in desc_l:
            target = ("#bdc3c7", "#2c3e50");  text_color = "white"
        elif "snow" in desc_l:
            target = ("#E0EAFC", "#CFDEF3");  text_color = "black"
        elif "thunder" in desc_l or "storm" in desc_l:
            target = ("#1a1a2e", "#16213e");  text_color = "white"
        else:
            target = ("#000000", "#434343");  text_color = "white"

        for lbl in [self.city_label, self.temp_label, self.desc_label]:
            lbl.configure(text_color=text_color)
        hist_color = "#cccccc" if text_color == "white" else "#555555"
        self.historical_label.configure(text_color=hist_color)

        self._animate_card_in(target)

        # ── Hourly strip ──────────────────────────────────────────────────
        for w in self.hourly_frame.winfo_children():
            w.destroy()
        for it in fc["list"][:8]:
            local_time = format_time(it["dt"], loc["timezone"])
            h_temp = round(it["main"]["temp"])
            pop = round(it.get("pop", 0) * 100)
            fw = ctk.CTkFrame(self.hourly_frame, corner_radius=10)
            fw.pack(side="left", padx=5, pady=5)
            ctk.CTkLabel(fw, text=local_time,
                         font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(5, 0))
            lbl_img = ctk.CTkLabel(fw, text="")
            h_icon = get_icon(it["weather"][0]["icon"], (40, 40), self.icon_cache)
            if h_icon:
                lbl_img.configure(image=h_icon)
            lbl_img.pack(pady=2, padx=10)
            ctk.CTkLabel(fw, text=f"{h_temp}{unit_str}",
                         font=ctk.CTkFont(size=14)).pack()
            if pop > 0:
                ctk.CTkLabel(fw, text=f"💧 {pop}%",
                             font=ctk.CTkFont(size=10),
                             text_color="#4a90e2").pack(pady=(0, 5))

        # ── 5-day forecast ────────────────────────────────────────────────
        for w in self.forecast_container.winfo_children():
            w.destroy()
        daily: dict = {}
        for it in fc["list"]:
            date_key = datetime.fromtimestamp(it["dt"]).strftime("%Y-%m-%d")
            daily.setdefault(date_key, []).append(it)

        days = list(daily.items())[:5]
        week_temps = [f["main"]["temp"] for day in days for f in day[1]]
        week_min, week_max = round(min(week_temps)), round(max(week_temps))

        for i, (date_key, forecasts) in enumerate(days):
            day_name = ("Today" if i == 0
                        else datetime.strptime(date_key, "%Y-%m-%d").strftime("%A")[:3])
            card = ctk.CTkFrame(self.forecast_container, corner_radius=10)
            card.pack(side="left", fill="both", expand=True, padx=5)
            ctk.CTkLabel(card, text=day_name,
                         font=ctk.CTkFont(weight="bold")).pack(pady=(10, 5))
            mid = forecasts[len(forecasts) // 2]
            f_icon = get_icon(mid["weather"][0]["icon"], (40, 40), self.icon_cache)
            li = ctk.CTkLabel(card, text="")
            if f_icon:
                li.configure(image=f_icon)
            li.pack(pady=5)
            day_temps = [f["main"]["temp"] for f in forecasts]
            d_min, d_max = round(min(day_temps)), round(max(day_temps))
            ctk.CTkLabel(card, text=f"{d_min}° – {d_max}°",
                         font=ctk.CTkFont(size=12)).pack()
            bar = MinMaxTempBar(card)
            bar.pack(pady=(0, 10))
            bar.set_temps(d_min, d_max, week_min, week_max)

        # ── Advanced detail cards ─────────────────────────────────────────
        sunrise = format_time(cw["sys"]["sunrise"], loc["timezone"])
        sunset = format_time(cw["sys"]["sunset"], loc["timezone"])

        # Dew point (Magnus formula)
        temp_c = cw["main"]["temp"] if units == "metric" else (cw["main"]["temp"] - 32) * 5 / 9
        rh = cw["main"]["humidity"]
        a_m, b_m = 17.27, 237.7
        if rh > 0:
            alpha_m = (a_m * temp_c) / (b_m + temp_c) + math.log(max(rh / 100.0, 1e-9))
            dew_c = (b_m * alpha_m) / (a_m - alpha_m)
        else:
            dew_c = temp_c
        dew_disp = round(dew_c) if units == "metric" else round(dew_c * 9 / 5 + 32)

        # UV index
        uv = data.get("uv_index")
        if uv is not None:
            level = ("Low" if uv < 3 else "Moderate" if uv < 6 else
                     "High" if uv < 8 else "Very High" if uv < 11 else "Extreme")
            uv_text = f"{uv:.1f} ({level})"
        else:
            uv_text = "N/A"

        details = [
            ("💧 Humidity",  f"{rh}%"),
            ("🌬️ Wind",      f"{cw['wind']['speed']} {speed_unit}"),
            ("📊 Pressure",  f"{cw['main']['pressure']} hPa"),
            ("👁️ Visibility", f"{cw.get('visibility', 0) / 1000:.1f} km"),
            ("☁️ Clouds",    f"{cw['clouds']['all']}%"),
            ("☀️ Sun Cycle", f"↑{sunrise} ↓{sunset}"),
            ("🌫️ AQI",       "Data N/A"),
            ("🌑 Moon Phase", ""),
            ("🌡️ Dew Point",  f"{dew_disp}°"),
            ("🔆 UV Index",   uv_text),
        ]

        self.detail_widgets["wind"].set_angle(cw["wind"].get("deg", 0))
        self.detail_widgets["sun"].set_times(cw["sys"]["sunrise"], cw["sys"]["sunset"])
        self.detail_widgets["moon"].set_date(datetime.now())

        if aqi and "list" in aqi and len(aqi["list"]) > 0:
            a_val = aqi["list"][0]["main"]["aqi"]
            a_text = ["Good", "Fair", "Moderate", "Poor", "Very Poor"][a_val - 1]
            details[6] = ("🌫️ AQI", f"{a_text} ({a_val}/5)")
            self.detail_widgets["aqi"].set_aqi(a_val)

        for i, (title, val) in enumerate(details):
            t_lbl, v_lbl = self.detail_labels[i]
            t_lbl.configure(text=title)
            v_lbl.configure(text=val)

        # ── Map ───────────────────────────────────────────────────────────
        self.map_view.update_map(loc["lat"], loc["lon"], loc["name"])

        # ── Temperature chart ─────────────────────────────────────────────
        times, temps = [], []
        for it in fc["list"][:12]:
            times.append(datetime.fromtimestamp(it["dt"]))
            temps.append(it["main"]["temp"])

        mode = ctk.get_appearance_mode()
        fg = "white" if mode == "Dark" else "black"

        self.ax.clear()
        lines = self.ax.plot(times, temps, marker="o", color="#4a90e2", linewidth=2)
        
        if hasattr(self, "_cursor") and self._cursor is not None:
            self._cursor.remove()
        self._cursor = mplcursors.cursor(lines, hover=True)

        @self._cursor.connect("add")
        def on_add(sel):
            sel.annotation.set_text(f"{sel.target[1]:.1f}{unit_str}")
            sel.annotation.get_bbox_patch().set(
                boxstyle="round,pad=0.5", fc="white", alpha=0.9)
            sel.annotation.set_color("black")

        self.ax.set_title("Temperature Forecast (36h)", color=fg)
        self.ax.set_ylabel(f"Temp ({unit_str})", color=fg)
        self.ax.grid(True, alpha=0.3)
        self.ax.tick_params(colors=fg)
        for spine in self.ax.spines.values():
            spine.set_color(fg)
        self.fig.patch.set_alpha(0)
        self.ax.patch.set_alpha(0)
        self.fig.autofmt_xdate()
        self.fig.tight_layout()
        self.canvas.draw()

        # ── Precipitation chart ───────────────────────────────────────────
        times_pop, pops = [], []
        for it in fc["list"][:16]:
            times_pop.append(datetime.fromtimestamp(it["dt"]))
            pops.append(round(it.get("pop", 0) * 100))

        self.ax2.clear()
        bar_colors = ["#1a5fa8" if p >= 60 else "#4a90e2" for p in pops]
        self.ax2.bar(range(len(pops)), pops, color=bar_colors, alpha=0.85, width=0.7)
        step = max(1, len(pops) // 6)
        self.ax2.set_xticks(range(0, len(pops), step))
        self.ax2.set_xticklabels(
            [times_pop[i].strftime("%d/%m\n%H:%M") for i in range(0, len(pops), step)],
            fontsize=7, color=fg)
        self.ax2.set_ylabel("Probability %", color=fg)
        self.ax2.set_ylim(0, 105)
        self.ax2.axhline(y=60, color="red", linestyle="--", alpha=0.5,
                         linewidth=1, label="60% threshold")
        self.ax2.set_title("Precipitation Probability (48h)", color=fg)
        self.ax2.grid(True, alpha=0.3, axis="y")
        self.ax2.tick_params(colors=fg)
        for spine in self.ax2.spines.values():
            spine.set_color(fg)
        self.fig2.patch.set_alpha(0)
        self.ax2.patch.set_alpha(0)
        self.fig2.tight_layout()
        self.canvas2.draw()


# ── helpers ───────────────────────────────────────────────────────────────────
def _lerp_hex(c1: str, c2: str, t: float) -> str:
    def h2r(h: str):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    r1, g1, b1 = h2r(c1)
    r2, g2, b2 = h2r(c2)
    r = max(0, min(255, int(r1 + (r2 - r1) * t)))
    g = max(0, min(255, int(g1 + (g2 - g1) * t)))
    b = max(0, min(255, int(b1 + (b2 - b1) * t)))
    return "#%02x%02x%02x" % (r, g, b)
