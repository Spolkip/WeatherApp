import customtkinter as ctk
import math
import pytz
from datetime import datetime

class GradientFrame(ctk.CTkFrame):
    def __init__(self, master, colors=("black", "white"), direction="vertical", **kwargs):
        super().__init__(master, **kwargs)
        self.colors = colors
        self.direction = direction
        self.canvas = ctk.CTkCanvas(self, highlightthickness=0)
        self.canvas.place(x=0, y=0, relwidth=1, relheight=1)
        self.bind("<Configure>", self._draw_gradient)

    def _hex_to_rgb(self, hex_color):
        if not hex_color.startswith('#'):
            r, g, b = self.winfo_rgb(hex_color)
            return (r // 256, g // 256, b // 256)
            
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 3:
            hex_color = ''.join(c + c for c in hex_color)
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb):
        return '#%02x%02x%02x' % rgb

    def _draw_gradient(self, event=None):
        self.canvas.delete("gradient")
        width = self.winfo_width()
        height = self.winfo_height()
        if width <= 1 or height <= 1: return

        mode = ctk.get_appearance_mode()
        idx = 0 if mode == "Light" else 1
        c1 = self.colors[0][idx] if isinstance(self.colors[0], tuple) else self.colors[0]
        c2 = self.colors[1][idx] if isinstance(self.colors[1], tuple) else self.colors[1]

        r1, g1, b1 = self._hex_to_rgb(c1)
        r2, g2, b2 = self._hex_to_rgb(c2)

        limit = height if self.direction == "vertical" else width
        steps = min(limit, 100)
        
        for i in range(steps):
            ratio = i / max(1, steps - 1)
            r = int(r1 + (r2 - r1) * ratio)
            g = int(g1 + (g2 - g1) * ratio)
            b = int(b1 + (b2 - b1) * ratio)
            color = self._rgb_to_hex((r, g, b))
            
            if self.direction == "vertical":
                y0 = int(i * height / steps)
                y1 = int((i + 1) * height / steps)
                self.canvas.create_rectangle(0, y0, width, y1, fill=color, outline=color, tags="gradient")
            else:
                x0 = int(i * width / steps)
                x1 = int((i + 1) * width / steps)
                self.canvas.create_rectangle(x0, 0, x1, height, fill=color, outline=color, tags="gradient")
        self.canvas.lower("gradient")

