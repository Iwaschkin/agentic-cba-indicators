# [TASK056] - Integrate Citations into Pipeline

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Wire new citation handling into the ingestion pipeline.

## Mapped Issues
- CN-13: Update `extract_citations()` to return `list[Citation]`
- CN-14: Update `MethodsGroupDoc.to_document_text()` for new format

## Implementation Plan
1. Update extract_citations() to use Citation.from_raw()
2. Handle spillover columns with Citation.from_raw()
3. Ensure MethodsGroupDoc.to_document_text() works with new format

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 56.1 | Update extract_citations() | Complete | 2026-01-17 | Returns list[Citation] |
| 56.2 | Handle spillover columns | Complete | 2026-01-17 | Unnamed: 32, 33 handled |
| 56.3 | Verify grouped doc text | Complete | 2026-01-17 | Uses method.to_text() |

## Progress Log
### 2026-01-17
- Task created from citation normalization strategy
- Depends on TASK055 (MethodDoc update)
- Updated extract_citations() to return list[Citation]
- All spillover columns handled via Citation.from_raw()
- KB rebuild validates pipeline integration

## Definition of Done
- [x] extract_citations() returns list[Citation]
- [x] Spillover columns handled correctly
- [x] MethodsGroupDoc text generation works
