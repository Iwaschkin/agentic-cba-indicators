# [TASK083] - Add PDF Text Length Limit

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-19

## Original Request
Add explicit text length limits to PDF extraction in ingest_usecases.py to prevent resource exhaustion.

## Mapped Issue
- **Issue ID:** P2-2
- **Priority:** P2 (Medium)
- **Phase:** 2

## Resolution
**Already addressed by existing code:**
1. `extract_pdf_summary()` has 4000-char limit (line 209)
2. `_embedding.py` has `MAX_EMBEDDING_CHARS=6000` truncation (line 63, 240)
3. All text going to embeddings is truncated at 6000 chars automatically
4. The concern about unbounded memory is mitigated by these existing limits

No code changes required - issue was a false positive in the review.
- Test verifies truncation
