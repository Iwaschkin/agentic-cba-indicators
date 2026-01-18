# [TASK089] - enrich_dois_batch API Call Fix

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18

## Original Request
Fix enrich_dois_batch() function which was skipping API calls in certain modes.

## Problem Description
The `--enrich-citations` CLI flag was calling `enrich_dois_batch(citations, preview_only=True)` which had logic that wrapped all API calls inside `if not preview_only:` blocks. This meant:

- `--preview-oa` worked correctly (called with `preview_only=False`)
- `--enrich-citations` skipped ALL API calls (showed 0% enrichment)

## Root Cause
```python
# Old code
if not preview_only:
    cf_meta = fetch_crossref_metadata(doi)  # Skipped when preview_only=True!
    if cf_meta:
        ...
```

The intent was to preview without mutating Citation objects, but the implementation skipped the API calls entirely.

## Implementation

### Changes Made

1. **scripts/ingest_excel.py - enrich_dois_batch()**
   - Renamed parameter: `preview_only` → `skip_mutation`
   - Moved API calls outside conditional (always fetch)
   - Only mutation is conditional on `skip_mutation`

```python
# New code
cf_meta = fetch_crossref_metadata(doi)  # Always call API
if cf_meta:
    crossref_found += 1
    if not skip_mutation:  # Only mutation is conditional
        for cite in doi_to_citations[doi]:
            cite.enrich_from_crossref(cf_meta)
```

2. **scripts/ingest_excel.py - preview_oa_coverage()**
   - Updated call: `enrich_dois_batch(citations, skip_mutation=True)`

3. **scripts/ingest_excel.py - enrich_citations()**
   - Updated call: `enrich_dois_batch(all_citations, skip_mutation=False)`

## Verification

- Tested `skip_mutation=False`: Citations properly enriched ✅
- Tested `skip_mutation=True`: APIs called but citations not modified ✅
- `--enrich-citations --limit 20` now shows 92.3% enrichment (was 0%)
- All 220 tests pass ✅

## Progress Log
### 2026-01-18
- Discovered bug during validation of citation enrichment
- Traced issue to `preview_only` parameter logic
- Refactored to `skip_mutation` with clear semantics
- Verified both modes work correctly via manual testing
- All tests pass