class AQIGauge(ctk.CTkFrame):
    def __init__(self, master, bg_color="#2b2b2b", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.canvas = ctk.CTkCanvas(self, width=100, height=60, bg=bg_color, highlightthickness=0)
        self.canvas.pack(pady=5)
        self.aqi = 1
        
    def set_aqi(self, aqi_value):
        self.aqi = aqi_value
        self.draw_gauge()

    def draw_gauge(self):
        self.canvas.delete("all")
        colors = ["#00e400", "#ffff00", "#ff7e00", "#ff0000", "#8f3f97"]
        start_ang = 180
        extent = 180 / 5
        for i, c in enumerate(colors):
            self.canvas.create_arc(10, 10, 90, 90, start=180 - (i+1)*extent, extent=extent, 
                                   style="arc", outline=c, width=8)
                                   
        angle = 180 - (self.aqi - 0.5) * extent
        rad = math.radians(angle)
        x = 50 + 35 * math.cos(rad)
        y = 50 - 35 * math.sin(rad)
        
        needle_color = "white" if ctk.get_appearance_mode() == "Dark" else "black"
        self.canvas.create_line(50, 50, x, y, width=2, fill=needle_color, arrow="last", tags="needle")
        self.canvas.create_oval(46, 46, 54, 54, fill="gray")

class WindCompass(ctk.CTkFrame):
    def __init__(self, master, bg_color="#2b2b2b", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.canvas = ctk.CTkCanvas(self, width=80, height=80, bg=bg_color, highlightthickness=0)
        self.canvas.pack(pady=5)
        self.angle = 0
        
    def set_angle(self, angle):
        self.angle = angle
        self.draw_compass()
        
    def draw_compass(self):
        self.canvas.delete("all")
        color = "white" if ctk.get_appearance_mode() == "Dark" else "black"
        self.canvas.create_oval(10, 10, 70, 70, outline="gray", width=2)
        
        self.canvas.create_text(40, 5, text="N", fill=color, font=("Arial", 8, "bold"))
        self.canvas.create_text(40, 75, text="S", fill=color, font=("Arial", 8))
        self.canvas.create_text(75, 40, text="E", fill=color, font=("Arial", 8))
        self.canvas.create_text(5, 40, text="W", fill=color, font=("Arial", 8))
        
        rad = math.radians(self.angle - 90)
        x = 40 + 25 * math.cos(rad)
        y = 40 + 25 * math.sin(rad)
        
        self.canvas.create_line(40, 40, x, y, width=3, fill="#4a90e2", arrow="last")
        self.canvas.create_oval(37, 37, 43, 43, fill="gray")

class MinMaxTempBar(ctk.CTkFrame):
    def __init__(self, master, bg_color="#2b2b2b", **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.canvas = ctk.CTkCanvas(self, width=100, height=10, bg=bg_color, highlightthickness=0)
        self.canvas.pack(pady=5)
        
    def set_temps(self, day_min, day_max, week_min, week_max):
        self.canvas.delete("all")
        width = 100
        height = 10
        
        bg_bar_color = "#404040" if ctk.get_appearance_mode() == "Dark" else "#e0e0e0"
        self.canvas.create_line(5, 5, width-5, 5, width=8, capstyle="round", fill=bg_bar_color)
        
        if week_max == week_min:
            return
            
        range_span = week_max - week_min
        
        x0 = 5 + (day_min - week_min) / range_span * (width - 10)
        x1 = 5 + (day_max - week_min) / range_span * (width - 10)
        
        if x1 - x0 < 4:
            x1 = x0 + 4
            
        self.canvas.create_line(x0, 5, x1, 5, width=8, capstyle="round", fill="#ff9800")

class LoadingSpinner(ctk.CTkFrame):
    def __init__(self, master, bg_color=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        if bg_color is None or bg_color == "transparent":
            bg = master.cget("fg_color")
            if isinstance(bg, (list, tuple)):
                bg = bg[1] if ctk.get_appearance_mode() == "Dark" else bg[0]
            if bg == "transparent": bg = "#2b2b2b"
            bg_color = bg
        self.canvas = ctk.CTkCanvas(self, width=100, height=100, bg=bg_color, highlightthickness=0)
        self.canvas.pack()
        self.angle = 0
        self.is_spinning = False
        
    def start(self):
        self.is_spinning = True
        self._spin()
        
    def stop(self):
        self.is_spinning = False
        
    def _spin(self):
        if not self.is_spinning: return
        self.canvas.delete("all")
        
        cx, cy = 50, 50
        radius = 15
        
        # Central sun circle
        self.canvas.create_oval(cx-12, cy-12, cx+12, cy+12, fill="#FFD194", outline="")
        
        # Animated rays
        for i in range(8):
            rad = math.radians(self.angle + i * 45)
            # Make the rays pulse slightly
            pulse = 3 * math.sin(math.radians(self.angle * 2 + i * 45))
            x1 = cx + (radius + 5) * math.cos(rad)
            y1 = cy + (radius + 5) * math.sin(rad)
            x2 = cx + (radius + 12 + pulse) * math.cos(rad)
            y2 = cy + (radius + 12 + pulse) * math.sin(rad)
            self.canvas.create_line(x1, y1, x2, y2, width=3, fill="#FFD194", capstyle="round")
            
        self.angle = (self.angle + 8) % 360
        self.after(40, self._spin)

class MoonPhaseWidget(ctk.CTkFrame):
    def __init__(self, master, bg_color=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        if bg_color is None or bg_color == "transparent":
            bg = master.cget("fg_color")
            if isinstance(bg, (list, tuple)):
                bg = bg[1] if ctk.get_appearance_mode() == "Dark" else bg[0]
            if bg == "transparent": bg = "#2b2b2b"
            bg_color = bg
        self.canvas = ctk.CTkCanvas(self, width=80, height=80, bg=bg_color, highlightthickness=0)
        self.canvas.pack(pady=5)
        self.phase = 0
        
    def set_date(self, dt):
        # Simple calculation based on known new moon: Jan 6, 2000, 18:14 UTC
        known_new_moon = datetime(2000, 1, 6, 18, 14, tzinfo=pytz.utc).timestamp()
        lunar_cycle = 2551443  # 29.53059 days in seconds
        diff = dt.timestamp() - known_new_moon
        phase = (diff % lunar_cycle) / lunar_cycle
        self.draw_moon(phase)
        
    def draw_moon(self, phase):
        self.canvas.delete("all")
        cx, cy = 40, 40
        radius = 30
        
        # Dark circle background
        self.canvas.create_oval(cx-radius, cy-radius, cx+radius, cy+radius, fill="#2b2b2b", outline="gray")
        
        moon_color = "#f5f5f5"
        
        if phase < 0.5: # Waxing (Right side illuminated)
            self.canvas.create_arc(cx-radius, cy-radius, cx+radius, cy+radius, start=270, extent=180, fill=moon_color, outline="")
            
            # Terminator line
            if phase < 0.25: # Waxing Crescent (draw dark oval over right side)
                oval_width = radius * (1 - phase * 4)
                self.canvas.create_oval(cx-oval_width, cy-radius, cx+oval_width, cy+radius, fill="#2b2b2b", outline="")
            else: # Waxing Gibbous (draw light oval over left side)
                oval_width = radius * ((phase - 0.25) * 4)
                self.canvas.create_oval(cx-oval_width, cy-radius, cx+oval_width, cy+radius, fill=moon_color, outline="")
                
        else: # Waning (Left side illuminated)
            self.canvas.create_arc(cx-radius, cy-radius, cx+radius, cy+radius, start=90, extent=180, fill=moon_color, outline="")
            
            # Terminator line
            if phase < 0.75: # Waning Gibbous (draw light oval over right side)
                oval_width = radius * (1 - (phase - 0.5) * 4)
                self.canvas.create_oval(cx-oval_width, cy-radius, cx+oval_width, cy+radius, fill=moon_color, outline="")
            else: # Waning Crescent (draw dark oval over left side)
                oval_width = radius * ((phase - 0.75) * 4)
                self.canvas.create_oval(cx-oval_width, cy-radius, cx+oval_width, cy+radius, fill="#2b2b2b", outline="")


class SunriseArcWidget(ctk.CTkFrame):
    """Visual arc showing sun position between sunrise and sunset."""
    def __init__(self, master, bg_color=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        if bg_color is None or bg_color == "transparent":
            bg = master.cget("fg_color")
            if isinstance(bg, (list, tuple)):
                bg = bg[1] if ctk.get_appearance_mode() == "Dark" else bg[0]
            if bg == "transparent":
                bg = "#2b2b2b"
            bg_color = bg
        self.canvas = ctk.CTkCanvas(self, width=120, height=68, bg=bg_color, highlightthickness=0)
        self.canvas.pack(pady=2)
        self.sunrise_ts = 0
        self.sunset_ts = 0

    def set_times(self, sunrise_ts: int, sunset_ts: int):
        self.sunrise_ts = sunrise_ts
        self.sunset_ts = sunset_ts
        self._draw_sun_arc()

    def _draw_sun_arc(self):
        self.canvas.delete("all")
        cx, cy = 60, 58
        rx, ry = 50, 42

        # Horizon line
        self.canvas.create_line(4, cy, 116, cy, fill="#555", width=1, dash=(4, 3))

        # Sun arc (semicircle above horizon)
        self.canvas.create_arc(cx - rx, cy - ry, cx + rx, cy + ry,
                               start=0, extent=180, style="arc",
                               outline="#4a90e2", width=2)

        # Sunrise / sunset time labels
        sr_text = datetime.fromtimestamp(self.sunrise_ts).strftime("%H:%M") if self.sunrise_ts else "--:--"
        ss_text = datetime.fromtimestamp(self.sunset_ts).strftime("%H:%M") if self.sunset_ts else "--:--"
        self.canvas.create_text(14, cy + 9, text=sr_text, fill="#FFD194", font=("Arial", 7))
        self.canvas.create_text(106, cy + 9, text=ss_text, fill="#FF8C42", font=("Arial", 7))

        # Sun position on arc
        now = datetime.now().timestamp()
        total_day = (self.sunset_ts - self.sunrise_ts) if (self.sunrise_ts and self.sunset_ts) else 0

        if total_day > 0 and self.sunrise_ts <= now <= self.sunset_ts:
            progress = (now - self.sunrise_ts) / total_day  # 0.0 → 1.0
            angle_rad = math.pi * (1.0 - progress)          # π → 0 (left to right)
            sun_x = cx + rx * math.cos(angle_rad)
            sun_y = cy - ry * math.sin(angle_rad)
            # Soft glow
            self.canvas.create_oval(sun_x - 9, sun_y - 9, sun_x + 9, sun_y + 9,
                                    fill="#FFE87C", outline="")
            self.canvas.create_oval(sun_x - 5, sun_y - 5, sun_x + 5, sun_y + 5,
                                    fill="#FFD700", outline="#FFA500", width=1)
        elif self.sunrise_ts and now < self.sunrise_ts:
            # Before sunrise — sun just below left horizon
            self.canvas.create_oval(cx - rx - 5, cy - 4, cx - rx + 5, cy + 6,
                                    fill="#FFD700", outline="#FFA500")
        else:
            # After sunset — sun just below right horizon
            self.canvas.create_oval(cx + rx - 5, cy - 4, cx + rx + 5, cy + 6,
                                    fill="#FF6B35", outline="#CC4411")
