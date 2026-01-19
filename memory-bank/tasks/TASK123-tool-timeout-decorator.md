# TASK123 - Add Tool Execution Timeout Decorator

**Status:** Completed
**Priority:** P1
**Phase:** 4 - Resilience
**Added:** 2026-01-19
**Updated:** 2026-01-19

## Original Request

From Code Review v2 Issue PNR-003: External API tools (weather, climate, World Bank) lack execution timeouts, risking agent hangs.

## Thought Process

Current state:
- Tools call external APIs via `fetch_json()` in `_http.py`
- `fetch_json()` has a 10s timeout per request
- But tools can make multiple requests or have retry loops
- No overall timeout per tool execution

Risk: A tool could hang indefinitely if:
1. DNS resolution stalls
2. Connection established but server never responds
3. Infinite retry loop triggered

Solution: Create `@timeout` decorator that wraps tool execution.

Options:
1. `signal.alarm` - UNIX only, not Windows compatible
2. `concurrent.futures.ThreadPoolExecutor` - cross-platform, can timeout
3. `async/await` with timeout - requires async refactor

Option 2 is preferred: cross-platform and minimal code change.

## Implementation Plan

- [x] 4.1 Create `@timeout(seconds)` decorator in `tools/_timeout.py`
- [x] 4.2 Use `ThreadPoolExecutor` with `future.result(timeout=)`
- [x] 4.3 Raise custom `ToolTimeoutError` on timeout
- [x] 4.4 Apply to high-risk tools (weather, climate, socioeconomic)
- [x] 4.5 Add tests for timeout behavior
- [x] 4.6 Document in tools docstrings

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 4.1 | Create timeout decorator | Complete | 2026-01-19 | Added tools/_timeout.py |
| 4.2 | Implement with ThreadPool | Complete | 2026-01-19 | ThreadPoolExecutor + future timeout |
| 4.3 | Define ToolTimeoutError | Complete | 2026-01-19 | Custom exception added |
| 4.4 | Apply to external API tools | Complete | 2026-01-19 | weather/climate/socioeconomic |
| 4.5 | Add timeout tests | Complete | 2026-01-19 | test_tools_timeout.py |
| 4.6 | Document in docstrings | Complete | 2026-01-19 | Module docstrings updated |

## Acceptance Criteria

- [x] `@timeout(30)` decorator exists and works cross-platform
- [x] Applied to weather, climate, socioeconomic tools
- [x] `ToolTimeoutError` raised on timeout with helpful message
- [x] Tests verify timeout behavior

## Definition of Done

- Code merged
- Targeted tests pass via VS Code integration
- External API tools protected

## Progress Log

### 2026-01-19
- Task created from Code Review v2 Issue PNR-003
### 2026-01-19
- Added cross-platform timeout decorator and applied to API tools.
- Added unit tests for timeout behavior.
