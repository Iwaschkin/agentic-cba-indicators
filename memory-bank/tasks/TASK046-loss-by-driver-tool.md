# [TASK046] - Implement Loss by Driver Tool

**Status:** Pending
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Implement `get_tree_cover_loss_by_driver()` to show deforestation causes.

## Thought Process
Uses GFW Beta Land API (`/v0/land/tree_cover_loss_by_driver`). Provides breakdown by driver: commodity, shifting agriculture, forestry, wildfire, urbanization.

## Implementation Plan
- Call Beta Land API with country code and threshold
- Parse driver categories from response
- Calculate percentages and identify dominant driver
- Format output with breakdown

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 46.1 | Implement Beta Land API call | Not Started | | |
| 46.2 | Parse driver categories | Not Started | | |
| 46.3 | Calculate percentages | Not Started | | |
| 46.4 | Format output string | Not Started | | |

## Progress Log
### 2026-01-17
- Task created as part of GFW forestry tools implementation plan
