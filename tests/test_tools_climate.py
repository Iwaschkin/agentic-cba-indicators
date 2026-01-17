"""Tests for climate tools."""

from __future__ import annotations


def test_get_climate_data_formats_output(monkeypatch):
    from agentic_cba_indicators.tools import climate

    def fake_geocode_city(city: str):
        return {
            "name": "Sample",
            "country": "Land",
            "latitude": 1.0,
            "longitude": 2.0,
        }

    def fake_fetch_json(url, params=None):
        return {
            "daily": {
                "temperature_2m_mean": [10.0, 12.0],
                "temperature_2m_max": [15.0, 16.0],
                "temperature_2m_min": [5.0, 6.0],
                "precipitation_sum": [1.0, 2.0],
                "time": ["1991-01-01", "1991-01-02"],
            }
        }

    monkeypatch.setattr(climate, "geocode_city", fake_geocode_city)
    monkeypatch.setattr(climate, "fetch_json", fake_fetch_json)

    result = climate.get_climate_data("Sample")

    assert "Climate Normals for Sample" in result
    assert "Month | Avg Temp" in result
