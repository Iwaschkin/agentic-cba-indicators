# [TASK040] - Update Prompts for Internal Tool Guidance

**Status:** Complete
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Update system prompts to guide agent on internal-only usage of help tools.

## Thought Process
The agent needs clear guidance that `list_tools()` and `describe_tool()` are internal-only and should never be mentioned to users. A soft acknowledgment ("I consulted internal tool docs") is acceptable.

## Implementation Plan
- Update `system_prompt_minimal.md` with internal tools section
- Update `system_prompt.md` with "INTERNAL TOOLS" section after "ABSOLUTE RULES"
- Add rule 5 forbidding mention of help tools to users

## Progress Tracking

**Overall Status:** Complete - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 3.1 | Update `system_prompt_minimal.md` | Complete | 2026-01-17 | Added internal tools section and soft ack guideline |
| 3.2 | Update `system_prompt.md` | Complete | 2026-01-17 | Added INTERNAL TOOLS section + rule 5 |

## Progress Log
### 2026-01-17
- Task created as part of internal tool docs feature
- Mapped from issues H-08, H-09
- Updated both prompt files with internal tools guidance
- Added rule 5 to ABSOLUTE RULES in main prompt
