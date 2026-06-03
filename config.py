import os
import json
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("WEATHER_KEY")

class Config:
    def __init__(self):
        self.settings = {
            "default_city": "",
            "units": "metric",
            "refresh_interval": 30,
            "api_key": API_KEY,
            "saved_locations": [],
            "alert_rules": [],
            "wallpaper_auto_update": False,
            "rain_notify": True,
            "appearance_mode": "System",
        }
        self.load_settings()

    def load_settings(self):
        try:
            if os.path.exists("weather_settings.json"):
                with open("weather_settings.json", "r") as f:
                    saved_settings = json.load(f)
                    self.settings.update(saved_settings)
        except Exception as e:
            print(f"Error loading settings: {e}")

    def save_settings(self):
        try:
            with open("weather_settings.json", "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default)
        
    def set(self, key, value):
        self.settings[key] = value
        self.save_settings()
