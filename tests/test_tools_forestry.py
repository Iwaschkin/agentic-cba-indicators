"""Tests for GFW forestry tools module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agentic_cba_indicators.tools.forestry import (
    GFW_BASE_URL,
    GFW_CANOPY_THRESHOLD,
    GFW_CIRCLE_POINTS,
    GFW_MAX_RADIUS_KM,
    VALID_WINDOW_YEARS,
    _create_circular_geostore,
    _get_gfw_headers,
    _gfw_get,
    _gfw_post,
    _validate_coordinates,
    _validate_country_code,
    _validate_radius_km,
    _validate_window_years,
    get_forest_carbon_stock,
    get_forest_extent,
    get_tree_cover_loss_by_driver,
    get_tree_cover_loss_trends,
)

# =============================================================================
# Validation Helper Tests
# =============================================================================


class TestValidateCountryCode:
    """Tests for _validate_country_code."""

    def test_valid_iso3_uppercase(self) -> None:
        """ISO3 codes should be returned uppercase."""
        assert _validate_country_code("TCD") == "TCD"
        assert _validate_country_code("tcd") == "TCD"
        assert _validate_country_code("Tcd") == "TCD"

    def test_valid_country_name(self) -> None:
        """Country names should be resolved to ISO3."""
        assert _validate_country_code("Chad") == "TCD"
        assert _validate_country_code("chad") == "TCD"
        assert _validate_country_code("Brazil") == "BRA"
        assert _validate_country_code("KENYA") == "KEN"

    def test_invalid_country(self) -> None:
        """Unknown countries should raise ValueError."""
        with pytest.raises(ValueError, match="not recognized"):
            _validate_country_code("InvalidCountry")

        with pytest.raises(ValueError, match="not recognized"):
            _validate_country_code("XX")


class TestValidateWindowYears:
    """Tests for _validate_window_years."""

    def test_valid_windows(self) -> None:
        """5 and 10 should be valid."""
        assert _validate_window_years(5) == 5
        assert _validate_window_years(10) == 10

    def test_invalid_window(self) -> None:
        """Other values should raise ValueError."""
        with pytest.raises(ValueError, match="must be 5 or 10"):
            _validate_window_years(7)

        with pytest.raises(ValueError, match="must be 5 or 10"):
            _validate_window_years(1)


class TestValidateRadiusKm:
    """Tests for _validate_radius_km."""

    def test_valid_radius(self) -> None:
        """Valid radii should pass through."""
        assert _validate_radius_km(10.0) == 10.0
        assert _validate_radius_km(50.0) == 50.0
        assert _validate_radius_km(0.1) == 0.1

    def test_radius_too_large(self) -> None:
        """Radius > 50km should raise ValueError."""
        with pytest.raises(ValueError, match="cannot exceed"):
            _validate_radius_km(51.0)

        with pytest.raises(ValueError, match="cannot exceed"):
            _validate_radius_km(100.0)

    def test_radius_zero_or_negative(self) -> None:
        """Zero or negative radius should raise ValueError."""
        with pytest.raises(ValueError, match="must be positive"):
            _validate_radius_km(0)

        with pytest.raises(ValueError, match="must be positive"):
            _validate_radius_km(-5)


class TestValidateCoordinates:
    """Tests for _validate_coordinates."""

    def test_valid_coordinates(self) -> None:
        """Valid coordinates should pass through."""
        assert _validate_coordinates(0, 0) == (0, 0)
        assert _validate_coordinates(90, 180) == (90, 180)
        assert _validate_coordinates(-90, -180) == (-90, -180)
        assert _validate_coordinates(12.5, 15.3) == (12.5, 15.3)

    def test_invalid_latitude(self) -> None:
        """Latitude out of range should raise ValueError."""
        with pytest.raises(ValueError, match="Latitude"):
            _validate_coordinates(91, 0)

        with pytest.raises(ValueError, match="Latitude"):
            _validate_coordinates(-91, 0)

    def test_invalid_longitude(self) -> None:
        """Longitude out of range should raise ValueError."""
        with pytest.raises(ValueError, match="Longitude"):
            _validate_coordinates(0, 181)

        with pytest.raises(ValueError, match="Longitude"):
            _validate_coordinates(0, -181)


# =============================================================================
# API Helper Tests
# =============================================================================


class TestGetGfwHeaders:
    """Tests for _get_gfw_headers."""

    def test_missing_api_key(self) -> None:
        """Should raise ValueError when API key not configured."""
        with patch("agentic_cba_indicators.tools.forestry.require_api_key") as mock:
            mock.side_effect = ValueError("GFW API key required")
            with pytest.raises(ValueError, match="GFW API key"):
                _get_gfw_headers()

    def test_headers_include_api_key(self) -> None:
        """Should include x-api-key header."""
        with patch("agentic_cba_indicators.tools.forestry.require_api_key") as mock:
            mock.return_value = "test_api_key_123"
            headers = _get_gfw_headers()

            assert headers["x-api-key"] == "test_api_key_123"
            assert headers["Content-Type"] == "application/json"
            assert headers["Accept"] == "application/json"


class TestGfwGet:
    """Tests for _gfw_get."""

    def test_successful_request(self) -> None:
        """Successful GET should return parsed JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": [{"year": 2020, "loss_ha": 1000}]}

        with patch("agentic_cba_indicators.tools.forestry.require_api_key") as mock_key:
            mock_key.return_value = "test_key"
            with patch(
                "agentic_cba_indicators.tools.forestry.create_client"
            ) as mock_client:
                client_instance = MagicMock()
                client_instance.get.return_value = mock_response
                mock_client.return_value = client_instance

                result = _gfw_get("/test/endpoint", params={"iso": "TCD"})

                assert result == {"data": [{"year": 2020, "loss_ha": 1000}]}
                client_instance.get.assert_called_once()

    def test_auth_error(self) -> None:
        """401 should raise APIError with auth message."""
        from agentic_cba_indicators.tools._http import APIError

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("agentic_cba_indicators.tools.forestry.require_api_key") as mock_key:
            mock_key.return_value = "test_key"
            with patch(
                "agentic_cba_indicators.tools.forestry.create_client"
            ) as mock_client:
                client_instance = MagicMock()
                client_instance.get.return_value = mock_response
                mock_client.return_value = client_instance

                with pytest.raises(APIError, match="authentication failed"):
                    _gfw_get("/test/endpoint")


