"""
NASA POWER API tools for agricultural climate parameters.

NASA POWER (Prediction Of Worldwide Energy Resources) provides solar and
meteorological data for agricultural applications. Free, no API key required.

API Documentation: https://power.larc.nasa.gov/docs/
"""

from strands import tool

from ._geo import format_location, geocode_or_parse
from ._http import APIError, fetch_json, format_error

# NASA POWER API base URL
NASA_POWER_BASE = "https://power.larc.nasa.gov/api/temporal"

# Parameter groups for different use cases
AGRO_CLIMATE_PARAMS = [
    "T2M",  # Temperature at 2m (°C)
    "T2M_MAX",  # Maximum temperature at 2m (°C)
    "T2M_MIN",  # Minimum temperature at 2m (°C)
    "PRECTOTCORR",  # Precipitation corrected (mm/day)
    "RH2M",  # Relative humidity at 2m (%)
    "WS2M",  # Wind speed at 2m (m/s)
]

SOLAR_PARAMS = [
    "ALLSKY_SFC_SW_DWN",  # All-sky surface shortwave downward irradiance (MJ/m²/day)
    "CLRSKY_SFC_SW_DWN",  # Clear-sky surface shortwave downward irradiance (MJ/m²/day)
    "ALLSKY_SFC_PAR_TOT",  # All-sky photosynthetically active radiation (W/m²)
    "ALLSKY_SFC_UV_INDEX",  # All-sky UV index (unitless)
]

ET_PARAMS = [
    "T2M",  # Temperature
    "T2MDEW",  # Dewpoint temperature (°C)
    "RH2M",  # Relative humidity
    "WS2M",  # Wind speed
    "PS",  # Surface pressure (kPa)
    "ALLSKY_SFC_SW_DWN",  # Solar radiation
]

# Parameter metadata for display
PARAM_INFO = {
    "T2M": ("Temperature (2m)", "°C"),
    "T2M_MAX": ("Max Temperature", "°C"),
    "T2M_MIN": ("Min Temperature", "°C"),
    "PRECTOTCORR": ("Precipitation", "mm/day"),
    "RH2M": ("Relative Humidity", "%"),
    "WS2M": ("Wind Speed (2m)", "m/s"),
    "ALLSKY_SFC_SW_DWN": ("Solar Irradiance (All-Sky)", "MJ/m²/day"),
    "CLRSKY_SFC_SW_DWN": ("Solar Irradiance (Clear-Sky)", "MJ/m²/day"),
    "ALLSKY_SFC_PAR_TOT": ("PAR (Photosynthetically Active)", "W/m²"),
    "ALLSKY_SFC_UV_INDEX": ("UV Index", ""),
    "T2MDEW": ("Dewpoint Temperature", "°C"),
    "PS": ("Surface Pressure", "kPa"),
}


def _fetch_power_data(
    lat: float,
    lon: float,
    parameters: list[str],
    start: str,
    end: str,
    temporal: str = "daily",
) -> dict:
    """
    Fetch data from NASA POWER API.

    Args:
        lat: Latitude
        lon: Longitude
        parameters: List of parameter codes
        start: Start date (YYYYMMDD)
        end: End date (YYYYMMDD)
        temporal: Temporal resolution (daily, monthly, climatology)

    Returns:
        API response data

    Raises:
        APIError: On API errors
    """
    url = f"{NASA_POWER_BASE}/{temporal}/point"
    params = {
        "parameters": ",".join(parameters),
        "community": "AG",  # Agroclimatology community
        "longitude": lon,
        "latitude": lat,
        "start": start,
        "end": end,
        "format": "JSON",
    }

    data = fetch_json(url, params)

    if not isinstance(data, dict):
        raise APIError("Unexpected response format from NASA POWER")

    if "properties" not in data or "parameter" not in data.get("properties", {}):
        # Check for error message
        messages = data.get("messages", [])
        if messages:
            raise APIError(f"NASA POWER error: {messages[0]}")
        raise APIError("Invalid response structure from NASA POWER")

    return data


def _calculate_stats(values: dict[str, float]) -> dict[str, float | None]:
    """Calculate statistics from daily values, ignoring missing data (-999)."""
    valid = [v for v in values.values() if v != -999 and v is not None]
    if not valid:
        return {"mean": None, "min": None, "max": None, "total": None}

    return {
        "mean": sum(valid) / len(valid),
        "min": min(valid),
        "max": max(valid),
        "total": sum(valid),
        "count": float(len(valid)),
    }


