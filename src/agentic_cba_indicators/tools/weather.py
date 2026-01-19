"""Weather tools using Open-Meteo API (free, no API key required)."""

from typing import Final

from strands import tool

from ._geo import geocode_city
from ._http import APIError, fetch_json, format_error
from ._timeout import timeout

# WMO Weather Code descriptions (plain text, for current weather)
# See: https://open-meteo.com/en/docs#weathervariables
WEATHER_CODE_DESCRIPTIONS: Final[dict[int, str]] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Foggy",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}

# WMO Weather Code descriptions with emoji (for forecasts)
WEATHER_CODE_EMOJI: Final[dict[int, str]] = {
    0: "☀️ Clear",
    1: "🌤️ Mainly clear",
    2: "⛅ Partly cloudy",
    3: "☁️ Overcast",
    45: "🌫️ Foggy",
    48: "🌫️ Rime fog",
    51: "🌧️ Light drizzle",
    53: "🌧️ Drizzle",
    55: "🌧️ Dense drizzle",
    61: "🌧️ Slight rain",
    63: "🌧️ Rain",
    65: "🌧️ Heavy rain",
    71: "🌨️ Light snow",
    73: "🌨️ Snow",
    75: "🌨️ Heavy snow",
    80: "🌦️ Rain showers",
    81: "🌦️ Moderate showers",
    82: "⛈️ Heavy showers",
    95: "⛈️ Thunderstorm",
    96: "⛈️ T-storm + hail",
    99: "⛈️ Severe t-storm",
}


@tool
@timeout(30)
def get_current_weather(city: str) -> str:
    """
    Get current weather conditions for a city.

    Args:
        city: Name of the city (e.g., "London", "New York", "Tokyo")

    Returns:
        Current weather information including temperature, humidity, wind, and conditions
    """
    location = geocode_city(city)
    if not location:
        return f"Could not find location: {city}"

    try:
        data = fetch_json(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
                "timezone": "auto",
            },
        )
    except APIError as e:
        return format_error(e, "fetching current weather")

    if not isinstance(data, dict):
        return "Error fetching current weather: unexpected response format"

    current = data.get("current", {})
    units = data.get("current_units", {})

    weather_desc = WEATHER_CODE_DESCRIPTIONS.get(
        current.get("weather_code", 0), "Unknown"
    )

    return f"""Current Weather for {location["name"]}, {location["country"]}:
- Conditions: {weather_desc}
- Temperature: {current.get("temperature_2m")}{units.get("temperature_2m", "°C")}
- Feels Like: {current.get("apparent_temperature")}{units.get("apparent_temperature", "°C")}
- Humidity: {current.get("relative_humidity_2m")}{units.get("relative_humidity_2m", "%")}
- Wind: {current.get("wind_speed_10m")} {units.get("wind_speed_10m", "km/h")} from {current.get("wind_direction_10m")}°
- Precipitation: {current.get("precipitation")} {units.get("precipitation", "mm")}"""


@tool
@timeout(30)
def get_weather_forecast(city: str, days: int = 7) -> str:
    """
    Get weather forecast for a city.

    Args:
        city: Name of the city (e.g., "London", "New York", "Tokyo")
        days: Number of days to forecast (1-16, default 7)

    Returns:
        Weather forecast with daily high/low temperatures and conditions
    """
    location = geocode_city(city)
    if not location:
        return f"Could not find location: {city}"

    days = min(max(1, days), 16)  # Clamp to valid range

    try:
        data = fetch_json(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
                "timezone": "auto",
                "forecast_days": days,
            },
        )
    except APIError as e:
        return format_error(e, "fetching forecast")

    if not isinstance(data, dict):
        return "Error fetching forecast: unexpected response format"

    daily = data.get("daily", {})
    _ = data.get("daily_units", {})  # Available but not currently used

    forecast_lines = [
        f"Weather Forecast for {location['name']}, {location['country']}:\n"
    ]

    dates = daily.get("time", [])
    temps_max = daily.get("temperature_2m_max", [])
    temps_min = daily.get("temperature_2m_min", [])
    weather = daily.get("weather_code", [])
    precip = daily.get("precipitation_sum", [])
    wind = daily.get("wind_speed_10m_max", [])

    # CR-0019: Use zip to safely iterate even if arrays have mismatched lengths
    for date, t_max, t_min, weather_code, prec, wnd in zip(
        dates, temps_max, temps_min, weather, precip, wind, strict=False
    ):
        weather_desc = WEATHER_CODE_EMOJI.get(weather_code, "Unknown")
        forecast_lines.append(
            f"📅 {date}: {weather_desc}\n"
            f"   High: {t_max}°C | Low: {t_min}°C | "
            f"Precip: {prec}mm | Wind: {wnd}km/h"
        )

    return "\n".join(forecast_lines)
