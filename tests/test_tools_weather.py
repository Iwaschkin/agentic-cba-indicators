"""Tests for weather tools."""

from __future__ import annotations


def test_get_current_weather_formats_output(monkeypatch):
    from agentic_cba_indicators.tools import weather

    def fake_geocode_city(city: str):
        return {
            "name": "Testville",
            "country": "Testland",
            "latitude": 1.0,
            "longitude": 2.0,
        }

    def fake_fetch_json(url, params=None):
        return {
            "current": {
                "temperature_2m": 21.5,
                "apparent_temperature": 20.0,
                "relative_humidity_2m": 50,
                "precipitation": 0.2,
                "weather_code": 1,
                "wind_speed_10m": 10.0,
                "wind_direction_10m": 180,
            },
            "current_units": {
                "temperature_2m": "°C",
                "apparent_temperature": "°C",
                "relative_humidity_2m": "%",
                "precipitation": "mm",
                "wind_speed_10m": "km/h",
            },
        }

    monkeypatch.setattr(weather, "geocode_city", fake_geocode_city)
    monkeypatch.setattr(weather, "fetch_json", fake_fetch_json)

    result = weather.get_current_weather("Testville")

    assert "Current Weather for Testville" in result
    assert "Temperature:" in result
