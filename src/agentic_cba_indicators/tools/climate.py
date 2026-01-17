"""Climate tools using Open-Meteo Climate API (free, no API key required)."""

from strands import tool

from ._geo import geocode_city
from ._http import APIError, fetch_json, format_error


@tool
def get_climate_data(city: str) -> str:
    """
    Get climate normals (30-year averages) for a city.
    Shows monthly average temperatures, precipitation, and other climate indicators.

    Args:
        city: Name of the city (e.g., "London", "Paris", "Sydney")

    Returns:
        Climate normals including monthly temperatures and precipitation
    """
    location = geocode_city(city)
    if not location:
        return f"Could not find location: {city}"

    try:
        data = fetch_json(
            "https://climate-api.open-meteo.com/v1/climate",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "start_date": "1991-01-01",
                "end_date": "2020-12-31",
                "models": "EC_Earth3P_HR",
                "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum",
            },
        )
    except APIError as e:
        return format_error(e, "fetching climate normals")

    if not isinstance(data, dict):
        return "Error fetching climate normals: unexpected response format"

    if "error" in data:
        return f"Climate data not available for {city}: {data.get('reason', 'Unknown error')}"

    daily = data.get("daily", {})

    # Calculate monthly averages from daily data
    months = [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]

    # Group by month and calculate averages
    temps_mean = daily.get("temperature_2m_mean", [])
    temps_max = daily.get("temperature_2m_max", [])
    temps_min = daily.get("temperature_2m_min", [])
    precip = daily.get("precipitation_sum", [])
    dates = daily.get("time", [])

    monthly_data: dict[int, dict[str, list[float]]] = {
        i: {"temps": [], "highs": [], "lows": [], "precip": []} for i in range(12)
    }

    for i, date in enumerate(dates):
        if i < len(temps_mean) and temps_mean[i] is not None:
            month_idx = int(date[5:7]) - 1
            monthly_data[month_idx]["temps"].append(temps_mean[i])
            if i < len(temps_max) and temps_max[i] is not None:
                monthly_data[month_idx]["highs"].append(temps_max[i])
            if i < len(temps_min) and temps_min[i] is not None:
                monthly_data[month_idx]["lows"].append(temps_min[i])
            if i < len(precip) and precip[i] is not None:
                monthly_data[month_idx]["precip"].append(precip[i])

    lines = [
        f"Climate Normals for {location['name']}, {location['country']} (1991-2020):\n"
    ]
    lines.append("Month | Avg Temp | High | Low  | Precip")
    lines.append("-" * 45)

    for i, month in enumerate(months):
        data = monthly_data[i]
        avg_temp = sum(data["temps"]) / len(data["temps"]) if data["temps"] else 0
        avg_high = sum(data["highs"]) / len(data["highs"]) if data["highs"] else 0
        avg_low = sum(data["lows"]) / len(data["lows"]) if data["lows"] else 0
        total_precip = (
            sum(data["precip"]) / 30 if data["precip"] else 0
        )  # Average monthly

        lines.append(
            f"{month:5} | {avg_temp:6.1f}°C | {avg_high:4.1f}°C | {avg_low:4.1f}°C | {total_precip:5.1f}mm"
        )

    return "\n".join(lines)


@tool
def get_historical_climate(city: str, year: int) -> str:
    """
    Get historical weather data for a specific year and city.

    Args:
        city: Name of the city (e.g., "London", "Paris", "Sydney")
        year: Year to get data for (1950-2023)

    Returns:
        Historical climate summary for the specified year
    """
    location = geocode_city(city)
    if not location:
        return f"Could not find location: {city}"

    year = min(max(1950, year), 2023)

    try:
        data = fetch_json(
            "https://archive-api.open-meteo.com/v1/archive",
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "start_date": f"{year}-01-01",
                "end_date": f"{year}-12-31",
                "daily": "temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
            },
        )
    except APIError as e:
        return format_error(e, "fetching historical climate data")

    if not isinstance(data, dict):
        return "Error fetching historical climate data: unexpected response format"

    if "error" in data:
        return f"Historical data not available: {data.get('reason', 'Unknown error')}"

    daily = data.get("daily", {})
    temps_mean = [t for t in daily.get("temperature_2m_mean", []) if t is not None]
    temps_max = [t for t in daily.get("temperature_2m_max", []) if t is not None]
    temps_min = [t for t in daily.get("temperature_2m_min", []) if t is not None]
    precip = [p for p in daily.get("precipitation_sum", []) if p is not None]

    if not temps_mean:
        return f"No data available for {city} in {year}"

    return f"""Historical Climate for {location["name"]}, {location["country"]} ({year}):

📊 Temperature Summary:
- Annual Mean: {sum(temps_mean) / len(temps_mean):.1f}°C
- Highest: {max(temps_max):.1f}°C
- Lowest: {min(temps_min):.1f}°C
- Average Daily High: {sum(temps_max) / len(temps_max):.1f}°C
- Average Daily Low: {sum(temps_min) / len(temps_min):.1f}°C

🌧️ Precipitation Summary:
- Total Annual: {sum(precip):.1f}mm
- Days with Precipitation: {sum(1 for p in precip if p > 0.1)}
- Wettest Day: {max(precip):.1f}mm"""
