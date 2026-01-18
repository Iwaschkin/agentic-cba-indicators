# ADR-004: Conversation-Scoped Tool Result Caching (Deferred)

## Status
**Deferred** - Acknowledged as beneficial, not implementing in Phase 5

## Context

The code review (P2-024) identified that tool results are not cached within a conversation. In multi-turn conversations, the agent may call the same tool with the same parameters multiple times.

**Current State:**
- API-level caching exists (P2-023): `fetch_json_cached()` with TTL for external APIs
- No conversation-scoped caching: Each tool call executes fresh, even within same session
- Tool calls can be expensive: Knowledge base queries, external API calls, geocoding

**Examples of Redundant Calls:**
1. User asks about indicator 107, agent calls `get_indicator_details(107)`
2. User asks follow-up, agent may call `get_indicator_details(107)` again
3. Same data returned, wasted computation and latency

## Decision

**Defer conversation-scoped tool result caching** to a future enhancement phase.

## Rationale

### Complexity Concerns

1. **Cache Scope Management**
   - Cache must be tied to conversation/session lifecycle
   - Requires integration with Strands conversation manager
   - Need to determine when to invalidate (conversation end, topic change)

2. **Cache Key Generation**
   - Tool calls include various parameter types (strings, lists, dicts)
   - Need robust serialization for cache keys
   - Some parameters may be semantically equivalent but different (e.g., "London" vs "london")

3. **Memory Management**
   - Conversation cache must be bounded
   - Need eviction policy (LRU, FIFO, size-based)
   - Long conversations could accumulate large caches

4. **Invalidation Complexity**
   - Knowledge base updates should invalidate cached KB queries
   - External data changes (time-sensitive data)
   - Hard to detect when cached data is stale

5. **Interaction with Existing Caching**
   - API-level caching (TTL) already provides partial benefit
   - Need to avoid double-caching complexity
   - Clear layering strategy required

### Mitigating Factors (Why Defer is Acceptable)

1. **API-Level Caching Addresses Main Concern**
   - External API calls (World Bank, ILO) are now cached
   - Most expensive operations benefit from TTL caching
   - Knowledge base queries are relatively fast (local ChromaDB)

2. **Agent Loop Control**
   - Strands agents typically don't repeat exact tool calls
   - System prompt can guide against redundant queries
   - User can ask agent to "use previous result"

3. **Conversation Length**
   - Most conversations are relatively short
   - Redundant calls have limited impact
   - Cost of implementation outweighs current benefit

## Alternatives Considered

### 1. Immediate Implementation
- **Pro:** Maximum performance benefit
- **Con:** Significant complexity for uncertain benefit
- **Decision:** Deferred due to complexity

### 2. Simple Dict Cache per Session
- **Pro:** Easy to implement
- **Con:** Unbounded memory, no invalidation, leaks across sessions
- **Decision:** Too naive, would create problems

### 3. Strands Hooks Integration
- **Pro:** Clean integration with agent lifecycle
- **Con:** Requires deep understanding of Strands internals
- **Decision:** Viable future approach, needs research

## Future Considerations

### When to Revisit

1. **Performance Metrics Show Need**
   - If metrics (TASK104) show high redundant tool call rate
   - If latency analysis shows KB queries dominate conversation time

2. **Strands Provides Support**
   - If Strands adds native conversation caching hooks
   - If community best practices emerge

3. **Long Conversation Use Cases**
   - If use cases require extended multi-turn analysis
   - If users report slow responses in long sessions

### Implementation Sketch (Future)

```python
# Hypothetical conversation cache integration
from strands.hooks import ConversationHook

class ToolResultCache(ConversationHook):
    def __init__(self, max_size: int = 100):
        self._cache: dict[str, Any] = {}
        self._max_size = max_size

    def on_conversation_start(self) -> None:
        self._cache.clear()

    def on_conversation_end(self) -> None:
        self._cache.clear()

    def cache_key(self, tool_name: str, args: dict) -> str:
        return f"{tool_name}:{json.dumps(args, sort_keys=True)}"

    def get_cached(self, key: str) -> Any | None:
        return self._cache.get(key)

    def set_cached(self, key: str, value: Any) -> None:
        if len(self._cache) >= self._max_size:
            # Evict oldest entry
            self._cache.pop(next(iter(self._cache)))
        self._cache[key] = value
```

## Consequences

### Positive
- Avoids complex implementation for uncertain benefit
- Keeps codebase simple and maintainable
- API-level caching provides immediate benefit
- Clear documentation of trade-off

### Negative
- Potential redundant tool calls in long conversations
- May need revisiting if usage patterns change
- Lost opportunity for maximum performance

## References

- Code Review Finding: P2-024
- Related: P2-023 (API caching - implemented in TASK112)
- Strands Documentation: https://strandsagents.com/latest/user-guide/concepts/hooks/
