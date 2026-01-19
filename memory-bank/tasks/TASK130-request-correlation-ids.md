# TASK130 - Add Request Correlation IDs

**Status:** Completed
**Priority:** P3
**Phase:** 3 - Medium Priority
**Added:** 2026-01-19
**Updated:** 2026-01-19

## Original Request

From Code Review v2 Action Plan: Add request correlation IDs for improved observability.

## Thought Process

Tool calls and HTTP requests are logged but not correlated across a single user request. A correlation ID per user turn (or per tool call) would help trace logs.

We should:
1. Decide scope (per user input or per tool call)
2. Generate IDs at agent entry point
3. Propagate through logging/audit/metrics
4. Update tests for ID presence

## Implementation Plan

- [x] 4.1 Define correlation ID scope and format
- [x] 4.2 Add ID generation in CLI entry or agent loop
- [x] 4.3 Propagate ID into logs/audit
- [x] 4.4 Add tests for ID propagation

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 4.1 | Define ID scope/format | Complete | 2026-01-19 | Per user request (UUID4) |
| 4.2 | Generate ID | Complete | 2026-01-19 | cli.py per-turn ID |
| 4.3 | Propagate to logging | Complete | 2026-01-19 | logging filter + audit session_id |
| 4.4 | Add tests | Complete | 2026-01-19 | test_logging_json + test_audit |

## Acceptance Criteria

- [x] Correlation IDs generated and logged
- [x] Audit entries include correlation ID
- [x] Tests cover propagation

## Definition of Done

- IDs implemented end-to-end
- Tests updated

## Progress Log

### 2026-01-19
- Task created from Code Review v2 Action Plan
### 2026-01-19
- Added correlation ID context and logging filter.
- Wired CLI to set correlation ID per user request.
- Audit logging uses correlation ID when available.
