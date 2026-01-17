# TASK002 - Standardize HTTP handling across tools + retries

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Standardize external HTTP calls to use shared `_http` utilities, add timeouts/validation, and improve retry behavior.

## Thought Process
Inconsistent HTTP handling leads to hangs and uneven error behavior. Centralization improves reliability and maintainability.

## Implementation Plan
- Replace direct httpx calls in tool modules with `_http.fetch_json()` where feasible
- Add explicit timeouts for remaining direct calls
- Add jittered backoff and upper bound to retry policy

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 2.1 | Update tool modules to use `_http` | Complete | 2026-01-17 | Weather/climate/socioeconomic/_geo updated |
| 2.2 | Add validation for API responses | Complete | 2026-01-17 | Added response checks in tools |
| 2.3 | Enhance retry policy with jitter/limits | Complete | 2026-01-17 | Added jittered backoff and cap |

## Progress Log
### 2026-01-17
- Task created
- Standardized HTTP usage in weather/climate/socioeconomic and _geo
- Added response validation and formatted error handling
- Added jittered backoff with max delay in _http
