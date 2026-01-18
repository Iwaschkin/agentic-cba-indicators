# [TASK104] - Basic Metrics Collection

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18
**Phase:** 2 - Observability Core
**Priority:** P0
**Issue ID:** P1-008

## Original Request
Implement metrics collection for tool invocations including call counts and latency histograms.

## Thought Process
Currently there's no visibility into tool performance. We need:
- Tool call counter (by tool name, success/failure)
- Latency histogram (by tool name)
- Simple in-memory implementation (no external dependencies)
- Optional: OpenTelemetry export

## Implementation Plan
1. ✅ Create src/agentic_cba_indicators/observability.py
2. ✅ Implement MetricsCollector class with counters and histograms
3. ✅ Create @instrument_tool decorator
4. ✅ Add get_metrics() function to retrieve current metrics
5. ✅ Add unit tests

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 4.1 | Create observability.py module | Complete | 2026-01-18 | 280 lines |
| 4.2 | Implement MetricsCollector class | Complete | 2026-01-18 | Thread-safe with Lock |
| 4.3 | Create @instrument_tool decorator | Complete | 2026-01-18 | Records latency and success |
| 4.4 | Add get_metrics() function | Complete | 2026-01-18 | Singleton pattern |
| 4.5 | Add unit tests for metrics | Complete | 2026-01-18 | 25 tests |

## Progress Log
### 2026-01-18
- Task created from code review finding P1-008
- Created src/agentic_cba_indicators/observability.py with:
  - ToolMetrics dataclass with percentile calculations
  - MetricsCollector class (thread-safe with threading.Lock)
  - Bounded latency samples (MAX_LATENCY_SAMPLES = 10000)
  - get_metrics() singleton function
  - reset_metrics() for testing
  - @instrument_tool decorator
  - get_metrics_summary() convenience function
- Created tests/test_observability.py with 25 tests:
  - ToolMetrics tests (7)
  - MetricsCollector tests (10)
  - Thread safety tests (1)
  - Decorator tests (5)
  - Global metrics tests (3)
- All 259 tests pass (234 existing + 25 new)
- Marked task as COMPLETED

## Definition of Done
- [x] Tool call counter working
- [x] Latency histogram working
- [x] Decorator can instrument any tool
- [x] Tests verify metric collection
