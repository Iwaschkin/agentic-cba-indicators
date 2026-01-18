# [TASK080] - Narrow Exception Handling in nasa_power.py

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-19

## Original Request
Replace broad `except Exception as e:` patterns with specific exception handling in nasa_power.py.

## Mapped Issue
- **Issue ID:** P1-1 (partial)
- **Priority:** P1 (High)
- **Phase:** 1

## Implementation Plan
1. Identify all `except Exception` blocks in nasa_power.py (~3 occurrences)
2. Replace with `except (APIError, httpx.HTTPError)`
3. Add logging for caught exceptions
4. Verify tests still pass

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Audit except blocks | Complete | 2026-01-19 | Audited NASA POWER handlers |
| 1.2 | Update all tool functions | Complete | 2026-01-19 | Specific exceptions applied |
| 1.3 | Run tests | Complete | 2026-01-19 | Tests pass |

## Progress Log
### 2026-01-19
- Narrowed exception handling in nasa_power.py
- Verified tests pass

## Definition of Done
- All 3 catch blocks use (APIError, httpx.HTTPError)
- Tests pass
