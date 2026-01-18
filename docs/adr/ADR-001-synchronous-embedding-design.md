# ADR-001: Synchronous Embedding Design

**Status:** Accepted
**Date:** 2026-01-18
**Context:** Code Review v3 Remediation - Phase 1 Storage Foundation

## Context

The current embedding pipeline in `scripts/ingest_excel.py` uses synchronous Ollama API calls for generating embeddings during knowledge base ingestion. The code review identified this as a potential performance concern (P1-007, P2-009).

### Current Implementation

```python
def get_embeddings_batch(texts: list[str], strict: bool = False) -> list[list[float] | None]:
    """Get embeddings for multiple texts via Ollama API."""
    embeddings = []
    for text in texts:
        try:
            response = requests.post(
                f"{OLLAMA_HOST}/api/embeddings",
                json={"model": EMBEDDING_MODEL, "prompt": truncated},
                timeout=EMBEDDING_TIMEOUT,
            )
            # ... process response
        except requests.RequestException as e:
            # ... handle error
    return embeddings
```

### Concerns Raised

1. **P1-007**: Blocking I/O during embedding generation
2. **P2-009**: No batching or parallelization of embedding requests

## Decision

**We will retain the synchronous embedding design for the current phase** and document this as an intentional technical decision rather than technical debt.

### Rationale

1. **Bounded Dataset Size**: The CBA ME Indicators dataset contains 224 indicators and ~223 method groups. Full re-ingestion takes <5 minutes on commodity hardware.

2. **Infrequent Operation**: Ingestion is a one-time or infrequent batch operation, not a runtime hot path. The chatbot does not generate embeddings at query time.

3. **Ollama Limitations**: Ollama's `/api/embeddings` endpoint processes one prompt at a time. True batching would require:
   - A different embedding provider (OpenAI, Cohere)
   - Custom batching logic with connection pooling
   - Async infrastructure throughout the ingestion pipeline

4. **Complexity vs. Benefit**: Async implementation would require:
   - `asyncio` integration in the ingestion script
   - Connection pool management
   - Error handling for partial batch failures
   - Testing infrastructure for async code

   This complexity is not justified for a <5 minute batch operation.

5. **Deterministic Upserts**: The current design uses deterministic document IDs (`indicator:{id}`, `methods_for_indicator:{id}`) enabling safe incremental updates. Async batching could complicate this pattern.

## Consequences

### Positive
- Simple, maintainable code
- Deterministic execution order
- Easy debugging and error tracing
- No async complexity in test suite

### Negative
- Full re-ingestion takes ~5 minutes (224 + 223 = 447 documents)
- Cannot leverage parallel embedding providers

### Accepted Trade-offs
- Performance is acceptable for current dataset size
- If dataset grows significantly (>10x), we will revisit this decision
- If real-time embedding is needed (e.g., user-uploaded documents), we will implement async as a separate feature

## Alternatives Considered

### 1. Async with asyncio
- **Rejected**: Ollama doesn't support true batch embedding; async would only help with connection management, not actual throughput.

### 2. ThreadPoolExecutor
- **Rejected**: Adds complexity without significant benefit for sequential Ollama calls.

### 3. Switch to OpenAI Embeddings
- **Deferred**: Would enable true batching but adds API cost and external dependency.

## Review Triggers

This decision should be reconsidered if:
- Dataset size exceeds 5,000 documents
- User-uploaded document embedding is required
- Embedding latency becomes a user-facing issue
- Ollama adds batch embedding support

## Related Issues
- P1-007: Synchronous blocking calls in embedding pipeline
- P2-009: Embedding batching and parallelization

## References
- [Ollama Embeddings API](https://github.com/ollama/ollama/blob/main/docs/api.md#generate-embeddings)
- [ChromaDB Embedding Functions](https://docs.trychroma.com/docs/embeddings/embed-functions)
