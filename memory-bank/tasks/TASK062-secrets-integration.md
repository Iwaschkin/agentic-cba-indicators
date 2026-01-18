# [TASK062] - Migrate CrossRef to secrets and add Unpaywall

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18

## Original Request
Migrate CrossRef API from os.environ.get() to centralized secrets system and add Unpaywall API support.

## Thought Process
- CrossRef currently uses os.environ.get("CROSSREF_MAILTO") directly, inconsistent with GFW pattern
- Unpaywall requires email parameter for polite pool access
- Both should use centralized _secrets.py module for consistency
- Environment variable naming: CROSSREF_EMAIL, UNPAYWALL_EMAIL

## Implementation Plan
1. Update SUPPORTED_KEYS in _secrets.py with crossref and unpaywall entries
2. Update _crossref.py to use get_api_key("crossref", required=False)
3. Add .env.example entries for both email variables
4. Test existing CrossRef enrichment still works

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 62.1 | Update SUPPORTED_KEYS in _secrets.py | Complete | 2026-01-18 | Added crossref and unpaywall |
| 62.2 | Update _crossref.py imports and email fetch | Complete | 2026-01-18 | Using get_api_key("crossref") |
| 62.3 | Update .env.example | Complete | 2026-01-18 | Added both email variables |
| 62.4 | Test CrossRef still works | Complete | 2026-01-18 | 10 tests pass |

## Progress Log
### 2026-01-18
- Task created from plan-unpaywall-crossref-enrichment.md analysis
- Added "crossref": "CROSSREF_EMAIL" and "unpaywall": "UNPAYWALL_EMAIL" to SUPPORTED_KEYS
- Updated _crossref.py to use get_api_key("crossref", required=False)
- Removed CROSSREF_MAILTO global variable
- Updated module docstring to reference CROSSREF_EMAIL
- Added citation enrichment section to .env.example
- Validated with test_config.py - all 10 tests pass
- ✅ Phase 1 complete
