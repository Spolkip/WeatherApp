import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image, ImageDraw
import threading
from plyer import notification
import pystray
from pystray import MenuItem as item
from datetime import datetime

from config import Config
from api_client import WeatherAPIClient
from ui.sidebar import Sidebar
from ui.main_view import MainView
from ui.dashboard import DashboardView
from ui.widget_overlay import WeatherOverlay
from ui.alert_rules import AlertRulesDialog
from ui.commute_planner import CommutePlanner
from utils import set_wallpaper, export_csv, export_pdf

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


# ── City tab bar ──────────────────────────────────────────────────────────────
class CityTabsBar(ctk.CTkFrame):
    """Horizontal scrollable tab strip showing saved locations."""

    def __init__(self, master, app_config, on_select, **kwargs):
        super().__init__(master, height=44, corner_radius=0,
                         fg_color=("gray88", "gray18"), **kwargs)
        self.app_config = app_config
        self.on_select = on_select
        self.active_city: str | None = None
        self.grid_propagate(False)
        self.refresh(None)

    def refresh(self, current_city: str | None):
        for w in self.winfo_children():
            w.destroy()
        self.active_city = current_city

        scroll = ctk.CTkScrollableFrame(
            self, orientation="horizontal",
            fg_color="transparent", height=40,
        )
        scroll.pack(fill="both", expand=True, padx=2, pady=2)

        self._add_tab(scroll, "🌐 Auto", None)
        for loc in self.app_config.get("saved_locations", []):
            self._add_tab(scroll, f"📍 {loc['name']}", loc["name"])

    def _add_tab(self, parent, label: str, city: str | None):
        is_active = (city == self.active_city)
        ctk.CTkButton(
            parent, text=label, height=30,
            width=max(80, len(label) * 9),
            fg_color="#3a7bd5" if is_active else "transparent",
            hover_color="#3a6073",
            border_width=0 if is_active else 1,
            corner_radius=6,
            font=ctk.CTkFont(size=12),
            command=lambda c=city: self._select(c),
        ).pack(side="left", padx=3, pady=3)

    def _select(self, city: str | None):
        self.active_city = city
        self.on_select(city or "")


