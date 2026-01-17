"""Tests for socio-economic tools."""

from __future__ import annotations


def test_get_country_indicators(monkeypatch):
    from agentic_cba_indicators.tools import socioeconomic

    def fake_fetch_json(url, params=None):
        if "restcountries" in url:
            return {
                "name": {"common": "Testland", "official": "Republic of Testland"},
                "population": 1_000_000,
                "area": 10_000,
                "region": "Test Region",
                "subregion": "Test Subregion",
                "capital": ["Test City"],
                "languages": {"en": "English"},
                "currencies": {"TST": {"name": "Test Dollar", "symbol": "$"}},
            }
        raise AssertionError("Unexpected URL")

    monkeypatch.setattr(socioeconomic, "fetch_json", fake_fetch_json)

    result = socioeconomic.get_country_indicators("Testland")

    assert "Country Profile" in result
    assert "Testland" in result


def test_get_world_bank_data(monkeypatch):
    from agentic_cba_indicators.tools import socioeconomic

    def fake_fetch_json(url, params=None):
        return [
            {"page": 1},
            [
                {
                    "date": "2023",
                    "value": 1000,
                    "country": {"value": "Testland"},
                }
            ],
        ]

    monkeypatch.setattr(socioeconomic, "fetch_json", fake_fetch_json)

    result = socioeconomic.get_world_bank_data("Testland", indicator="gdp")

    assert "GDP" in result
    assert "2023" in result
