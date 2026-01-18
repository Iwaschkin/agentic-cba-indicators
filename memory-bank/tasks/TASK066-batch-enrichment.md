# [TASK066] - Create enrich_dois_batch() function

**Status:** Not Started
**Added:** 2026-01-18
**Updated:** 2026-01-18

## Original Request
Create batch enrichment function combining CrossRef + Unpaywall APIs.

## Thought Process
- Combine both APIs in single batch operation
- Rate limit: 0.1s delay between DOIs
- Progress logging every 10 DOIs
- Return stats tuple for reporting
- Support preview_only mode for --preview-oa flag

## Implementation Plan
1. Create enrich_dois_batch() function in ingest_excel.py
2. Iterate unique DOIs, call both APIs
3. Add rate limiting and progress logging
4. Return (crossref_found, unpaywall_found, total_enriched)

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 66.1 | Create enrich_dois_batch() function | Complete | 2026-01-18 | Dual-API enrichment with rate limiting |
| 66.2 | Implement dual-API call loop | Complete | 2026-01-18 | CrossRef then Unpaywall per DOI |
| 66.3 | Add rate limiting | Complete | 2026-01-18 | 0.1s delay between DOIs |
| 66.4 | Add progress logging | Complete | 2026-01-18 | Log every 10 DOIs |
| 66.5 | Integrate into ingest() | Complete | 2026-01-18 | Called from preview functions |

## Progress Log
### 2026-01-18
- Task created from plan-unpaywall-crossref-enrichment.md analysis
- Created enrich_dois_batch() function with preview_only parameter
- Returns tuple: (crossref_found, unpaywall_found, total_enriched)
- Implements 0.1s rate limiting via time.sleep()
- Progress logging every 10 DOIs or on first/last
- Handles unique DOI deduplication
- Updated enrich_citations() to use batch function
- Syntax validated with py_compile
- ✅ Phase 4 TASK066 complete
