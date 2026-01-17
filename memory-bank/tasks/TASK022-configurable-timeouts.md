# [TASK022] - Extract Hardcoded Timeouts to Config

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-17
**Priority:** P2 - Medium
**Phase:** 6

## Original Request
Address P2-03: Hardcoded timeout values (60s, 30s) scattered across multiple files.

## Thought Process
Timeout values were hardcoded in multiple locations:
- `_http.py` - 30s (already a constant, but not configurable)
- `_embedding.py` - 60s for single embedding, 120s for batch embedding
- `commodities.py` - 30s (direct httpx call)

Note: After TASK021 (embedding consolidation), knowledge_base.py and ingest scripts
now use the shared _embedding.py module, so we only need to fix timeouts there.

Solution: Make all timeouts configurable via environment variables with sensible defaults.

## Implementation Plan
- [x] Update _http.py to read timeout from HTTP_TIMEOUT env var
- [x] Update _embedding.py to add OLLAMA_EMBEDDING_TIMEOUT and OLLAMA_BATCH_EMBEDDING_TIMEOUT
- [x] Update commodities.py to use shared _http module
- [x] Verify tests pass

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 22.1 | Make _http.py timeouts configurable | Complete | 2025-01-17 | HTTP_TIMEOUT, HTTP_RETRIES, HTTP_BACKOFF_* |
| 22.2 | Make _embedding.py timeouts configurable | Complete | 2025-01-17 | OLLAMA_EMBEDDING_TIMEOUT, OLLAMA_BATCH_EMBEDDING_TIMEOUT |
| 22.3 | Update commodities.py to use _http | Complete | 2025-01-17 | Uses create_client() with DEFAULT_TIMEOUT |
| 22.4 | Verify tests | Complete | 2025-01-17 | All 35 tests pass |

## Progress Log
### 2025-01-17
- Task created from code review finding P2-03
- Updated `_http.py`:
  - Added `import os`
  - DEFAULT_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "30.0"))
  - DEFAULT_RETRIES = int(os.environ.get("HTTP_RETRIES", "3"))
  - DEFAULT_BACKOFF_BASE = float(os.environ.get("HTTP_BACKOFF_BASE", "1.0"))
  - DEFAULT_BACKOFF_MAX = float(os.environ.get("HTTP_BACKOFF_MAX", "30.0"))
- Updated `_embedding.py`:
  - Added _EMBEDDING_TIMEOUT = float(os.environ.get("OLLAMA_EMBEDDING_TIMEOUT", "60.0"))
  - Added _BATCH_EMBEDDING_TIMEOUT = float(os.environ.get("OLLAMA_BATCH_EMBEDDING_TIMEOUT", "120.0"))
  - Updated get_embedding() to use _EMBEDDING_TIMEOUT
  - Updated get_embeddings_batch() to use _BATCH_EMBEDDING_TIMEOUT
- Updated `commodities.py`:
  - Replaced `import httpx` with `from ._http import DEFAULT_TIMEOUT, create_client`
  - Updated _make_request() to use create_client() with headers
- All 35 tests passing
- Task complete

## Environment Variables Added
| Variable | Default | Description |
|----------|---------|-------------|
| HTTP_TIMEOUT | 30.0 | Default HTTP request timeout (seconds) |
| HTTP_RETRIES | 3 | Default retry count for failed requests |
| HTTP_BACKOFF_BASE | 1.0 | Base delay for exponential backoff (seconds) |
| HTTP_BACKOFF_MAX | 30.0 | Maximum backoff delay (seconds) |
| OLLAMA_EMBEDDING_TIMEOUT | 60.0 | Timeout for single embedding requests |
| OLLAMA_BATCH_EMBEDDING_TIMEOUT | 120.0 | Timeout for batch embedding requests |

## Acceptance Criteria
- [x] All timeout values configurable via environment variables
- [x] Sensible defaults preserved
- [x] No hardcoded timeout values in application code
- [x] Tests pass
