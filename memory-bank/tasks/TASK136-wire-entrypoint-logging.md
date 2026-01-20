# TASK136 - Wire Entry Point Logging Setup

**Status:** Completed
**Added:** 2026-01-20
**Updated:** 2026-01-20
**Priority:** P1
**Phase:** Phase 3 - Observability Wiring

## Original Request
Call `setup_logging()` in CLI and UI entry points so configured logging is active.

## Thought Process
Logging configuration is implemented but not invoked at entry points, leaving JSON formatting and correlation IDs inactive.

## Implementation Plan
- Call `setup_logging()` early in CLI `main()`.
- Call `setup_logging()` early in UI `main()`.
- Add tests verifying log format env var works.

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 136.1 | Wire CLI logging setup | Complete | 2026-01-20 | Add `setup_logging()` |
| 136.2 | Wire UI logging setup | Complete | 2026-01-20 | Add `setup_logging()` |
| 136.3 | Add logging setup test | Complete | 2026-01-20 | Env-var based format |

## Progress Log
### 2026-01-20
- Task created from code review CR-0006.
- Added `setup_logging()` to CLI and UI entry points.
- Added CLI wiring test for logging setup invocation.
