# TASK007 - Move pyright to dev dependencies only

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Remove pyright from runtime dependencies and move to dev-only.

## Thought Process
Runtime dependency footprint should be minimal; tooling belongs in dev extras.

## Implementation Plan
- Move pyright from dependencies to dev group in pyproject.toml
- Validate dependency groups

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 7.1 | Update pyproject dependencies | Complete | 2026-01-17 | Moved pyright to dev extras |

## Progress Log
### 2026-01-17
- Task created
- Moved pyright from runtime dependencies to dev extras
