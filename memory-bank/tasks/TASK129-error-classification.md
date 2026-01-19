# TASK129 - Add Tool Error Classification

**Status:** Completed
**Priority:** P3
**Phase:** 3 - Medium Priority
**Added:** 2026-01-19
**Updated:** 2026-01-19

## Original Request

From Code Review v2 Action Plan: Enhance error categorization to distinguish transient vs permanent tool failures.

## Thought Process

Currently tools return error strings or raise exceptions without classification. A standard error classification would enable smarter retry decisions and clearer diagnostics.

We should:
1. Define error categories (transient, permanent, validation, rate-limit)
2. Add an error type or structured error payload
3. Integrate with logging/audit output
4. Keep user-facing output simple

## Implementation Plan

- [x] 3.1 Define error categories and mapping
- [x] 3.2 Add helper for classification (e.g., in _http or security)
- [x] 3.3 Update tools to include category in errors
- [x] 3.4 Update tests for classification

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 3.1 | Define categories | Complete | 2026-01-19 | ErrorCategory enum added |
| 3.2 | Add classification helper | Complete | 2026-01-19 | classify_error() in _http.py |
| 3.3 | Update tool errors | Complete | 2026-01-19 | format_error includes category |
| 3.4 | Add tests | Complete | 2026-01-19 | test_http classification tests |

## Acceptance Criteria

- [x] Error categories defined and documented
- [x] Tools return classified errors (internally)
- [x] Tests cover classification

## Definition of Done

- Classification implemented
- Tests updated

## Progress Log

### 2026-01-19
- Task created from Code Review v2 Action Plan
### 2026-01-19
- Added ErrorCategory and classify_error().
- Updated format_error to include category.
- Added classification tests.
