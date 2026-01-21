# [TASK138] - Create MCP Server Module

**Status:** Pending
**Added:** 2026-01-21
**Updated:** 2026-01-21

## Original Request
Create the MCP server module that wraps all tools with timeout/audit/metrics and exposes them via stdio transport using FastMCP.

## Thought Process
- MCP (Model Context Protocol) provides native tool discovery, replacing the need for help tools
- Server wraps tools with existing `_wrap_tool()` for timeout/audit/metrics consistency
- Server stays stateless - config remains in client (CLI/UI)
- Uses stdio transport for subprocess communication

## Implementation Plan
- [ ] Create `src/agentic_cba_indicators/mcp_server.py`
- [ ] Import FastMCP from `mcp.server.fastmcp`
- [ ] Import all tools from tools module (excluding help tools)
- [ ] Apply `_wrap_tool()` before MCP registration
- [ ] Add server instructions describing tool categories
- [ ] Create `run_server()` entry point

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Create mcp_server.py file | Not Started | 2026-01-21 | |
| 1.2 | Implement FastMCP server setup | Not Started | 2026-01-21 | |
| 1.3 | Register wrapped tools | Not Started | 2026-01-21 | |
| 1.4 | Add run_server() entry point | Not Started | 2026-01-21 | |

## Progress Log
### 2026-01-21
- Task created as part of MCP Server Migration plan
- Mapped to Issue ID: MCP-01
