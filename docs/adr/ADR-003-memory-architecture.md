# ADR-003: Memory Architecture and Limitations

**Status:** Accepted
**Date:** 2026-01-18
**Deciders:** Development team
**Category:** Memory Architecture

## Context

The code review identified several memory-related issues:
- **P1-003**: Fixed window size doesn't account for token budget
- **P1-004**: No long-term memory system implemented
- **P1-005**: No dynamic context budget tracking at runtime
- **P2-012**: No message summarization when window truncates
- **P2-015**: No selective memory retrieval; entire window is always included

The original implementation used Strands SDK's `SlidingWindowConversationManager` with a fixed message count (default 5), which doesn't account for message length. Long tool outputs could still exceed context limits.

Full memory systems in production AI agents typically include:
- Token-aware context management
- Message summarization before truncation
- Selective retrieval based on relevance
- Long-term persistence across sessions
- User preference storage

## Decision

**Implement token-budget memory management; defer advanced memory features.**

### Implemented: Token-Budget Conversation Manager

Created `TokenBudgetConversationManager` in `src/agentic_cba_indicators/memory.py` that:

1. **Token Estimation**: Uses pluggable token estimation (default: chars/4 heuristic)
2. **Budget-Based Trimming**: Removes oldest messages when budget exceeded
3. **Tool Pair Preservation**: Keeps toolUse/toolResult pairs intact during trimming
4. **Minimum Preservation**: Always keeps last 2 messages for conversation continuity
5. **Overflow Handling**: Aggressive reduction when `ContextWindowOverflowException` occurs
6. **Configuration**: `context_budget` option in `providers.yaml`

```python
# Usage in providers.yaml
agent:
  context_budget: 8000  # Max tokens for conversation history
```

### Deferred Features

The following memory features are explicitly deferred:

#### P2-012: Message Summarization

**What**: Summarize old messages before discarding them to preserve context.

**Why Deferred**:
- Requires additional LLM calls (latency, cost)
- Complex prompt engineering for good summaries
- Must handle summary quality validation
- Token overhead for summary storage

**Future Implementation**:
```python
# Potential approach
class SummarizingConversationManager(TokenBudgetConversationManager):
    def _summarize_before_trim(self, messages_to_remove):
        summary = self.llm.generate(
            f"Summarize key points: {messages_to_remove}"
        )
        return {"role": "system", "content": f"[Context summary: {summary}]"}
```

#### P2-015: Selective Memory Retrieval

**What**: Retrieve relevant messages based on current query rather than including entire window.

**Why Deferred**:
- Requires embedding message history
- Needs vector similarity search infrastructure
- Complex relevance scoring logic
- May miss important context if retrieval is imprecise

**Future Implementation**:
```python
# Potential approach using ChromaDB
def get_relevant_context(self, query: str, messages: list) -> list:
    query_embedding = embed(query)
    # Search message history by semantic similarity
    relevant_ids = self.message_index.query(query_embedding, n=5)
    return [messages[i] for i in relevant_ids]
```

#### P1-004: Long-term Memory / Cross-Session Persistence

**What**: Persist conversation history and learned preferences across sessions.

**Why Deferred**:
- Requires persistent storage (file, database)
- Privacy considerations for storing conversations
- Complex session management
- Must handle memory growth over time

**Future Implementation Options**:
1. **File-based**: JSON/SQLite for local persistence
2. **Memory Bank pattern**: Markdown files like this project uses for humans
3. **Vector store**: ChromaDB collection for message history
4. **Hybrid**: Short-term in memory, long-term in persistent store

## Rationale

### Token-Budget Priority

P1-003 and P1-005 were high-priority issues because they could cause runtime failures:
- Context overflow errors from the LLM provider
- Unpredictable behavior when context is silently truncated

The token-budget approach provides:
- Predictable memory bounds
- Graceful degradation (oldest removed first)
- Configuration flexibility per model
- No additional dependencies

### Deferral Justification

Advanced memory features (summarization, selective retrieval, persistence) are deferred because:

1. **Sufficient for MVP**: Token-budget management handles the critical failure mode
2. **Complexity vs Value**: Each feature adds significant implementation complexity
3. **Usage Pattern**: CLI chatbot sessions are typically short (< 10 turns)
4. **Development Resources**: Focus on core functionality and stability first

## Consequences

### Positive
- Predictable context management with bounded memory
- No LLM calls for memory management (fast, free)
- Simple configuration via `context_budget`
- Clear upgrade path when features become necessary

### Negative
- Loss of potentially valuable context when trimming
- No learning across sessions
- No intelligent context selection
- Users must re-establish context each session

### Neutral
- Behavior is transparent (oldest messages removed first)
- Configuration allows tuning per use case

## Review Triggers

Revisit this decision when:
- Users report losing important context during conversations
- Sessions consistently exceed 10+ turns
- Enterprise deployment requires audit/compliance persistence
- RAG patterns need conversation-aware retrieval
- Multi-user deployment needs user preference isolation

## Alternatives Considered

### 1. Full OpenAI-style Memory Implementation

Use a memory backend like LangChain's memory or OpenAI Assistants threads.

**Rejected because**: Adds dependencies, complexity, and is overkill for CLI chatbot.

### 2. Always Include Everything

Don't manage memory; let the LLM provider handle truncation.

**Rejected because**: Provider truncation is unpredictable and may cut mid-message.

### 3. Fixed Message Count (Original)

Use `SlidingWindowConversationManager` with window_size.

**Partially Rejected**: Still available as fallback (`conversation_window` config) but token-budget is preferred for models with variable message lengths.

## Implementation Notes

### Configuration

```yaml
# providers.yaml
agent:
  # Option 1: Token budget (recommended)
  context_budget: 8000  # Use TokenBudgetConversationManager

  # Option 2: Message count (legacy)
  # conversation_window: 5  # Use SlidingWindowConversationManager
```

### Token Estimation

The default heuristic (chars/4) is intentionally conservative. For more accuracy:

```python
# Custom tokenizer
from tiktoken import encoding_for_model

def tiktoken_estimator(text: str) -> int:
    enc = encoding_for_model("gpt-4")
    return len(enc.encode(text))

manager = TokenBudgetConversationManager(
    max_tokens=8000,
    token_estimator=tiktoken_estimator
)
```

### Model-Specific Budgets

Recommended `context_budget` values by model:

| Model | Context Window | Recommended Budget |
|-------|---------------|-------------------|
| llama3.1 8B | 128K | 8000-16000 |
| Claude 3.5 | 200K | 16000-32000 |
| GPT-4 Turbo | 128K | 8000-16000 |
| Gemini Pro | 1M | 32000+ |

Budget should be ~10-25% of context window, leaving room for:
- System prompt
- Current user message
- Tool outputs
- Model response

## References

- [Strands SDK ConversationManager](https://strandsagents.com/latest/user-guide/concepts/conversation-management/)
- [Token Estimation Best Practices](https://cookbook.openai.com/examples/how_to_count_tokens_with_tiktoken)
- [P1-003, P1-005 in Code Review](../development/code-reviews/agentic_ai_code_review_report-2026-01-18-v1.md)
