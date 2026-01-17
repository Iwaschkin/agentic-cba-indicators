# [TASK011] - Add Coordinate Validation

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-17
**Priority:** P1 - High
**Phase:** 2

## Original Request
Address P1-01: Latitude/longitude values not validated for valid ranges in NASA POWER, SoilGrids, and other tools.

## Thought Process
Multiple tools accept latitude/longitude parameters but don't validate them against valid ranges:
- Latitude: -90 to +90
- Longitude: -180 to +180

Invalid coordinates can cause API errors, unexpected behavior, or security issues.

Solution: Create a centralized validation function and apply it across all coordinate-accepting tools.

Files affected:
- `tools/nasa_power.py` - Direct lat/lon input ✅
- `tools/soilgrids.py` - Direct lat/lon input ✅
- `tools/biodiversity.py` - Direct lat/lon input ✅
- `tools/climate.py` - Uses geocode_city (no direct input, N/A)
- `tools/weather.py` - Uses geocode_city (no direct input, N/A)

## Implementation Plan
- [x] Create `validate_coordinates()` in `_geo.py`
- [x] Add validation to all tools accepting lat/lon
- [x] Return user-friendly error messages for invalid coordinates
- [ ] Add unit tests (deferred to TASK006)

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 11.1 | Create validate_coordinates() function | Complete | 2025-01-17 | Added CoordinateValidationError and validate_coordinates() to _geo.py |
| 11.2 | Apply to nasa_power.py | Complete | 2025-01-17 | Added import and validation in _fetch_power_data() |
| 11.3 | Apply to soilgrids.py | Complete | 2025-01-17 | Added import and validation in _fetch_soil_data() |
| 11.4 | Apply to climate.py | N/A | 2025-01-17 | Uses geocode_city, no direct lat/lon input |
| 11.5 | Apply to weather.py | N/A | 2025-01-17 | Uses geocode_city, no direct lat/lon input |
| 11.6 | Apply to biodiversity.py | Complete | 2025-01-17 | Added import and validation in _search_occurrences() |
| 11.7 | Add unit tests | Deferred | 2025-01-17 | Covered in TASK006 (expand test coverage) |

## Progress Log
### 2025-01-17
- Task created from code review finding P1-01
- Assigned to Phase 2 (Input Validation)
- Created CoordinateValidationError exception and validate_coordinates() function in _geo.py
- Applied validation to nasa_power.py, soilgrids.py, and biodiversity.py
- Confirmed climate.py and weather.py use geocode_city (coordinates come from Nominatim API)
- All 30 tests passing
- Task complete

## Acceptance Criteria
- [x] All coordinate inputs validated before API calls
- [x] Clear error messages for out-of-range coordinates
- [x] Centralized validation function reused across tools
- [ ] Tests verify validation for edge cases (deferred to TASK006)
