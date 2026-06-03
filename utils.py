import pytz
from datetime import datetime
from PIL import Image, ImageDraw
import io
import requests
import customtkinter as ctk

def format_time(timestamp, timezone_str):
    if not timezone_str:
        return datetime.fromtimestamp(timestamp).strftime("%H:%M")
    tz = pytz.timezone(timezone_str)
    return datetime.fromtimestamp(timestamp, tz).strftime("%H:%M")

def get_icon(icon_code, size, icon_cache):
    key = f"{icon_code}_{size[0]}"
    if key in icon_cache:
        return icon_cache[key]
        
    try:
        scale = "4x" if size[0] > 50 else "2x"
        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@{scale}.png"
        img_res = requests.get(icon_url, stream=True)
        if img_res.status_code == 200:
            img = Image.open(io.BytesIO(img_res.content))
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            icon_cache[key] = ctk_img
            return ctk_img
    except Exception as e:
        pass
    return None


def generate_tray_icon(current_weather: dict | None, unit_str: str):
    """Generate a dynamic system tray icon based on current weather."""
    from PIL import Image, ImageDraw, ImageFont
    
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    if not current_weather:
        draw.ellipse([4, 4, 60, 60], fill=(73, 109, 137))
        try:
            font = ImageFont.truetype("arial.ttf", 36)
        except Exception:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), "W", font=font)
        x = (size - (bbox[2] - bbox[0])) // 2
        y = (size - (bbox[3] - bbox[1])) // 2 - 4
        draw.text((x, y), "W", fill="white", font=font)
        return img
        
    temp = round(current_weather["main"]["temp"])
    desc = current_weather["weather"][0]["description"].lower()
    
    if "clear" in desc or "sun" in desc:
        bg_color = (255, 165, 0)
    elif "rain" in desc or "drizzle" in desc:
        bg_color = (58, 123, 213)
    elif "snow" in desc:
        bg_color = (200, 215, 255)
    elif "thunder" in desc or "storm" in desc:
        bg_color = (70, 50, 90)
    else:
        bg_color = (120, 130, 140)
        
    draw.rounded_rectangle([4, 4, 60, 60], radius=12, fill=bg_color)
    
    try:
        font = ImageFont.truetype("arialbd.ttf", 26)
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", 26)
        except Exception:
            font = ImageFont.load_default()
            
    text = f"{temp}°"
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (size - (bbox[2] - bbox[0])) // 2
    y = (size - (bbox[3] - bbox[1])) // 2 - 2
    draw.text((x, y), text, fill="white", font=font)
    
    return img



