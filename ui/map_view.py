import customtkinter as ctk
import tkintermapview

class MapView(ctk.CTkFrame):
    def __init__(self, master, config, **kwargs):
        super().__init__(master, corner_radius=15, **kwargs)
        self.app_config = config
        self.grid_propagate(False)
        self.pack_propagate(False)
        
        self.map_widget = tkintermapview.TkinterMapView(self, corner_radius=15)
        self.map_widget.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.map_widget.canvas.configure(bg="#2b2b2b") # Dark background for transparent radar tiles
        
        self.style_var = ctk.StringVar(value="Standard")
        self.style_btn = ctk.CTkSegmentedButton(self, values=["Standard", "Dark", "Satellite", "Radar"], 
                                                variable=self.style_var, command=self.change_style)
        self.style_btn.place(relx=0.05, rely=0.05)
        
    def change_style(self, style):
        if style == "Standard":
            self.map_widget.set_tile_server("https://a.tile.openstreetmap.org/{z}/{x}/{y}.png")
        elif style == "Dark":
            self.map_widget.set_tile_server("https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png")
        elif style == "Satellite":
            self.map_widget.set_tile_server("https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}&s=Ga", max_zoom=22)
        elif style == "Radar":
            api_key = self.app_config.get("api_key")
            if api_key:
                self.map_widget.set_tile_server(f"https://tile.openweathermap.org/map/precipitation_new/{{z}}/{{x}}/{{y}}.png?appid={api_key}")

    def update_map(self, lat, lon, city_name):
        self.map_widget.set_position(lat, lon)
        self.map_widget.set_zoom(8 if self.style_var.get() == "Radar" else 10)
        self.map_widget.delete_all_marker()
        if self.style_var.get() != "Radar":
            self.map_widget.set_marker(lat, lon, text=city_name)
