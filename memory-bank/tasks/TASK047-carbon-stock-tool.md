# [TASK047] - Implement Forest Carbon Stock Tool

**Status:** Pending
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Implement `get_forest_carbon_stock()` for above-ground biomass baseline.

## Thought Process
Requires circular geostore creation then zonal analysis on WHRC biomass layer. Returns biomass density and estimated carbon (using 0.47 conversion factor).

## Implementation Plan
- Validate radius_km
- Create circular geostore
- Query `/analysis/zonal` for biomass layer
- Calculate carbon from biomass
- Format output with density, total, and carbon estimate

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 47.1 | Validate inputs | Not Started | | |
| 47.2 | Create geostore | Not Started | | |
| 47.3 | Query zonal analysis | Not Started | | |
| 47.4 | Calculate carbon estimate | Not Started | | |
| 47.5 | Format output | Not Started | | |

## Progress Log
### 2026-01-17
- Task created as part of GFW forestry tools implementation plan