def set_wallpaper(city: str, temp: int, desc: str, unit_str: str, condition: str) -> bool:
    """Generate a weather wallpaper and set it as desktop background (Windows only)."""
    try:
        import ctypes
        import tempfile
        import os

        user32 = ctypes.windll.user32  # type: ignore
        w = user32.GetSystemMetrics(0) or 1920
        h = user32.GetSystemMetrics(1) or 1080

        cond = condition.lower()
        if "clear" in cond or "sun" in cond:
            c1, c2 = (255, 165, 0), (135, 206, 250)
        elif "rain" in cond or "drizzle" in cond:
            c1, c2 = (58, 123, 213), (58, 96, 115)
        elif "cloud" in cond or "overcast" in cond:
            c1, c2 = (100, 110, 130), (60, 65, 80)
        elif "snow" in cond:
            c1, c2 = (200, 215, 255), (150, 175, 220)
        elif "thunder" in cond or "storm" in cond:
            c1, c2 = (20, 20, 45), (70, 50, 90)
        else:
            c1, c2 = (30, 50, 80), (10, 20, 40)

        img = Image.new("RGB", (w, h))
        draw = ImageDraw.Draw(img)
        for y in range(h):
            ratio = y / h
            r = int(c1[0] + (c2[0] - c1[0]) * ratio)
            g = int(c1[1] + (c2[1] - c1[1]) * ratio)
            b = int(c1[2] + (c2[2] - c1[2]) * ratio)
            draw.line([(0, y), (w, y)], fill=(r, g, b))

        # Draw text info (centered)
        try:
            from PIL import ImageFont
            font_big = ImageFont.truetype("arial.ttf", max(h // 8, 80))
            font_med = ImageFont.truetype("arial.ttf", max(h // 22, 36))
            font_sm = ImageFont.truetype("arial.ttf", max(h // 30, 26))
        except Exception:
            font_big = font_med = font_sm = None  # type: ignore

        def draw_text(text, y_pos, font, fill=(255, 255, 255)):
            bbox = draw.textbbox((0, 0), text, font=font) if font else (0, 0, len(text) * 10, 20)
            x = (w - (bbox[2] - bbox[0])) // 2
            draw.text((x, y_pos), text, fill=fill, font=font)

        y0 = h // 3
        draw_text(f"{temp}{unit_str}", y0, font_big)
        draw_text(city, y0 + max(h // 8, 80) + 10, font_med, (220, 220, 220))
        draw_text(desc.title(), y0 + max(h // 8, 80) + 10 + max(h // 22, 36) + 8, font_sm, (180, 180, 180))

        tmp_path = os.path.join(tempfile.gettempdir(), "weather_wallpaper.bmp")
        img.save(tmp_path, "BMP")
        ctypes.windll.user32.SystemParametersInfoW(20, 0, tmp_path, 3)  # type: ignore
        return True
    except Exception as e:
        print(f"Wallpaper error: {e}")
        return False


def export_csv(data: dict, filepath: str) -> None:
    """Export weather data to a CSV file."""
    import csv
    from datetime import datetime as dt

    cw = data["current"]
    fc = data["forecast"]
    loc = data["location"]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Weather Export", dt.now().strftime("%Y-%m-%d %H:%M")])
        writer.writerow([])
        writer.writerow(["City", loc.get("name", "")])
        writer.writerow(["Temperature", cw["main"]["temp"]])
        writer.writerow(["Feels Like", cw["main"]["feels_like"]])
        writer.writerow(["Humidity (%)", cw["main"]["humidity"]])
        writer.writerow(["Pressure (hPa)", cw["main"]["pressure"]])
        writer.writerow(["Wind Speed (m/s)", cw["wind"]["speed"]])
        writer.writerow(["Description", cw["weather"][0]["description"]])
        writer.writerow([])
        writer.writerow(["=== Forecast ==="])
        writer.writerow(["Time", "Temp", "Description", "Rain %"])
        for item in fc["list"]:
            ts = dt.fromtimestamp(item["dt"]).strftime("%Y-%m-%d %H:%M")
            writer.writerow([ts, round(item["main"]["temp"]),
                             item["weather"][0]["description"],
                             round(item.get("pop", 0) * 100)])


def export_pdf(data: dict, filepath: str) -> bool:
    """Export weather data to a PDF file. Returns False if reportlab not installed."""
    try:
        from reportlab.lib.pagesizes import letter  # type: ignore
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer  # type: ignore
        from reportlab.lib.styles import getSampleStyleSheet  # type: ignore
        from reportlab.lib import colors  # type: ignore
        from datetime import datetime as dt

        cw = data["current"]
        fc = data["forecast"]
        loc = data["location"]

        doc = SimpleDocTemplate(filepath, pagesize=letter)
        styles = getSampleStyleSheet()
        elements = []

        elements.append(Paragraph(f"Weather Report — {loc.get('name', '')}", styles["Title"]))
        elements.append(Paragraph(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M')}", styles["Normal"]))
        elements.append(Spacer(1, 16))

        elements.append(Paragraph("Current Conditions", styles["Heading2"]))
        rows = [
            ["Metric", "Value"],
            ["Temperature", f"{round(cw['main']['temp'])}°"],
            ["Feels Like", f"{round(cw['main']['feels_like'])}°"],
            ["Humidity", f"{cw['main']['humidity']}%"],
            ["Pressure", f"{cw['main']['pressure']} hPa"],
            ["Wind Speed", f"{cw['wind']['speed']} m/s"],
            ["Description", cw["weather"][0]["description"].title()],
        ]
        t = Table(rows, colWidths=[200, 220])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5fa8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("PADDING", (0, 0), (-1, -1), 6),
        ]))
        elements.append(t)
        elements.append(Spacer(1, 16))

        elements.append(Paragraph("48-Hour Forecast", styles["Heading2"]))
        fc_rows = [["Time", "Temp", "Description", "Rain %"]]
        for item in fc["list"][:16]:
            ts = dt.fromtimestamp(item["dt"]).strftime("%m/%d %H:%M")
            fc_rows.append([ts, f"{round(item['main']['temp'])}°",
                           item["weather"][0]["description"].title(),
                           f"{round(item.get('pop', 0) * 100)}%"])
        ft = Table(fc_rows, colWidths=[90, 60, 210, 60])
        ft.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5fa8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("PADDING", (0, 0), (-1, -1), 4),
        ]))
        elements.append(ft)
        doc.build(elements)
        return True
    except ImportError:
        return False
    except Exception as e:
        print(f"PDF export error: {e}")
        return False
