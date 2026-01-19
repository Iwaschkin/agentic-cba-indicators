# TASK127 - Standardize Tool Context Usage

**Status:** Completed
**Priority:** P3
**Phase:** 3 - Medium Priority
**Added:** 2026-01-19
**Updated:** 2026-01-19

## Original Request

From Code Review v2 Issue ATI-004: Tool context not consistently used across all tools.

## Thought Process

Some tools use `ToolContext` (internal help tools) while most external tools rely on module-level state. The review suggests standardizing tool context usage for consistency and future extensibility.

We should:
1. Inventory which tools accept `ToolContext`
2. Decide on a consistent pattern (likely only internal tools)
3. Update docstrings and usage accordingly
4. Document any tools intentionally not using context

## Implementation Plan

- [x] 1.1 Inventory ToolContext usage across tools
- [x] 1.2 Define policy (internal-only vs wider usage)
- [x] 1.3 Update affected tools/docstrings
- [x] 1.4 Add tests or documentation for intended behavior

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Inventory ToolContext usage | Complete | 2026-01-19 | Only internal help tools use ToolContext |
| 1.2 | Define policy | Complete | 2026-01-19 | Documented internal-only policy |
| 1.3 | Update tools/docstrings | Complete | 2026-01-19 | CONTRIBUTING policy added |
| 1.4 | Add tests/docs | Complete | 2026-01-19 | Doc update sufficient |

## Acceptance Criteria

- [x] ToolContext usage policy documented
- [x] Tool docstrings updated to reflect policy
- [x] Any changes covered by tests or docs

## Definition of Done

- Policy documented
- Tools consistent with policy
- Tests/docs updated

## Progress Log

### 2026-01-19
- Task created from Code Review v2 Issue ATI-004
### 2026-01-19
- Audited ToolContext usage; internal help tools only.
- Documented policy in CONTRIBUTING.
