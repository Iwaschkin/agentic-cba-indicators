# [TASK021] - Consolidate Embedding Functions

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-17
**Priority:** P2 - Medium
**Phase:** 5

## Original Request
Address P2-10: Embedding helper duplicated across knowledge_base.py and ingest scripts.

## Thought Process
Embedding functions were duplicated in three locations:
- `tools/knowledge_base.py` - _get_embedding() for single text, with retry/validation
- `scripts/ingest_excel.py` - get_embeddings_batch() for batch embedding
- `scripts/ingest_usecases.py` - get_embeddings_batch() for batch embedding

Additionally, TLS validation and header functions were duplicated.

Solution: Create a shared `_embedding.py` module in tools/ with all embedding functionality:
1. `get_embedding()` - Single text with rate limiting, retry, validation
2. `get_embeddings_batch()` - Batch embedding with truncation and fallback
3. TLS validation and headers

## Implementation Plan
- [x] Create tools/_embedding.py with shared functions
- [x] Update knowledge_base.py to import from _embedding.py
- [x] Update ingest_excel.py to import from _embedding.py
- [x] Update ingest_usecases.py to import from _embedding.py
- [x] Remove duplicate implementations
- [x] Verify tests pass

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 21.1 | Create _embedding.py module | Complete | 2025-01-17 | ~230 lines with both functions |
| 21.2 | Update knowledge_base.py | Complete | 2025-01-17 | Removed ~140 lines of duplicate code |
| 21.3 | Update ingest_excel.py | Complete | 2025-01-17 | Removed ~50 lines of duplicate code |
| 21.4 | Update ingest_usecases.py | Complete | 2025-01-17 | Removed ~60 lines of duplicate code |
| 21.5 | Verify tests | Complete | 2025-01-17 | All 35 tests pass |

## Progress Log
### 2025-01-17
- Task created from code review finding P2-10
- Created `src/agentic_cba_indicators/tools/_embedding.py`:
  - EmbeddingError exception
  - _validate_ollama_tls() for TLS validation
  - _get_ollama_headers() for auth headers
  - get_embedding() for single text (with rate limiting, retry, validation)
  - get_embeddings_batch() for batch embedding (with truncation, fallback)
- Updated knowledge_base.py to import from _embedding.py
- Removed duplicate code from knowledge_base.py (~140 lines)
- Updated ingest_excel.py to import get_embeddings_batch
- Removed TLS/headers/batch functions from ingest_excel.py (~50 lines)
- Updated ingest_usecases.py to import get_embeddings_batch
- Removed TLS/headers/batch functions from ingest_usecases.py (~60 lines)
- All 35 tests passing
- Task complete

## Acceptance Criteria
- [x] Single embedding function implementation in _embedding.py
- [x] All files import from shared location
- [x] No duplicate implementations
- [x] Tests verify embedding functionality
