# [TASK108] - Token-Budget Conversation Manager

**Status:** Completed
**Added:** 2026-01-18
**Updated:** 2026-01-18
**Completed:** 2026-01-18
**Phase:** 3 - Memory Architecture
**Priority:** P0
**Issue IDs:** P1-003, P1-005

## Original Request
Replace fixed sliding window conversation manager with token-aware context management.

## Thought Process
Current `SlidingWindowConversationManager` uses fixed message count (default 5) which doesn't account for message length. Long tool outputs can still exceed context limits. Need token-counting approach.

Options:
1. Use tiktoken library (accurate but adds dependency)
2. Simple heuristic (4 chars = 1 token, fast approximation)

Decision: Start with heuristic, make tokenizer pluggable.

Research findings:
- Strands SDK `ConversationManager` base class provides `apply_management()`, `reduce_context()`, `register_hooks()`
- `SlidingWindowConversationManager` uses fixed message count (window_size)
- `BeforeModelCallEvent` hook for per-turn management
- `ContextWindowOverflowException` for overflow handling
- SDK uses message format with role, content array (text, toolUse, toolResult)

## Implementation Plan
1. Create src/agentic_cba_indicators/memory.py
2. Implement TokenBudgetConversationManager class
3. Add max_tokens parameter and get_context() method
4. Add simple token estimation (chars/4)
5. Update cli.py to use new manager
6. Add configuration option in providers.yaml
7. Add unit tests

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 8.1 | Create memory.py module | Complete | 2026-01-18 | ~420 lines |
| 8.2 | Implement TokenBudgetConversationManager | Complete | 2026-01-18 | Extends SDK ConversationManager |
| 8.3 | Add token estimation function | Complete | 2026-01-18 | chars/4 heuristic, pluggable |
| 8.4 | Update cli.py to use new manager | Complete | 2026-01-18 | Conditional selection |
| 8.5 | Add context_budget config option | Complete | 2026-01-18 | AgentConfig + validation |
| 8.6 | Add unit tests | Complete | 2026-01-18 | 36 tests in test_memory.py |

## Progress Log
### 2026-01-18
- Task created from code review findings P1-003, P1-005

### 2026-01-18 (Implementation)
- Researched Strands SDK ConversationManager interface via Context7 and DeepWiki
- Created `src/agentic_cba_indicators/memory.py` with:
  - `estimate_tokens_heuristic()` - chars/4 approximation
  - `_message_to_text()` - converts messages to plain text
  - `estimate_message_tokens()` and `estimate_messages_tokens()`
  - `TokenBudgetConversationManager` class:
    - `max_tokens`: Budget parameter (default 8000)
    - `token_estimator`: Pluggable estimation function
    - `per_turn`: When to apply (False/True/int)
    - `apply_management()`: Trims oldest messages to fit budget
    - `reduce_context()`: Aggressive reduction on overflow
    - `_trim_to_budget()`: Core trimming logic
    - `_adjust_for_tool_pairs()`: Preserves toolUse/toolResult pairs
- Updated `AgentConfig` dataclass with `context_budget` field
- Updated config validation for new field
- Updated `cli.py` to conditionally use TokenBudgetConversationManager
- Updated `ui.py` similarly
- Updated `providers.yaml` with documentation for context_budget option
- Created comprehensive test suite `tests/test_memory.py` (36 tests)
- Fixed test issues:
  - Added `__name__` field to get_state() for SDK compatibility
  - Fixed state dict to include `removed_message_count`
  - Adjusted test budgets to allow meaningful trimming
- All 36 tests pass, full suite 348 tests pass

## Files Changed
- `src/agentic_cba_indicators/memory.py` (NEW ~420 lines)
- `src/agentic_cba_indicators/config/provider_factory.py` (modified)
- `src/agentic_cba_indicators/cli.py` (modified)
- `src/agentic_cba_indicators/ui.py` (modified)
- `src/agentic_cba_indicators/config/providers.yaml` (modified)
- `tests/test_memory.py` (NEW ~430 lines)

## Definition of Done
- [x] Token counting replaces fixed window
- [x] Configurable budget via providers.yaml
- [x] Messages trimmed to fit budget
- [x] Most recent messages prioritized
- [x] Tests verify budget enforcement
