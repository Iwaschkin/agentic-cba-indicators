"""
Global Forest Watch (GFW) forestry tools for forest state monitoring.

Provides tools for analyzing tree cover, deforestation trends, carbon stocks,
and loss drivers. Focus on baselines and trends (not real-time alerts).

API Documentation: https://data-api.globalforestwatch.org/docs
"""

from __future__ import annotations

import math
import random
import time
from datetime import datetime
from typing import Any, Final

import httpx
from strands import tool

from agentic_cba_indicators.config import require_api_key
from agentic_cba_indicators.logging_config import get_logger

from ._http import APIError, create_client, format_error, sanitize_error
from ._mappings import COUNTRY_CODES_ISO3, normalize_key
from ._timeout import timeout

# Module logger
logger = get_logger(__name__)

# GFW API configuration
GFW_BASE_URL: Final[str] = "https://data-api.globalforestwatch.org"
GFW_CANOPY_THRESHOLD: Final[int] = 30  # Default canopy cover threshold (%)
GFW_MAX_RADIUS_KM: Final[float] = 50.0  # Maximum radius for geostore queries
GFW_CIRCLE_POINTS: Final[int] = 32  # Points to approximate a circle polygon

# Valid window years for trend analysis (M&E standards)
VALID_WINDOW_YEARS: Final[tuple[int, ...]] = (5, 10)

# Default retries for GFW API (their rate limits can be aggressive)
GFW_RETRIES: Final[int] = 3
GFW_TIMEOUT: Final[float] = 60.0  # GFW queries can be slow
GFW_BACKOFF_BASE: Final[float] = 1.0  # Base delay for exponential backoff
GFW_BACKOFF_MAX: Final[float] = 30.0  # Maximum backoff delay


# =============================================================================
# Validation Helpers
# =============================================================================


def _validate_country_code(country: str) -> str:
    """Validate and normalize country to ISO 3166-1 alpha-3 code.

    Args:
        country: Country name or ISO3 code (e.g., "Chad", "TCD")

    Returns:
        Uppercase ISO3 code (e.g., "TCD")

    Raises:
        ValueError: If country code not recognized
    """
    # First check if it's already a valid ISO3 code (3 uppercase letters)
    if len(country) == 3 and country.isalpha():
        return country.upper()

    # Try lookup by normalized name
    normalized = normalize_key(country)
    if normalized in COUNTRY_CODES_ISO3:
        return COUNTRY_CODES_ISO3[normalized]

    # Build helpful error message
    example_countries = ["Chad (TCD)", "Brazil (BRA)", "Kenya (KEN)", "India (IND)"]
    raise ValueError(
        f"Country code '{country}' not recognized. "
        f"Use ISO 3166-1 alpha-3 codes (e.g., {', '.join(example_countries)})"
    )


def _validate_window_years(window_years: int) -> int:
    """Validate trend window is 5 or 10 years (M&E standards).

    Args:
        window_years: Requested window

    Returns:
        Validated window

    Raises:
        ValueError: If not 5 or 10
    """
    if window_years not in VALID_WINDOW_YEARS:
        raise ValueError(
            f"window_years must be {' or '.join(map(str, VALID_WINDOW_YEARS))} "
            "(standard M&E evaluation periods)"
        )
    return window_years


def _validate_radius_km(radius_km: float) -> float:
    """Validate radius is within GFW limits.

    Args:
        radius_km: Requested radius

    Returns:
        Validated radius

    Raises:
        ValueError: If radius exceeds maximum
    """
    if radius_km <= 0:
        raise ValueError("radius_km must be positive")
    if radius_km > GFW_MAX_RADIUS_KM:
        raise ValueError(
            f"radius_km cannot exceed {GFW_MAX_RADIUS_KM}km for GFW queries"
        )
    return radius_km


