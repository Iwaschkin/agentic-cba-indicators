# [TASK016] - Fix JSON Decode Error Handling

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-17
**Priority:** P1 - High
**Phase:** 4

## Original Request
Address P1-06: `fetch_json()` catches generic Exception but `json.JSONDecodeError` may expose raw response content.

## Thought Process
The `fetch_json()` function in `_http.py` uses a broad `except Exception` which can:
1. Mask specific JSON parsing errors
2. Potentially expose raw response content in error messages
3. Make debugging difficult

Solution: Add specific handling for `json.JSONDecodeError` to provide clear error messages without exposing potentially sensitive response data.

## Implementation Plan
- [x] Add specific JSONDecodeError handling in fetch_json()
- [x] Sanitize error messages (don't include raw response body)
- [x] Provide helpful error context (URL, error line number)
- [x] Add unit tests for malformed JSON responses

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 16.1 | Add JSONDecodeError handler | Complete | 2025-01-17 | Try/except around response.json() |
| 16.2 | Sanitize error messages | Complete | 2025-01-17 | Uses sanitize_error() on URL |
| 16.3 | Add helpful error context | Complete | 2025-01-17 | Includes msg and line number |
| 16.4 | Add unit tests | Complete | 2025-01-17 | test_handles_json_decode_error |

## Progress Log
### 2025-01-17
- Task created from code review finding P1-06
- Assigned to Phase 4 (Error Handling)
- Added import for `json` module
- Wrapped response.json() in try/except JSONDecodeError
- Error message includes: sanitized URL, error msg, line number
- Does NOT include raw response body (security)
- Added test with mock HTTP client returning invalid JSON
- All 35 tests passing
- Task complete

## Acceptance Criteria
- [x] JSONDecodeError handled specifically
- [x] Raw response body not exposed in errors
- [x] Error messages include URL and context
- [x] Tests verify error handling behavior
