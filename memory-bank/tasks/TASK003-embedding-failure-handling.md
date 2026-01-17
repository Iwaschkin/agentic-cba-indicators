# TASK003 - Improve ingestion embedding failure handling

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Prevent silent embedding failures and add strict/skip behavior with reporting.

## Thought Process
Zero-vector fallbacks hide data integrity issues and degrade retrieval quality. Fail-fast or explicit skips improve observability and correctness.

## Implementation Plan
- Add strict mode to abort on embedding failure
- Track and report failed documents
- Skip upsert for failed embeddings in non-strict mode

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 3.1 | Add strict/skip embedding behavior | Complete | 2026-01-17 | Added strict flag and skip logic |
| 3.2 | Emit embedding failure summary | Complete | 2026-01-17 | Added error summaries for failures |
| 3.3 | Update ingestion docs/flags | Complete | 2026-01-17 | Added --strict flag to CLIs |

## Progress Log
### 2026-01-17
- Task created
- Added strict embedding failure handling with skip behavior
- Added embedding failure summaries and error reporting
- Added --strict flags to ingestion CLIs
