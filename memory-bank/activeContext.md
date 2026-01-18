# Active Context

## Current Focus
**BUG FIXES COMPLETE** - DOI regex pattern and enrichment batch processing verified.

## Recent Changes (2026-01-18)

### Bug Fix: DOI Regex Truncation ✅
- **Problem**: DOI regex pattern `[^\s\]\)]+` was stopping at first `)` or `]` character
- **Impact**: Truncated valid DOIs in older Elsevier and J. Vegetation Science formats
  - `10.1016/0011-7471(64)90001-4` → was extracted as `10.1016/0011-7471(64`
  - `10.1658/1100-9233(2007)18[315:AOMETS]2.0.CO;2` → was truncated at `(`
- **Fix**: Changed pattern to `[^\s<>]+` (only exclude whitespace and angle brackets)
- **Added**: Trailing punctuation stripping (`.`, `,`, `;`, `:`) in normalize_doi() and extract_doi_from_text()
- **Tests**: Added 8 regression tests for parentheses/brackets/trailing punctuation

### Bug Fix: enrich_dois_batch API Calls (Prior Session) ✅
- **Problem**: `--enrich-citations` was calling `enrich_dois_batch(preview_only=True)` which skipped all API calls
- **Fix**: Renamed parameter to `skip_mutation`, always call APIs (only mutation is conditional)
- **Verified**: Both `skip_mutation=True` and `skip_mutation=False` work correctly

## Test Status
**All 220 tests passing** (8 new regression tests added)

## Validation Results
- Citation extraction: 1153 total, 991 with DOI (85.9%)
- CrossRef API: 90.6% success rate (125/138 unique DOIs)
- Unpaywall API: 90.6% success rate
- OA coverage: 40.2% (463/1153 citations)
- Previously failing DOI `10.1016/0011-7471(64)90001-4` now resolves in CrossRef ✅

## Next Steps
1. Commit DOI regex fix with descriptive message
2. Consider KB rebuild to pick up previously truncated DOIs
3. Continue with any remaining enhancements from plan documents
