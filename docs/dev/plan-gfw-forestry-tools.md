# Global Forest Watch Forestry Tools Implementation Plan

## Overview

Add forest state monitoring tools using the Global Forest Watch (GFW) API. These tools focus on **baselines and trends** rather than real-time alerts, aligned with M&E cycles for regenerative agriculture projects.

**API Base:** `https://data-api.globalforestwatch.org/`
**Authentication:** API key via `x-api-key` header
**Key Registration:** `require_api_key("gfw")` from `config/_secrets.py`

---

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Focus | State monitoring | User requirement: "less about real time alerts, more about ongoing state of affairs" |
| Trend windows | 5 or 10 years | Standard M&E evaluation periods |
| Canopy threshold | 30% (GFW default) | Keep GFW default for now; can parameterize later |
| Geostore handling | Create on-the-fly | Skip caching complexity; each query creates fresh geostore |
| Tool count | 4 functions | Comprehensive coverage without overwhelming LLM |

---

## Tools Specification

### 1. `get_tree_cover_loss_trends`

**Purpose:** Historical deforestation rates over 5 or 10 year windows

**Signature:**
```python
@tool
def get_tree_cover_loss_trends(
    country: str,
    region: str | None = None,
    window_years: int = 10
) -> str:
    """
    Get historical tree cover loss trends for a country or region.

    Args:
        country: ISO 3166-1 alpha-3 country code (e.g., "TCD" for Chad)
        region: Optional sub-national region name
        window_years: Trend window - 5 or 10 years (default 10)

    Returns:
        Annual loss rates, total loss, and trend direction
    """
```

**API Endpoints:**
- `/dataset/umd_tree_cover_loss/latest/query/json` with SQL filtering by country/year
- Aggregate by year, compute 5/10 year trend

**Output includes:**
- Annual loss (hectares) for each year in window
- Total loss over period
- Average annual loss rate
- Trend direction (increasing/decreasing/stable)

---

### 2. `get_forest_carbon_stock`

**Purpose:** Above-ground biomass baseline for carbon accounting

**Signature:**
```python
@tool
def get_forest_carbon_stock(
    lat: float,
    lon: float,
    radius_km: float = 10.0
) -> str:
    """
    Get forest carbon stock (above-ground biomass) for an area.

    Args:
        lat: Latitude of center point
        lon: Longitude of center point
        radius_km: Radius in kilometers (default 10km, max 50km)

    Returns:
        Biomass density (Mg/ha), total carbon estimate, data year
    """
```

**API Endpoints:**
1. `POST /geostore/` - Create circular geostore from lat/lon/radius
2. `POST /analysis/zonal` - Query `whrc_aboveground_biomass_stock_2000__Mg_ha-1` layer

**Output includes:**
- Mean biomass density (Mg/ha)
- Total above-ground biomass (Mg)
- Estimated carbon (Mg C) using 0.47 conversion factor
- Area analyzed (ha)
- Data source year (2000 baseline)

---

### 3. `get_tree_cover_loss_by_driver`

**Purpose:** Understand WHY deforestation is happening

**Signature:**
```python
@tool
def get_tree_cover_loss_by_driver(
    country: str,
    region: str | None = None,
    start_year: int | None = None,
    end_year: int | None = None
) -> str:
    """
    Get tree cover loss broken down by driver/cause.

    Args:
        country: ISO 3166-1 alpha-3 country code
        region: Optional sub-national region name
        start_year: Start year (default: 5 years ago)
        end_year: End year (default: most recent available)

    Returns:
        Loss by driver type (commodity, forestry, shifting agriculture, etc.)
    """
```

**API Endpoint:**
- `GET /v0/land/tree_cover_loss_by_driver` (Beta Land API)
- Parameters: `iso`, `adm1` (optional), `threshold=30`

**Driver categories (from GFW):**
- Commodity-driven deforestation
- Shifting agriculture
- Forestry
- Wildfire
- Urbanization
- Unknown/Other

**Output includes:**
- Loss by driver (hectares and %)
- Dominant driver identification
- Year range analyzed

---

### 4. `get_forest_extent`

**Purpose:** Current forest cover baseline

**Signature:**
```python
@tool
def get_forest_extent(
    lat: float,
    lon: float,
    radius_km: float = 10.0
) -> str:
    """
    Get current forest extent and characteristics for an area.

    Args:
        lat: Latitude of center point
        lon: Longitude of center point
        radius_km: Radius in kilometers (default 10km, max 50km)

    Returns:
        Tree cover %, primary forest area, intact forest landscapes
    """
```

**API Endpoints:**
1. `POST /geostore/` - Create circular geostore
2. `POST /analysis/zonal` - Query multiple layers:
   - `umd_tree_cover_density_2000__percent` (baseline cover)
   - `umd_tree_cover_loss__year` (cumulative loss to date)
   - Primary forest layer (if available)
   - Intact Forest Landscapes (if available)

**Output includes:**
- Current tree cover % (baseline - cumulative loss)
- Primary forest area (ha)
- Intact forest landscape area (ha)
- Total analyzed area (ha)

---

## Implementation Details

### File Structure

