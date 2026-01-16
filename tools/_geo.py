"""
Shared geocoding utilities for location-based tools.

Provides consistent coordinate lookup from city/place names
using the Open-Meteo geocoding API (free, no API key required).
"""

from typing import TypedDict

import httpx

# Simple in-memory cache to avoid repeated geocoding requests
_geocode_cache: dict[str, dict | None] = {}


class GeoLocation(TypedDict):
    """Geocoding result structure."""

    name: str
    country: str
    latitude: float
    longitude: float
    admin1: str | None  # State/province
    timezone: str | None


def geocode_city(city: str, use_cache: bool = True) -> GeoLocation | None:
    """
    Get latitude and longitude for a city name.

    Uses Open-Meteo geocoding API (free, no API key).

    Args:
        city: Name of the city (e.g., "London", "New York")
        use_cache: Whether to use cached results

    Returns:
        GeoLocation dict with name, country, latitude, longitude, or None if not found
    """
    cache_key = city.lower().strip()

    # Check cache
    if use_cache and cache_key in _geocode_cache:
        cached = _geocode_cache[cache_key]
        return GeoLocation(**cached) if cached else None

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )

            if response.status_code != 200:
                _geocode_cache[cache_key] = None
                return None

            data = response.json()

            if "results" not in data or len(data["results"]) == 0:
                _geocode_cache[cache_key] = None
                return None

            result = data["results"][0]
            location: GeoLocation = {
                "name": result.get("name", city),
                "country": result.get("country", "Unknown"),
                "latitude": result.get("latitude"),
                "longitude": result.get("longitude"),
                "admin1": result.get("admin1"),
                "timezone": result.get("timezone"),
            }

            # Cache the result
            if use_cache:
                _geocode_cache[cache_key] = dict(location)

            return location

    except Exception:
        _geocode_cache[cache_key] = None
        return None


def geocode_or_parse(location: str) -> tuple[float, float] | None:
    """
    Get coordinates from either a city name or lat,lon string.

    Args:
        location: Either a city name or "lat,lon" string

    Returns:
        Tuple of (latitude, longitude) or None if not found

    Examples:
        >>> geocode_or_parse("London")
        (51.5074, -0.1278)
        >>> geocode_or_parse("51.5074,-0.1278")
        (51.5074, -0.1278)
    """
    # Try parsing as coordinates first
    if "," in location:
        try:
            parts = location.split(",")
            lat = float(parts[0].strip())
            lon = float(parts[1].strip())
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return (lat, lon)
        except (ValueError, IndexError):
            pass

    # Try geocoding as city name
    result = geocode_city(location)
    if result:
        return (result["latitude"], result["longitude"])

    return None


def format_location(lat: float, lon: float, precision: int = 4) -> str:
    """
    Format coordinates for display.

    Args:
        lat: Latitude
        lon: Longitude
        precision: Decimal places

    Returns:
        Formatted string like "51.5074°N, 0.1278°W"
    """
    lat_dir = "N" if lat >= 0 else "S"
    lon_dir = "E" if lon >= 0 else "W"
    return f"{abs(lat):.{precision}f}°{lat_dir}, {abs(lon):.{precision}f}°{lon_dir}"


def clear_cache() -> None:
    """Clear the geocoding cache."""
    global _geocode_cache
    _geocode_cache = {}
