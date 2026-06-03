import customtkinter as ctk
import requests
import threading
from ui.custom_widgets import GradientFrame
from utils import get_icon

class DashboardView(ctk.CTkToplevel):
    def __init__(self, master, config, icon_cache, **kwargs):
        super().__init__(master, **kwargs)
        self.title("Saved Locations Dashboard")
        self.geometry("900x600")
        self.app_config = config
        self.icon_cache = icon_cache
        self.attributes('-topmost', True)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(self, text="World Weather Dashboard", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, pady=20)
        
        self.scroll_frame = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        
        self.scroll_frame.grid_columnconfigure((0, 1, 2), weight=1)
        self.load_dashboard()
        
    def load_dashboard(self):
        saved_locations = self.app_config.get("saved_locations", [])
        if not saved_locations:
            ctk.CTkLabel(self.scroll_frame, text="No saved locations yet!").grid(row=0, column=1, pady=50)
            return
            
        for i, loc in enumerate(saved_locations):
            card = GradientFrame(self.scroll_frame, corner_radius=15, height=150)
            card.grid(row=i//3, column=i%3, padx=10, pady=10, sticky="nsew")
            card.grid_propagate(False)
            
            lbl_city = ctk.CTkLabel(card, text=loc["name"], font=ctk.CTkFont(size=18, weight="bold"), text_color="white", bg_color="transparent")
            lbl_city.pack(pady=(15, 0))
            
            lbl_temp = ctk.CTkLabel(card, text="--°", font=ctk.CTkFont(size=36, weight="bold"), text_color="white", bg_color="transparent")
            lbl_temp.pack(pady=5)
            
            lbl_desc = ctk.CTkLabel(card, text="Loading...", font=ctk.CTkFont(size=12), text_color="white", bg_color="transparent")
            lbl_desc.pack()
            
            threading.Thread(target=self.fetch_card_weather, args=(loc, card, lbl_temp, lbl_desc), daemon=True).start()

    def fetch_card_weather(self, loc, card, lbl_temp, lbl_desc):
        try:
            api_key = self.app_config.get("api_key")
            units = self.app_config.get("units")
            url = f"https://api.openweathermap.org/data/2.5/weather?lat={loc['lat']}&lon={loc['lon']}&appid={api_key}&units={units}"
            res = requests.get(url)
            if res.status_code == 200:
                data = res.json()
                self.after(0, lambda: self.update_card(card, lbl_temp, lbl_desc, data))
        except Exception:
            pass
            
    def update_card(self, card, lbl_temp, lbl_desc, data):
        unit_str = "°C" if self.app_config.get("units") == "metric" else "°F"
        temp = round(data["main"]["temp"])
        desc = data["weather"][0]["description"]
        
        lbl_temp.configure(text=f"{temp}{unit_str}")
        lbl_desc.configure(text=desc.title())
        
        condition = desc.lower()
        if "clear" in condition or "sun" in condition:
            card.colors = ("#FFD194", "#70E1F5")
            lbl_temp.configure(text_color="black")
            card.winfo_children()[1].configure(text_color="black")
            lbl_desc.configure(text_color="black")
        elif "rain" in condition or "drizzle" in condition:
            card.colors = ("#3a7bd5", "#3a6073")
        elif "cloud" in condition or "overcast" in condition:
            card.colors = ("#bdc3c7", "#2c3e50")
        elif "snow" in condition:
            card.colors = ("#E0EAFC", "#CFDEF3")
            lbl_temp.configure(text_color="black")
            card.winfo_children()[1].configure(text_color="black")
            lbl_desc.configure(text_color="black")
        else:
            card.colors = ("#000000", "#434343")
        card._draw_gradient()
