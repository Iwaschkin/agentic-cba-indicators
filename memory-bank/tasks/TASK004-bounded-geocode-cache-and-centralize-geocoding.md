# TASK004 - Implement bounded geocode cache + centralize geocoding

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Add bounded/TTL geocode cache and remove duplicate geocoding logic in tool modules.

## Thought Process
Unbounded caches risk memory growth; duplicated geocoding causes inconsistent behavior.

## Implementation Plan
- Implement LRU/TTL cache in `_geo.py`
- Update weather/climate tools to use `_geo.geocode_city()`

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 4.1 | Add bounded cache | Complete | 2026-01-17 | Added LRU-style cache with max size |
| 4.2 | Replace duplicate geocoding | Complete | 2026-01-17 | Weather/climate now use _geo.geocode_city |

## Progress Log
### 2026-01-17
- Task created
- Implemented bounded geocode cache with configurable size
- Centralized geocoding usage in weather and climate tools