def _validate_coordinates(lat: float, lon: float) -> tuple[float, float]:
    """Validate latitude and longitude ranges.

    Args:
        lat: Latitude (-90 to 90)
        lon: Longitude (-180 to 180)

    Returns:
        Tuple of (lat, lon)

    Raises:
        ValueError: If coordinates out of range
    """
    if not -90 <= lat <= 90:
        raise ValueError(f"Latitude must be between -90 and 90, got {lat}")
    if not -180 <= lon <= 180:
        raise ValueError(f"Longitude must be between -180 and 180, got {lon}")
    return lat, lon


# =============================================================================
# GFW API Helpers
# =============================================================================


def _get_gfw_headers() -> dict[str, str]:
    """Get headers for GFW API requests including authentication.

    Returns:
        Headers dict with x-api-key and Content-Type

    Raises:
        ValueError: If GFW_API_KEY not configured
    """
    api_key = require_api_key("gfw")
    return {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _gfw_get(
    endpoint: str,
    params: dict[str, Any] | None = None,
    client: httpx.Client | None = None,
    retries: int = GFW_RETRIES,
) -> dict[str, Any]:
    """Make authenticated GET request to GFW API with retry logic.

    Implements exponential backoff with jitter for 429 and 5xx errors.

    Args:
        endpoint: API endpoint (e.g., "/v0/land/tree_cover_loss_by_driver")
        params: Query parameters
        client: Optional existing client
        retries: Number of retry attempts (default: GFW_RETRIES)

    Returns:
        Parsed JSON response

    Raises:
        APIError: On HTTP errors after exhausting retries
    """
    should_close = client is None
    headers = _get_gfw_headers()
    client = client or create_client(timeout=GFW_TIMEOUT, headers=headers)

    url = f"{GFW_BASE_URL}{endpoint}"
    last_error: APIError | None = None

    try:
        for attempt in range(retries + 1):
            try:
                response = client.get(url, params=params)

                if response.status_code == 200:
                    return response.json()

                # Handle common error cases
                if response.status_code == 401:
                    raise APIError(
                        "GFW API authentication failed. Check your GFW_API_KEY.",
                        status_code=401,
                    )
                if response.status_code == 404:
                    raise APIError(
                        f"GFW resource not found: {endpoint}",
                        status_code=404,
                    )

                # Retryable errors: 429 (rate limit) and 5xx (server errors)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < retries:
                        # Check for Retry-After header on 429
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            delay = min(float(retry_after), GFW_BACKOFF_MAX)
                        else:
                            base_delay = GFW_BACKOFF_BASE * (2**attempt)
                            jitter = random.uniform(0, GFW_BACKOFF_BASE)
                            delay = min(base_delay + jitter, GFW_BACKOFF_MAX)
                        logger.debug(
                            "GFW API error %d, retrying in %.1fs (attempt %d/%d)",
                            response.status_code,
                            delay,
                            attempt + 1,
                            retries,
                        )
                        time.sleep(delay)
                        continue

                    # Exhausted retries
                    if response.status_code == 429:
                        raise APIError(
                            f"GFW API rate limit exceeded after {retries} retries.",
                            status_code=429,
                        )
                    raise APIError(
                        f"GFW API server error ({response.status_code}) after {retries} retries.",
                        status_code=response.status_code,
                    )

                # Generic non-retryable error
                error_text = response.text[:200] if response.text else "No details"
                raise APIError(
                    f"GFW API error: HTTP {response.status_code} - {sanitize_error(error_text)}",
                    status_code=response.status_code,
                )

            except httpx.TimeoutException as e:
                last_error = APIError("GFW API request timed out")
                if attempt < retries:
                    delay = GFW_BACKOFF_BASE * (2**attempt)
                    logger.debug(
                        "GFW API timeout, retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        retries,
                    )
                    time.sleep(delay)
                    continue
                raise APIError(
                    f"GFW API request timed out after {retries} retries"
                ) from e
            except httpx.RequestError as e:
                last_error = APIError(f"GFW API request failed: {e!s}")
                if attempt < retries:
                    delay = GFW_BACKOFF_BASE * (2**attempt)
                    logger.debug(
                        "GFW API request error, retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        retries,
                    )
                    time.sleep(delay)
                    continue
                raise APIError(
                    f"GFW API request failed after {retries} retries: {e!s}"
                ) from e

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise APIError("GFW API request failed unexpectedly")

    finally:
        if should_close:
            client.close()


def _gfw_post(
    endpoint: str,
    json_data: dict[str, Any],
    client: httpx.Client | None = None,
    retries: int = GFW_RETRIES,
) -> dict[str, Any]:
    """Make authenticated POST request to GFW API with retry logic.

    Implements exponential backoff with jitter for 429 and 5xx errors.

    Args:
        endpoint: API endpoint (e.g., "/geostore")
        json_data: JSON body to post
        client: Optional existing client
        retries: Number of retry attempts (default: GFW_RETRIES)

    Returns:
        Parsed JSON response

    Raises:
        APIError: On HTTP errors after exhausting retries
    """
    should_close = client is None
    headers = _get_gfw_headers()
    client = client or create_client(timeout=GFW_TIMEOUT, headers=headers)

    url = f"{GFW_BASE_URL}{endpoint}"
    last_error: APIError | None = None

    try:
        for attempt in range(retries + 1):
            try:
                response = client.post(url, json=json_data)

                if response.status_code in (200, 201):
                    return response.json()

                # Handle common error cases
                if response.status_code == 401:
                    raise APIError(
                        "GFW API authentication failed. Check your GFW_API_KEY.",
                        status_code=401,
                    )
                if response.status_code == 400:
                    error_text = (
                        response.text[:200] if response.text else "Invalid request"
                    )
                    raise APIError(
                        f"GFW API bad request: {sanitize_error(error_text)}",
                        status_code=400,
                    )

                # Retryable errors: 429 (rate limit) and 5xx (server errors)
                if response.status_code == 429 or response.status_code >= 500:
                    if attempt < retries:
                        # Check for Retry-After header on 429
                        retry_after = response.headers.get("Retry-After")
                        if retry_after:
                            delay = min(float(retry_after), GFW_BACKOFF_MAX)
                        else:
                            base_delay = GFW_BACKOFF_BASE * (2**attempt)
                            jitter = random.uniform(0, GFW_BACKOFF_BASE)
                            delay = min(base_delay + jitter, GFW_BACKOFF_MAX)
                        logger.debug(
                            "GFW API error %d, retrying in %.1fs (attempt %d/%d)",
                            response.status_code,
                            delay,
                            attempt + 1,
                            retries,
                        )
                        time.sleep(delay)
                        continue

                    # Exhausted retries
                    if response.status_code == 429:
                        raise APIError(
                            f"GFW API rate limit exceeded after {retries} retries.",
                            status_code=429,
                        )
                    raise APIError(
                        f"GFW API server error ({response.status_code}) after {retries} retries.",
                        status_code=response.status_code,
                    )

                # Generic non-retryable error
                error_text = response.text[:200] if response.text else "No details"
                raise APIError(
                    f"GFW API error: HTTP {response.status_code} - {sanitize_error(error_text)}",
                    status_code=response.status_code,
                )

            except httpx.TimeoutException as e:
                last_error = APIError("GFW API request timed out")
                if attempt < retries:
                    delay = GFW_BACKOFF_BASE * (2**attempt)
                    logger.debug(
                        "GFW API timeout, retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        retries,
                    )
                    time.sleep(delay)
                    continue
                raise APIError(
                    f"GFW API request timed out after {retries} retries"
                ) from e
            except httpx.RequestError as e:
                last_error = APIError(f"GFW API request failed: {e!s}")
                if attempt < retries:
                    delay = GFW_BACKOFF_BASE * (2**attempt)
                    logger.debug(
                        "GFW API request error, retrying in %.1fs (attempt %d/%d)",
                        delay,
                        attempt + 1,
                        retries,
                    )
                    time.sleep(delay)
                    continue
                raise APIError(
                    f"GFW API request failed after {retries} retries: {e!s}"
                ) from e

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        raise APIError("GFW API request failed unexpectedly")

    finally:
        if should_close:
            client.close()


def _create_circular_geostore(lat: float, lon: float, radius_km: float) -> str:
    """Create a circular geostore and return its ID.

    Approximates a circle as a 32-point polygon. The geostore is created
    on-the-fly (not cached) for simplicity.

    Args:
        lat: Center latitude
        lon: Center longitude
        radius_km: Radius in kilometers

    Returns:
        Geostore ID from GFW API

    Raises:
        APIError: On HTTP errors
        ValueError: On invalid inputs
    """
    # CR-0021: Validation raises ValueError on invalid input; return values unused
    _validate_coordinates(lat, lon)
    _validate_radius_km(radius_km)

    # Convert radius from km to degrees (approximate)
    # 1 degree latitude ≈ 111 km
    # 1 degree longitude ≈ 111 * cos(lat) km
    lat_rad = math.radians(lat)
    radius_lat = radius_km / 111.0
    radius_lon = radius_km / (111.0 * math.cos(lat_rad))

    # Generate polygon points (counterclockwise)
    coordinates = []
    for i in range(GFW_CIRCLE_POINTS):
        angle = 2 * math.pi * i / GFW_CIRCLE_POINTS
        point_lon = lon + radius_lon * math.cos(angle)
        point_lat = lat + radius_lat * math.sin(angle)
        coordinates.append([point_lon, point_lat])

    # Close the polygon
    coordinates.append(coordinates[0])

    # Create GeoJSON
    geojson = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [coordinates],
                },
            }
        ],
    }

    # POST to geostore endpoint
    response = _gfw_post("/geostore", {"geojson": geojson})

    # Extract geostore ID from response
    geostore_id = response.get("data", {}).get("id")
    if not geostore_id:
        raise APIError("GFW API did not return a geostore ID")

    return geostore_id