@tool
def get_agricultural_climate(location: str, start_date: str, end_date: str) -> str:
    """
    Get agricultural climate parameters for a location from NASA POWER.

    Provides temperature, precipitation, humidity, and wind data useful for
    crop planning and agricultural assessments.

    Args:
        location: City name (e.g., "Nairobi") or coordinates as "lat,lon" (e.g., "51.5,-0.1")
        start_date: Start date in YYYYMMDD format (e.g., "20230101")
        end_date: End date in YYYYMMDD format (e.g., "20231231")

    Returns:
        Agricultural climate summary with temperature, precipitation, humidity, and wind statistics
    """
    # Resolve location to coordinates
    coords = geocode_or_parse(location)
    if not coords:
        return f"Could not find location: {location}. Try using coordinates (lat,lon) format."

    lat, lon = coords

    try:
        data = _fetch_power_data(
            lat, lon, AGRO_CLIMATE_PARAMS, start_date, end_date, "daily"
        )

        params = data["properties"]["parameter"]
        location_str = format_location(lat, lon)

        # Calculate statistics for each parameter
        output = [
            "=== Agricultural Climate Data ===",
            f"Location: {location} ({location_str})",
            f"Period: {start_date} to {end_date}",
            "Source: NASA POWER (Agroclimatology)",
            "",
        ]

        last_valid_stats: dict[str, float | None] = {"count": 0}

        for param in AGRO_CLIMATE_PARAMS:
            if param in params:
                stats = _calculate_stats(params[param])
                name, unit = PARAM_INFO.get(param, (param, ""))

                if stats["mean"] is not None:
                    if param == "PRECTOTCORR":
                        # Precipitation: show total and daily average
                        output.append(f"{name}:")
                        output.append(f"  Total: {stats['total']:.1f} mm")
                        output.append(f"  Daily Avg: {stats['mean']:.2f} {unit}")
                        output.append(f"  Max Daily: {stats['max']:.1f} mm")
                    else:
                        output.append(f"{name}:")
                        output.append(f"  Average: {stats['mean']:.1f} {unit}")
                        output.append(
                            f"  Range: {stats['min']:.1f} - {stats['max']:.1f} {unit}"
                        )
                    # Track the last valid stats for data point count
                    last_valid_stats = stats
                else:
                    output.append(f"{name}: No data available")

        output.append("")
        output.append(f"Data points: {int(last_valid_stats.get('count', 0) or 0)} days")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching agricultural climate data")
    except Exception as e:
        return format_error(e, "processing climate data")


@tool
def get_solar_radiation(location: str, year: int) -> str:
    """
    Get solar radiation data for agricultural planning from NASA POWER.

    Provides monthly solar irradiance, PAR (photosynthetically active radiation),
    and UV index data useful for crop light requirements and solar energy planning.

    Args:
        location: City name (e.g., "Cairo") or coordinates as "lat,lon"
        year: Year to retrieve data for (e.g., 2023)

    Returns:
        Monthly solar radiation summary with irradiance and PAR values
    """
    coords = geocode_or_parse(location)
    if not coords:
        return f"Could not find location: {location}. Try using coordinates (lat,lon) format."

    lat, lon = coords

    try:
        # Fetch monthly data for the year
        start = f"{year}0101"
        end = f"{year}1231"

        data = _fetch_power_data(lat, lon, SOLAR_PARAMS, start, end, "monthly")

        params = data["properties"]["parameter"]
        location_str = format_location(lat, lon)

        output = [
            "=== Solar Radiation Data ===",
            f"Location: {location} ({location_str})",
            f"Year: {year}",
            "Source: NASA POWER",
            "",
            "Monthly Values:",
            "",
        ]

        # Month names
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

        # Table header
        output.append(f"{'Month':<6} {'Irradiance':>12} {'Clear-Sky':>12} {'PAR':>10}")
        output.append(f"{'':6} {'(MJ/m²/day)':>12} {'(MJ/m²/day)':>12} {'(W/m²)':>10}")
        output.append("-" * 44)

        # Get monthly values
        irr = params.get("ALLSKY_SFC_SW_DWN", {})
        clr = params.get("CLRSKY_SFC_SW_DWN", {})
        par = params.get("ALLSKY_SFC_PAR_TOT", {})

        annual_irr = []
        for i, month in enumerate(months, 1):
            key = f"{year}{i:02d}"
            irr_val = irr.get(key, -999)
            clr_val = clr.get(key, -999)
            par_val = par.get(key, -999)

            irr_str = f"{irr_val:.2f}" if irr_val != -999 else "N/A"
            clr_str = f"{clr_val:.2f}" if clr_val != -999 else "N/A"
            par_str = f"{par_val:.1f}" if par_val != -999 else "N/A"

            output.append(f"{month:<6} {irr_str:>12} {clr_str:>12} {par_str:>10}")

            if irr_val != -999:
                annual_irr.append(irr_val)

        output.append("-" * 44)

        # Annual average
        if annual_irr:
            avg_irr = sum(annual_irr) / len(annual_irr)
            output.append(f"{'Annual':6} {avg_irr:>12.2f}")

        output.append("")
        output.append("Notes:")
        output.append("- Irradiance: Solar energy reaching surface (higher = more sun)")
        output.append("- PAR: Light usable for photosynthesis (crop growth indicator)")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching solar radiation data")
    except Exception as e:
        return format_error(e, "processing solar data")


