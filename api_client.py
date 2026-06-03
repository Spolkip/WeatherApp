import requests
import threading
from geopy.geocoders import Nominatim
from geopy.location import Location as GeoLocation
from typing import cast
import timezonefinder

class WeatherAPIClient:
    def __init__(self, config):
        self.config = config
        self.geolocator = Nominatim(user_agent="weather_app")
        self.tf = None
        self._tf_lock = threading.Lock()
        # Pre-warm TimezoneFinder in the background so first request isn't slow
        threading.Thread(target=self._prewarm_tf, daemon=True).start()

    def _prewarm_tf(self):
        with self._tf_lock:
            if self.tf is None:
                self.tf = timezonefinder.TimezoneFinder()

    def fetch_weather(self, city, on_success, on_error):
        threading.Thread(target=self._fetch_weather_thread, args=(city, on_success, on_error), daemon=True).start()

    def _fetch_weather_thread(self, city, on_success, on_error):
        try:
            api_key = self.config.get("api_key")
            if not api_key:
                raise Exception("API key not configured.")

            # If no city given, resolve via IP (runs in background thread — safe)
            if not city:
                try:
                    import requests as _req
                    ip_data = _req.get('https://ipapi.co/json/', timeout=5).json()
                    city = ip_data.get('city', 'London')
                except Exception:
                    city = 'London'

            location = cast(GeoLocation, self.geolocator.geocode(city))
            if not location:
                raise Exception("Could not find location")
                
            lat = location.latitude
            lon = location.longitude
            
            with self._tf_lock:
                if not self.tf:
                    self.tf = timezonefinder.TimezoneFinder()
            timezone_str = self.tf.timezone_at(lng=lon, lat=lat)
            
            location_data = {
                "name": location.address.split(",")[0],
                "lat": lat,
                "lon": lon,
                "timezone": timezone_str
            }
            
            units = self.config.get("units")
            current_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units={units}"
            res = requests.get(current_url)
            res.raise_for_status()
            current_weather = res.json()
            
            forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={api_key}&units={units}&cnt=40"
            res = requests.get(forecast_url)
            res.raise_for_status()
            forecast_data = res.json()
            
            aqi_url = f"http://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={api_key}"
            res = requests.get(aqi_url)
            res.raise_for_status()
            air_quality = res.json()

            # UV index from Open-Meteo (free, no key needed)
            uv_index = None
            try:
                uv_url = (f"https://api.open-meteo.com/v1/forecast?"
                          f"latitude={lat}&longitude={lon}&current=uv_index&timezone=auto")
                uv_res = requests.get(uv_url, timeout=6)
                if uv_res.status_code == 200:
                    uv_index = uv_res.json().get("current", {}).get("uv_index")
            except Exception:
                pass

            data = {
                "location": location_data,
                "current": current_weather,
                "forecast": forecast_data,
                "air_quality": air_quality,
                "uv_index": uv_index,
            }
            on_success(data)
        except Exception as e:
            on_error(str(e))

    def fetch_autofill(self, query, on_success):
        if not self.config.get("api_key"): return
        threading.Thread(target=self._fetch_autofill_thread, args=(query, on_success), daemon=True).start()

    def _fetch_autofill_thread(self, query, on_success):
        try:
            url = f"http://api.openweathermap.org/geo/1.0/direct?q={query}&limit=5&appid={self.config.get('api_key')}"
            res = requests.get(url)
            if res.status_code == 200:
                on_success(res.json())
        except Exception:
            pass

    def fetch_historical(self, lat, lon, on_success, on_error):
        """Fetch same-day-last-year avg temp from Open-Meteo archive (free, no key)."""
        threading.Thread(
            target=self._fetch_historical_thread,
            args=(lat, lon, on_success, on_error),
            daemon=True
        ).start()

    def _fetch_historical_thread(self, lat, lon, on_success, on_error):
        try:
            from datetime import date
            last_year_date = date.today().replace(year=date.today().year - 1).isoformat()
            units_param = "celsius" if self.config.get("units") == "metric" else "fahrenheit"
            url = (
                f"https://archive-api.open-meteo.com/v1/archive?"
                f"latitude={lat}&longitude={lon}"
                f"&start_date={last_year_date}&end_date={last_year_date}"
                f"&daily=temperature_2m_max,temperature_2m_min"
                f"&temperature_unit={units_param}&timezone=auto"
            )
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                t_max = data["daily"]["temperature_2m_max"][0]
                t_min = data["daily"]["temperature_2m_min"][0]
                if t_max is not None and t_min is not None:
                    on_success(round((t_max + t_min) / 2))
                else:
                    on_error("No historical data")
            else:
                on_error(f"HTTP {res.status_code}")
        except Exception as e:
            on_error(str(e))

    def fetch_time_machine(self, lat, lon, date_str, on_success, on_error):
        """Fetch historical daily data for a specific date from Open-Meteo archive."""
        threading.Thread(
            target=self._fetch_time_machine_thread,
            args=(lat, lon, date_str, on_success, on_error),
            daemon=True
        ).start()

    def _fetch_time_machine_thread(self, lat, lon, date_str, on_success, on_error):
        try:
            units_param = "celsius" if self.config.get("units") == "metric" else "fahrenheit"
            wind_param = "ms" if self.config.get("units") == "metric" else "mph"
            url = (
                f"https://archive-api.open-meteo.com/v1/archive?"
                f"latitude={lat}&longitude={lon}"
                f"&start_date={date_str}&end_date={date_str}"
                f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
                f"&temperature_unit={units_param}&wind_speed_unit={wind_param}&timezone=auto"
            )
            res = requests.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                try:
                    d = data["daily"]
                    result = {
                        "t_max": d["temperature_2m_max"][0],
                        "t_min": d["temperature_2m_min"][0],
                        "precip": d["precipitation_sum"][0],
                        "wind": d["windspeed_10m_max"][0],
                        "date": date_str
                    }
                    if result["t_max"] is None:
                        on_error("Data not available for this date")
                    else:
                        on_success(result)
                except (KeyError, IndexError):
                    on_error("Invalid data format received")
            else:
                on_error(f"HTTP {res.status_code}")
        except Exception as e:
            on_error(str(e))