# =============================================================================
# Tool Functions
# =============================================================================


@tool
@timeout(60)
def get_tree_cover_loss_trends(
    country: str,
    region: str | None = None,
    window_years: int = 10,
) -> str:
    """
    Get historical tree cover loss trends for a country or region.

    Analyzes deforestation rates over 5 or 10 year windows to show trends.
    Uses Global Forest Watch data with 30% canopy cover threshold.

    Args:
        country: Country name or ISO 3166-1 alpha-3 code (e.g., "Chad", "TCD")
        region: Optional sub-national region name (not yet implemented)
        window_years: Trend window - 5 or 10 years (default 10)

    Returns:
        Annual loss rates, total loss, and trend direction
    """
    try:
        iso3 = _validate_country_code(country)
        window = _validate_window_years(window_years)

        # Calculate year range
        current_year = datetime.now().year
        # GFW data typically lags 1-2 years
        end_year = current_year - 2
        start_year = end_year - window + 1

        # Query GFW dataset API
        # The UMD tree cover loss dataset aggregated by year and country
        params = {
            "sql": f"""
                SELECT umd_tree_cover_loss__year as year,
                       SUM(area__ha) as loss_ha
                FROM data
                WHERE iso = '{iso3}'
                  AND umd_tree_cover_loss__year >= {start_year}
                  AND umd_tree_cover_loss__year <= {end_year}
                  AND umd_tree_cover_density_2000__threshold >= {GFW_CANOPY_THRESHOLD}
                GROUP BY umd_tree_cover_loss__year
                ORDER BY umd_tree_cover_loss__year
            """.strip()
        }

        response = _gfw_get(
            "/dataset/umd_tree_cover_loss/latest/query/json",
            params=params,
        )

        data = response.get("data", [])

        if not data:
            return (
                f"No tree cover loss data available for {iso3} ({start_year}-{end_year}).\n"
                "The country may not have significant forest cover or data may not be available."
            )

        # Process results
        years = []
        losses = []
        for row in data:
            year = row.get("year")
            loss = row.get("loss_ha", 0)
            if year is not None:
                years.append(int(year))
                losses.append(float(loss))

        if not years:
            return f"No tree cover loss data available for {iso3}."

        total_loss = sum(losses)
        avg_annual = total_loss / len(years)

        # Calculate trend (simple linear regression direction)
        if len(years) >= 2:
            # Compare first half to second half for trend
            mid = len(losses) // 2
            first_half_avg = sum(losses[:mid]) / mid if mid > 0 else 0
            second_half_avg = (
                sum(losses[mid:]) / (len(losses) - mid) if len(losses) > mid else 0
            )

            if second_half_avg > first_half_avg * 1.1:
                trend = "📈 INCREASING (deforestation accelerating)"
            elif second_half_avg < first_half_avg * 0.9:
                trend = "📉 DECREASING (deforestation slowing)"
            else:
                trend = "➡️ STABLE"
        else:
            trend = "Insufficient data for trend"

        # Format output
        output_lines = [
            f"Tree Cover Loss Trends for {iso3}",
            f"Period: {min(years)}-{max(years)} ({window} year window)",
            f"Canopy threshold: ≥{GFW_CANOPY_THRESHOLD}%",
            "",
            "Annual Loss (hectares):",
        ]

        for year, loss in zip(years, losses, strict=False):
            bar = "█" * min(int(loss / avg_annual * 5), 20) if avg_annual > 0 else ""
            output_lines.append(f"  {year}: {loss:,.0f} ha {bar}")

        output_lines.extend(
            [
                "",
                f"Total Loss: {total_loss:,.0f} hectares",
                f"Average Annual Loss: {avg_annual:,.0f} hectares/year",
                f"Trend: {trend}",
                "",
                "Source: Global Forest Watch (Hansen/UMD/Google/USGS/NASA)",
            ]
        )

        if region:
            output_lines.append(
                "\nNote: Sub-national region filtering not yet implemented."
            )

        return "\n".join(output_lines)

    except ValueError as e:
        return str(e)
    except APIError as e:
        return format_error(e, "fetching tree cover loss trends")


