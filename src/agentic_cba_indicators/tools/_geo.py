"""
Shared geocoding utilities for location-based tools.

Provides consistent coordinate lookup from city/place names
using the Open-Meteo geocoding API (free, no API key required).
"""

import os
from collections import OrderedDict
from typing import TypedDict

from ._http import APIError, fetch_json

# Simple bounded in-memory cache to avoid repeated geocoding requests
MAX_CACHE_SIZE = int(os.environ.get("AGENTIC_CBA_GEO_CACHE_SIZE", "256"))
_geocode_cache: OrderedDict[str, dict | None] = OrderedDict()


class GeoLocation(TypedDict):
    """Geocoding result structure."""

    name: str
    country: str
    latitude: float
    longitude: float
    admin1: str | None  # State/province
    timezone: str | None


class CoordinateValidationError(ValueError):
    """Exception raised for invalid coordinate values."""

    pass


def validate_coordinates(
    latitude: float, longitude: float, context: str = ""
) -> tuple[float, float]:
    """
    Validate latitude and longitude values are within valid ranges.

    Args:
        latitude: Latitude value to validate (-90 to +90)
        longitude: Longitude value to validate (-180 to +180)
        context: Optional context for error messages (e.g., "for NASA POWER query")

    Returns:
        Tuple of (latitude, longitude) if valid

    Raises:
        CoordinateValidationError: If coordinates are out of range
    """
    ctx = f" {context}" if context else ""

    if not isinstance(latitude, (int, float)):
        raise CoordinateValidationError(
            f"Latitude must be a number{ctx}, got {type(latitude).__name__}"
        )
    if not isinstance(longitude, (int, float)):
        raise CoordinateValidationError(
            f"Longitude must be a number{ctx}, got {type(longitude).__name__}"
        )

    if latitude < -90 or latitude > 90:
        raise CoordinateValidationError(
            f"Latitude {latitude} is out of range{ctx}. Must be between -90 and +90."
        )
    if longitude < -180 or longitude > 180:
        raise CoordinateValidationError(
            f"Longitude {longitude} is out of range{ctx}. Must be between -180 and +180."
        )

    return (float(latitude), float(longitude))


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
        _geocode_cache.move_to_end(cache_key)
        if cached is None:
            return None
        # Return cached result as GeoLocation
        return GeoLocation(
            name=cached.get("name", ""),
            country=cached.get("country", ""),
            latitude=cached.get("latitude", 0.0),
            longitude=cached.get("longitude", 0.0),
            admin1=cached.get("admin1"),
            timezone=cached.get("timezone"),
        )

    try:
        data = fetch_json(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
        )

        if not isinstance(data, dict) or "results" not in data or not data["results"]:
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
            _geocode_cache.move_to_end(cache_key)
            if len(_geocode_cache) > MAX_CACHE_SIZE:
                _geocode_cache.popitem(last=False)

        return location

    except APIError:
        _geocode_cache[cache_key] = None
        _geocode_cache.move_to_end(cache_key)
        if len(_geocode_cache) > MAX_CACHE_SIZE:
            _geocode_cache.popitem(last=False)
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
    _geocode_cache = OrderedDict()
