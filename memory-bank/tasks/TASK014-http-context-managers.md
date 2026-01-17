# [TASK014] - Use HTTP Client Context Managers

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-17
**Priority:** P1 - High
**Phase:** 3

## Original Request
Address P1-02: HTTP clients created without context managers may leak connections on exceptions.

## Thought Process
Multiple files create `httpx.Client()` instances without using context managers (`with` statements). If exceptions occur during requests, connections may not be properly closed, leading to:
1. Resource exhaustion
2. Connection pool depletion
3. Memory leaks in long-running processes

Files audited:
- `tools/knowledge_base.py` - `_get_embedding()` ✅ Uses context manager
- `tools/_http.py` - `fetch_json()` ✅ Uses try/finally with client.close()
- `tools/commodities.py` - `_make_api_request()` ✅ Uses context manager
- `scripts/ingest_excel.py` - `get_embedding()` ✅ Uses context manager
- `scripts/ingest_usecases.py` - `_get_embedding()` ✅ Uses context manager

## Implementation Plan
- [x] Audit knowledge_base.py - Already correct
- [x] Audit ingest_excel.py - Already correct
- [x] Audit ingest_usecases.py - Already correct
- [x] Audit _http.py - Uses try/finally pattern (correct)
- [x] Audit commodities.py - Already correct

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 14.1 | Audit knowledge_base.py | Complete | 2025-01-17 | Already uses `with httpx.Client()` |
| 14.2 | Audit ingest_excel.py | Complete | 2025-01-17 | Already uses `with httpx.Client()` |
| 14.3 | Audit ingest_usecases.py | Complete | 2025-01-17 | Already uses `with httpx.Client()` |
| 14.4 | Audit _http.py | Complete | 2025-01-17 | Uses try/finally with client.close() |
| 14.5 | Audit commodities.py | Complete | 2025-01-17 | Already uses `with httpx.Client()` |

## Progress Log
### 2025-01-17
- Task created from code review finding P1-02
- Assigned to Phase 3 (Resource Management)
- Audited all files using httpx.Client
- All usages already properly handle cleanup via context managers or try/finally
- This was a false positive - code was already correct
- Task complete (no changes needed)

## Acceptance Criteria
- [x] All httpx.Client usage wrapped in context managers or try/finally
- [x] Connections properly closed on exceptions
- [x] No resource leaks in error paths
