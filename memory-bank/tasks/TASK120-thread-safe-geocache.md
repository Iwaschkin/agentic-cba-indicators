# TASK120 - Make Geocoding Cache Thread-Safe

**Status:** Completed
**Priority:** P1
**Phase:** 2 - Thread Safety
**Added:** 2026-01-19
**Updated:** 2026-01-19

## Original Request

From Code Review v2 Issue PNR-001: The `_GEOCODE_CACHE` in `_geo.py` is a plain dict, which is not thread-safe for concurrent access in multi-threaded environments.

## Thought Process

Current implementation:
```python
_GEOCODE_CACHE: dict[str, dict[str, Any] | None] = {}
```

This is problematic because:
1. Dict operations aren't atomic in CPython for all cases
2. Concurrent writes can cause data corruption
3. Agent could be used in multi-threaded contexts (e.g., Streamlit)

Solutions considered:
1. `threading.Lock` - explicit locking, verbose but clear
2. `cachetools.TTLCache` with lock - already used elsewhere in codebase
3. `functools.lru_cache` - built-in, thread-safe in CPython 3.9+

Implemented with `cachetools.TTLCache` plus a `threading.Lock`, matching the thread-safe pattern already used in `_http.py` and allowing TTL-based eviction.

## Implementation Plan

- [x] 2.1 Import cachetools and threading
- [x] 2.2 Replace dict with TTLCache + lock
- [x] 2.3 Remove manual dict cache usage
- [x] 2.4 Add cache clearing function for testing
- [x] 2.5 Update tests to use cache clearing

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 2.1 | Import cachetools/threading | Complete | 2026-01-19 | Added TTLCache + Lock |
| 2.2 | Apply decorator | Not Applicable | 2026-01-19 | Used TTLCache instead |
| 2.3 | Remove manual cache | Complete | 2026-01-19 | Replaced with TTLCache |
| 2.4 | Add cache clear function | Complete | 2026-01-19 | Added clear_geocode_cache() |
| 2.5 | Update tests | Complete | 2026-01-19 | Adjusted tests to clear cache |

## Acceptance Criteria

- [x] `_GEOCODE_CACHE` dict removed
- [x] Thread-safety achieved via TTLCache + lock
- [x] Existing weather/climate tests pass

## Definition of Done

- Code merged
- All tests pass
- Manual verification: `grep "_GEOCODE_CACHE" _geo.py` returns empty

## Progress Log

### 2026-01-19
- Task created from Code Review v2 Issue PNR-001
### 2026-01-19
- Replaced geocode cache with TTLCache + threading lock in `tools/_geo.py`.
- Added `clear_geocode_cache()` helper for tests and updated cache usage.
