# [TASK148] - Refactor CLI to MCPClient

**Status:** Pending
**Added:** 2026-01-21
**Updated:** 2026-01-21

## Original Request
Refactor CLI to use MCPClient instead of direct tool passing. Remove fallback tool parsing code.

## Thought Process
- MCPClient spawns MCP server as subprocess via stdio
- tool_filters.allowed used for reduced mode (filter by tool names)
- CLI creates Agent with tools from mcp_client.list_tools_sync()
- Wrap agent usage in `with mcp_client:` context manager
- Remove legacy fallback tool parsing (_parse_fallback_tool_call, regex)
- Simplify callback handler

## Implementation Plan
- [ ] Add MCPClient imports
- [ ] Create MCPClient with agentic-cba-mcp command
- [ ] Build tool_filters based on config
- [ ] Update create_agent_from_config to use MCPClient
- [ ] Remove _parse_fallback_tool_call function
- [ ] Remove _FALLBACK_TOOL_PATTERN regex
- [ ] Simplify main loop

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Add MCPClient imports | Not Started | 2026-01-21 | |
| 1.2 | Create MCPClient setup | Not Started | 2026-01-21 | |
| 1.3 | Update agent creation | Not Started | 2026-01-21 | |
| 1.4 | Remove fallback parsing | Not Started | 2026-01-21 | |
| 1.5 | Simplify main loop | Not Started | 2026-01-21 | |

## Progress Log
### 2026-01-21
- Task created as part of MCP Server Migration plan
- Mapped to Issue IDs: MCP-08, MCP-10
