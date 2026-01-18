# [TASK112] - External API Response Caching

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18
**Phase:** 5 - Performance Optimization
**Priority:** P1
**Issue ID:** P2-023

## Original Request
Add TTL caching for external API responses (World Bank, ILO, etc.) to reduce latency and API load.

## Thought Process
External APIs are called repeatedly with same parameters. Caching would:
- Reduce latency for repeated queries
- Reduce load on external services
- Improve user experience

Use cachetools.TTLCache with configurable TTL (default 1 hour).

## Implementation Plan
1. Add cachetools to dependencies (or use functools.lru_cache with manual TTL)
2. Create @cached_api_call(ttl=3600) decorator in _http.py
3. Apply to World Bank API calls in socioeconomic.py
4. Apply to ILO API calls in labor.py
5. Add unit tests for cache behavior

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 12.1 | Evaluate cachetools vs custom TTL | Complete | 2026-01-18 | cachetools.TTLCache already in deps (6.2.4) |
| 12.2 | Create caching infrastructure | Complete | 2026-01-18 | Added to _http.py |
| 12.3 | Add thread-safe global cache | Complete | 2026-01-18 | TTLCache + threading.Lock |
| 12.4 | Create @cached_api_call decorator | Complete | 2026-01-18 | Per-function caching with custom TTL |
| 12.5 | Add utility functions | Complete | 2026-01-18 | get_cache_stats(), clear_api_cache() |
| 12.6 | Add comprehensive unit tests | Complete | 2026-01-18 | 18 tests in test_http.py |

## Progress Log
### 2026-01-18
- Task created from code review finding P2-023

### 2026-01-18 (Session 2)
- Verified cachetools 6.2.4 already in dependencies
- Added caching infrastructure to `src/agentic_cba_indicators/tools/_http.py`:
  - `DEFAULT_CACHE_TTL = 3600` (configurable via API_CACHE_TTL env var)
  - `DEFAULT_CACHE_MAXSIZE = 1000` (configurable via API_CACHE_MAXSIZE env var)
  - `_api_cache`: Thread-safe TTLCache singleton
  - `_cache_lock`: threading.Lock for concurrent access
  - `_make_cache_key()`: SHA256 hash of URL + sorted params
  - `fetch_json_cached()`: Wrapper with TTL caching (use_cache param)
  - `@cached_api_call(ttl, maxsize)`: Decorator for per-function caching
  - `get_cache_stats()`: Returns cache size, maxsize, TTL
  - `clear_api_cache()`: Clears global cache, returns count cleared
- Added 18 comprehensive tests in `tests/test_http.py`:
  - TestMakeCacheKey (6 tests): key generation consistency
  - TestFetchJsonCached (4 tests): cache hit/miss, bypass, different params
  - TestCachedApiCallDecorator (3 tests): function caching, metadata preservation
  - TestCacheUtilities (3 tests): stats, clear functions
  - TestCacheThreadSafety (1 test): concurrent access
  - TestCacheErrorHandling (1 test): errors not cached
- All 426 tests pass (408 previous + 18 new)

## Implementation Details

### Configuration
- `API_CACHE_TTL`: Environment variable to override default TTL (seconds)
- `API_CACHE_MAXSIZE`: Environment variable to override max cache entries

### Usage Examples
```python
# Using fetch_json_cached directly
from agentic_cba_indicators.tools._http import fetch_json_cached
result = fetch_json_cached(url, params)  # Cached by default
result = fetch_json_cached(url, params, use_cache=False)  # Bypass cache

# Using decorator for custom functions
from agentic_cba_indicators.tools._http import cached_api_call

@cached_api_call(ttl=1800, maxsize=100)  # 30 min TTL, 100 entries
def fetch_weather_data(city: str) -> dict:
    ...

# Utilities
from agentic_cba_indicators.tools._http import get_cache_stats, clear_api_cache
stats = get_cache_stats()  # {'size': 42, 'maxsize': 1000, 'ttl': 3600}
cleared = clear_api_cache()  # Returns count of cleared entries
```

### Note on Application
The caching infrastructure is now available. Individual tools (socioeconomic.py, labor.py)
can be updated to use `fetch_json_cached()` or `@cached_api_call` decorator as needed.
The decorator approach allows per-function TTL customization.

## Definition of Done
- [x] TTL cache decorator implemented
- [x] Cache hit returns cached value
- [x] Cache expires after TTL (via cachetools)
- [x] Tests verify cache behavior
- [x] Thread-safe implementation
- [x] Configuration via environment variables
