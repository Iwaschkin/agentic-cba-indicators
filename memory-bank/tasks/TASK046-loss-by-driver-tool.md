# [TASK046] - Implement Loss by Driver Tool

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-18

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

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 46.1 | Implement Beta Land API call | Complete | 2026-01-18 | GFW driver endpoint queried |
| 46.2 | Parse driver categories | Complete | 2026-01-18 | Driver breakdown parsed |
| 46.3 | Calculate percentages | Complete | 2026-01-18 | Percentages computed |
| 46.4 | Format output string | Complete | 2026-01-18 | Output includes dominant driver |

## Progress Log
### 2026-01-17
- Task created as part of GFW forestry tools implementation plan
### 2026-01-18
- Implemented get_tree_cover_loss_by_driver() tool
