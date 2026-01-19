# Known Limitations

This document describes known limitations of the Agentic CBA Indicators system. These are acknowledged constraints that don't require immediate resolution but are documented for transparency and future planning.

**Last updated:** 2026-01-19

## Table of Contents

- [Tool System](#tool-system)
- [Knowledge Base](#knowledge-base)
- [Memory & Context](#memory--context)
- [Reasoning & Planning](#reasoning--planning)
- [Performance & Caching](#performance--caching)
- [Security & Validation](#security--validation)
- [Observability & Debugging](#observability--debugging)
- [Extensibility](#extensibility)
- [Prompts & Configuration](#prompts--configuration)

---

## Tool System

### P3-001: No Tool Versioning
**Description:** No versioning or deprecation mechanism for tool APIs.

**Impact:** Tool signature changes require code updates across all usages.

**Rationale:** Current tool set is stable; versioning adds complexity without current benefit.

**Future:** Consider if tool ecosystem grows significantly.

---

### P3-002: Inconsistent Error Handling
**Description:** Error handling varies between tools; some return error strings, others raise exceptions.

**Impact:** Inconsistent user experience for error messages.

**Rationale:** Tools evolved incrementally; standardization is lower priority than functionality.

**Mitigation:** All errors are caught at agent level and presented cleanly.

---

### P3-003: Long Tool Outputs ✅ MITIGATED
**Description:** Tool outputs can be very long, potentially exceeding context limits.

**Status:** **Mitigated in TASK113** - `truncate_tool_output()` limits output to 50K characters.

---

### P3-004: No Agent-Level Output Caching
**Description:** Tool results are not cached at the agent level within a conversation.

**Impact:** Same tool may be called multiple times with same parameters.

**Rationale:** API-level caching (TASK112) provides partial mitigation. Full conversation caching deferred (ADR-004).

**Future:** Consider Strands hooks integration when available.

---

### P3-005: No Parallel Tool Execution
**Description:** Tools run sequentially; no concurrent execution support.

**Impact:** Multi-tool queries take longer than necessary.

**Rationale:** Strands framework handles tool execution; parallelism requires framework support.

**Future:** Monitor Strands roadmap for async/parallel tool support.

---

### P3-024: Tool Context Discovery Relies on Agent Internals
**Description:** Internal help tools inspect `ToolContext.agent.tool_registry` or `agent.tools`.

**Impact:** Changes in Strands agent internals could break tool discovery.

**Rationale:** No public API currently exposes the active tool registry.

**Mitigation:** Module-level registry fallback (`set_active_tools()`) and unit tests.

**Future:** Replace with official Strands API when available.

---

## Knowledge Base

### P3-006: Fixed Embedding Model
**Description:** Embedding model (bge-m3) is fixed with no runtime selection.

**Impact:** Cannot easily switch to different embedding models.

**Rationale:** bge-m3 provides good multilingual support and 8K context. Model switching requires KB rebuild.

**Future:** Document model switch procedure if needed.

---

### P3-007: No Cross-Attention Re-ranking
**Description:** No query-document cross-attention for re-ranking search results.

**Impact:** Search relies purely on embedding similarity.

**Rationale:** Current semantic search quality is acceptable. Re-ranking adds latency and complexity.

**Future:** Consider if search quality issues are reported.

---

### P3-008: No Knowledge Staleness Detection
**Description:** No mechanism to detect or invalidate stale knowledge.

**Impact:** KB may contain outdated information if source data changes.

**Rationale:** Source data (Excel files) are manually versioned. Versioning metadata (TASK102) tracks ingestion time.

**Mitigation:** Clear KB and re-ingest when source data updates.

---

### P3-009: Embedding Truncation
**Description:** Documents truncated at 24,000 characters for embedding.

**Impact:** Very long documents may lose tail content in embeddings.

**Rationale:** 24K chars ≈ 6K tokens, fitting within bge-m3's 8K context with margin.

**Mitigation:** Most indicator documents are well under this limit.

---

### P3-010: No Multi-Source Result Merging
**Description:** No mechanism to cross-reference or merge results from multiple collections.

**Impact:** User must manually correlate indicator and method information.

**Rationale:** `get_indicator_details()` already combines indicator + methods. Advanced merging adds complexity.

---

## Memory & Context

### P3-011: No Memory Importance Ranking
**Description:** No ranking of memory/context by importance.

**Impact:** All conversation history treated equally.

**Rationale:** Token-budget manager (TASK108) handles context limits. Importance ranking deferred (ADR-003).

**Future:** Consider if context overflow becomes problematic.

---

### P3-025: Heuristic Token Estimation
**Description:** Token budgets use a provider-agnostic chars/4 heuristic, not tokenizer-specific counts.

**Impact:** Estimates can deviate from actual provider token counts, affecting trimming precision.

**Rationale:** Multi-provider support makes a single tokenizer (e.g., tiktoken) unreliable across models.

**Mitigation:** `system_prompt_budget` reserves space for prompt + tools; trimming is conservative.

**Future:** Add provider-specific tokenizers when unified APIs become available.

---

## Reasoning & Planning

### P3-012: No Visible Planning Traces
**Description:** No tree search or planning traces visible to users.

**Impact:** Users cannot see agent's reasoning process.

**Rationale:** Strands framework handles agent loop internally. Tracing deferred (ADR-002).

**Future:** Consider debug mode with reasoning traces.

---

### P3-013: Implicit Multi-Step Planning
**Description:** Multi-step tasks rely entirely on LLM's implicit planning.

**Impact:** Complex workflows may not be optimally planned.

**Rationale:** Strands agents use chain-of-thought naturally. Explicit planning adds latency.

**Future:** Consider ReAct-style explicit planning for complex queries.

---

### P3-014: No Dead-End Detection
**Description:** No detection when tools consistently fail.

**Impact:** Agent may retry failed approaches without recognition.

**Rationale:** Self-correction mechanisms deferred (ADR-005).

**Mitigation:** Tool retry limits prevent infinite loops.

---

### P3-015: No Learning from Corrections
**Description:** No mechanism to learn from user corrections.

**Impact:** Same mistakes may recur across sessions.

**Rationale:** Learning requires long-term memory (deferred, ADR-003) and fine-tuning infrastructure.

**Future:** Consider feedback collection for prompt improvement.

---

## Performance & Caching

### P3-016: Geocoding Cache Thread Safety ✅ MITIGATED
**Description:** Geocoding cache was previously not thread-safe.

**Status:** **Mitigated in TASK120** - replaced with `cachetools.TTLCache` + `threading.Lock`.

---

## Security & Validation

### P3-017: No API Response Schema Validation
**Description:** External API responses are not validated against schemas.

**Impact:** Unexpected response formats may cause errors.

**Rationale:** Response parsing includes defensive checks. Full schema validation adds overhead.

**Mitigation:** Error handling catches malformed responses.

---

### P3-018: No Read-Only Tool Distinction
**Description:** No distinction between read-only and write tools.

**Impact:** All tools treated equivalently by agent.

**Rationale:** Current tools are all read-only (queries, searches). No write operations exist.

**Future:** Consider if write operations are added.

---

## Observability & Debugging

### P3-019: No Tool Parameter Logging
**Description:** Tool parameters not logged for debugging.

**Impact:** Harder to diagnose tool call issues.

**Rationale:** Audit logging (TASK105) logs tool names but not parameters to avoid log bloat.

**Mitigation:** Debug logging available at TRACE level.

---

## Extensibility

### P3-020: No Dynamic Tool Loading
**Description:** No plugin system for dynamic tool loading.

**Impact:** New tools require code changes and restart.

**Rationale:** Tool set is domain-specific and curated. Plugin system adds security concerns.

**Future:** Consider MCP tool integration for external tools.

---

### P3-021: No Hot-Reload
**Description:** Tool changes require application restart.

**Impact:** Development iteration requires restart.

**Rationale:** Standard Python behavior. Hot-reload adds complexity.

**Mitigation:** Fast startup time (~2s).

---

## Prompts & Configuration

### P3-022: No Prompt Versioning
**Description:** No version tracking or A/B testing for prompts.

**Impact:** Cannot easily compare prompt variations.

**Rationale:** Prompts are tracked in git. A/B testing requires evaluation infrastructure.

**Future:** Consider if prompt optimization becomes focus.

---

### P3-023: No Dynamic Prompt Variables
**Description:** No template variables for runtime prompt injection.

**Impact:** Prompts are static at startup.

**Rationale:** Current prompts are sufficient. Dynamic injection adds security risk.

**Future:** Consider if per-user customization needed.

---

## Summary

| Category | Count | Critical | Mitigated |
|----------|-------|----------|-----------|
| Tool System | 6 | 0 | 1 (P3-003) |
| Knowledge Base | 5 | 0 | 0 |
| Memory & Context | 2 | 0 | 0 |
| Reasoning & Planning | 4 | 0 | 0 |
| Performance & Caching | 1 | 0 | 1 (P3-016) |
| Security & Validation | 2 | 0 | 0 |
| Observability & Debugging | 1 | 0 | 0 |
| Extensibility | 2 | 0 | 0 |
| Prompts & Configuration | 2 | 0 | 0 |
| **Total** | **25** | **0** | **2** |

## References

- Code Review: `docs/development/code-reviews/agentic_ai_code_review_report-2026-01-18-v1.md`
- Architecture Decision Records: `docs/adr/`
- Deferred Features Summary: `docs/adr/ADR-006-deferred-features-summary.md`