class TestGfwPost:
    """Tests for _gfw_post."""

    def test_successful_request(self) -> None:
        """Successful POST should return parsed JSON."""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"data": {"id": "geostore_123"}}

        with patch("agentic_cba_indicators.tools.forestry.require_api_key") as mock_key:
            mock_key.return_value = "test_key"
            with patch(
                "agentic_cba_indicators.tools.forestry.create_client"
            ) as mock_client:
                client_instance = MagicMock()
                client_instance.post.return_value = mock_response
                mock_client.return_value = client_instance

                result = _gfw_post("/geostore", {"geojson": {}})

                assert result == {"data": {"id": "geostore_123"}}
                client_instance.post.assert_called_once()


class TestCreateCircularGeostore:
    """Tests for _create_circular_geostore."""

    def test_creates_32_point_polygon(self) -> None:
        """Should create polygon with 32 points (+ closing point)."""
        mock_response = {"data": {"id": "geostore_abc"}}

        with patch("agentic_cba_indicators.tools.forestry._gfw_post") as mock_post:
            mock_post.return_value = mock_response

            geostore_id = _create_circular_geostore(12.0, 15.0, 10.0)

            assert geostore_id == "geostore_abc"

            # Check the geometry
            call_args = mock_post.call_args
            geojson = call_args[0][1]["geojson"]
            coordinates = geojson["features"][0]["geometry"]["coordinates"][0]

            # 32 points + 1 closing point = 33
            assert len(coordinates) == GFW_CIRCLE_POINTS + 1
            # First and last should be the same (closed polygon)
            assert coordinates[0] == coordinates[-1]

    def test_invalid_coordinates(self) -> None:
        """Should raise ValueError for invalid coordinates."""
        with pytest.raises(ValueError, match="Latitude"):
            _create_circular_geostore(100, 15, 10)

    def test_invalid_radius(self) -> None:
        """Should raise ValueError for radius > 50km."""
        with pytest.raises(ValueError, match="cannot exceed"):
            _create_circular_geostore(12, 15, 60)


# =============================================================================
# Tool Function Tests
# =============================================================================


