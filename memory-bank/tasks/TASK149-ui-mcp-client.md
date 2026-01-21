# [TASK149] - Refactor UI to MCPClient

**Status:** Pending
**Added:** 2026-01-21
**Updated:** 2026-01-21

## Original Request
Refactor UI to use MCPClient instead of direct tool passing.

## Thought Process
- Same MCPClient pattern as CLI
- Update create_agent_for_ui() to use MCPClient
- Streamlit session state may need adjustment for MCP context

## Implementation Plan
- [ ] Add MCPClient imports
- [ ] Update create_agent_for_ui() to use MCPClient
- [ ] Handle MCP context in Streamlit session

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Add MCPClient imports | Not Started | 2026-01-21 | |
| 1.2 | Update create_agent_for_ui | Not Started | 2026-01-21 | |
| 1.3 | Handle session state | Not Started | 2026-01-21 | |

## Progress Log
### 2026-01-21
- Task created as part of MCP Server Migration plan
- Mapped to Issue ID: MCP-09
