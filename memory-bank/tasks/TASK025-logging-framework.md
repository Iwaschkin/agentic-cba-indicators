# [TASK025] - Add Logging Framework

**Status:** Completed
**Added:** 2025-01-17
**Updated:** 2025-01-18
**Priority:** P2 - Medium
**Phase:** 7

## Original Request
Address P2-06: No logging framework - print statements and no debug/info/warning levels.

## Thought Process
The codebase lacks structured logging:
- Uses print statements for output
- No log levels (debug, info, warning, error)
- No log formatting or destinations
- Difficult to diagnose issues in production

Solution: Add Python's standard `logging` module with appropriate configuration.
Note: Most print statements should REMAIN as prints - they're intentional CLI UI output.
Logging added for debugging retry/error paths that aren't user-facing.

## Implementation Plan
- [x] Set up logging configuration in cli.py
- [x] Create logger instances in each module
- [x] Add logging to retry/error paths
- [x] Add appropriate log levels
- [x] Configure log format (timestamp, level, module)

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 25.1 | Create logging_config.py module | Complete | 2025-01-18 | get_logger(), setup_logging(), set_log_level() |
| 25.2 | Add logging to _http.py | Complete | 2025-01-18 | Retry debug logging for rate limit, server error, timeout |
| 25.3 | Add logging to _embedding.py | Complete | 2025-01-18 | Retry debug logging, batch fallback logging |
| 25.4 | Add logging to knowledge_base.py | Complete | 2025-01-18 | ChromaDB retry debug logging |
| 25.5 | Decide on print statements | Complete | 2025-01-18 | Keep as CLI UI output (not converted) |

## Progress Log
### 2025-01-17
- Task created from code review finding P2-06
- Assigned to Phase 7 (Observability)

### 2025-01-18
- Created logging_config.py with:
  - get_logger(name) - get a logger instance
  - setup_logging() - configure at entry point
  - set_log_level() - runtime level change
  - AGENTIC_CBA_LOG_LEVEL env var support
- Added debug logging to _http.py for all retry paths
- Added debug logging to _embedding.py for timeout/server retries and batch fallback
- Added debug logging to knowledge_base.py for ChromaDB client/collection retries
- Analyzed print statements - kept as intentional CLI UI output
- All 35 tests pass

## Acceptance Criteria
- [x] Logging framework configured (logging_config.py)
- [x] Appropriate log levels used (DEBUG for retries)
- [x] Print statements analyzed (kept as CLI output)
- [x] Log format includes timestamp and level (verbose mode)
- [x] AGENTIC_CBA_LOG_LEVEL env var documented

## Files Modified
- Created: `src/agentic_cba_indicators/logging_config.py`
- Modified: `src/agentic_cba_indicators/tools/_http.py`
- Modified: `src/agentic_cba_indicators/tools/_embedding.py`
- Modified: `src/agentic_cba_indicators/tools/knowledge_base.py`
