"""Weather tools using Open-Meteo API (free, no API key required)."""

import httpx
from strands import tool


# Geocoding to get coordinates from city name
async def _geocode_city(city: str) -> dict | None:
    """Get latitude and longitude for a city name."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return {
                "name": result.get("name"),
                "country": result.get("country"),
                "latitude": result.get("latitude"),
                "longitude": result.get("longitude"),
            }
        return None


def _geocode_city_sync(city: str) -> dict | None:
    """Synchronous version of geocoding."""
    with httpx.Client() as client:
        response = client.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )
        data = response.json()
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            return {
                "name": result.get("name"),
                "country": result.get("country"),
                "latitude": result.get("latitude"),
                "longitude": result.get("longitude"),
            }
        return None


@tool
def get_current_weather(city: str) -> str:
    """
    Get current weather conditions for a city.

    Args:
        city: Name of the city (e.g., "London", "New York", "Tokyo")

    Returns:
        Current weather information including temperature, humidity, wind, and conditions
    """
    location = _geocode_city_sync(city)
    if not location:
        return f"Could not find location: {city}"

    with httpx.Client() as client:
        response = client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m,wind_direction_10m",
                "timezone": "auto",
            },
        )
        data = response.json()

    current = data.get("current", {})
    units = data.get("current_units", {})

    # Weather code descriptions
    weather_codes = {
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

    weather_desc = weather_codes.get(current.get("weather_code", 0), "Unknown")

    return f"""Current Weather for {location["name"]}, {location["country"]}:
- Conditions: {weather_desc}
- Temperature: {current.get("temperature_2m")}{units.get("temperature_2m", "°C")}
- Feels Like: {current.get("apparent_temperature")}{units.get("apparent_temperature", "°C")}
- Humidity: {current.get("relative_humidity_2m")}{units.get("relative_humidity_2m", "%")}
- Wind: {current.get("wind_speed_10m")} {units.get("wind_speed_10m", "km/h")} from {current.get("wind_direction_10m")}°
- Precipitation: {current.get("precipitation")} {units.get("precipitation", "mm")}"""


@tool
def get_weather_forecast(city: str, days: int = 7) -> str:
    """
    Get weather forecast for a city.

    Args:
        city: Name of the city (e.g., "London", "New York", "Tokyo")
        days: Number of days to forecast (1-16, default 7)

    Returns:
        Weather forecast with daily high/low temperatures and conditions
    """
    location = _geocode_city_sync(city)
    if not location:
        return f"Could not find location: {city}"

    days = min(max(1, days), 16)  # Clamp to valid range

    with httpx.Client() as client:
        response = client.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
                "timezone": "auto",
                "forecast_days": days,
            },
        )
        data = response.json()

    daily = data.get("daily", {})
    _ = data.get("daily_units", {})  # Available but not currently used

    weather_codes = {
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

    forecast_lines = [
        f"Weather Forecast for {location['name']}, {location['country']}:\n"
    ]

    dates = daily.get("time", [])
    temps_max = daily.get("temperature_2m_max", [])
    temps_min = daily.get("temperature_2m_min", [])
    weather = daily.get("weather_code", [])
    precip = daily.get("precipitation_sum", [])
    wind = daily.get("wind_speed_10m_max", [])

    for i in range(len(dates)):
        weather_desc = weather_codes.get(weather[i], "Unknown")
        forecast_lines.append(
            f"📅 {dates[i]}: {weather_desc}\n"
            f"   High: {temps_max[i]}°C | Low: {temps_min[i]}°C | "
            f"Precip: {precip[i]}mm | Wind: {wind[i]}km/h"
        )

    return "\n".join(forecast_lines)
