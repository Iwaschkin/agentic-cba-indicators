# TASK122 - Account for System Prompt in Token Budget

**Status:** Completed
**Priority:** P2
**Phase:** 3 - Token Estimation
**Added:** 2026-01-19
**Updated:** 2026-01-19

## Original Request

From Code Review v2 Issue MSM-002: `TokenBudgetConversationManager` doesn't account for system prompt tokens, potentially exceeding context limits.

## Thought Process

Current implementation reserves `max_tokens` for conversation but ignores:
1. System prompt (loaded from `prompts/*.md`)
2. Tool definitions (62 tools × ~100 tokens each ≈ 6K tokens)
3. Provider-specific overhead

The system prompt is substantial (~2-3K chars = ~500-750 tokens estimated).

Options:
1. Add `system_prompt_tokens` parameter to constructor
2. Auto-detect by measuring at agent creation time
3. Use conservative default buffer (e.g., 10K tokens)

Option 1 is most explicit and testable.

## Implementation Plan

- [x] 3.1 Add `system_prompt_budget` parameter to `TokenBudgetConversationManager`
- [x] 3.2 Subtract system budget from available conversation budget
- [x] 3.3 Update `cli.py` to pass estimated system prompt size
- [x] 3.4 Add tests for budget calculation
- [x] 3.5 Document in docstring

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 3.1 | Add constructor param | Complete | 2026-01-19 | Added system_prompt_budget + validation |
| 3.2 | Update budget math | Complete | 2026-01-19 | effective_budget used in trimming |
| 3.3 | Update cli.py | Complete | 2026-01-19 | Added prompt+tools budget estimate |
| 3.4 | Add tests | Complete | 2026-01-19 | Tests added and executed |
| 3.5 | Update docstrings | Complete | 2026-01-19 | Docstring + effective_budget property |

## Acceptance Criteria

- [x] `system_prompt_budget` parameter exists
- [x] Effective conversation budget = max_tokens - system_prompt_budget
- [x] Tests verify budget calculation
- [x] cli.py passes reasonable estimate

## Definition of Done

- Code merged
- Tests pass
- Documentation updated

## Progress Log

### 2026-01-19
- Task created from Code Review v2 Issue MSM-002
### 2026-01-19
- Added `system_prompt_budget` parameter, validation, and `effective_budget` to `memory.py`.
- Updated trimming logic to use effective budget.
- Added tests in `tests/test_memory.py` (not run yet).
- Pending: wire budget estimation in `cli.py` and run tests.
### 2026-01-19
- Wired system prompt budget estimation into `cli.py`.
- Added helper to estimate prompt + tool definitions budget.
- Targeted tests run via VS Code test integration.
