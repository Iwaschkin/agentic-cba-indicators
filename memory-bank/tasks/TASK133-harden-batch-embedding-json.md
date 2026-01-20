# TASK133 - Harden Batch Embedding JSON Parsing

**Status:** Completed
**Added:** 2026-01-20
**Updated:** 2026-01-20
**Priority:** P1
**Phase:** Phase 2 - Embedding Resilience

## Original Request
Protect batch embedding against malformed JSON responses and ensure fallback behavior.

## Thought Process
`get_embeddings_batch()` calls `response.json()` without error handling. Malformed JSON causes ingestion failures without fallback.

## Implementation Plan
- Add JSON decode handling in batch embedding path.
- Fallback to individual embedding or safe None returns when non-strict.
- Add a unit test for malformed JSON.

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 133.1 | Add JSON decode guard in batch path | Complete | 2026-01-20 | Handle JSON errors safely |
| 133.2 | Add fallback behavior | Complete | 2026-01-20 | Individual embedding fallback |
| 133.3 | Add unit test | Complete | 2026-01-20 | Invalid JSON response |

## Progress Log
### 2026-01-20
- Task created from code review CR-0003.
- Added JSON decode handling and fallback in batch embeddings.
- Added test for malformed JSON response fallback.
