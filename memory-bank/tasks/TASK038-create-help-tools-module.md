# [TASK038] - Create Internal Help Tools Module

**Status:** Complete
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Create `src/agentic_cba_indicators/tools/_help.py` with internal help tools for agent self-discovery.

## Thought Process
The agent needs self-documenting capability without bloating the system prompt. By providing `list_tools()` and `describe_tool()` as internal-only tools, the agent can discover and understand available tools at runtime. These tools should use a registry pattern set at CLI startup.

## Implementation Plan
- Create `_help.py` module with `@tool` decorator
- Implement `_active_tools` module-level registry
- Implement `set_active_tools()` to set registry at startup
- Implement `list_tools()` to return names + first docstring line
- Implement `describe_tool(name)` to return full docstring

## Progress Tracking

**Overall Status:** Complete - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Create `_help.py` file with registry | Complete | 2026-01-17 | Module created with `_active_tools` list |
| 1.2 | Implement `set_active_tools()` | Complete | 2026-01-17 | Sets global registry |
| 1.3 | Implement `list_tools()` tool | Complete | 2026-01-17 | Returns bullet list with first docstring line |
| 1.4 | Implement `describe_tool()` tool | Complete | 2026-01-17 | Returns full docstring or not found message |

## Progress Log
### 2026-01-17
- Task created as part of internal tool docs feature
- Mapped from issues H-01, H-02, H-03, H-04
- Created `_help.py` with all 4 components
- Used `@tool` decorator from strands
- Implemented Google-style docstrings
