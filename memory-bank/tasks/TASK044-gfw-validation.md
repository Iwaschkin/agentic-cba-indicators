# [TASK044] - Add Input Validation Helpers

**Status:** Pending
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Add validation helpers for country codes, window_years, and radius_km.

## Thought Process
Consistent input validation prevents confusing API errors. Country codes should be ISO 3166-1 alpha-3. Window years restricted to 5 or 10 (M&E standards). Radius capped at 50km per GFW limits.

## Implementation Plan
- `_validate_country_code()` using `COUNTRY_CODES_ISO3` from `_mappings.py`
- `_validate_window_years()` accepting only 5 or 10
- `_validate_radius_km()` capping at 50km

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 44.1 | Add country code validation | Not Started | | |
| 44.2 | Add window_years validation | Not Started | | |
| 44.3 | Add radius_km validation | Not Started | | |

## Progress Log
### 2026-01-17
- Task created as part of GFW forestry tools implementation plan
