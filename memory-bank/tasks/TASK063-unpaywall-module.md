# [TASK063] - Create _unpaywall.py module

**Status:** Not Started
**Added:** 2026-01-18
**Updated:** 2026-01-18

## Original Request
Create new module for Unpaywall API integration with metadata dataclass and fetch function.

## Thought Process
- Unpaywall provides Open Access status and PDF URLs for DOIs
- API: https://api.unpaywall.org/v2/{doi}?email={email}
- Need dataclass for OA metadata fields
- Error handling for 404, 429, network errors critical
- Should return None on errors, not fail ingestion

## Implementation Plan
1. Create src/agentic_cba_indicators/tools/_unpaywall.py
2. Define UnpaywallMetadata dataclass
3. Implement fetch_unpaywall_metadata() function
4. Add error handling, timeout, logging

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 63.1 | Create _unpaywall.py file structure | Complete | 2026-01-18 | Module docstring, imports |
| 63.2 | Define UnpaywallMetadata dataclass | Complete | 2026-01-18 | 7 fields: doi, is_oa, oa_status, pdf_url, license, version, host_type |
| 63.3 | Implement fetch_unpaywall_metadata() | Complete | 2026-01-18 | HTTP call with error handling |
| 63.4 | Add logging and timeout handling | Complete | 2026-01-18 | Debug logs, 10s timeout, 404/429 handling |

## Progress Log
### 2026-01-18
- Task created from plan-unpaywall-crossref-enrichment.md analysis
- Created src/agentic_cba_indicators/tools/_unpaywall.py
- Defined UnpaywallMetadata dataclass with all OA fields
- Implemented fetch_unpaywall_metadata() with email from get_api_key("unpaywall")
- Added error handling for 404 (not found), 429 (rate limit), timeout, general errors
- Added _parse_unpaywall_response() helper for clean data extraction
- All errors return None (don't fail ingestion)
- Syntax validated with py_compile
- ✅ Phase 2 complete
