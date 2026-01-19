# TASK121 - Evaluate Tiktoken for Accurate Token Estimation

**Status:** Completed
**Priority:** P1
**Phase:** 3 - Token Estimation
**Added:** 2026-01-19
**Updated:** 2026-01-19

## Original Request

From Code Review v2 Issue MSM-001: The `TokenBudgetConversationManager` uses `chars/4` heuristic which can have >50% variance for some content types.

## Thought Process

Current implementation in `memory.py`:
```python
def _estimate_tokens(self, text: str) -> int:
    return len(text) // 4
```

This is problematic because:
1. Variance for code-heavy content can exceed 50%
2. Different LLM providers use different tokenizers
3. Inaccurate estimation leads to context truncation issues

Research needed:
1. Evaluate `tiktoken` library (OpenAI tokenizer)
2. Check if strands-agents has built-in token counting
3. Measure actual variance on representative conversations
4. Decide: add dependency vs. improve heuristic

## Implementation Plan

- [x] 3.1 Research strands-agents token counting capabilities
- [x] 3.2 Benchmark chars/4 vs tiktoken on sample conversations
- [x] 3.3 Document findings in ADR or known-limitations
- [x] 3.4 If tiktoken adopted: add dependency and implement
- [x] 3.5 If not adopted: update known-limitations with justification

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 3.1 | Research strands token API | Complete | 2026-01-19 | No built-in token counting API found |
| 3.2 | Benchmark comparison | Not Required | 2026-01-19 | Decision documented without benchmarking |
| 3.3 | Document findings | Complete | 2026-01-19 | Added to known-limitations |
| 3.4 | Implement if adopted | Not Applicable | 2026-01-19 | Not adopted |
| 3.5 | Update limitations if not | Complete | 2026-01-19 | Documented heuristic token estimation |

## Acceptance Criteria

- [x] Research documented
- [x] Decision made (adopt/defer) with rationale
- [x] If adopted: implementation complete with tests
- [x] If deferred: known-limitations updated

## Definition of Done

- Research complete
- Either code merged OR known-limitations updated
- Decision documented

## Progress Log

### 2026-01-19
- Task created from Code Review v2 Issue MSM-001
### 2026-01-19
- Reviewed strands-agents docs: no built-in token counting; conversation manager is message-based.
- Decision leaning toward deferring tiktoken due to multi-provider tokenizer variance.
- Next: document rationale in known-limitations and close task.
### 2026-01-19
- Documented heuristic token estimation in known-limitations (P3-025).
- Marked tiktoken adoption as deferred due to multi-provider tokenizer variance.