@tool
@timeout(60)
def get_tree_cover_loss_by_driver(
    country: str,
    region: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
) -> str:
    """
    Get tree cover loss broken down by driver/cause.

    Shows what is causing deforestation in the specified area:
    - Commodity-driven (agriculture expansion)
    - Shifting agriculture
    - Forestry (logging)
    - Wildfire
    - Urbanization

    Args:
        country: Country name or ISO 3166-1 alpha-3 code (e.g., "Chad", "TCD")
        region: Optional sub-national region name (not yet implemented)
        start_year: Start year (default: 5 years ago)
        end_year: End year (default: most recent available)

    Returns:
        Loss by driver type with percentages and dominant driver
    """
    try:
        iso3 = _validate_country_code(country)

        # Default year range
        current_year = datetime.now().year
        if end_year is None:
            end_year = current_year - 2  # GFW data typically lags
        if start_year is None:
            start_year = end_year - 4  # 5 year window

        # Query GFW Beta Land API for drivers
        params = {
            "iso": iso3,
            "threshold": GFW_CANOPY_THRESHOLD,
            "start_year": start_year,
            "end_year": end_year,
        }

        response = _gfw_get("/v0/land/tree_cover_loss_by_driver", params=params)

        data = response.get("data", [])

        if not data:
            return (
                f"No driver data available for {iso3} ({start_year}-{end_year}).\n"
                "This data may not be available for all countries."
            )

        # Process driver categories
        driver_totals: dict[str, float] = {}
        total_loss = 0.0

        for row in data:
            driver = row.get("tsc_tree_cover_loss_drivers__type", "Unknown")
            loss = float(row.get("area__ha", 0))
            driver_totals[driver] = driver_totals.get(driver, 0) + loss
            total_loss += loss

        if total_loss == 0:
            return f"No tree cover loss recorded for {iso3} ({start_year}-{end_year})."

        # Sort by loss amount
        sorted_drivers = sorted(driver_totals.items(), key=lambda x: x[1], reverse=True)

        # Find dominant driver
        dominant = sorted_drivers[0][0] if sorted_drivers else "Unknown"

        # Format output
        output_lines = [
            f"Tree Cover Loss by Driver for {iso3}",
            f"Period: {start_year}-{end_year}",
            f"Canopy threshold: ≥{GFW_CANOPY_THRESHOLD}%",
            "",
            "Loss by Driver:",
        ]

        for driver, loss in sorted_drivers:
            pct = (loss / total_loss * 100) if total_loss > 0 else 0
            bar = "█" * int(pct / 5)  # 20 chars = 100%
            # Clean up driver names
            driver_display = driver.replace("_", " ").title()
            output_lines.append(
                f"  {driver_display}: {loss:,.0f} ha ({pct:.1f}%) {bar}"
            )

        output_lines.extend(
            [
                "",
                f"Total Loss: {total_loss:,.0f} hectares",
                f"Dominant Driver: {dominant.replace('_', ' ').title()}",
                "",
                "Source: Global Forest Watch (Curtis et al.)",
            ]
        )

        if region:
            output_lines.append(
                "\nNote: Sub-national region filtering not yet implemented."
            )

        return "\n".join(output_lines)

    except ValueError as e:
        return str(e)
    except APIError as e:
        return format_error(e, "fetching loss by driver")