# ── Main application ──────────────────────────────────────────────────────────
class WeatherApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Weather Pro Ultimate")
        self.geometry("1300x900")
        self.minsize(1100, 800)
        self.protocol("WM_DELETE_WINDOW", self.hide_window)

        self.app_config = Config()
        self.api_client = WeatherAPIClient(self.app_config)
        self.icon_cache: dict = {}
        self.last_alert_time: float = 0.0
        self._last_rain_notify_time: float = 0.0
        self._rule_notify_times: dict = {}
        self.current_weather = None
        self._current_data = None
        self._pending_city: str | None = None
        self._overlay: WeatherOverlay | None = None
        self._overlay_visible = False

        # Apply saved appearance mode
        ctk.set_appearance_mode(self.app_config.get("appearance_mode", "System"))

        # Grid: sidebar spans both rows; row 0 = tab bar, row 1 = main view
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self.sidebar = Sidebar(
            self,
            on_search=self.on_search,
            on_add_location=self.add_current_location,
            on_show_settings=self.show_settings,
            on_show_dashboard=self.show_dashboard,
            on_remove_location=self.remove_location,
            on_show_commute=self.show_commute_planner,
            on_show_alert_rules=self.show_alert_rules,
            on_toggle_overlay=self.toggle_overlay,
            config=self.app_config,
            api_client=self.api_client,
        )
        self.sidebar.grid(row=0, column=0, rowspan=2, sticky="nsew")

        self.tabs_bar = CityTabsBar(
            self, self.app_config, on_select=self.on_tab_select)
        self.tabs_bar.grid(row=0, column=1, sticky="ew")

        self.main_view = MainView(
            self, self.app_config, self.icon_cache,
            on_unit_toggle=self.toggle_units,
            on_tm_fetch=self.fetch_time_machine)
        self.main_view.grid(row=1, column=1, sticky="nsew")

        # Keyboard shortcuts
        self.bind("<Control-r>", lambda _: self.refresh_weather())
        self.bind("<Control-R>", lambda _: self.refresh_weather())

        self.refresh_weather()
        self.auto_refresh()

    # ------------------------------------------------------------------ tray
    def hide_window(self):
        self.withdraw()
        from utils import generate_tray_icon
        unit_str = "°C" if self.app_config.get("units") == "metric" else "°F"
        image = generate_tray_icon(self.current_weather, unit_str)

        def city_cb(name):
            return lambda icon, _item: self.quick_select_city(icon, name)

        items = [item("Restore", self.show_window)]
        saved = self.app_config.get("saved_locations", [])
        if saved:
            items.append(pystray.Menu.SEPARATOR)
            for loc in saved:
                items.append(item(loc["name"], city_cb(loc["name"])))
        items += [pystray.Menu.SEPARATOR, item("Quit", self.quit_window)]

        title = "Weather Pro Ultimate"
        if self.current_weather:
            t = round(self.current_weather["main"]["temp"])
            u = "°C" if self.app_config.get("units") == "metric" else "°F"
            title = f"{self.current_weather['name']}: {t}{u}"

        self.tray_icon = pystray.Icon(
            "wapp", image, title, pystray.Menu(*items))
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def quick_select_city(self, icon, city_name: str):
        icon.stop()
        self.tray_icon = None
        self.after(0, self.deiconify)
        self.after(100, lambda: self.refresh_weather(city_name))

    def show_window(self, icon, _item):
        icon.stop()
        self.tray_icon = None
        self.after(0, self.deiconify)

    def quit_window(self, icon, _item):
        icon.stop()
        self.quit()

    # ------------------------------------------------------------------ navigation
    def on_search(self, city: str):
        self.refresh_weather(city)

    def on_tab_select(self, city: str):
        self.refresh_weather(city if city else None)

    def toggle_units(self):
        cur = self.app_config.get("units", "metric")
        self.app_config.set("units", "imperial" if cur == "metric" else "metric")
        self.refresh_weather(self._pending_city)

    # ------------------------------------------------------------------ fetch
    def refresh_weather(self, city: str | None = None):
        if not city:
            city = self.app_config.get("default_city", "") or None
        self._pending_city = city

        if not self.app_config.get("api_key"):
            messagebox.showerror("API Error", "OpenWeatherMap API key not configured")
            return

        self.sidebar.set_status("Fetching weather data…")
        self.sidebar.search_btn.configure(state="disabled")
        self.main_view.show_loading()
        self.api_client.fetch_weather(
            self._pending_city or "", self.on_weather_success, self.on_weather_error)

    def on_weather_success(self, data: dict):
        self.current_weather = data["current"]
        self._current_data = data
        resolved = data["location"]["name"]

        self.after(0, lambda: (
            self.sidebar.city_entry.delete(0, "end"),
            self.sidebar.city_entry.insert(0, resolved),
        ))

        if getattr(self, "tray_icon", None) is not None:
            from utils import generate_tray_icon
            unit_str = "°C" if self.app_config.get("units") == "metric" else "°F"
            self.tray_icon.icon = generate_tray_icon(self.current_weather, unit_str)
            self.tray_icon.title = f"{resolved}: {round(self.current_weather['main']['temp'])}{unit_str}"

        # Severe weather notification (original)
        wid = self.current_weather["weather"][0]["id"]
        if wid in [211, 212, 221, 502, 503, 504, 602, 781]:
            now = datetime.now().timestamp()
            if now - self.last_alert_time > 3600:
                desc = self.current_weather["weather"][0]["description"].title()
                city = self.current_weather["name"]
                try:
                    getattr(notification, "notify")(  # type: ignore[attr-defined]
                        title="Severe Weather Alert!",
                        message=f"{desc} in {city}",
                        app_name="Weather Pro", timeout=10)
                    self.last_alert_time = now
                except Exception:
                    pass

        self.after(0, lambda: self._update_ui(data))
        self.after(150, lambda: self._check_rain_notification(data))
        self.after(250, lambda: self._evaluate_alert_rules(data))
        self.after(350, lambda: self._scan_forecast_alerts(data))

        # Historical comparison (async, non-blocking)
        lat, lon = data["location"]["lat"], data["location"]["lon"]
        self.api_client.fetch_historical(
            lat, lon,
            lambda avg: self.after(0, lambda a=avg: self.main_view.set_historical_temp(a)),
            lambda _: None,
        )

        # Wallpaper auto-update (opt-in)
        if self.app_config.get("wallpaper_auto_update", False):
            cw = data["current"]
            threading.Thread(
                target=set_wallpaper,
                args=(cw["name"], round(cw["main"]["temp"]),
                      cw["weather"][0]["description"],
                      "°C" if self.app_config.get("units") == "metric" else "°F",
                      cw["weather"][0]["description"]),
                daemon=True,
            ).start()

        # Overlay update
        if self._overlay and self._overlay_visible:
            self.after(0, lambda: self._overlay.update_weather(data))

        # City tabs: highlight saved location if current city matches
        saved_names = {l["name"] for l in self.app_config.get("saved_locations", [])}
        active = resolved if resolved in saved_names else None
        self.after(0, lambda: self.tabs_bar.refresh(active))

    def fetch_time_machine(self, date_str: str):
        if not self._current_data:
            return
        loc = self._current_data["location"]
        self.api_client.fetch_time_machine(
            loc["lat"], loc["lon"], date_str,
            lambda data: self.after(0, lambda: self.main_view.update_time_machine(data)),
            lambda err: self.after(0, lambda: self.main_view.tm_date_lbl.configure(text=f"Error: {err}", text_color="red"))
        )

    # ------------------------------------------------------------------ notifications
    def _check_rain_notification(self, data: dict):
        if not self.app_config.get("rain_notify", True):
            return
        for slot in data["forecast"]["list"][:2]:
            pop = slot.get("pop", 0)
            wid = slot["weather"][0]["id"]
            if pop > 0.6 or (200 <= wid < 600):
                now = datetime.now().timestamp()
                if now - self._last_rain_notify_time > 3600:
                    try:
                        dt_str = datetime.fromtimestamp(slot["dt"]).strftime("%H:%M")
                        desc = slot["weather"][0]["description"].title()
                        getattr(notification, "notify")(  # type: ignore[attr-defined]
                            title="Rain Alert 🌧️",
                            message=f"{desc} expected around {dt_str}",
                            app_name="Weather Pro", timeout=8)
                        self._last_rain_notify_time = now
                    except Exception:
                        pass
                break

    def _evaluate_alert_rules(self, data: dict):
        cw = data["current"]
        field_map = {
            "temp":       cw["main"]["temp"],
            "feels_like": cw["main"]["feels_like"],
            "humidity":   cw["main"]["humidity"],
            "wind_speed": cw["wind"]["speed"],
            "pressure":   cw["main"]["pressure"],
            "visibility": cw.get("visibility", 0),
            "clouds":     cw["clouds"]["all"],
        }
        for rule in self.app_config.get("alert_rules", []):
            field, op = rule.get("field"), rule.get("operator")
            threshold = rule.get("threshold", 0)
            value = field_map.get(field)  # type: ignore[arg-type]
            if value is None:
                continue
            triggered = (
                (op == ">"  and value > threshold) or
                (op == ">=" and value >= threshold) or
                (op == "<"  and value < threshold) or
                (op == "<=" and value <= threshold) or
                (op == "==" and abs(value - threshold) < 0.5)
            )
            if triggered:
                key = f"{field}_{op}_{threshold}"
                now = datetime.now().timestamp()
                if now - self._rule_notify_times.get(key, 0) > 3600:
                    label = rule.get("label", "Weather Alert")
                    try:
                        getattr(notification, "notify")(  # type: ignore[attr-defined]
                            title=f"⚡ {label}",
                            message=f"{field} is {round(value)}  (rule: {op} {threshold})",
                            app_name="Weather Pro", timeout=8)
                        self._rule_notify_times[key] = now
                    except Exception:
                        pass

    def _scan_forecast_alerts(self, data: dict):
        alerts = []
        cw = data["current"]
        seen: set = set()

        if cw["wind"]["speed"] > 13.9:
            alerts.append({"level": "warning",
                           "message": f"⚠️ High wind: {cw['wind']['speed']} m/s"})

        for slot in data["forecast"]["list"][:8]:
            wid = slot["weather"][0]["id"]
            ts = datetime.fromtimestamp(slot["dt"]).strftime("%H:%M")
            if 200 <= wid <= 232 and "thunder" not in seen:
                alerts.append({"level": "danger",
                               "message": f"⛈️ Thunder expected at {ts}"})
                seen.add("thunder")
            elif (502 <= wid <= 504 or wid == 522) and "heavy_rain" not in seen:
                alerts.append({"level": "warning",
                               "message": f"🌧️ Heavy rain at {ts}"})
                seen.add("heavy_rain")
            elif 602 <= wid <= 622 and "heavy_snow" not in seen:
                alerts.append({"level": "warning",
                               "message": f"❄️ Heavy snow at {ts}"})
                seen.add("heavy_snow")

        temp = cw["main"]["temp"]
        if temp > 38:
            alerts.append({"level": "danger",
                           "message": f"🔥 Extreme heat: {round(temp)}°C"})
        elif temp < -20:
            alerts.append({"level": "danger",
                           "message": f"🥶 Extreme cold: {round(temp)}°C"})

        self.after(0, lambda a=alerts: self.sidebar.update_alerts(a))

    # ------------------------------------------------------------------ ui updates
    def on_weather_error(self, err: str):
        self.after(0, lambda e=err: self._show_error(e))

    def _show_error(self, err: str):
        self.main_view.hide_loading()
        self.sidebar.set_status("Error fetching data")
        self.sidebar.search_btn.configure(state="normal")
        messagebox.showerror("Error", err)

    def _update_ui(self, data: dict):
        self.main_view.hide_loading()
        self.main_view.update_data(data)
        self.sidebar.set_status(
            f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
        self.sidebar.search_btn.configure(state="normal")

    # ------------------------------------------------------------------ locations
    def add_current_location(self):
        if not self.current_weather:
            messagebox.showwarning("No Data", "No current weather data available")
            return
        city = self.current_weather["name"]
        country = self.current_weather.get("sys", {}).get("country", "")
        locs = self.app_config.get("saved_locations", [])
        for loc in locs:
            if loc["name"] == city and loc.get("country") == country:
                messagebox.showinfo("Already Saved",
                                    f"{city} is already in saved locations")
                return
        locs.append({"name": city, "country": country,
                     "lat": self.current_weather["coord"]["lat"],
                     "lon": self.current_weather["coord"]["lon"]})
        self.app_config.set("saved_locations", locs)
        self.sidebar.update_locations_list()
        self.tabs_bar.refresh(None)

    def remove_location(self, index: int):
        locs = self.app_config.get("saved_locations", [])
        locs.pop(index)
        self.app_config.set("saved_locations", locs)
        self.sidebar.update_locations_list()
        self.tabs_bar.refresh(None)

    # ------------------------------------------------------------------ refresh scheduling
    def auto_refresh(self):
        ms = self.app_config.get("refresh_interval", 30) * 60 * 1000
        self.after(ms, self._scheduled_refresh)

    def _scheduled_refresh(self):
        self.refresh_weather()
        ms = self.app_config.get("refresh_interval", 30) * 60 * 1000
        self.after(ms, self._scheduled_refresh)

    # ------------------------------------------------------------------ dialogs
    def show_dashboard(self):
        DashboardView(self, self.app_config, self.icon_cache)

    def show_commute_planner(self):
        CommutePlanner(self, self.api_client, self.app_config, self.icon_cache)

    def show_alert_rules(self):
        AlertRulesDialog(self, self.app_config)

    def toggle_overlay(self):
        if not self._overlay or not self._overlay.winfo_exists():
            self._overlay = WeatherOverlay(self)
            if self._current_data:
                self._overlay.update_weather(self._current_data)
            self._overlay_visible = True
            self.sidebar.set_overlay_btn_text(True)
        else:
            if self._overlay_visible:
                self._overlay.withdraw()
                self._overlay_visible = False
                self.sidebar.set_overlay_btn_text(False)
            else:
                self._overlay.deiconify()
                self._overlay_visible = True
                self.sidebar.set_overlay_btn_text(True)

    def show_settings(self):
        win = ctk.CTkToplevel(self)
        win.title("Settings")
        win.geometry("440x600")
        win.attributes("-topmost", True)
        win.grab_set()

        ctk.CTkLabel(win, text="Settings",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=20)

        def labeled_entry(label_text: str, default: str) -> ctk.CTkEntry:
            ctk.CTkLabel(win, text=label_text).pack(anchor="w", padx=20)
            e = ctk.CTkEntry(win)
            e.pack(fill="x", padx=20, pady=(0, 12))
            e.insert(0, default)
            return e

        e_city = labeled_entry(
            "Default City (blank = auto-detect by IP)",
            self.app_config.get("default_city", ""))

        ctk.CTkLabel(win, text="Units").pack(anchor="w", padx=20)
        units_cb = ctk.CTkComboBox(win, values=["metric", "imperial"])
        units_cb.pack(fill="x", padx=20, pady=(0, 12))
        units_cb.set(self.app_config.get("units", "metric"))

        e_key = labeled_entry("API Key", self.app_config.get("api_key", ""))
        e_interval = labeled_entry(
            "Refresh Interval (minutes)",
            str(self.app_config.get("refresh_interval", 30)))

        rain_var = ctk.BooleanVar(value=self.app_config.get("rain_notify", True))
        wp_var = ctk.BooleanVar(
            value=self.app_config.get("wallpaper_auto_update", False))

        ctk.CTkCheckBox(win, text="🌧️ Smart rain notifications",
                        variable=rain_var).pack(anchor="w", padx=20, pady=4)
        ctk.CTkCheckBox(win, text="🖼️ Auto-update desktop wallpaper (Windows)",
                        variable=wp_var).pack(anchor="w", padx=20, pady=4)

        def save():
            self.app_config.set("default_city", e_city.get())
            self.app_config.set("units", units_cb.get())
            self.app_config.set("api_key", e_key.get())
            try:
                self.app_config.set("refresh_interval", int(e_interval.get()))
            except ValueError:
                pass
            self.app_config.set("rain_notify", rain_var.get())
            self.app_config.set("wallpaper_auto_update", wp_var.get())
            win.destroy()
            self.refresh_weather()

        def do_export():
            if not self._current_data:
                messagebox.showwarning("No Data", "No weather data to export yet")
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("PDF files", "*.pdf"),
                           ("All files", "*.*")],
                title="Export Weather Data",
            )
            if not path:
                return
            if path.lower().endswith(".pdf"):
                ok = export_pdf(self._current_data, path)
                if not ok:
                    messagebox.showerror(
                        "Error",
                        "PDF export failed.\nInstall reportlab:\n  pip install reportlab")
            else:
                export_csv(self._current_data, path)
                messagebox.showinfo("Export", f"Exported to:\n{path}")

        ctk.CTkButton(win, text="💾 Save Settings", command=save).pack(pady=10)
        ctk.CTkButton(win, text="📤 Export Weather Data", command=do_export,
                      fg_color="transparent", border_width=1).pack(pady=4)


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()