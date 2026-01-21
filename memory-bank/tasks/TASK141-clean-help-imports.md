# [TASK141] - Clean Help Tool Imports

**Status:** Pending
**Added:** 2026-01-21
**Updated:** 2026-01-21

## Original Request
Remove all help tool imports and references from `tools/__init__.py`.

## Thought Process
- After deleting _help.py, all imports from it will fail
- Need to remove from `__all__`, `_REDUCED_TOOLS_RAW`, `_FULL_TOOLS_RAW`
- Tool counts will decrease after removal

## Implementation Plan
- [ ] Remove `._help` imports from tools/__init__.py
- [ ] Remove help tools from `__all__`
- [ ] Remove help tools from `_REDUCED_TOOLS_RAW`
- [ ] Remove help tools from `_FULL_TOOLS_RAW`

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Remove imports from ._help | Not Started | 2026-01-21 | |
| 1.2 | Update __all__ list | Not Started | 2026-01-21 | |
| 1.3 | Update _REDUCED_TOOLS_RAW | Not Started | 2026-01-21 | |
| 1.4 | Update _FULL_TOOLS_RAW | Not Started | 2026-01-21 | |

## Progress Log
### 2026-01-21
- Task created as part of MCP Server Migration plan
- Mapped to Issue ID: MCP-03
