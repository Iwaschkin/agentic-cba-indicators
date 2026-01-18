# [TASK042] - Create GFW API Request Helper

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-18

## Original Request
Create the core `_gfw_request()` helper function for authenticated GFW API calls.

## Thought Process
The GFW API requires authentication via `x-api-key` header. We already have `require_api_key("gfw")` in `_secrets.py` and `fetch_json()` in `_http.py`. This helper will combine them for DRY GFW requests.

## Implementation Plan
- Create `forestry.py` module scaffold
- Add `GFW_BASE_URL` constant
- Implement `_gfw_request()` using `fetch_json()` and `require_api_key()`
- Support GET and POST methods

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 42.1 | Create forestry.py with imports | Complete | 2026-01-18 | Module created with GFW helpers |
| 42.2 | Add GFW_BASE_URL constant | Complete | 2026-01-18 | Base URL configured |
| 42.3 | Implement _gfw_request() | Complete | 2026-01-18 | Shared request helper using _http + secrets |

## Progress Log
### 2026-01-17
- Task created as part of GFW forestry tools implementation plan
### 2026-01-18
- Implemented GFW request helper and forestry.py scaffold
