# Agentic AI System Code Review Report (2026-01-20, v1)

## Executive Summary
The system is well-structured with clear tool boundaries, token-budget memory controls, and strong HTTP hygiene. The most impactful gaps are operational: observability and audit logging are implemented but not integrated into tool execution, and the internal tool discovery relies on agent internals that could break with Strands updates. Knowledge base access is robust and cached, but lacks freshness detection and ranking enhancements. These gaps are manageable with low-effort wiring and a small set of architectural reinforcements.

## 1. Agent-Tool Integration

### Tool Discovery & Selection
- Internal help tools provide runtime discovery and categorization, with a registry set at startup. This gives the agent a controlled view of the active tool set. [src/agentic_cba_indicators/tools/_help.py](src/agentic_cba_indicators/tools/_help.py#L1-L220), [src/agentic_cba_indicators/cli.py](src/agentic_cba_indicators/cli.py#L66-L120)
- Discovery relies on ToolContext agent internals (`tool_registry`, `tools`) with a module-level fallback. This is brittle if Strands changes internals. [src/agentic_cba_indicators/tools/_help.py](src/agentic_cba_indicators/tools/_help.py#L62-L118)

### Tool Invocation Pattern
- Tools are statically registered in the tool sets; selection is binary (reduced/full). [src/agentic_cba_indicators/tools/__init__.py](src/agentic_cba_indicators/tools/__init__.py#L1-L200)
- Timeouts are implemented as a shared executor wrapper, but there is no global enforcement at tool registration. [src/agentic_cba_indicators/tools/_timeout.py](src/agentic_cba_indicators/tools/_timeout.py#L1-L78)

### Tool Response Processing
- Long tool outputs are truncated for knowledge base outputs, preventing context overflow. [src/agentic_cba_indicators/tools/knowledge_base.py](src/agentic_cba_indicators/tools/knowledge_base.py#L540-L612), [src/agentic_cba_indicators/tools/knowledge_base.py](src/agentic_cba_indicators/tools/knowledge_base.py#L1680-L1720), [src/agentic_cba_indicators/security.py](src/agentic_cba_indicators/security.py#L420-L504)

### Missing Tool Capabilities
- No explicit tool execution telemetry (latency/error counts) despite observability module existing. [src/agentic_cba_indicators/observability.py](src/agentic_cba_indicators/observability.py#L1-L220)
- No audit logging of tool invocations, even though audit module supports it. [src/agentic_cba_indicators/audit.py](src/agentic_cba_indicators/audit.py#L1-L220)

### Tool Orchestration
- Tool orchestration is single-step and sequential; no parallel calls or batching at agent layer. This is acceptable for current scope but creates latency for multi-tool queries.

## 2. Knowledge Base Integration

### Retrieval Mechanisms
- ChromaDB singleton with retries and query caching provides stable read performance. [src/agentic_cba_indicators/tools/knowledge_base.py](src/agentic_cba_indicators/tools/knowledge_base.py#L24-L220)
- Exact-match shortcuts (indicator ID/principle codes) reduce embedding overhead. [src/agentic_cba_indicators/tools/knowledge_base.py](src/agentic_cba_indicators/tools/knowledge_base.py#L84-L132)

### Context Relevance
- Semantic search uses embedding similarity with adjustable threshold; relevance is filtered before formatting. [src/agentic_cba_indicators/tools/knowledge_base.py](src/agentic_cba_indicators/tools/knowledge_base.py#L140-L240)

### Knowledge Freshness
- Versioning metadata exists, but there is no automated staleness detection or invalidation beyond manual re-ingest.

### RAG Quality
- No re-ranking or hybrid retrieval beyond embedding similarity; this is a quality ceiling for ambiguous queries.

### Knowledge Source Diversity
- Focused on internal KB collections (indicators/methods/use cases). External sources are handled through tools, not RAG merging.

## 3. Memory & State Management

### Short-term Memory
- Token budget manager estimates tokens and trims context while preserving tool-use/result pairs. This is a strong foundation for multi-provider support. [src/agentic_cba_indicators/memory.py](src/agentic_cba_indicators/memory.py#L1-L220)
- System prompt budget is reserved based on prompt+tool docs; this is a practical control. [src/agentic_cba_indicators/cli.py](src/agentic_cba_indicators/cli.py#L32-L116)

### Long-term Memory
- Not implemented; no persistence across sessions beyond KB. This aligns with documented deferrals.

### State Persistence
- Conversation manager exposes state, but there is no CLI-level session persistence layer.

## 4. Agent Architecture & Design Patterns

- The system uses a straightforward agent + tools + KB design, with a clean separation of concerns. [src/agentic_cba_indicators/tools/__init__.py](src/agentic_cba_indicators/tools/__init__.py#L1-L200)
- Planning is implicit; no explicit plan/reflect loop or self-correction hooks.
- Error recovery is handled at tool level (retries/timeouts) and by the agent conversation manager. [src/agentic_cba_indicators/tools/_http.py](src/agentic_cba_indicators/tools/_http.py#L1-L220), [src/agentic_cba_indicators/tools/_timeout.py](src/agentic_cba_indicators/tools/_timeout.py#L1-L78)

## 5. Performance & Reliability

- HTTP retries with backoff and response caching reduce external API load. [src/agentic_cba_indicators/tools/_http.py](src/agentic_cba_indicators/tools/_http.py#L1-L220)
- Tool timeout wrapper exists but requires consistent application at registration time. [src/agentic_cba_indicators/tools/_timeout.py](src/agentic_cba_indicators/tools/_timeout.py#L1-L78)
- Query caching for KB reduces redundant searches. [src/agentic_cba_indicators/tools/knowledge_base.py](src/agentic_cba_indicators/tools/knowledge_base.py#L34-L86)

## 6. Security & Safety Concerns

- User input is sanitized and injection patterns are logged. [src/agentic_cba_indicators/security.py](src/agentic_cba_indicators/security.py#L1-L200)
- HTTP error messages are sanitized to remove credentials. [src/agentic_cba_indicators/tools/_http.py](src/agentic_cba_indicators/tools/_http.py#L32-L120)
- Audit logging supports redaction, but is not wired into runtime. [src/agentic_cba_indicators/audit.py](src/agentic_cba_indicators/audit.py#L1-L200)

## 7. Configuration & Extensibility

- Tool registration is explicit and readable. [src/agentic_cba_indicators/tools/__init__.py](src/agentic_cba_indicators/tools/__init__.py#L1-L200)
- Prompt loading uses a minimal prompt by default; the full prompt exists but is unused, risking documentation drift. [src/agentic_cba_indicators/prompts/__init__.py](src/agentic_cba_indicators/prompts/__init__.py#L1-L60), [src/agentic_cba_indicators/prompts/system_prompt.md](src/agentic_cba_indicators/prompts/system_prompt.md#L1-L60)

---

## Critical Issues

1. Observability not integrated into tool execution
   - Impact: No real runtime visibility for tool latency/error rates.
   - Evidence: Metrics collector exists but is not applied to tools. [src/agentic_cba_indicators/observability.py](src/agentic_cba_indicators/observability.py#L1-L220)

2. Audit logging not wired
   - Impact: No audit trail for tool invocations or outcomes despite security design.
   - Evidence: Audit module is standalone with no runtime integration. [src/agentic_cba_indicators/audit.py](src/agentic_cba_indicators/audit.py#L1-L220)

3. Tool discovery depends on internal Strands agent attributes
   - Impact: Potential breakage on Strands upgrades.
   - Evidence: Reliance on `tool_registry` and `tools` attributes. [src/agentic_cba_indicators/tools/_help.py](src/agentic_cba_indicators/tools/_help.py#L62-L118)

## Architecture Recommendations

1. Centralize tool wrapping
   - Wrap all tools with timeout + metrics + audit in a single registration path.
   - Best location: tool assembly in [src/agentic_cba_indicators/tools/__init__.py](src/agentic_cba_indicators/tools/__init__.py#L1-L200).

2. Stabilize tool discovery
   - Prefer a registry provided by Strands if available; otherwise maintain a deterministic, internal tool registry independent of agent internals.
   - Anchor in [src/agentic_cba_indicators/tools/_help.py](src/agentic_cba_indicators/tools/_help.py#L62-L118).

3. Prompt consolidation
   - Remove divergence risk by either using the full prompt or explicitly documenting why minimal is preferred, and keep tool guidance in one source. [src/agentic_cba_indicators/prompts/__init__.py](src/agentic_cba_indicators/prompts/__init__.py#L1-L60)

## Missing Features

1. Tool-level telemetry (metrics + audit) applied uniformly.
2. Knowledge freshness detection or ingestion version enforcement.
3. Optional re-ranking or hybrid retrieval for KB queries.
4. Parallel tool execution strategy for multi-tool requests.

## Quick Wins

1. Apply `instrument_tool` across tools during registration to start collecting latency and success metrics. [src/agentic_cba_indicators/observability.py](src/agentic_cba_indicators/observability.py#L1-L220)
2. Add audit logging in a centralized tool wrapper to capture parameters and results safely. [src/agentic_cba_indicators/audit.py](src/agentic_cba_indicators/audit.py#L1-L220)
3. Ensure `setup_logging()` is invoked at CLI entry points for consistent logging behavior. [src/agentic_cba_indicators/logging_config.py](src/agentic_cba_indicators/logging_config.py#L70-L180), [src/agentic_cba_indicators/cli.py](src/agentic_cba_indicators/cli.py#L1-L220)

## Code-Specific Observations (Atomic Problems → Suggestions)

1. Problem: Observability exists but is not used.
   - Suggestion: Wrap tools with `instrument_tool` during registration.
   - References: [src/agentic_cba_indicators/observability.py](src/agentic_cba_indicators/observability.py#L1-L220), [src/agentic_cba_indicators/tools/__init__.py](src/agentic_cba_indicators/tools/__init__.py#L1-L200)

2. Problem: Audit logging is present but disconnected from tool runtime.
   - Suggestion: Add a wrapper that logs tool invocation + latency around tool execution.
   - References: [src/agentic_cba_indicators/audit.py](src/agentic_cba_indicators/audit.py#L1-L220)

3. Problem: Tool discovery depends on agent internals.
   - Suggestion: Maintain a stable internal registry, and use ToolContext only as a best-effort source.
   - References: [src/agentic_cba_indicators/tools/_help.py](src/agentic_cba_indicators/tools/_help.py#L62-L118), [src/agentic_cba_indicators/cli.py](src/agentic_cba_indicators/cli.py#L96-L120)

4. Problem: Prompt source divergence (full prompt exists but minimal prompt is always used).
   - Suggestion: Either consolidate to one prompt or document intentional split with automated sync checks.
   - References: [src/agentic_cba_indicators/prompts/__init__.py](src/agentic_cba_indicators/prompts/__init__.py#L1-L60), [src/agentic_cba_indicators/prompts/system_prompt.md](src/agentic_cba_indicators/prompts/system_prompt.md#L1-L60)

5. Problem: Tool timeouts are implemented but not enforced globally.
   - Suggestion: Apply the timeout decorator in tool registration to guarantee coverage.
   - References: [src/agentic_cba_indicators/tools/_timeout.py](src/agentic_cba_indicators/tools/_timeout.py#L1-L78)

6. Problem: Token budget relies on heuristic estimation only.
   - Suggestion: Add optional provider-specific estimators when available to reduce trim inaccuracies.
   - References: [src/agentic_cba_indicators/memory.py](src/agentic_cba_indicators/memory.py#L1-L220)

## Prioritized Action Plan

1. P0 (Reliability/Observability)
   - Wrap all tools with instrumentation + audit logging + timeout at registration.
   - Outcome: Consistent telemetry and safety net across tool calls.

2. P1 (Stability)
   - Decouple tool discovery from Strands internals; keep module registry authoritative.

3. P2 (Quality)
   - Consolidate prompt sources or add validation to prevent drift.
   - Add optional reranking for KB queries.

4. P3 (Usability)
   - Explore parallel tool execution for multi-tool user requests.

---

## Implementation Plan with Tracking

Each issue below includes a reference ID and a task list with owners to be assigned. Status defaults to **Planned**.

### CR-ISSUE-001 — Tool telemetry not integrated (metrics + audit + timeout)
**Priority:** P0
**Status:** Done

**Plan:**
1. Create a centralized tool wrapper to apply `instrument_tool`, audit logging, and `timeout()`.
2. Apply the wrapper to all tools when assembling `REDUCED_TOOLS` and `FULL_TOOLS`.
3. Preserve tool metadata (name/docstring) for internal help tools.
4. Add tests validating metrics increment and audit log writes when enabled.

**Tasks:**
- **CR-ISSUE-001-T1**: Implement tool wrapper composition in [src/agentic_cba_indicators/tools/__init__.py](src/agentic_cba_indicators/tools/__init__.py). **Status:** Done
- **CR-ISSUE-001-T2**: Wire audit logging to wrapper using [src/agentic_cba_indicators/audit.py](src/agentic_cba_indicators/audit.py). **Status:** Done
- **CR-ISSUE-001-T3**: Apply timeout decorator from [src/agentic_cba_indicators/tools/_timeout.py](src/agentic_cba_indicators/tools/_timeout.py). **Status:** Done
- **CR-ISSUE-001-T4**: Add metrics tests in [tests](tests) targeting `instrument_tool` usage. **Status:** Done
- **CR-ISSUE-001-T5**: Add audit logging tests in [tests](tests) gated by `AGENTIC_CBA_AUDIT_LOG`. **Status:** Done

**Required Detail:**
- Wrapper order: `timeout()` (outer) → audit logging → `instrument_tool` (inner).
- Audit logging should sanitize parameters and truncate results using existing helpers.
- Failures must be logged with error category and latency if available.

---

### CR-ISSUE-002 — Tool discovery depends on Strands internals
**Priority:** P1
**Status:** Done

**Plan:**
1. Add a deterministic tool registry owned by the project.
2. Populate registry at tool assembly time to reflect reduced/full sets.
3. Use registry as primary source; ToolContext as secondary.
4. Add tests for registry-first behavior and fallback.

**Tasks:**
- **CR-ISSUE-002-T1**: Define registry structure in [src/agentic_cba_indicators/tools/_help.py](src/agentic_cba_indicators/tools/_help.py). **Status:** Done
- **CR-ISSUE-002-T2**: Populate registry during tool assembly in [src/agentic_cba_indicators/tools/__init__.py](src/agentic_cba_indicators/tools/__init__.py). **Status:** Done
- **CR-ISSUE-002-T3**: Update `list_tools()`/`describe_tool()` to use registry first. [src/agentic_cba_indicators/tools/_help.py](src/agentic_cba_indicators/tools/_help.py) **Status:** Done
- **CR-ISSUE-002-T4**: Add tests for registry and ToolContext fallback in [tests](tests). **Status:** Done

**Required Detail:**
- Registry must preserve tool ordering to maintain category output consistency.
- Fallback to ToolContext only if registry is empty.

---

### CR-ISSUE-003 — Prompt source divergence (full vs minimal)
**Priority:** P2
**Status:** Done

**Plan:**
1. Decide the single authoritative prompt source.
2. Update prompt loader to reflect the decision.
3. Document prompt strategy to prevent future drift.

**Tasks:**
- **CR-ISSUE-003-T1**: Consolidate prompt selection logic in [src/agentic_cba_indicators/prompts/__init__.py](src/agentic_cba_indicators/prompts/__init__.py). **Status:** Done
- **CR-ISSUE-003-T2**: Update usage in [src/agentic_cba_indicators/cli.py](src/agentic_cba_indicators/cli.py) if prompt name changes. **Status:** Done
- **CR-ISSUE-003-T3**: Add documentation note in [README.md](README.md) or [docs](docs). **Status:** Done

**Required Detail:**
- If both prompts remain, add a sync check and fail fast on divergence.

---

### CR-ISSUE-004 — Knowledge freshness detection missing
**Priority:** P2
**Status:** Done

**Plan:**
1. Add freshness logic based on ingestion timestamps.
2. Provide configurable TTL via environment variable.
3. Surface freshness warnings in version/summary tools.
4. Add tests for staleness thresholds.

**Tasks:**
- **CR-ISSUE-004-T1**: Implement freshness check in [src/agentic_cba_indicators/tools/knowledge_base.py](src/agentic_cba_indicators/tools/knowledge_base.py). **Status:** Done
- **CR-ISSUE-004-T2**: Expose TTL config and document defaults in [docs/known-limitations.md](docs/known-limitations.md). **Status:** Done
- **CR-ISSUE-004-T3**: Add staleness tests in [tests](tests). **Status:** Done

**Required Detail:**
- TTL should default to disabled (no warning) unless env var set.

---

### CR-ISSUE-005 — No re-ranking or hybrid retrieval for KB queries
**Priority:** P2
**Status:** Done

**Plan:**
1. Add optional lexical scoring for reranking.
2. Combine embedding similarity and lexical score for final ordering.
3. Make reranking opt-in via a flag or config.
4. Add tests for ranking stability and correctness.

**Tasks:**
- **CR-ISSUE-005-T1**: Implement lexical scorer in [src/agentic_cba_indicators/tools/knowledge_base.py](src/agentic_cba_indicators/tools/knowledge_base.py). **Status:** Done
- **CR-ISSUE-005-T2**: Add `rerank` parameter to relevant search tools. [src/agentic_cba_indicators/tools/knowledge_base.py](src/agentic_cba_indicators/tools/knowledge_base.py) **Status:** Done
- **CR-ISSUE-005-T3**: Add ranking tests in [tests](tests). **Status:** Done

**Required Detail:**
- Maintain backward compatibility by defaulting `rerank=False`.

---

### CR-ISSUE-006 — Parallel tool execution not supported
**Priority:** P3
**Status:** Done

**Plan:**
1. Add a feature flag for parallel execution in the CLI/agent config.
2. Implement a bounded thread pool for multi-tool requests.
3. Preserve result ordering to avoid response drift.
4. Add integration tests for parallel workflows.

**Tasks:**
- **CR-ISSUE-006-T1**: Add configuration flag and wiring in [src/agentic_cba_indicators/cli.py](src/agentic_cba_indicators/cli.py). **Status:** Done
- **CR-ISSUE-006-T2**: Implement bounded executor wrapper for tools in [src/agentic_cba_indicators/tools/__init__.py](src/agentic_cba_indicators/tools/__init__.py). **Status:** Done
- **CR-ISSUE-006-T3**: Add integration tests in [tests/test_integration.py](tests/test_integration.py). **Status:** Done

**Required Detail:**
- Restrict parallelism to read-only tools; avoid concurrent access to mutable/shared state.
