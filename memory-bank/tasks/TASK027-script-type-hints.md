# [TASK027] - Add Type Hints to Ingestion Scripts

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-18
**Priority:** P2 - Medium
**Phase:** 8

## Original Request
Address P2-09: Missing type hints in ingestion scripts (`ingest_excel.py`, `ingest_usecases.py`).

## Thought Process
Ran pyright on the scripts and found 2 issues per script:
1. `ingest_excel.py`:
   - Missing import of `EMBEDDING_MODEL` constant
   - Type error: `test_emb[0]` could be `None` (from `list[float] | None`)

2. `ingest_usecases.py`:
   - Import `fitz` (pymupdf) not found - optional dependency
   - Same `test_emb[0]` type error

Fixes applied:
- Import `EMBEDDING_MODEL` from `_embedding.py`
- Add null check: `len(test_emb[0]) if test_emb[0] is not None else 0`
- Add `type: ignore[import-not-found]` for optional `fitz` import

## Implementation Plan
- [x] Fix type errors in ingest_excel.py
- [x] Fix type errors in ingest_usecases.py
- [x] Run pyright verification
- [x] Run tests

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 27.1 | Fix ingest_excel.py type errors | Complete | 2025-01-18 | Import EMBEDDING_MODEL, null check |
| 27.2 | Fix ingest_usecases.py type errors | Complete | 2025-01-18 | Type ignore for fitz, null check |
| 27.3 | Run pyright verification | Complete | 2025-01-18 | Both pass cleanly |

## Progress Log
### 2025-01-17
- Task created from code review finding P2-09
- Assigned to Phase 8 (Type Safety)

### 2025-01-18
- Ran pyright on scripts: found 2 errors in each
- Fixed ingest_excel.py: imported EMBEDDING_MODEL, added null check
- Fixed ingest_usecases.py: added type: ignore for fitz, added null check
- Both scripts now pass pyright
- All 35 tests pass

## Acceptance Criteria
- [x] All functions have type hints (already had them)
- [x] pyright passes without errors
- [x] Complex structures typed appropriately

## Files Modified
- `scripts/ingest_excel.py`: Added EMBEDDING_MODEL import, null check for test_emb
- `scripts/ingest_usecases.py`: Type ignore for fitz, null check for test_emb
