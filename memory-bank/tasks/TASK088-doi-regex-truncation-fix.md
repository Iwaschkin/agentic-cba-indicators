# [TASK088] - DOI Regex Truncation Fix

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18

## Original Request
Fix DOI regex pattern that was truncating valid DOIs containing parentheses and brackets.

## Problem Description
The DOI regex pattern `[^\s\]\)]+` stopped at the first `)` or `]` character, which incorrectly truncated valid DOIs in older journal formats:

**Affected DOIs:**
- `10.1016/0011-7471(64)90001-4` → extracted as `10.1016/0011-7471(64`
- `10.1016/0167-7012(94)00076-X` → extracted as `10.1016/0167-7012(94`
- `10.1016/s1002-0160(18)60017-9` → extracted as `10.1016/s1002-0160(18`
- `10.1658/1100-9233(2007)18[315:AOMETS]2.0.CO;2` → extracted as `10.1658/1100-9233(2007`
- `10.5091/plecevo.2011.472.` → trailing dot not stripped

## Implementation

### Changes Made

1. **scripts/ingest_excel.py - DOI_PATTERN**
   - Changed from: `(10\.\d{4,}/[^\s\]\)]+)`
   - Changed to: `(10\.\d{4,}/[^\s<>]+)`
   - Only excludes whitespace and angle brackets (for HTML context)

2. **scripts/ingest_excel.py - normalize_doi()**
   - Added: `doi = match.group(1).rstrip(".,;:")` to strip trailing punctuation

3. **scripts/ingest_excel.py - extract_doi_from_text()**
   - Added: `return match.group(1).rstrip(".,;:").lower()` to strip trailing punctuation

4. **tests/test_citation_normalization.py**
   - Added 8 regression tests for:
     - Old Elsevier format with parentheses (3 tests)
     - J. Vegetation Science format with brackets (1 test)
     - Trailing punctuation stripping (4 tests)

## Verification

- All 220 tests pass ✅
- Pyright: 0 errors ✅
- Previously failing DOI `10.1016/0011-7471(64)90001-4` now resolves in CrossRef ✅
- Citation preview still shows 85.9% DOI extraction rate

## Progress Log
### 2026-01-18
- Identified bug via systematic edge case testing
- Created test script to compare regex patterns
- Fixed DOI_PATTERN to allow parentheses and brackets
- Added trailing punctuation stripping to normalize_doi() and extract_doi_from_text()
- Added 8 regression tests
- Verified fix against CrossRef API
- All 220 tests pass