```
src/agentic_cba_indicators/tools/
├── forestry.py          # NEW - GFW tools
├── _geo.py              # Existing - geocode_city(), can add country code lookup
├── _http.py             # Existing - fetch_json() with retry
└── __init__.py          # Update exports
```

### Dependencies

- `httpx` (already in project)
- `require_api_key("gfw")` from `config/_secrets.py` (already registered)

### HTTP Pattern

```python
from ._http import fetch_json, APIError, format_error
from agentic_cba_indicators.config import require_api_key

GFW_BASE_URL = "https://data-api.globalforestwatch.org"

def _gfw_request(endpoint: str, method: str = "GET", **kwargs) -> dict:
    """Make authenticated GFW API request."""
    api_key = require_api_key("gfw")
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    url = f"{GFW_BASE_URL}{endpoint}"
    return fetch_json(url, method=method, headers=headers, **kwargs)
```

### Geostore Creation Helper

```python
def _create_circular_geostore(lat: float, lon: float, radius_km: float) -> str:
    """Create a circular geostore and return its ID."""
    # Create GeoJSON circle approximation (32-point polygon)
    # POST to /geostore/
    # Return geostore_id for use in subsequent queries
```

### Tool Export Pattern

In `tools/__init__.py`:
```python
from .forestry import (
    get_tree_cover_loss_trends,
    get_forest_carbon_stock,
    get_tree_cover_loss_by_driver,
    get_forest_extent,
)

__all__ = [
    # ... existing ...
    "get_tree_cover_loss_trends",
    "get_forest_carbon_stock",
    "get_tree_cover_loss_by_driver",
    "get_forest_extent",
]

FULL_TOOLS = [
    # ... existing ...
    get_tree_cover_loss_trends,
    get_forest_carbon_stock,
    get_tree_cover_loss_by_driver,
    get_forest_extent,
]
```

---

## CBA Indicator Coverage

| GFW Tool | CBA Indicators Supported |
|----------|--------------------------|
| `get_tree_cover_loss_trends` | 17 (Tree cover), 24 (Forest cover change), 45 (Deforestation rate) |
| `get_forest_carbon_stock` | 107 (Soil organic carbon - proxy), 100 (Above-ground biomass) |
| `get_tree_cover_loss_by_driver` | 44 (Land use change drivers), 45 (Deforestation rate) |
| `get_forest_extent` | 17 (Tree cover), 25 (Primary forest), 26 (Intact forest) |

---

## Testing Plan

### Unit Tests (`tests/test_tools_forestry.py`)

1. **API key handling**
   - Missing key raises `ValueError` with helpful message
   - Key is passed in `x-api-key` header

2. **Input validation**
   - `window_years` accepts only 5 or 10
   - `radius_km` capped at 50km
   - Invalid country codes return helpful error

3. **Geostore creation**
   - Circular polygon has correct coordinates
   - GeoJSON structure is valid

4. **Response parsing**
   - Handles empty results gracefully
   - Formats numbers with appropriate precision
   - Includes data source attribution

5. **Error handling**
   - API errors (4xx, 5xx) return formatted messages
   - Network timeouts handled
   - Rate limiting (429) triggers retry

### Integration Tests (manual)

- Query Chad (TCD) - primary use case country
- Compare results with GFW web interface
- Verify carbon calculations against known values

---

## Error Messages

```python
# Missing API key
"GFW API key required. Set GFW_API_KEY environment variable or run: python scripts/get_gfw_api_key.py"

# Invalid country
"Country code '{code}' not recognized. Use ISO 3166-1 alpha-3 codes (e.g., 'TCD' for Chad)."

# Invalid window
"window_years must be 5 or 10 (standard M&E evaluation periods)"

# Radius too large
"radius_km cannot exceed 50km for GFW queries"

# No data available
"No forest data available for this location. The area may be outside GFW coverage."
```

---

## Future Enhancements (Out of Scope)

- [ ] Parameterize canopy threshold (currently fixed at 30%)
- [ ] Add geostore caching for repeated queries
- [ ] Support custom GeoJSON input (not just circles)
- [ ] Add deforestation alerts (GLAD, RADD) for real-time monitoring
- [ ] Add forest gain/restoration tracking

---

## Implementation Checklist

- [ ] Create `src/agentic_cba_indicators/tools/forestry.py`
  - [ ] `_gfw_request()` helper with auth
  - [ ] `_create_circular_geostore()` helper
  - [ ] `get_tree_cover_loss_trends()`
  - [ ] `get_forest_carbon_stock()`
  - [ ] `get_tree_cover_loss_by_driver()`
  - [ ] `get_forest_extent()`
- [ ] Update `tools/__init__.py` exports
- [ ] Create `tests/test_tools_forestry.py`
- [ ] Update `.env.example` with GFW instructions
- [ ] Test with Chad (TCD) queries
- [ ] Run full test suite + linting
- [ ] Commit with conventional commit message

---

## References

- [GFW Data API Docs](https://data-api.globalforestwatch.org/docs)
- [GFW API Key Request](https://data-api.globalforestwatch.org/auth/request)
- [Tree Cover Loss Dataset](https://data.globalforestwatch.org/datasets/tree-cover-loss)
- [WHRC Biomass Dataset](https://data.globalforestwatch.org/datasets/aboveground-live-woody-biomass-density)
