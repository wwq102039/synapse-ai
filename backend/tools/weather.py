import json
import urllib.request
import urllib.parse
from . import register


@register(
    "weather",
    "查询城市实时天气。返回温度、湿度、风速和天气状况。",
    {"city": {"type": "string", "description": "城市名称，如 '北京'、'上海'、'东京'"}}
)
def weather(city: str) -> str:
    """Fetch weather using Open-Meteo free API (no key needed)."""
    try:
        # First geocode the city
        geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={urllib.parse.quote(city)}&count=1&language=en"
        req = urllib.request.Request(geo_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            geo_data = json.loads(resp.read().decode())

        if not geo_data.get("results"):
            return json.dumps({"error": f"City not found: {city}"})

        loc = geo_data["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]

        # Get weather
        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,"
            f"weather_code,apparent_temperature&timezone=auto"
        )
        req2 = urllib.request.Request(weather_url)
        with urllib.request.urlopen(req2, timeout=10) as resp2:
            wdata = json.loads(resp2.read().decode())

        current = wdata.get("current", {})
        weather_codes = {
            0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle",
            53: "Moderate drizzle", 55: "Dense drizzle", 61: "Slight rain",
            63: "Moderate rain", 65: "Heavy rain", 71: "Slight snow",
            73: "Moderate snow", 75: "Heavy snow", 95: "Thunderstorm",
        }

        return json.dumps({
            "city": loc["name"],
            "country": loc.get("country", ""),
            "temperature_c": current.get("temperature_2m"),
            "feels_like_c": current.get("apparent_temperature"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "wind_speed_kmh": current.get("wind_speed_10m"),
            "condition": weather_codes.get(current.get("weather_code"), "Unknown"),
        }, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"Weather fetch failed: {str(e)}"})
