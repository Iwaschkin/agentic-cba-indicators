# [TASK113] - Tool Output Truncation

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18
**Phase:** 5 - Performance Optimization
**Priority:** P2
**Issue ID:** P3-003

## Original Request
Add output length limits to prevent very long tool outputs from exceeding context limits.

## Thought Process
Some tools (e.g., export_indicator_selection) can produce very long outputs that may exceed LLM context limits. Need to truncate with clear indicator.

## Implementation Plan
1. Add MAX_TOOL_OUTPUT_LENGTH = 50000 constant
2. Create truncate_output(text, max_len) utility function
3. Apply to export_indicator_selection()
4. Apply to other long-output tools as needed
5. Add unit test

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 13.1 | Add MAX_TOOL_OUTPUT_LENGTH constant | Complete | 2026-01-18 | Added to security.py |
| 13.2 | Create truncate_tool_output() function | Complete | 2026-01-18 | Returns (text, was_truncated) |
| 13.3 | Apply to export_indicator_selection | Complete | 2026-01-18 | Truncation applied |
| 13.4 | Apply to get_indicator_details | Complete | 2026-01-18 | Truncation applied |
| 13.5 | Add unit tests | Complete | 2026-01-18 | 9 tests added |

## Progress Log
### 2026-01-18
- Task created from code review finding P3-003

### 2026-01-18 (Session 2)
- Added to `src/agentic_cba_indicators/security.py`:
  - `MAX_TOOL_OUTPUT_LENGTH = 50000` (chars, ~12500 tokens)
  - `TRUNCATION_SUFFIX = "\n\n...(output truncated)"`
  - `truncate_tool_output(text, max_length, suffix)` function returning (text, was_truncated)
- Applied truncation to `knowledge_base.py`:
  - `export_indicator_selection()` - generates markdown reports for up to 20 indicators
  - `get_indicator_details()` - returns indicator with all methods
- Added 9 tests in `tests/test_security.py`:
  - TestTruncateToolOutput (8 tests): short/long output, custom suffix, empty, exact limit
  - TestToolOutputConstants (2 tests): reasonable limits, suffix defined
- All 435 tests pass (426 + 9 new)

## Implementation Details

### Added to security.py
```python
MAX_TOOL_OUTPUT_LENGTH: Final[int] = 50000  # ~12500 tokens
TRUNCATION_SUFFIX: Final[str] = "\n\n...(output truncated)"

def truncate_tool_output(
    text: str,
    max_length: int = MAX_TOOL_OUTPUT_LENGTH,
    suffix: str = TRUNCATION_SUFFIX,
) -> tuple[str, bool]:
    """Truncate tool output to prevent context overflow."""
```

### Usage in Tools
```python
from agentic_cba_indicators.security import truncate_tool_output

result = "\n".join(output)
truncated_result, _ = truncate_tool_output(result)
return truncated_result
```

## Definition of Done
- [x] Output truncated at max length
- [x] Truncation suffix "...(truncated)" added
- [x] Test verifies truncation
- [x] Applied to long-output tools
