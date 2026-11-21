"""Weather via Open-Meteo (free, no key; verify terms). Falls back to mild defaults offline."""
import json
import urllib.request

from . import config


def season_from(temp_c: float, rain: bool) -> str:
    if rain: return "monsoon"
    if temp_c <= 16: return "winter"
    if temp_c >= 29: return "summer"
    return "all"


def get_weather(lat=None, lon=None, timeout=4) -> dict:
    lat, lon = lat or config.LAT, lon or config.LON
    url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
           "&daily=temperature_2m_max,precipitation_probability_max&timezone=auto&forecast_days=1")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            d = json.load(r)["daily"]
        t, rain = float(d["temperature_2m_max"][0]), float(d["precipitation_probability_max"][0]) >= 60
        return {"temp_c": t, "rain": rain, "season": season_from(t, rain), "source": "open-meteo"}
    except Exception:  # noqa: BLE001
        return {"temp_c": 27.0, "rain": False, "season": "all", "source": "default (offline)"}
