# [TASK147] - Simplify System Prompt

**Status:** Pending
**Added:** 2026-01-21
**Updated:** 2026-01-21

## Original Request
Simplify system_prompt_minimal.md by removing tool discovery instructions since MCP provides native discovery.

## Thought Process
- MCP protocol handles tool discovery natively
- Remove internal tools section
- Remove "Never say Calling tool" rule
- Keep domain logic (Indicator Selection Workflow)
- Keep response formatting and citation requirements

## Implementation Plan
- [ ] Remove internal tools section from prompt
- [ ] Remove tool discovery instructions
- [ ] Remove "Never say Calling tool" rule
- [ ] Keep Indicator Selection Workflow
- [ ] Keep response formatting guidelines

## Progress Tracking

**Overall Status:** Not Started - 0%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Remove internal tools section | Not Started | 2026-01-21 | |
| 1.2 | Remove tool discovery instructions | Not Started | 2026-01-21 | |
| 1.3 | Verify workflow and formatting kept | Not Started | 2026-01-21 | |

## Progress Log
### 2026-01-21
- Task created as part of MCP Server Migration plan
- Mapped to Issue ID: MCP-11
