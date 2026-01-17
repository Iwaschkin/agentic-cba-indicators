"""Tests for geo utilities (_geo.py) including coordinate validation."""

from __future__ import annotations

import pytest


class TestCoordinateValidation:
    """Tests for validate_coordinates function."""

    def test_valid_coordinates(self):
        """Test that valid coordinates pass validation."""
        from agentic_cba_indicators.tools._geo import validate_coordinates

        # Normal coordinates
        lat, lon = validate_coordinates(40.7128, -74.0060)
        assert lat == 40.7128
        assert lon == -74.0060

    def test_edge_coordinates(self):
        """Test boundary values for coordinates."""
        from agentic_cba_indicators.tools._geo import validate_coordinates

        # North pole
        lat, lon = validate_coordinates(90, 0)
        assert lat == 90

        # South pole
        lat, lon = validate_coordinates(-90, 0)
        assert lat == -90

        # International date line
        lat, lon = validate_coordinates(0, 180)
        assert lon == 180

        lat, lon = validate_coordinates(0, -180)
        assert lon == -180

    def test_latitude_out_of_range_high(self):
        """Test that latitude > 90 raises error."""
        from agentic_cba_indicators.tools._geo import (
            CoordinateValidationError,
            validate_coordinates,
        )

        with pytest.raises(CoordinateValidationError) as exc_info:
            validate_coordinates(91, 0)

        assert "Latitude 91" in str(exc_info.value)
        assert "out of range" in str(exc_info.value)

    def test_latitude_out_of_range_low(self):
        """Test that latitude < -90 raises error."""
        from agentic_cba_indicators.tools._geo import (
            CoordinateValidationError,
            validate_coordinates,
        )

        with pytest.raises(CoordinateValidationError) as exc_info:
            validate_coordinates(-91, 0)

        assert "Latitude -91" in str(exc_info.value)

    def test_longitude_out_of_range_high(self):
        """Test that longitude > 180 raises error."""
        from agentic_cba_indicators.tools._geo import (
            CoordinateValidationError,
            validate_coordinates,
        )

        with pytest.raises(CoordinateValidationError) as exc_info:
            validate_coordinates(0, 181)

        assert "Longitude 181" in str(exc_info.value)
        assert "out of range" in str(exc_info.value)

    def test_longitude_out_of_range_low(self):
        """Test that longitude < -180 raises error."""
        from agentic_cba_indicators.tools._geo import (
            CoordinateValidationError,
            validate_coordinates,
        )

        with pytest.raises(CoordinateValidationError) as exc_info:
            validate_coordinates(0, -181)

        assert "Longitude -181" in str(exc_info.value)

    def test_latitude_wrong_type(self):
        """Test that non-numeric latitude raises error."""
        from agentic_cba_indicators.tools._geo import (
            CoordinateValidationError,
            validate_coordinates,
        )

        with pytest.raises(CoordinateValidationError) as exc_info:
            validate_coordinates("40", 0)  # type: ignore[arg-type]

        assert "must be a number" in str(exc_info.value)
        assert "str" in str(exc_info.value)

    def test_longitude_wrong_type(self):
        """Test that non-numeric longitude raises error."""
        from agentic_cba_indicators.tools._geo import (
            CoordinateValidationError,
            validate_coordinates,
        )

        with pytest.raises(CoordinateValidationError) as exc_info:
            validate_coordinates(0, None)  # type: ignore[arg-type]

        assert "must be a number" in str(exc_info.value)

    def test_context_included_in_error(self):
        """Test that context string is included in error message."""
        from agentic_cba_indicators.tools._geo import (
            CoordinateValidationError,
            validate_coordinates,
        )

        with pytest.raises(CoordinateValidationError) as exc_info:
            validate_coordinates(100, 0, context="for weather query")

        assert "for weather query" in str(exc_info.value)