class TestGetTreeCoverLossTrends:
    """Tests for get_tree_cover_loss_trends tool."""

    def test_successful_query(self) -> None:
        """Should return formatted trend data."""
        mock_data = {
            "data": [
                {"year": 2020, "loss_ha": 1000},
                {"year": 2021, "loss_ha": 1200},
                {"year": 2022, "loss_ha": 1100},
            ]
        }

        with patch("agentic_cba_indicators.tools.forestry._gfw_get") as mock_get:
            mock_get.return_value = mock_data

            result = get_tree_cover_loss_trends("TCD", window_years=5)

            assert "TCD" in result
            assert "2020" in result
            assert "Total Loss" in result
            assert "Trend:" in result

    def test_invalid_country(self) -> None:
        """Should return error for invalid country."""
        result = get_tree_cover_loss_trends("InvalidCountry")
        assert "not recognized" in result

    def test_invalid_window(self) -> None:
        """Should return error for invalid window."""
        result = get_tree_cover_loss_trends("TCD", window_years=7)
        assert "must be 5 or 10" in result

    def test_no_data(self) -> None:
        """Should handle empty results gracefully."""
        with patch("agentic_cba_indicators.tools.forestry._gfw_get") as mock_get:
            mock_get.return_value = {"data": []}

            result = get_tree_cover_loss_trends("TCD")

            assert "No tree cover loss data" in result


class TestGetTreeCoverLossByDriver:
    """Tests for get_tree_cover_loss_by_driver tool."""

    def test_successful_query(self) -> None:
        """Should return formatted driver breakdown."""
        mock_data = {
            "data": [
                {"tsc_tree_cover_loss_drivers__type": "commodity", "area__ha": 5000},
                {
                    "tsc_tree_cover_loss_drivers__type": "shifting_agriculture",
                    "area__ha": 3000,
                },
            ]
        }

        with patch("agentic_cba_indicators.tools.forestry._gfw_get") as mock_get:
            mock_get.return_value = mock_data

            result = get_tree_cover_loss_by_driver("TCD")

            assert "TCD" in result
            assert "Commodity" in result
            assert "Dominant Driver" in result

    def test_invalid_country(self) -> None:
        """Should return error for invalid country."""
        result = get_tree_cover_loss_by_driver("InvalidCountry")
        assert "not recognized" in result


class TestGetForestCarbonStock:
    """Tests for get_forest_carbon_stock tool."""

    def test_successful_query(self) -> None:
        """Should return formatted carbon data."""
        mock_geostore = {"data": {"id": "geo_123"}}
        mock_zonal = {
            "data": {
                "attributes": {
                    "mean": 150.0,
                    "count": 10000,
                }
            }
        }

        with patch("agentic_cba_indicators.tools.forestry._gfw_post") as mock_post:
            mock_post.side_effect = [mock_geostore, mock_zonal]

            result = get_forest_carbon_stock(12.0, 15.0, 10.0)

            assert "Carbon Stock" in result
            assert "Biomass" in result
            assert "CO₂ Equivalent" in result

    def test_invalid_coordinates(self) -> None:
        """Should return error for invalid coordinates."""
        result = get_forest_carbon_stock(100.0, 15.0)
        assert "Latitude" in result

    def test_invalid_radius(self) -> None:
        """Should return error for radius > 50km."""
        result = get_forest_carbon_stock(12.0, 15.0, 60.0)
        assert "cannot exceed" in result


class TestGetForestExtent:
    """Tests for get_forest_extent tool."""

    def test_successful_query(self) -> None:
        """Should return formatted extent data."""
        mock_geostore = {"data": {"id": "geo_123"}}
        mock_zonal = {
            "data": {
                "attributes": {
                    "mean": 45.0,
                    "count": 10000,
                }
            }
        }

        with patch("agentic_cba_indicators.tools.forestry._gfw_post") as mock_post:
            mock_post.side_effect = [mock_geostore, mock_zonal]

            result = get_forest_extent(12.0, 15.0, 10.0)

            assert "Forest Extent" in result
            assert "Tree Cover" in result
            assert "Category:" in result

    def test_invalid_coordinates(self) -> None:
        """Should return error for invalid coordinates."""
        result = get_forest_extent(100.0, 15.0)
        assert "Latitude" in result


# =============================================================================
# Constants Tests
# =============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_gfw_base_url(self) -> None:
        """Base URL should be HTTPS."""
        assert GFW_BASE_URL.startswith("https://")
        assert "globalforestwatch" in GFW_BASE_URL

    def test_canopy_threshold(self) -> None:
        """Canopy threshold should be 30%."""
        assert GFW_CANOPY_THRESHOLD == 30

    def test_max_radius(self) -> None:
        """Max radius should be 50km."""
        assert GFW_MAX_RADIUS_KM == 50.0

    def test_circle_points(self) -> None:
        """Circle should use 32 points."""
        assert GFW_CIRCLE_POINTS == 32

    def test_valid_windows(self) -> None:
        """Valid windows should be 5 and 10."""
        assert VALID_WINDOW_YEARS == (5, 10)