@tool
@timeout(60)
def get_forest_carbon_stock(
    lat: float,
    lon: float,
    radius_km: float = 10.0,
) -> str:
    """
    Get forest carbon stock (above-ground biomass) for an area.

    Estimates carbon storage using WHRC above-ground biomass data.
    Useful for carbon accounting and baseline assessments.

    Args:
        lat: Latitude of center point
        lon: Longitude of center point
        radius_km: Radius in kilometers (default 10km, max 50km)

    Returns:
        Biomass density (Mg/ha), total carbon estimate, data year
    """
    try:
        _validate_coordinates(lat, lon)
        radius = _validate_radius_km(radius_km)

        # Create circular geostore
        geostore_id = _create_circular_geostore(lat, lon, radius)

        # Query zonal statistics for biomass
        # Using WHRC above-ground biomass stock (2000 baseline)
        zonal_request = {
            "geostore_id": geostore_id,
            "layer": "whrc_aboveground_biomass_stock_2000__Mg_ha-1",
            "statistics": ["mean", "sum", "count"],
        }

        response = _gfw_post("/analysis/zonal", zonal_request)

        stats = response.get("data", {}).get("attributes", {})

        if not stats:
            return (
                f"No biomass data available for location ({lat:.4f}, {lon:.4f}).\n"
                "The area may be outside GFW coverage or have no forest."
            )

        # Extract statistics
        mean_biomass = stats.get("mean", 0)
        pixel_count = stats.get("count", 0)

        # Estimate area (each pixel is approximately 30m x 30m = 0.09 ha)
        pixel_area_ha = 0.09
        area_ha = pixel_count * pixel_area_ha

        # Calculate totals
        total_biomass_mg = mean_biomass * area_ha

        # Convert biomass to carbon (approximately 47% of biomass is carbon)
        carbon_fraction = 0.47
        total_carbon_mg = total_biomass_mg * carbon_fraction

        # Format output
        output_lines = [
            "Forest Carbon Stock Analysis",
            f"Location: {lat:.4f}°, {lon:.4f}°",
            f"Radius: {radius:.1f} km",
            "",
            "Biomass Estimates:",
            f"  Mean Density: {mean_biomass:.1f} Mg/ha (megagrams per hectare)",
            f"  Analyzed Area: {area_ha:,.0f} hectares",
            f"  Total Above-ground Biomass: {total_biomass_mg:,.0f} Mg",
            "",
            "Carbon Estimates:",
            f"  Carbon Fraction: {carbon_fraction:.0%}",
            f"  Estimated Carbon Stock: {total_carbon_mg:,.0f} Mg C",
            f"  CO₂ Equivalent: {total_carbon_mg * 3.67:,.0f} Mg CO₂e",
            "",
            "Data Source: WHRC Above-ground Biomass (2000 baseline)",
            "",
            "Note: This is a baseline estimate. Actual current carbon stock",
            "may differ due to forest loss since 2000.",
        ]

        return "\n".join(output_lines)

    except ValueError as e:
        return str(e)
    except APIError as e:
        return format_error(e, "fetching carbon stock")


