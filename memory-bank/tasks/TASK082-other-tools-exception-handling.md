# [TASK082] - Narrow Exception Handling in Remaining Tools

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-19

## Original Request
Replace broad `except Exception as e:` patterns in remaining tool modules (weather, climate, socioeconomic, biodiversity, etc.).

## Mapped Issue
- **Issue ID:** P1-1 (partial)
- **Priority:** P1 (High)
- **Phase:** 1

## Implementation Plan
1. Audit weather.py, climate.py, socioeconomic.py, biodiversity.py, labor.py, gender.py, agriculture.py, commodities.py, soilgrids.py
2. Replace any broad exception handlers with specific exceptions
3. Verify tests still pass

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Audit all remaining tool modules | Not Started | | |
| 1.2 | Update any broad handlers found | Not Started | | |
| 1.3 | Run tests | Not Started | | |

## Progress Log

## Definition of Done
- All tool modules use specific exception handling
- Tests pass
