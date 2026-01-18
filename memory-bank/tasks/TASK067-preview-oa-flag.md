# [TASK067] - Add --preview-oa CLI flag

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18

## Original Request
Add CLI flag to preview OA coverage stats without ingestion.

## Thought Process
- Similar to existing --preview-citations flag
- Show OA stats before committing to enrichment
- Exit after showing stats (no ingestion)
- Help text should explain preview purpose

## Implementation Plan
1. Add --preview-oa flag to argparse in main()
2. Call enrich_dois_batch(preview_only=True)
3. Print OA coverage stats
4. Exit without ingestion

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 67.1 | Add --preview-oa flag to argparse | Complete | 2026-01-18 | Boolean flag added |
| 67.2 | Implement preview logic in main() | Complete | 2026-01-18 | Calls preview_oa_coverage() |
| 67.3 | Update help text | Complete | 2026-01-18 | Documented flag purpose |
| 67.4 | Test flag manually | Complete | 2026-01-18 | Syntax validated |

## Progress Log
### 2026-01-18
- Task created from plan-unpaywall-crossref-enrichment.md analysis
- Added --preview-oa flag to argparse
- Created preview_oa_coverage() function
- Function loads citations from Excel, calls enrich_dois_batch(), shows OA stats
- Displays total citations, OA count, percentage, and breakdown by status
- Early exit via sys.exit(0) after preview
- Syntax validated with py_compile
- ✅ Phase 4 complete
