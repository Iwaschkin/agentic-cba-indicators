# [TASK039] - Integrate Help Tools into CLI

**Status:** Complete
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Wire help tools into CLI agent creation without exposing them in public tool catalogs.

## Thought Process
Help tools need to be available to the agent but hidden from user-facing tool counts and exports. The CLI should call `set_active_tools()` before creating the agent, then append help tools to the tool list passed to the Agent constructor.

## Implementation Plan
- Export help tools from `tools/__init__.py` (not in REDUCED/FULL_TOOLS)
- Update `cli.py` to import help tools
- Call `set_active_tools()` before agent creation
- Append help tools to agent's tool list
- Preserve original tool count for banner display

## Progress Tracking

**Overall Status:** Complete - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 2.1 | Export help tools from `__init__.py` | Complete | 2026-01-17 | Added imports with comment explaining exclusion |
| 2.2 | Update CLI imports | Complete | 2026-01-17 | Imported from `tools._help` |
| 2.3 | Call `set_active_tools()` in CLI | Complete | 2026-01-17 | Called before agent creation |
| 2.4 | Append help tools to agent tool list | Complete | 2026-01-17 | Uses `tools_with_help` list |

## Progress Log
### 2026-01-17
- Task created as part of internal tool docs feature
- Mapped from issues H-05, H-06, H-07
- Updated `tools/__init__.py` with help tool imports
- Updated `cli.py` to integrate help tools
- Original tool count preserved for user-facing banner
