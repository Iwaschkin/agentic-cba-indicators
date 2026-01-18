# Agentic AI System Code Review Report

**Project:** Agentic CBA Indicators
**Date:** January 18, 2026
**Version:** 1.0
**Reviewer:** Automated Architectural Review

---

## Executive Summary

This review examines a production-quality agentic AI system built with the Strands Agents SDK. The system provides a CLI and Streamlit UI chatbot for querying weather, climate, socio-economic data, and CBA ME Indicators using multiple AI providers (Ollama, Anthropic, OpenAI, AWS Bedrock, Google Gemini). The architecture demonstrates solid software engineering practices with notable strengths in modularity, error handling, and security. However, there are opportunities for improvement in areas such as observability, memory management, and tool orchestration patterns.

**Overall Assessment:** Well-architected production system with thoughtful security controls. Recommended for production use with minor enhancements.

---

## Table of Contents

1. [Agent-Tool Integration](#1-agent-tool-integration)
2. [Knowledge Base Integration](#2-knowledge-base-integration)
3. [Memory & State Management](#3-memory--state-management)
4. [Agent Architecture & Design Patterns](#4-agent-architecture--design-patterns)
5. [Performance & Reliability](#5-performance--reliability)
6. [Security & Safety Concerns](#6-security--safety-concerns)
7. [Configuration & Extensibility](#7-configuration--extensibility)
8. [Critical Issues](#8-critical-issues)
9. [Architecture Recommendations](#9-architecture-recommendations)
10. [Missing Features](#10-missing-features)
11. [Quick Wins](#11-quick-wins)
12. [Prioritized Action Plan](#12-prioritized-action-plan)

---

## 1. Agent-Tool Integration

### 1.1 Tool Discovery & Selection

**Strengths:**
- **Self-discovery mechanism**: Internal help tools (`list_tools`, `describe_tool`, `search_tools`, `list_tools_by_category`) in [_help.py](../../../src/agentic_cba_indicators/tools/_help.py) allow the agent to discover available tools at runtime
- **Category-based organization**: Tools are categorized (weather, soil, biodiversity, knowledge_base, etc.) enabling structured discovery
- **Context-aware tool access**: Uses `@tool(context=True)` decorator to access `ToolContext` for runtime tool registry introspection

```python
# _help.py:128-140
@tool(context=True)
def list_tools(tool_context: ToolContext) -> str:
    """List all available tools with one-line summaries."""
    tools = _get_tools_from_context(tool_context)
    # ...
```

**Issues:**
- **P2-001**: Tool categories defined in `_TOOL_CATEGORIES` dictionary are keyword-based, which can misclassify tools if names change
- **P3-001**: No tool versioning or deprecation mechanism for API evolution

**Recommendations:**
- Add explicit `category` metadata to `@tool` decorator for reliable categorization
- Implement tool version tagging for backward compatibility tracking

### 1.2 Tool Invocation Pattern

**Strengths:**
- **Clean decorator pattern**: All tools use the Strands `@tool` decorator with clear docstrings
- **Consistent return type**: All tools return `str` for uniform agent response handling
- **Well-documented parameters**: Docstrings include Args/Returns sections that LLMs can parse

```python
# weather.py:56-71
@tool
def get_current_weather(city: str) -> str:
    """
    Get current weather conditions for a city.

    Args:
        city: Name of the city (e.g., "London", "New York", "Tokyo")

    Returns:
        Current weather information including temperature, humidity, wind, and conditions
    """
```

**Issues:**
- **P2-002**: No explicit parameter validation decorators; validation happens inside tool functions
- **P3-002**: Error handling varies between tools; some return error strings, others raise exceptions

### 1.3 Tool Response Processing

**Strengths:**
- **Human-readable formatting**: Tool outputs use markdown, emojis, and structured text
- **Consistent error formatting**: `format_error()` in [_http.py](../../../src/agentic_cba_indicators/tools/_http.py) provides sanitized error messages

**Issues:**
- **P2-003**: No structured output schema (e.g., JSON) for programmatic parsing by downstream systems
- **P3-003**: Tool outputs can be very long (e.g., `export_indicator_selection`), potentially exceeding context limits

### 1.4 Missing Tool Capabilities

- **P2-004**: No tool for batch operations (e.g., get weather for multiple cities in one call)
- **P2-005**: No conversational memory tool (e.g., "save this search for later")
- **P3-004**: No tool output caching at the agent level

### 1.5 Tool Orchestration

**Strengths:**
- **Dual tool sets**: `REDUCED_TOOLS` (22 tools) and `FULL_TOOLS` (62 tools) in [__init__.py](../../../src/agentic_cba_indicators/tools/__init__.py) allow model-appropriate tool loading

**Issues:**
- **P2-006**: No explicit tool chaining or workflow definitions; relies entirely on LLM reasoning
- **P3-005**: No parallel tool execution support; tools run sequentially

---

## 2. Knowledge Base Integration

### 2.1 Retrieval Mechanisms

**Strengths:**
- **Semantic search**: ChromaDB with Ollama embeddings (bge-m3) in [knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py)
- **Exact-match fallback**: ID patterns (e.g., "indicator 107") trigger metadata filters before semantic search
- **Similarity thresholds**: `min_similarity` parameter filters low-relevance results (default 0.3)

```python
# knowledge_base.py:200-260 - Dual search strategy
exact_term = _extract_exact_match_term(query)
if exact_term:
    results = collection.get(where_document={"$contains": exact_term}, ...)
if not exact_term or not docs:
    results = collection.query(query_embeddings=[query_embedding], ...)
```

**Issues:**
- **P1-001**: ChromaDB client created on every tool call; no connection pooling
- **P2-007**: No query rewriting or expansion for better retrieval
- **P3-006**: Fixed embedding model (bge-m3) with no runtime selection

### 2.2 Context Relevance

**Strengths:**
- **Result limiting**: `_MAX_SEARCH_RESULTS_*` constants prevent context overflow
- **Metadata-based filtering**: Can filter by principle, class, component, measurement approach

**Issues:**
- **P2-008**: No relevance feedback mechanism to improve retrieval over time
- **P3-007**: No query-document cross-attention for re-ranking results

### 2.3 Knowledge Freshness

**Strengths:**
- **Deterministic ingestion**: [ingest_excel.py](../../../scripts/ingest_excel.py) uses stable document IDs for upsert operations
- **Clear source tracking**: Excel file path and ingestion timestamp could be tracked

**Issues:**
- **P1-002**: No knowledge versioning or TTL (time-to-live) metadata
- **P2-009**: No incremental update detection; full re-ingestion required
- **P3-008**: No mechanism to invalidate stale knowledge

### 2.4 RAG Quality

**Strengths:**
- **Rich metadata**: Indicators include component, class, unit, principles, criteria coverage
- **Method grouping**: All methods for an indicator stored as single document for context coherence
- **OA enrichment**: Integration with Unpaywall/CrossRef for citation metadata

**Issues:**
- **P2-010**: Fixed chunk size (entire documents); no adaptive chunking for long content
- **P3-009**: Embedding truncation at 24,000 chars may lose information from large documents

### 2.5 Knowledge Source Diversity

**Strengths:**
- **Multiple collections**: `indicators`, `methods`, `usecases` for different data types
- **External APIs**: Weather (Open-Meteo), Soil (SoilGrids), Biodiversity (GBIF), etc.

**Issues:**
- **P2-011**: No knowledge source provenance tracking in responses
- **P3-010**: No mechanism to cross-reference or merge results from multiple sources

---

## 3. Memory & State Management

### 3.1 Short-term Memory

**Strengths:**
- **Sliding window**: `SlidingWindowConversationManager` in [cli.py](../../../src/agentic_cba_indicators/cli.py#L64-L66) maintains conversation context
- **Configurable window**: `conversation_window` parameter (default 5 turns) in config

```python
# cli.py:64-66
conversation_manager = SlidingWindowConversationManager(
    window_size=agent_config.conversation_window,
)
```

**Issues:**
- **P1-003**: Fixed window size doesn't account for token budget; long tool outputs may still exceed context
- **P2-012**: No message summarization when window truncates

### 3.2 Long-term Memory

**Issues:**
- **P1-004**: **No long-term memory system implemented**. Conversations are lost on session end.
- **P2-013**: No user preference storage
- **P2-014**: No cross-session context persistence

### 3.3 Memory Retrieval

**Issues:**
- **P2-015**: No selective memory retrieval; entire window is always included
- **P3-011**: No memory importance ranking

### 3.4 Context Window Management

**Strengths:**
- **Tool set sizing**: Reduced tool set (22 tools) for smaller context models

**Issues:**
- **P1-005**: No dynamic context budget tracking at runtime
- **P2-016**: System prompt (694 lines in full version) is very large; minimal version used by default but full version exists

---

## 4. Agent Architecture & Design Patterns

### 4.1 Control Flow

**Strengths:**
- **Strands Agent abstraction**: Clean separation between agent logic and tool implementation
- **Simple invocation**: `agent(user_input)` handles reasoning and tool calls internally

**Issues:**
- **P2-017**: No explicit ReAct or Chain-of-Thought prompting in system prompt
- **P3-012**: No tree search or planning traces visible

### 4.2 Planning Capabilities

**Strengths:**
- **System prompt guidance**: Minimal prompt provides tool usage rules and patterns

```markdown
# system_prompt_minimal.md
Knowledge Base Usage Rules:
1. Indicator selection → search_usecases() first
2. Topic requests → search_indicators()
3. Method requests → search_methods() then find_feasible_methods()
```

**Issues:**
- **P2-018**: No explicit task decomposition tool or planner
- **P3-013**: Multi-step tasks rely entirely on LLM implicit planning

### 4.3 Error Recovery

**Strengths:**
- **Retry logic**: HTTP requests in [_http.py](../../../src/agentic_cba_indicators/tools/_http.py#L91-L156) include exponential backoff
- **Graceful degradation**: Tools return error strings rather than crashing
- **ChromaDB retries**: [knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L76-L123) implements retry for transient failures

**Issues:**
- **P2-019**: No agent-level error recovery (e.g., retry with different tool)
- **P3-014**: No dead-end detection when tools consistently fail

### 4.4 Feedback Loops

**Issues:**
- **P1-006**: **No self-correction mechanism**. Agent cannot verify its own outputs.
- **P2-020**: No tool output validation against expected patterns
- **P3-015**: No learning from user corrections

### 4.5 Modularity

**Strengths:**
- **Clean separation**: Tools, config, prompts, paths all in separate modules
- **Package structure**: Standard `src/` layout with `py.typed` marker
- **Type hints**: Comprehensive typing throughout codebase

---

## 5. Performance & Reliability

### 5.1 Latency Bottlenecks

**Identified Bottlenecks:**
- **P1-007**: ChromaDB client recreation on each tool call (no connection pooling)
- **P2-021**: Embedding generation is synchronous with rate limiting (0.1s minimum interval)
- **P2-022**: No request coalescing for rapid-fire tool calls

### 5.2 Rate Limiting

**Strengths:**
- **HTTP retry logic**: Exponential backoff with jitter for 429/5xx errors
- **Embedding rate limit**: `_MIN_EMBEDDING_INTERVAL` prevents Ollama flooding
- **Configurable limits**: Environment variables for timeouts, retries, backoff

```python
# _http.py:20-25
DEFAULT_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "30.0"))
DEFAULT_RETRIES = int(os.environ.get("HTTP_RETRIES", "3"))
DEFAULT_BACKOFF_BASE = float(os.environ.get("HTTP_BACKOFF_BASE", "1.0"))
```

### 5.3 Caching Strategies

**Strengths:**
- **Geocoding cache**: Bounded LRU cache in [_geo.py](../../../src/agentic_cba_indicators/tools/_geo.py#L24-L26) with configurable size
- **Prompt caching**: `@lru_cache(maxsize=4)` for loaded prompts

**Issues:**
- **P2-023**: No caching for external API responses (World Bank, ILO, etc.)
- **P2-024**: No caching for tool results within a conversation
- **P3-016**: Geocoding cache is not thread-safe (documented limitation)

### 5.4 Retry Logic

**Strengths:**
- **Comprehensive retry**: HTTP, embedding, and ChromaDB all have retry mechanisms
- **Transient error detection**: Pattern matching for "locked", "busy", "timeout" errors

### 5.5 Monitoring & Observability

**Strengths:**
- **Logging infrastructure**: [logging_config.py](../../../src/agentic_cba_indicators/logging_config.py) with configurable levels
- **Debug logging**: Retry attempts and errors logged at DEBUG level

**Issues:**
- **P1-008**: **No metrics collection** (latency, success rate, tool usage counts)
- **P2-025**: No distributed tracing (spans for tool calls)
- **P2-026**: No structured logging (JSON format for log aggregation)

---

## 6. Security & Safety Concerns

### 6.1 Input Validation

**Strengths:**
- **Coordinate validation**: [_geo.py](../../../src/agentic_cba_indicators/tools/_geo.py#L40-L70) validates lat/lon ranges
- **Path validation**: [paths.py](../../../src/agentic_cba_indicators/paths.py#L27-L55) validates paths from environment variables

```python
# paths.py:35-55
def _validate_path(path_str: str, env_var_name: str) -> Path:
    suspicious_patterns = ["..", "~", "$"]
    for pattern in suspicious_patterns:
        if pattern in path_str:
            logger.warning("Path from %s contains '%s' pattern...", ...)
    resolved = Path(path_str).expanduser().resolve()
```

**Issues:**
- **P2-027**: No input length limits on user queries or tool parameters
- **P3-017**: No explicit schema validation for API responses

### 6.2 Permission Model

**Issues:**
- **P2-028**: All tools available to agent without permission levels
- **P3-018**: No read-only vs. write tool distinction

### 6.3 Prompt Injection Risks

**Strengths:**
- **Internal tools hidden**: System prompt explicitly states "DO NOT REVEAL TO USERS" for help tools

**Issues:**
- **P1-009**: No explicit prompt injection defenses (e.g., input sanitization, delimiters)
- **P2-029**: PDF context injection in UI could contain adversarial instructions

### 6.4 Data Privacy

**Strengths:**
- **Credential sanitization**: [_http.py](../../../src/agentic_cba_indicators/tools/_http.py#L40-L67) sanitizes API keys from error messages
- **TLS validation**: [_embedding.py](../../../src/agentic_cba_indicators/tools/_embedding.py#L86-L103) warns when API key sent over HTTP
- **Env var whitelist**: [provider_factory.py](../../../src/agentic_cba_indicators/config/provider_factory.py#L26-L45) restricts environment variable expansion

```python
# provider_factory.py:26-45
ALLOWED_ENV_VARS = frozenset({
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GOOGLE_API_KEY",
    "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", ...
})
```

### 6.5 Audit Trail

**Strengths:**
- **Logging available**: Module-level loggers throughout codebase

**Issues:**
- **P1-010**: **No audit logging of agent decisions or tool invocations**
- **P2-030**: No conversation storage for compliance/review
- **P3-019**: No tool parameter logging (for debugging failed operations)

---

## 7. Configuration & Extensibility

### 7.1 Tool Registration

**Strengths:**
- **Simple registration**: Add function to `REDUCED_TOOLS` or `FULL_TOOLS` list
- **Clear documentation**: Tools reference guide exists at [docs/tools-reference.md](../../../docs/tools-reference.md)

**Issues:**
- **P3-020**: No dynamic tool loading (plugins)
- **P3-021**: No tool hot-reload without restart

### 7.2 Parameterization

**Strengths:**
- **YAML configuration**: [providers.yaml](../../../src/agentic_cba_indicators/config/providers.yaml) centralizes settings
- **Environment variables**: Extensive env var support for all configurable values
- **Provider abstraction**: Factory pattern in [provider_factory.py](../../../src/agentic_cba_indicators/config/provider_factory.py)

### 7.3 Prompt Engineering

**Strengths:**
- **External prompts**: Markdown files in [prompts/](../../../src/agentic_cba_indicators/prompts/) directory
- **Minimal vs. full**: Two prompt variants for different use cases
- **Cached loading**: `@lru_cache` for prompt file reads

**Issues:**
- **P3-022**: No prompt versioning or A/B testing support
- **P3-023**: No prompt template variables for dynamic injection

### 7.4 Environment Management

**Strengths:**
- **XDG compliance**: Uses `platformdirs` for platform-appropriate paths
- **Clear resolution order**: Config file, user config, bundled default
- **Dev dependency separation**: `dev` extras in pyproject.toml

---

## 8. Critical Issues

| ID | Category | Issue | Impact | File Reference |
|----|----------|-------|--------|----------------|
| P1-001 | Performance | ChromaDB client recreation per call | High latency, resource waste | [knowledge_base.py#L76](../../../src/agentic_cba_indicators/tools/knowledge_base.py#L76) |
| P1-002 | Data | No knowledge versioning/TTL | Stale data served | [ingest_excel.py](../../../scripts/ingest_excel.py) |
| P1-003 | Memory | Fixed window doesn't account for tokens | Context overflow | [cli.py#L64](../../../src/agentic_cba_indicators/cli.py#L64) |
| P1-004 | Memory | No long-term memory | Poor user experience | System-wide |
| P1-005 | Memory | No dynamic context budget | Unpredictable failures | System-wide |
| P1-006 | Architecture | No self-correction mechanism | Incorrect outputs persist | System-wide |
| P1-007 | Performance | Synchronous operations bottleneck | Slow response times | [_embedding.py](../../../src/agentic_cba_indicators/tools/_embedding.py) |
| P1-008 | Observability | No metrics collection | Blind to performance issues | System-wide |
| P1-009 | Security | No prompt injection defenses | Potential manipulation | System-wide |
| P1-010 | Audit | No audit logging | Compliance risk | System-wide |

---

## 9. Architecture Recommendations

### 9.1 Implement Connection Pooling for ChromaDB

**Current:**
```python
def _get_chroma_client() -> ClientAPI:
    return chromadb.PersistentClient(path=str(kb_path))  # Created each call
```

**Recommended:**
```python
# Module-level singleton with lazy initialization
_chroma_client: ClientAPI | None = None
_chroma_lock = threading.Lock()

def get_chroma_client() -> ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        with _chroma_lock:
            if _chroma_client is None:
                _chroma_client = chromadb.PersistentClient(path=str(kb_path))
    return _chroma_client
```

### 9.2 Add Token-Aware Conversation Management

**Recommendation:** Replace `SlidingWindowConversationManager` with a token-counting manager:

```python
class TokenBudgetConversationManager:
    def __init__(self, max_tokens: int = 8000, model: str = "gpt-4"):
        self.max_tokens = max_tokens
        self.tokenizer = tiktoken.encoding_for_model(model)

    def get_context(self, messages: list[Message]) -> list[Message]:
        """Return messages that fit within token budget."""
        budget = self.max_tokens
        result = []
        for msg in reversed(messages):
            tokens = len(self.tokenizer.encode(msg.content))
            if tokens > budget:
                break
            result.insert(0, msg)
            budget -= tokens
        return result
```

### 9.3 Implement Observability Layer

**Recommendation:** Add OpenTelemetry integration:

```python
from opentelemetry import trace, metrics

tracer = trace.get_tracer("agentic_cba_indicators")
meter = metrics.get_meter("agentic_cba_indicators")

tool_calls_counter = meter.create_counter("tool.calls", description="Tool invocations")
tool_latency = meter.create_histogram("tool.latency_ms", description="Tool latency")

def instrument_tool(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        with tracer.start_as_current_span(f"tool.{func.__name__}"):
            start = time.monotonic()
            try:
                result = func(*args, **kwargs)
                tool_calls_counter.add(1, {"tool": func.__name__, "status": "success"})
                return result
            finally:
                tool_latency.record((time.monotonic() - start) * 1000)
    return wrapper
```

### 9.4 Add Response Validation

**Recommendation:** Implement output schema validation:

```python
from pydantic import BaseModel, ValidationError

class WeatherResponse(BaseModel):
    location: str
    temperature: float
    conditions: str

@tool
def get_current_weather(city: str) -> str:
    data = fetch_weather(city)
    try:
        validated = WeatherResponse(**data)
        return format_weather(validated)
    except ValidationError as e:
        logger.warning("Weather response validation failed: %s", e)
        return format_error_response(e)
```

---

## 10. Missing Features

| Priority | Feature | Benefit | Effort |
|----------|---------|---------|--------|
| High | Metrics/tracing | Production observability | Medium |
| High | Long-term memory | Cross-session context | Medium |
| High | Audit logging | Compliance, debugging | Low |
| Medium | Tool output caching | Reduced latency | Low |
| Medium | Query rewriting | Better retrieval | Medium |
| Medium | Batch tool operations | Efficiency | Medium |
| Low | Dynamic tool loading | Plugin ecosystem | High |
| Low | A/B prompt testing | Optimization | Medium |

---

## 11. Quick Wins

### 11.1 Add Connection Pooling (Est. 2 hours)

Replace per-call ChromaDB client creation with module-level singleton.

**File:** [knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py)

### 11.2 Enable Structured Logging (Est. 1 hour)

Add JSON formatter option to logging config for log aggregation.

**File:** [logging_config.py](../../../src/agentic_cba_indicators/logging_config.py)

### 11.3 Add Basic Audit Logging (Est. 2 hours)

Log tool invocations with timestamps and parameters (sanitized).

**File:** New file `audit.py`

### 11.4 Add Tool Output Length Limits (Est. 1 hour)

Truncate very long tool outputs with "... (truncated)" suffix.

**File:** [_help.py](../../../src/agentic_cba_indicators/tools/_help.py)

### 11.5 Cache External API Responses (Est. 3 hours)

Add `@lru_cache` or `cachetools.TTLCache` for World Bank, ILO, etc.

**Files:** [socioeconomic.py](../../../src/agentic_cba_indicators/tools/socioeconomic.py), [labor.py](../../../src/agentic_cba_indicators/tools/labor.py)

---

## 12. Prioritized Action Plan

### Phase 1: Critical Fixes (Week 1-2)

1. **Implement ChromaDB connection pooling** (P1-001, P1-007)
2. **Add basic audit logging** (P1-010)
3. **Add token-aware context management** (P1-003, P1-005)

### Phase 2: Observability (Week 3-4)

4. **Integrate OpenTelemetry metrics** (P1-008)
5. **Add structured JSON logging** (P2-026)
6. **Implement tool invocation tracing** (P2-025)

### Phase 3: Security Hardening (Week 5-6)

7. **Add prompt injection defenses** (P1-009)
8. **Implement input length limits** (P2-027)
9. **Add PDF content sanitization** (P2-029)

### Phase 4: Performance Optimization (Week 7-8)

10. **Add API response caching** (P2-023, P2-024)
11. **Implement knowledge versioning** (P1-002)
12. **Add query rewriting for RAG** (P2-007)

### Phase 5: Advanced Features (Week 9+)

13. **Implement long-term memory** (P1-004)
14. **Add self-correction mechanism** (P1-006)
15. **Build batch operation tools** (P2-004)

---

## Appendix A: Test Coverage Analysis

**Current test files:**
- `test_config.py` - Configuration loading ✓
- `test_http.py` - HTTP utilities, error sanitization ✓
- `test_paths.py` - Path resolution, security ✓
- `test_secrets.py` - API key management ✓
- `test_tools_help.py` - Internal help tools ✓
- `test_tools_*.py` - Individual tool tests ✓

**Missing test coverage:**
- Agent integration tests (end-to-end)
- Knowledge base retrieval accuracy
- Conversation memory behavior
- Error recovery scenarios
- Concurrent access (thread safety)

---

## Appendix B: File Reference Index

| Component | Primary File |
|-----------|--------------|
| Agent Entry Point | [cli.py](../../../src/agentic_cba_indicators/cli.py) |
| UI Entry Point | [ui.py](../../../src/agentic_cba_indicators/ui.py) |
| Provider Factory | [provider_factory.py](../../../src/agentic_cba_indicators/config/provider_factory.py) |
| Tool Registry | [tools/__init__.py](../../../src/agentic_cba_indicators/tools/__init__.py) |
| Knowledge Base | [knowledge_base.py](../../../src/agentic_cba_indicators/tools/knowledge_base.py) |
| HTTP Utilities | [_http.py](../../../src/agentic_cba_indicators/tools/_http.py) |
| Embedding | [_embedding.py](../../../src/agentic_cba_indicators/tools/_embedding.py) |
| Help Tools | [_help.py](../../../src/agentic_cba_indicators/tools/_help.py) |
| System Prompts | [prompts/](../../../src/agentic_cba_indicators/prompts/) |
| Configuration | [config/providers.yaml](../../../src/agentic_cba_indicators/config/providers.yaml) |

---

*Report generated by automated code review. Manual verification recommended for critical security findings.*
