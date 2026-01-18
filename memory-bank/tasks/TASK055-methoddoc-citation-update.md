# [TASK055] - Update MethodDoc for Citation Type

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Update MethodDoc to use list[Citation] instead of list[str].

## Mapped Issues
- CN-10: Update `MethodDoc.citations` type from `list[str]` to `list[Citation]`
- CN-11: Update `MethodDoc.to_text()` to use `to_embed_string()`
- CN-12: Add `MethodDoc.to_display_text()` method

## Implementation Plan
1. Change citations type annotation to list[Citation]
2. Update to_text() to call c.to_embed_string() for each citation
3. Add to_display_text() method using c.to_display_string()

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 55.1 | Update citations type | Complete | 2026-01-17 | list[str] → list[Citation] |
| 55.2 | Update to_text() | Complete | 2026-01-17 | Uses to_embed_string() |
| 55.3 | Add to_display_text() | Complete | 2026-01-17 | New method with URLs |

## Progress Log
### 2026-01-17
- Task created from citation normalization strategy
- Depends on TASK054 (Citation dataclass)
- Updated MethodDoc.citations type annotation
- Modified to_text() for embeddings (no URLs)
- Added to_display_text() for user output (with URLs)

## Definition of Done
- [ ] MethodDoc.citations is list[Citation]
- [ ] to_text() uses embed format (no URLs)
- [ ] to_display_text() includes URLs for display