class TestGeocodeCity:
    """Tests for geocode_city function."""

    def test_geocode_returns_none_for_unknown_city(self, monkeypatch):
        """Test that geocode returns None when API returns no results."""
        from agentic_cba_indicators.tools import _geo

        def fake_fetch_json(url, params=None):
            return {"results": []}

        monkeypatch.setattr(_geo, "fetch_json", fake_fetch_json)
        # Clear cache to ensure fresh call
        _geo._geocode_cache.clear()

        result = _geo.geocode_city("NonexistentCity12345")
        assert result is None

    def test_geocode_cache_behavior(self, monkeypatch):
        """Test that geocode caches results."""
        from agentic_cba_indicators.tools import _geo

        call_count = 0

        def fake_fetch_json(url, params=None):
            nonlocal call_count
            call_count += 1
            return {
                "results": [
                    {
                        "name": "TestCity",
                        "country": "TC",
                        "latitude": 10.0,
                        "longitude": 20.0,
                        "admin1": "TestState",
                        "timezone": "Test/Zone",
                    }
                ]
            }

        monkeypatch.setattr(_geo, "fetch_json", fake_fetch_json)
        _geo._geocode_cache.clear()

        # First call should hit API
        result1 = _geo.geocode_city("TestCity")
        assert result1 is not None
        assert call_count == 1

        # Second call should use cache
        result2 = _geo.geocode_city("TestCity")
        assert result2 is not None
        assert call_count == 1  # Still 1, used cache

        # Call without cache should hit API again
        result3 = _geo.geocode_city("TestCity", use_cache=False)
        assert result3 is not None
        assert call_count == 2

    def test_geocode_handles_api_error(self, monkeypatch):
        """Test that geocode handles API errors gracefully."""
        from agentic_cba_indicators.tools import _geo
        from agentic_cba_indicators.tools._http import APIError

        def fake_fetch_json(url, params=None):
            raise APIError("Service unavailable", status_code=503)

        monkeypatch.setattr(_geo, "fetch_json", fake_fetch_json)
        _geo._geocode_cache.clear()

        result = _geo.geocode_city("London")
        assert result is None


class TestGeocodeOrParse:
    """Tests for geocode_or_parse function."""

    def test_parse_coordinate_string(self, monkeypatch):
        """Test parsing of coordinate strings."""
        from agentic_cba_indicators.tools._geo import geocode_or_parse

        # Don't need to mock API if we're just parsing coordinates
        result = geocode_or_parse("40.7128, -74.0060")
        assert result is not None
        lat, lon = result
        assert abs(lat - 40.7128) < 0.0001
        assert abs(lon - (-74.0060)) < 0.0001

    def test_parse_coordinate_variations(self, monkeypatch):
        """Test various coordinate format variations."""
        from agentic_cba_indicators.tools._geo import geocode_or_parse

        # Without space
        result = geocode_or_parse("40.7128,-74.0060")
        assert result is not None

        # With extra spaces
        result = geocode_or_parse("  40.7128 ,  -74.0060  ")
        assert result is not None

    def test_falls_back_to_geocode(self, monkeypatch):
        """Test that non-coordinate strings fall back to geocoding."""
        from agentic_cba_indicators.tools import _geo

        def fake_geocode_city(city, use_cache=True):
            return {
                "name": "New York",
                "country": "US",
                "latitude": 40.7128,
                "longitude": -74.0060,
            }

        monkeypatch.setattr(_geo, "geocode_city", fake_geocode_city)

        result = _geo.geocode_or_parse("New York")
        assert result is not None
        lat, _lon = result
        assert abs(lat - 40.7128) < 0.0001

    def test_invalid_location_returns_none(self, monkeypatch):
        """Test that invalid locations return None."""
        from agentic_cba_indicators.tools import _geo

        def fake_geocode_city(city, use_cache=True):
            return None

        monkeypatch.setattr(_geo, "geocode_city", fake_geocode_city)

        result = _geo.geocode_or_parse("InvalidLocation12345")
        assert result is None
