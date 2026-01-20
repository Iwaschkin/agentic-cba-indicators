# TASK131 - Fix UI Prompt Selection

**Status:** Completed
**Added:** 2026-01-20
**Updated:** 2026-01-20
**Priority:** P1
**Phase:** Phase 1 - Config Fidelity

## Original Request
Ensure the Streamlit UI respects the configured `prompt_name` when creating the agent.

## Thought Process
The UI agent factory loads `AgentConfig` but always calls `get_system_prompt()` without passing `prompt_name`. This diverges from CLI behavior and ignores configured prompt selection.

## Implementation Plan
- Update UI agent factory to pass `agent_config.prompt_name` to `get_system_prompt()`.
- Add a unit test that confirms the selected prompt name is used.

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 131.1 | Update UI prompt selection | Complete | 2026-01-20 | Use `prompt_name` from config |
| 131.2 | Add test for prompt selection | Complete | 2026-01-20 | Verify prompt name passed |

## Progress Log
### 2026-01-20
- Task created from code review CR-0001.
- Updated UI agent factory to pass `agent_config.prompt_name`.
- Added `test_create_agent_for_ui_uses_prompt_name`.
