# [TASK032] - Update Placeholder URLs

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-18
**Priority:** P3 - Low
**Phase:** 9

## Original Request
Address P3-04: Placeholder or commented URLs that may be outdated.

## Thought Process
Searched for URLs in the codebase:
- Most URLs are legitimate API endpoints (Open-Meteo, World Bank, GBIF, FAO, etc.)
- Found example.com URLs only in test files (intentional for testing)
- Found `yourusername` placeholder URLs in pyproject.toml [project.urls]

Solution: Comment out the placeholder URLs in pyproject.toml with a note to update when publishing.

## Implementation Plan
- [x] Audit all URLs in code and comments
- [x] Verify URLs are accessible (API endpoints are live)
- [x] Update or remove broken links (commented out placeholders)
- [x] Document any required manual verification

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 32.1 | Find all URLs in codebase | Complete | 2025-01-18 | Grep search for URLs |
| 32.2 | Verify URL accessibility | Complete | 2025-01-18 | All API URLs are live |
| 32.3 | Update broken links | Complete | 2025-01-18 | Commented out pyproject.toml placeholders |
| 32.4 | Document findings | Complete | 2025-01-18 | Added NOTE comment |

## Progress Log
### 2025-01-17
- Task created from code review finding P3-04
- Assigned to Phase 9 (Code Cleanup)

### 2025-01-18
- Searched for URLs: found ~30 in src/, mostly API endpoints
- Searched for placeholders: found `yourusername` in pyproject.toml
- Commented out [project.urls] section with NOTE to update when publishing
- All test URLs (example.com) are intentional for testing
- All 35 tests pass

## Acceptance Criteria
- [x] All URLs verified (API endpoints are live services)
- [x] Broken links updated or removed (placeholders commented out)
- [x] Documentation accurate (NOTE added)

## Files Modified
- `pyproject.toml` - Commented out [project.urls] with NOTE
