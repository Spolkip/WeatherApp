import customtkinter as ctk
from utils import get_icon


class WeatherOverlay(ctk.CTkToplevel):
    """Mini always-on-top draggable weather widget (HUD)."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.88)
        self.geometry("230+100+100")

        self._drag_x = 0
        self._drag_y = 0

        self._setup_ui()
        # Bind dragging to every child widget
        for w in (self, self.main_frame):
            w.bind("<ButtonPress-1>", self._drag_start)
            w.bind("<B1-Motion>", self._drag_move)

    # ------------------------------------------------------------------
    def _setup_ui(self):
        self.main_frame = ctk.CTkFrame(
            self, corner_radius=14,
            fg_color=("gray92", "#1e1e2e"),
            border_width=1, border_color=("gray70", "#3a3a5c"),
        )
        self.main_frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Close button (top-right corner)
        close_btn = ctk.CTkButton(
            self.main_frame, text="✕", width=22, height=22,
            fg_color="transparent", hover_color="#cc3333",
            text_color=("gray40", "gray60"), font=ctk.CTkFont(size=10),
            command=self.withdraw,
        )
        close_btn.place(relx=1.0, x=-4, y=4, anchor="ne")

        top = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        top.pack(fill="both", expand=True, padx=10, pady=(8, 6))

        self.icon_lbl = ctk.CTkLabel(top, text="", width=54, height=54, bg_color="transparent")
        self.icon_lbl.pack(side="left", padx=(0, 8))

        info = ctk.CTkFrame(top, fg_color="transparent")
        info.pack(side="left", fill="both", expand=True)

        self.city_lbl = ctk.CTkLabel(
            info, text="Loading…", anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray10", "gray90"),
        )
        self.city_lbl.pack(fill="x")

        self.temp_lbl = ctk.CTkLabel(
            info, text="--°", anchor="w",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=("#1a6fd4", "#4a90e2"),
        )
        self.temp_lbl.pack(fill="x")

        self.desc_lbl = ctk.CTkLabel(
            info, text="", anchor="w",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
        )
        self.desc_lbl.pack(fill="x")

    # ------------------------------------------------------------------
    def update_weather(self, data: dict):
        cw = data["current"]
        loc = data["location"]
        try:
            cfg = self.master.app_config  # type: ignore[attr-defined]
            unit_str = "°C" if cfg.get("units") == "metric" else "°F"
            icon_cache = self.master.icon_cache  # type: ignore[attr-defined]
        except AttributeError:
            unit_str = "°C"
            icon_cache = {}

        city = loc.get("name", cw["name"])
        temp = round(cw["main"]["temp"])
        desc = cw["weather"][0]["description"].title()
        humidity = cw["main"]["humidity"]

        self.city_lbl.configure(text=city)
        self.temp_lbl.configure(text=f"{temp}{unit_str}")
        self.desc_lbl.configure(text=f"{desc}  💧{humidity}%")

        icon = get_icon(cw["weather"][0]["icon"], (54, 54), icon_cache)
        if icon:
            self.icon_lbl.configure(image=icon)

    # ------------------------------------------------------------------
    def _drag_start(self, event):
        self._drag_x = event.x
        self._drag_y = event.y

    def _drag_move(self, event):
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")