@tool
@timeout(60)
def get_forest_extent(
    lat: float,
    lon: float,
    radius_km: float = 10.0,
) -> str:
    """
    Get current forest extent and characteristics for an area.

    Returns tree cover percentage and area statistics for the
    specified location using Global Forest Watch data.

    Args:
        lat: Latitude of center point
        lon: Longitude of center point
        radius_km: Radius in kilometers (default 10km, max 50km)

    Returns:
        Tree cover %, primary forest area, total analyzed area
    """
    try:
        _validate_coordinates(lat, lon)
        radius = _validate_radius_km(radius_km)

        # Create circular geostore
        geostore_id = _create_circular_geostore(lat, lon, radius)

        # Query zonal statistics for tree cover
        zonal_request = {
            "geostore_id": geostore_id,
            "layer": "umd_tree_cover_density_2000__percent",
            "statistics": ["mean", "sum", "count"],
        }

        response = _gfw_post("/analysis/zonal", zonal_request)

        stats = response.get("data", {}).get("attributes", {})

        if not stats:
            return (
                f"No tree cover data available for location ({lat:.4f}, {lon:.4f}).\n"
                "The area may be outside GFW coverage."
            )

        # Extract statistics
        mean_cover = stats.get("mean", 0)
        pixel_count = stats.get("count", 0)

        # Estimate area (each pixel is approximately 30m x 30m = 0.09 ha)
        pixel_area_ha = 0.09
        total_area_ha = pixel_count * pixel_area_ha

        # Estimate forest area (pixels with cover >= threshold)
        # This is approximate since we only have mean
        forested_area_ha = total_area_ha * (mean_cover / 100)

        # Calculate radius in degrees for display
        # (informational - actual query used km)

        # Format output
        output_lines = [
            "Forest Extent Analysis",
            f"Location: {lat:.4f}°, {lon:.4f}°",
            f"Radius: {radius:.1f} km",
            "",
            "Tree Cover Statistics (2000 baseline):",
            f"  Mean Tree Cover: {mean_cover:.1f}%",
            f"  Total Analyzed Area: {total_area_ha:,.0f} hectares",
            f"  Estimated Forest Area: {forested_area_ha:,.0f} hectares",
            "",
            "Coverage Assessment:",
        ]

        # Categorize coverage level
        if mean_cover >= 70:
            output_lines.append("  Category: Dense Forest (≥70% cover)")
        elif mean_cover >= 40:
            output_lines.append("  Category: Moderate Forest (40-70% cover)")
        elif mean_cover >= 10:
            output_lines.append("  Category: Sparse Forest/Woodland (10-40% cover)")
        else:
            output_lines.append("  Category: Non-forest (<10% cover)")

        output_lines.extend(
            [
                "",
                f"Canopy Threshold Used: ≥{GFW_CANOPY_THRESHOLD}%",
                "Data Source: Hansen/UMD/Google/USGS/NASA (Global Forest Watch)",
                "",
                "Note: This shows 2000 baseline data. Use get_tree_cover_loss_trends()",
                "to see how cover has changed since then.",
            ]
        )

        return "\n".join(output_lines)

    except ValueError as e:
        return str(e)
    except APIError as e:
        return format_error(e, "fetching forest extent")
