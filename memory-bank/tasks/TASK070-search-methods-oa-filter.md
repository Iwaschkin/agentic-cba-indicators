# [TASK070] - Add oa_only filter to search_methods()

**Status:** Not Started
**Added:** 2026-01-18
**Updated:** 2026-01-18

## Original Request
Add parameter to filter search_methods() results to only indicators with OA citations.

## Thought Process
- Users may want to prioritize indicators with freely available methods
- Filter via ChromaDB where clause: has_oa_citations=True
- Maintain existing search behavior when oa_only=False
- Update docstring to document new parameter

## Implementation Plan
1. Add oa_only parameter to search_methods()
2. Add where clause filter when oa_only=True
3. Update tool docstring
4. Test filtering behavior

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 70.1 | Add oa_only parameter | Not Started | - | Default False for backward compatibility |
| 70.2 | Implement where clause filtering | Not Started | - | where={"has_oa_citations": True} |
| 70.3 | Update docstring | Not Started | - | Document filtering behavior |
| 70.4 | Test with/without filter | Not Started | - | Validate result counts |

## Progress Log
### 2026-01-18
- Task created from plan-unpaywall-crossref-enrichment.md analysis