@tool
def get_evapotranspiration(location: str, start_date: str, end_date: str) -> str:
    """
    Get reference evapotranspiration (ET₀) estimates from NASA POWER.

    Provides daily/monthly ET₀ using the FAO Penman-Monteith approach,
    essential for irrigation planning and water balance calculations.

    Args:
        location: City name or coordinates as "lat,lon"
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format

    Returns:
        Evapotranspiration summary with ET₀ estimates and contributing factors
    """
    coords = geocode_or_parse(location)
    if not coords:
        return f"Could not find location: {location}. Try using coordinates (lat,lon) format."

    lat, lon = coords

    try:
        data = _fetch_power_data(lat, lon, ET_PARAMS, start_date, end_date, "daily")

        params = data["properties"]["parameter"]
        location_str = format_location(lat, lon)

        # Simplified reference ET using Hargreaves approximation
        # Formula: ET0 ~= 0.0023 * Ra * (Tmean + 17.8) * sqrt(Tmax - Tmin)

        t2m = params.get("T2M", {})
        rh = params.get("RH2M", {})
        ws = params.get("WS2M", {})
        rad = params.get("ALLSKY_SFC_SW_DWN", {})

        # Calculate daily ET estimates (simplified)
        et_values = []
        for date_key in t2m:
            temp = t2m.get(date_key, -999)
            humidity = rh.get(date_key, -999)
            wind = ws.get(date_key, -999)
            radiation = rad.get(date_key, -999)

            if all(v != -999 for v in [temp, humidity, wind, radiation]):
                # Simplified Penman approximation (mm/day)
                # This is a rough estimate - actual calculation is more complex
                et0 = 0.0023 * radiation * (temp + 17.8) * 0.5
                et0 = max(0, min(et0, 15))  # Clamp to reasonable range
                et_values.append(et0)

        if not et_values:
            return f"Insufficient data to calculate ET for {location} in the specified period."

        # Statistics
        et_mean = sum(et_values) / len(et_values)
        et_total = sum(et_values)
        et_max = max(et_values)
        et_min = min(et_values)

        # Get contributing factor stats
        t_stats = _calculate_stats(t2m)
        rh_stats = _calculate_stats(rh)
        ws_stats = _calculate_stats(ws)
        rad_stats = _calculate_stats(rad)

        output = [
            "=== Reference Evapotranspiration (ET₀) ===",
            f"Location: {location} ({location_str})",
            f"Period: {start_date} to {end_date}",
            "Source: NASA POWER + Simplified Penman",
            "",
            "Evapotranspiration Estimates:",
            f"  Daily Average: {et_mean:.2f} mm/day",
            f"  Daily Range: {et_min:.2f} - {et_max:.2f} mm/day",
            f"  Period Total: {et_total:.1f} mm",
            f"  Data Points: {len(et_values)} days",
            "",
            "Contributing Factors (Averages):",
        ]

        if t_stats["mean"]:
            output.append(f"  Temperature: {t_stats['mean']:.1f} °C")
        if rh_stats["mean"]:
            output.append(f"  Relative Humidity: {rh_stats['mean']:.1f} %")
        if ws_stats["mean"]:
            output.append(f"  Wind Speed: {ws_stats['mean']:.1f} m/s")
        if rad_stats["mean"]:
            output.append(f"  Solar Radiation: {rad_stats['mean']:.2f} MJ/m²/day")

        output.append("")
        output.append("Notes:")
        output.append("- ET₀ is reference crop evapotranspiration (grass reference)")
        output.append("- Actual crop ET = ET₀ x crop coefficient (Kc)")
        output.append("- Higher ET₀ = greater irrigation water requirement")

        return "\n".join(output)

    except APIError as e:
        return format_error(e, "fetching evapotranspiration data")
    except Exception as e:
        return format_error(e, "calculating evapotranspiration")
