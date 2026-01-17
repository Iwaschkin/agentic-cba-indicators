# [TASK043] - Create Circular Geostore Helper

**Status:** Pending
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Create `_create_circular_geostore()` helper to generate circular polygons for GFW zonal analysis.

## Thought Process
GFW zonal analysis requires a geostore_id. We need to POST a GeoJSON polygon to `/geostore/` and extract the returned ID. A circle is approximated as a 32-point polygon.

## Implementation Plan
- Implement circle-to-polygon math (lat/lon + radius_km → 32 points)
- POST GeoJSON to GFW `/geostore/` endpoint
- Return geostore_id for use in subsequent queries

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 43.1 | Implement circle polygon math | Not Started | | |
| 43.2 | Create GeoJSON structure | Not Started | | |
| 43.3 | POST to geostore endpoint | Not Started | | |

## Progress Log
### 2026-01-17
- Task created as part of GFW forestry tools implementation plan
