# [TASK143] - Remove UI set_active_tools

**Status:** Pending
**Added:** 2026-01-21
**Updated:** 2026-01-21

## Original Request
Remove the `set_active_tools()` call from UI since help tools are removed.

## Thought Process
- Same as CLI - `set_active_tools()` is no longer needed
- Will be replaced by MCPClient in Phase 4

## Implementation Plan
- [ ] Remove import of `set_active_tools` from ui.py
- [ ] Remove call to `set_active_tools(list(tools))` in ui.py

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Remove set_active_tools import | Not Started | 2026-01-21 | |
| 1.2 | Remove set_active_tools call | Not Started | 2026-01-21 | |

## Progress Log
### 2026-01-21
- Task created as part of MCP Server Migration plan
- Mapped to Issue ID: MCP-05
