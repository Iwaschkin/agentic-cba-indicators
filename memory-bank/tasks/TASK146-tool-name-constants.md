# [TASK146] - Add Tool Name Constants

**Status:** Pending
**Added:** 2026-01-21
**Updated:** 2026-01-21

## Original Request
Add `REDUCED_TOOL_NAMES` and `FULL_TOOL_NAMES` constants to `tools/__init__.py`.

## Thought Process
- MCPClient needs tool names for `tool_filters.allowed` in reduced mode
- Constants derived from tool tuples after help tool removal
- Exported via `__all__` for CLI/UI access

## Implementation Plan
- [ ] Add REDUCED_TOOL_NAMES list
- [ ] Add FULL_TOOL_NAMES list
- [ ] Add to __all__ exports

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Add REDUCED_TOOL_NAMES | Not Started | 2026-01-21 | |
| 1.2 | Add FULL_TOOL_NAMES | Not Started | 2026-01-21 | |
| 1.3 | Update __all__ | Not Started | 2026-01-21 | |

## Progress Log
### 2026-01-21
- Task created as part of MCP Server Migration plan
- Mapped to Issue ID: MCP-06
