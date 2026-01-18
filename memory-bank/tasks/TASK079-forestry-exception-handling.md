# [TASK079] - Narrow Exception Handling in forestry.py

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-19

## Original Request
Replace broad `except Exception as e:` patterns with specific exception handling in forestry.py.

## Mapped Issue
- **Issue ID:** P1-1 (partial)
- **Priority:** P1 (High)
- **Phase:** 1

## Implementation Plan
1. Identify all `except Exception` blocks in forestry.py (~4 occurrences)
2. Replace with `except (APIError, httpx.HTTPError)`
3. Add logging for caught exceptions
4. Verify tests still pass

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Audit except blocks | Not Started | | |
| 1.2 | Update all 4 tool functions | Not Started | | |
| 1.3 | Run tests | Not Started | | |

## Progress Log

## Definition of Done
- All 4 catch blocks use (APIError, httpx.HTTPError)
- Tests pass
