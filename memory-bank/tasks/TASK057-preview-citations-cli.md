# [TASK057] - Preview Citations CLI Flag

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Add --preview-citations CLI flag to show normalization stats without modifying KB.

## Mapped Issues
- CN-15: Add `--preview-citations` CLI flag for validation

## Implementation Plan
1. Add --preview-citations argument to argparse
2. Create preview_citations() function
3. Show stats: total, with DOI, without DOI, extracted from text
4. Exit early if flag is set (don't modify KB)

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 57.1 | Add argparse argument | Complete | 2026-01-17 | --preview-citations flag |
| 57.2 | Create preview function | Complete | 2026-01-17 | Shows 85.9% DOI rate |
| 57.3 | Early exit logic | Complete | 2026-01-17 | Returns before KB modify |

## Progress Log
### 2026-01-17
- Task created from citation normalization strategy
- Part of Phase 4 implementation
- Implemented preview_citations() function
- Shows total 1153 citations, 991 with DOIs (85.9%)
- Does not modify KB when flag is set

## Definition of Done
- [x] --preview-citations flag works
- [x] Shows total citations, DOI counts
- [x] Does not modify KB when flag is set
