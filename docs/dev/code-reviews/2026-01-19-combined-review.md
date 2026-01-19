# Repository Code Review (Combined)

**Date:** 2026-01-19
**Reviewers:** Claude Opus 4.5, GPT-5.2-Codex
**Repository:** agentic-cba-indicators

---

## Executive Summary

This document consolidates findings from two independent AI code reviews performed on 2026-01-19. Overlapping findings have been merged, and all unique valid findings retained. The combined review identifies **35 distinct issues** across security, reliability, correctness, and configuration categories.

### Critical Issues (Top 15)

1. **CR-0001 (High):** Real API key and emails stored in local `.env` file
2. **CR-0002 (Blocker):** Duplicate `if __name__ == "__main__"` guard causes CLI to run twice
3. **CR-0003 (High):** ChromaDB singleton lacks resource cleanup/shutdown hook
4. **CR-0004 (High):** Token budget manager's tool result truncation is destructive
5. **CR-0005 (High):** Geocode cache empty dict marker returns fake (0,0) location
6. **CR-0006 (High):** Missing timeout decorator on several external API tools
7. **CR-0007 (High):** Provider factory may leak API keys in exception stack traces
8. **CR-0008 (High):** Timed-out tools continue running in background threads
9. **CR-0009 (Medium):** Streamlit UI agent factory ignores `system_prompt_budget`
10. **CR-0010 (Medium):** Biodiversity longitude range formula explodes near equator
11. **CR-0011 (Medium):** Unit symbols corrupted (°C, m², CO2e, etc.) across tools
12. **CR-0012 (Medium):** Valid zero values treated as missing across multiple tools
13. **CR-0013 (Medium):** Ingestion script silently continues on embedding failures
14. **CR-0014 (Medium):** GFW retry settings unused; transient failures not retried
15. **CR-0015 (Medium):** Global embedding rate limit state not thread-safe

### Risk Posture

**Overall: Medium-High**

The repository demonstrates solid engineering practices with proper thread-safety patterns, defensive input sanitization, and comprehensive error handling in most modules. However, critical issues require attention:

- **Security:** API key exposure risk (local dev only), credential leakage via exceptions
- **Reliability:** Resource cleanup gaps (ChromaDB, audit logger), unbounded thread spawning
- **Data Integrity:** Silent embedding failures, destructive truncation, encoding issues
- **Correctness:** Geocode cache bug, longitude formula bug, zero-value handling
- **Observability:** Correlation ID edge cases, missing CI workflows

---

## Review Methodology

### Scanned Areas

| Area | Files/Patterns |
|------|----------------|
| Source code | `src/agentic_cba_indicators/**/*.py` (21 files) |
| Tool modules | `src/agentic_cba_indicators/tools/**/*.py` (22 files) |
| Configuration | `pyproject.toml`, `providers.yaml`, `config/**/*.py`, `.env` |
| Tests | `tests/**/*.py` (21 files) |
| Scripts | `scripts/**/*.py` (3 files) |
| Documentation | `docs/**/*.md`, `README.md`, `CONTRIBUTING.md` |
| Build/CI | `Makefile`, `dev.ps1`, `.github/` |

### Source Reviews

| Reviewer | Document |
|----------|----------|
| Claude Opus 4.5 | `2026-01-19-opus-review.md` (24 findings) |
| GPT-5.2-Codex | `2026-01-19-gpt52-codex-review.md` (16 findings) |

### Assumptions and Limitations

1. No CI/CD pipeline files (`.github/workflows/`) were found
2. Docker/IaC configurations were not present
3. Analysis is static; runtime behavior assumptions based on code reading
4. `.env` file is gitignored and exists for local development only
5. Some hypotheses require runtime verification

---

## Issue Index (Tracking System)

| ID | Severity | Category | Component | File:Line | Title | Source | Status |
|----|----------|----------|-----------|-----------|-------|--------|--------|
| CR-0001 | High | Security | Env/Secrets | `.env` | Real API key and emails in local `.env` | GPT | ⏭️ Skipped |
| CR-0002 | Blocker | Bug | CLI | cli.py:357-359 | Duplicate `__main__` guard | Both | ✅ Fixed |
| CR-0003 | High | Reliability | knowledge_base | knowledge_base.py:93-130 | ChromaDB singleton lacks cleanup | Opus | ✅ Fixed |
| CR-0004 | High | Broken behaviour | memory | memory.py:510-543 | Destructive tool result truncation | Opus | ✅ Fixed |
| CR-0005 | High | Bug | _geo | _geo.py:107-126 | Geocode cache empty dict returns (0,0) | Both | ✅ Fixed |
| CR-0006 | High | Reliability | tools | Multiple | Missing timeout decorator | Opus | ✅ Fixed |
| CR-0007 | High | Security | provider_factory | provider_factory.py:266-295 | API key leakage via exceptions | Opus | ✅ Fixed |
| CR-0008 | High | Reliability | _timeout | _timeout.py:31-47 | Timed-out tools continue in background | Both | ✅ Fixed |
| CR-0009 | Medium | Broken behaviour | ui | ui.py:77-109 | UI missing system_prompt_budget | Both | ✅ Fixed |
| CR-0010 | Medium | Bug | biodiversity | biodiversity.py:393 | Longitude range explodes near equator | GPT | ✅ Fixed |
| CR-0011 | Medium | Bug | Multiple | weather.py, etc. | Unit symbols corrupted (mojibake) | GPT | ✅ Verified OK |
| CR-0012 | Medium | Bug | Multiple | labor.py:225, etc. | Zero values treated as missing | GPT | ✅ Fixed |
| CR-0013 | Medium | Data loss | ingest_excel | ingest_excel.py | Silent embedding failure | Opus | ✅ Verified OK |
| CR-0014 | Medium | Reliability | forestry | forestry.py:37 | GFW retry settings unused | GPT | ✅ Fixed |
| CR-0015 | Medium | Reliability | _embedding | _embedding.py:118-160 | Rate limit state not thread-safe | Opus | ✅ Fixed |
| CR-0016 | Medium | Observability | cli | cli.py:343-356 | Correlation ID not cleared on error | Opus | ✅ Fixed |
| CR-0017 | Medium | Bug | _help | _help.py:96-104 | Greedy keyword categorization | Opus | ✅ Fixed |
| CR-0018 | Medium | Bug | knowledge_base | knowledge_base.py:55-60 | Mutable tuple cache keys | Opus | ✅ Fixed |
| CR-0019 | Medium | Bug | weather | weather.py:154 | Forecast array mismatch (Hypothesis) | GPT | ✅ Fixed |
| CR-0020 | Medium | Security | security | security.py:165-175 | Truncation can split UTF-8 | Opus | ✅ Fixed |
| CR-0021 | Medium | Bug | forestry | forestry.py:100+ | Unused validation result | Opus | ✅ Fixed |
| CR-0022 | Medium | Config/Build | pyproject | pyproject.toml:77 | Missing LICENSE file in sdist | GPT | ✅ Fixed |
| CR-0023 | Low | Bug | _geo | _geo.py:216 | `clear_cache()` uses undefined OrderedDict | GPT | ✅ Fixed |
| CR-0024 | Low | Reliability | audit | audit.py:200+ | Audit logger file handle unclosed | Opus | ✅ Verified OK |
| CR-0025 | Low | Bug | soilgrids | soilgrids.py:45-55 | Texture classification edge cases | Opus | ✅ Fixed |
| CR-0026 | Low | Test gap | tests | test_chromadb_singleton.py | Missing concurrent access test | Opus | ✅ Fixed |
| CR-0027 | Low | API/Contract | tools/__init__ | tools/__init__.py:138-166 | Tool lists mutable | Opus | ✅ Fixed |
| CR-0028 | Low | Docs mismatch | Multiple | tools/__init__.py, README | Tool count inconsistent | GPT | ✅ Fixed |
| CR-0029 | Low | Docs mismatch | pyproject | pyproject.toml:65-68 | Commented project.urls | Opus | ✅ Fixed |
| CR-0030 | Low | Config/Build | pyproject | pyproject.toml:183-195 | Duplicate dev dependencies | Opus | ✅ Fixed |
| CR-0031 | Low | Dead code | commodities | commodities.py:626 | Duplicate returns | GPT | ✅ Fixed |
| CR-0032 | Low | Dead code | socioeconomic | socioeconomic.py:137-138 | Unused variable | Opus | ✅ Verified OK |
| CR-0033 | Low | Reliability | _crossref | _crossref.py:170-180 | Regex not compiled | Opus | ✅ Fixed |
| CR-0034 | Low | Broken behaviour | cli, tools | cli.py:201, etc. | Control chars/mojibake in output | GPT | ✅ Verified OK |
| CR-0035 | Low | Test gap | CI | .github/ | No CI workflows for tests/linting | GPT | ⏭️ Skipped |

---

## Findings (Detailed)

### CR-0001: Real API key and emails stored in local `.env` file

- **Severity:** High
- **Category:** Security
- **Component:** Env/Secrets
- **Location:** `.env:11`
- **Source:** GPT-5.2-Codex
- **Evidence:**
  ```
  USDA_FAS_API_KEY=<REDACTED>
  CROSSREF_EMAIL=<REDACTED>
  UNPAYWALL_EMAIL=<REDACTED>
  ```
- **Impact:**
  - API key exposure enables unauthorized usage or quota exhaustion
  - Personal emails can be harvested if `.env` is accidentally committed
- **Mitigating Factors:**
  - File is in `.gitignore` and exists for local development only
  - No evidence of exposure in git history
- **Reproduction/Trigger:**
  - Open `.env` in repo root
- **Recommended fix:**
  - Rotate the USDA FAS key as a precaution
  - Consider using `.env.local` pattern with `.env.example` for placeholders
  - Add pre-commit secret scanning
- **Tests/Verification:**
  - Verify git history has no `.env` commits
  - Confirm rotated keys work

---

### CR-0002: Duplicate `if __name__ == "__main__"` guard causes CLI to run twice

- **Severity:** Blocker
- **Category:** Bug
- **Component:** CLI
- **Location:** [cli.py:357-359](src/agentic_cba_indicators/cli.py#L357-L359)
- **Source:** Both reviewers
- **Evidence:**
  ```python
  if __name__ == "__main__":
      main()
  if __name__ == "__main__":
      main()
  ```
- **Impact:**
  - CLI starts a second session after the first exits; users must quit twice
  - Agent created twice, doubling resource consumption
  - Could cause race conditions if ChromaDB accessed during overlapping startups
- **Reproduction/Trigger:**
  - Run `python src/agentic_cba_indicators/cli.py` directly and exit
- **Recommended fix:**
  - Remove the duplicate `if __name__ == "__main__": main()` block (lines 358-359)
- **Tests/Verification:**
  - Run cli.py directly and verify banner appears only once
  - Add linting rule to detect duplicate main guards

---

### CR-0003: ChromaDB singleton lacks resource cleanup/shutdown hook

- **Severity:** High
- **Category:** Reliability
- **Component:** knowledge_base
- **Location:** [knowledge_base.py:93-175](src/agentic_cba_indicators/tools/knowledge_base.py#L93-L175)
- **Source:** Opus
- **Evidence:**
  ```python
  _chroma_client: ClientAPI | None = None
  _chroma_client_lock = threading.Lock()

  def _get_chroma_client() -> ClientAPI:
      global _chroma_client
      # ... client creation but no shutdown/cleanup registration
  ```
- **Impact:**
  - SQLite write-ahead log may not be flushed on process exit
  - Database could be left in inconsistent state on abnormal termination
  - Potential data loss for recently upserted embeddings
- **Reproduction/Trigger:**
  - Run agent, add data, force-kill process (Ctrl+C during write)
  - Check `kb_data/chroma.sqlite3` for WAL files
- **Recommended fix:**
  - Register an `atexit.register()` handler that calls cleanup
  - Alternatively, expose a `shutdown_chroma_client()` function and call from CLI exit paths
- **Tests/Verification:**
  - Unit test that verifies cleanup is called on module unload
  - Integration test with process termination scenarios

---

### CR-0004: Token budget manager's tool result truncation is destructive

- **Severity:** High
- **Category:** Broken behaviour
- **Component:** memory
- **Location:** [memory.py:510-543](src/agentic_cba_indicators/memory.py#L510-L543)
- **Source:** Opus
- **Evidence:**
  ```python
  def _try_truncate_tool_results(self, messages: list[dict[str, Any]]) -> bool:
      if len(text) > 1000:  # Truncate large results
          rc["text"] = truncation_message  # Overwrites ALL content
          truncated = True
  ```
- **Impact:**
  - Agent loses context about tool results, leading to confused responses
  - User queries that depend on tool output fail silently
  - No indication to user which tool results were lost
- **Reproduction/Trigger:**
  - Query knowledge base with verbose results
  - Continue conversation until context overflow triggers
- **Recommended fix:**
  - Preserve a meaningful prefix (e.g., first 800 chars + "... [truncated]")
  - Log which tool results were truncated
  - Consider making truncation threshold configurable
- **Tests/Verification:**
  - Unit test verifying partial content preservation
  - Integration test with conversation exceeding context budget

---

### CR-0005: Geocode cache empty dict marker returns fake (0,0) location

- **Severity:** High
- **Category:** Bug
- **Component:** _geo
- **Location:** [_geo.py:107-126](src/agentic_cba_indicators/tools/_geo.py#L107-L126)
- **Source:** Both reviewers
- **Evidence:**
  ```python
  cached = _geocode_cache.get(cache_key)
  if cached is not None:
      return GeoLocation(... latitude=cached.get("latitude", 0.0), ...)
  ...
  _geocode_cache[cache_key] = {}  # Empty dict marks "not found"
  ```
  The empty dict `{}` passes `cached is not None`, causing GeoLocation construction with defaults.
- **Impact:**
  - Cities previously not found return malformed GeoLocation objects
  - Downstream tools receive `(0.0, 0.0)` coordinates (Null Island)
  - Weather and soil queries for invalid cities return data for wrong location
- **Reproduction/Trigger:**
  - Call `geocode_city("NonexistentCity")` twice
  - Second call returns GeoLocation with 0.0 coords instead of None
- **Recommended fix:**
  ```python
  if cached is not None:
      if not cached:  # Empty dict = not found marker
          return None
      return GeoLocation(...)
  ```
- **Tests/Verification:**
  - Unit test for cache hit on previously not-found city
  - Verify None is returned, not malformed GeoLocation

---

### CR-0006: Missing timeout decorator on several external API tools

- **Severity:** High
- **Category:** Reliability
- **Component:** tools
- **Location:** Multiple files
- **Source:** Opus
- **Status:** ✅ **FIXED** - Added @timeout decorator to all external API tools
- **Implementation:**
  - `agriculture.py`: Added `@timeout(30)` to 4 tools: `get_forest_statistics`, `get_crop_production`, `get_land_use`, `search_fao_indicators`
  - `biodiversity.py`: Added `@timeout(30)` to 4 tools: `search_species`, `get_species_occurrences`, `get_biodiversity_summary`, `get_species_taxonomy`
  - `commodities.py`: Added `@timeout(30)` to 5 tools: `get_commodity_production`, `get_commodity_trade`, `compare_commodity_producers`, `list_fas_commodities`, `search_commodity_data`
  - `forestry.py`: Added `@timeout(60)` to 4 tools (60s because GFW API is slow): `get_tree_cover_loss_trends`, `get_tree_cover_loss_by_driver`, `get_forest_carbon_stock`, `get_forest_extent`
  - `gender.py`: Added `@timeout(30)` to 4 tools: `get_gender_indicators`, `compare_gender_gaps`, `get_gender_time_series`, `search_gender_indicators`
  - `labor.py`: Added `@timeout(30)` to 4 tools: `get_labor_indicators`, `get_employment_by_gender`, `get_labor_time_series`, `search_labor_indicators`
  - `sdg.py`: Added `@timeout(30)` to 4 tools: `get_sdg_progress`, `search_sdg_indicators`, `get_sdg_series_data`, `get_sdg_for_cba_principle`
- **Total:** 29 tools now have timeout protection

---

### CR-0007: Provider factory may leak API keys in exception stack traces

- **Severity:** High
- **Category:** Security
- **Component:** provider_factory
- **Location:** [provider_factory.py:266-295](src/agentic_cba_indicators/config/provider_factory.py#L266-L295)
- **Source:** Opus
- **Evidence:**
  ```python
  return AnthropicModel(
      client_args={"api_key": provider_config.api_key},
  )
  ```
  If the model constructor raises an exception, the stack trace may include credentials.
- **Impact:**
  - API keys could appear in error logs
  - Shared logs or crash reports expose credentials
- **Reproduction/Trigger:**
  - Set an invalid API key format
  - Run CLI and observe exception traceback
- **Recommended fix:**
  - Wrap model creation in try/except and sanitize errors before re-raising
  - Use a ProviderCreationError that doesn't include credentials
- **Tests/Verification:**
  - Unit test with mock model that raises exception
  - Verify API key not in exception message

---

### CR-0008: Timed-out tools continue running in background threads

- **Severity:** High
- **Category:** Reliability
- **Component:** _timeout
- **Location:** [_timeout.py:31-47](src/agentic_cba_indicators/tools/_timeout.py#L31-L47)
- **Source:** Both reviewers (Opus: unbounded spawning, GPT: no cancellation)
- **Evidence:**
  ```python
  with ThreadPoolExecutor(max_workers=1) as executor:
      future = executor.submit(func, *args, **kwargs)
      return future.result(timeout=seconds)
  ```
- **Impact:**
  - Each tool invocation creates a new ThreadPoolExecutor (unbounded spawning)
  - Timed-out functions keep running, causing duplicate API calls or resource leaks
  - Thread exhaustion under high concurrency
- **Reproduction/Trigger:**
  - Call a long-running tool with short timeout
  - Observe background work continuing after timeout
- **Recommended fix:**
  - Use a module-level bounded executor shared across calls
  - Cancel futures on timeout
  - Consider process-based timeouts for safe termination
- **Tests/Verification:**
  - Load test with concurrent tool calls
  - Verify thread count stays bounded
  - Assert timed-out functions don't continue mutating state

---

### CR-0009: Streamlit UI agent factory ignores `system_prompt_budget`

- **Severity:** Medium
- **Category:** Broken behaviour
- **Component:** ui
- **Location:** [ui.py:77-109](src/agentic_cba_indicators/ui.py#L77-L109)
- **Source:** Both reviewers
- **Evidence:**
  ```python
  # UI:
  if agent_config.context_budget is not None:
      conversation_manager = TokenBudgetConversationManager(
          max_tokens=agent_config.context_budget,
      )  # Missing system_prompt_budget

  # CLI correctly uses:
  conversation_manager = TokenBudgetConversationManager(
      max_tokens=agent_config.context_budget,
      system_prompt_budget=system_prompt_budget,
  )
  ```
- **Impact:**
  - UI agents use full context_budget without reserving space for system prompt
  - Context overflow more likely in UI compared to CLI
  - Inconsistent behavior between entry points
- **Reproduction/Trigger:**
  - Run Streamlit UI with context_budget set and large tool set
  - Have long conversation
- **Recommended fix:**
  - Calculate `system_prompt_budget` in `create_agent_for_ui()` matching CLI pattern
- **Tests/Verification:**
  - Unit test comparing UI and CLI agent configuration parity

---

### CR-0010: Biodiversity longitude range formula explodes near equator

- **Severity:** Medium
- **Category:** Bug
- **Component:** biodiversity
- **Location:** [biodiversity.py:393](src/agentic_cba_indicators/tools/biodiversity.py#L393)
- **Source:** GPT-5.2-Codex
- **Evidence:**
  ```python
  lon_range = radius_km / (111 * abs(lat) / 90 + 0.001) if abs(lat) < 89 else ...
  ```
- **Impact:**
  - At or near the equator, `abs(lat)` is ~0, making `lon_range` huge
  - Invalid bounding boxes or overly broad queries
- **Reproduction/Trigger:**
  - Call `get_biodiversity_summary("0,0", radius_km=50)`
  - Inspect the request bounds
- **Recommended fix:**
  - Use cosine-based formula for longitude scaling: `lon_range = radius_km / (111 * cos(radians(lat)))`
  - Clamp to valid bounds
- **Tests/Verification:**
  - Add tests for lat=0 and lat=80 that validate reasonable lon_range

---

### CR-0011: Unit symbols corrupted (°C, m², CO2e, etc.) across tools

- **Severity:** Medium
- **Category:** Bug
- **Component:** Multiple tools
- **Location:** weather.py:104, nasa_power.py, soilgrids.py, forestry.py, socioeconomic.py
- **Source:** GPT-5.2-Codex
- **Status:** ✅ **VERIFIED OK** - Files are properly UTF-8 encoded with correct Unicode symbols (°C, m², CO₂, km², dm³)
- **Evidence:**
  ```python
  "øC"        # should be "°C" (weather.py)
  "MJ/mı/day" # should be "MJ/m²/day" (nasa_power.py)
  "kg/dmü"    # should be "kg/dm³" (soilgrids.py)
  "COż"       # should be "CO₂" (forestry.py)
  "kmı"       # should be "km²" (socioeconomic.py)
  ```
- **Verification:** Grep searches found correct symbols in all files. No mojibake patterns detected.

---

### CR-0012: Valid zero values treated as missing across multiple tools

- **Severity:** Medium
- **Category:** Bug
- **Component:** Multiple tools
- **Location:** labor.py:225, nasa_power.py:387, soilgrids.py:286, sdg.py:373, biodiversity.py:309
- **Source:** GPT-5.2-Codex
- **Evidence:**
  ```python
  # labor.py - truthiness check fails for 0
  if prev_value and value:
      change = float(value) - float(prev_value)
  ```
- **Impact:**
  - Legitimate zero values (0 precipitation, 0% unemployment) are omitted or shown as "N/A"
  - Skews summaries and trends
- **Reproduction/Trigger:**
  - Provide data with 0.0 values; observe missing output/trend
- **Recommended fix:**
  - Use explicit `is not None` checks instead of truthiness
- **Tests/Verification:**
  - Add unit tests for zero values in each affected tool

---

### CR-0013: Ingestion script silently continues on embedding failures

- **Severity:** Medium
- **Category:** Data loss
- **Component:** ingest_excel
- **Location:** scripts/ingest_excel.py (embedding batch processing section)
- **Source:** Opus
- **Status:** ✅ **VERIFIED OK** - Script already tracks and reports embedding failures
- **Implementation:**
  - Tracks `failed_ids` in `upsert_indicators()` and `upsert_methods()`
  - Prints warnings: `"WARNING: Skipping N indicators due to embedding failures"`
  - Adds failures to `summary["errors"]`
  - Exits with status 1 if errors occurred
  - Has `--strict` mode that fails immediately on any embedding error

---

### CR-0014: GFW retry settings unused; transient API failures not retried

- **Severity:** Medium
- **Category:** Reliability
- **Component:** forestry
- **Location:** [forestry.py:37](src/agentic_cba_indicators/tools/forestry.py#L37)
- **Source:** GPT-5.2-Codex
- **Status:** ✅ **FIXED** - Implemented retry logic with exponential backoff
- **Implementation:**
  - Added `GFW_BACKOFF_BASE` (1.0s) and `GFW_BACKOFF_MAX` (30.0s) constants
  - `_gfw_get()` and `_gfw_post()` now retry on 429 and 5xx errors
  - Uses exponential backoff with jitter: `delay = min(base * 2^attempt + jitter, max)`
  - Respects `Retry-After` header when present
  - Also retries on timeout and connection errors
  - Clear error messages indicate retry exhaustion

---

### CR-0015: Global embedding rate limit state not thread-safe

- **Severity:** Medium
- **Category:** Reliability
- **Component:** _embedding
- **Location:** [_embedding.py:118-160](src/agentic_cba_indicators/tools/_embedding.py#L118-L160)
- **Source:** Opus
- **Evidence:**
  ```python
  _last_embedding_time: float = 0.0

  def get_embedding(text: str) -> list[float]:
      global _last_embedding_time
      now = time.monotonic()
      elapsed = now - _last_embedding_time
      if elapsed < _MIN_EMBEDDING_INTERVAL:
          time.sleep(_MIN_EMBEDDING_INTERVAL - elapsed)
      _last_embedding_time = time.monotonic()
  ```
- **Impact:**
  - Concurrent embedding calls may both pass rate limit check
  - Could exceed Ollama rate limits
  - Race condition between read and write
- **Reproduction/Trigger:**
  - Multiple threads calling `get_embedding()` simultaneously
- **Recommended fix:**
  - Use `threading.Lock` around rate limit check and update
- **Tests/Verification:**
  - Concurrent test with multiple threads
  - Verify rate limiting is enforced

---

### CR-0016: Correlation ID context not cleared on exception paths

- **Severity:** Medium
- **Category:** Observability
- **Component:** cli
- **Location:** [cli.py:343-356](src/agentic_cba_indicators/cli.py#L343-L356)
- **Source:** Opus
- **Evidence:**
  ```python
  correlation_id = str(uuid.uuid4())
  set_correlation_id(correlation_id)
  # If exception occurs here (before try block), ID never cleared
  try:
      agent(safe_input)
  finally:
      set_correlation_id(None)
  ```
- **Impact:**
  - Subsequent requests may inherit stale correlation ID
  - Debugging with correlation IDs produces misleading results
- **Reproduction/Trigger:**
  - Input text that causes pre-try-block code to raise
- **Recommended fix:**
  - Move `set_correlation_id()` inside the try block, or wrap entire input processing in try/finally
- **Tests/Verification:**
  - Unit test with mock exception in input processing

---

### CR-0017: Help tool `_categorize_tool` may miscategorize due to greedy keyword matching

- **Severity:** Medium
- **Category:** Bug
- **Component:** _help
- **Location:** [_help.py:96-104](src/agentic_cba_indicators/tools/_help.py#L96-L104)
- **Source:** Opus
- **Evidence:**
  ```python
  for cat_id, (_, keywords) in _TOOL_CATEGORIES.items():
      for keyword in keywords:
          if keyword in name_lower:
              return cat_id  # First match wins
  ```
- **Impact:**
  - Tools may appear in wrong categories
  - Agent may fail to find relevant tools
- **Reproduction/Trigger:**
  - Call `list_tools_by_category("forestry")` and check categorizations
- **Recommended fix:**
  - Use more specific keywords or exact function name prefixes
  - Order categories from most specific to least
- **Tests/Verification:**
  - Snapshot test of all tool categorizations

---

### CR-0018: Knowledge base query cache uses mutable tuple keys

- **Severity:** Medium
- **Category:** Bug
- **Component:** knowledge_base
- **Location:** [knowledge_base.py:55-60](src/agentic_cba_indicators/tools/knowledge_base.py#L55-L60)
- **Source:** Opus
- **Evidence:**
  ```python
  _kb_query_cache: TTLCache[tuple[Any, ...], str] = TTLCache(...)
  ```
  Type annotation `tuple[Any, ...]` permits mutable elements.
- **Impact:**
  - Future code changes could introduce unhashable cache keys
  - Potential runtime TypeError
- **Reproduction/Trigger:**
  - Not currently triggerable; defensive typing issue
- **Recommended fix:**
  - Restrict type: `TTLCache[tuple[str | int | float | bool, ...], str]`
- **Tests/Verification:**
  - Unit test with various parameter types

---

### CR-0019: Weather forecast indexing can throw on mismatched arrays (Hypothesis)

- **Severity:** Medium
- **Category:** Bug
- **Component:** weather
- **Location:** [weather.py:154](src/agentic_cba_indicators/tools/weather.py#L154)
- **Source:** GPT-5.2-Codex
- **Evidence:**
  ```python
  for i in range(len(dates)):
      weather_desc = WEATHER_CODE_EMOJI.get(weather[i], "Unknown")
      ... temps_max[i] ... temps_min[i] ... precip[i] ... wind[i]
  ```
- **Impact:**
  - If API returns arrays of different lengths, loop raises IndexError
- **Reproduction/Trigger:**
  - Hypothesis: Open-Meteo response with missing `weather_code` or shorter array
- **Recommended fix:**
  - Iterate using `zip()` with safe fill policy or validate array lengths
- **Tests/Verification:**
  - Add test with mismatched arrays and assert graceful response
- **Notes:**
  - Hypothesis; confirm by sampling Open-Meteo edge cases

---

### CR-0020: Truncation in sanitize_user_input can split UTF-8 grapheme clusters

- **Severity:** Medium
- **Category:** Security
- **Component:** security
- **Location:** [security.py:165-175](src/agentic_cba_indicators/security.py#L165-L175)
- **Source:** Opus
- **Evidence:**
  ```python
  result = result[:max_length]
  # Word-boundary logic doesn't account for combining characters
  ```
- **Impact:**
  - Unicode combining characters (diacritics) could be separated from base
  - Emojis with modifiers could be split
- **Reproduction/Trigger:**
  - Input long text ending with emoji sequence (e.g., "👨‍👩‍👧‍👦")
- **Recommended fix:**
  - Use `grapheme` library for grapheme cluster-aware truncation
- **Tests/Verification:**
  - Unit test with emoji sequences near truncation boundary

---

### CR-0021: Forestry validation functions return unused values

- **Severity:** Medium
- **Category:** Bug
- **Component:** forestry
- **Location:** [forestry.py:100+](src/agentic_cba_indicators/tools/forestry.py#L100)
- **Source:** Opus
- **Evidence:**
  ```python
  def _validate_window_years(window_years: int) -> int:
      if window_years not in VALID_WINDOW_YEARS:
          raise ValueError(...)
      return window_years
  ```
  Hypothesis: Callers may not use return values.
- **Impact:**
  - Validation performed but results discarded
  - Invalid values could still be used downstream
- **Reproduction/Trigger:**
  - Check all call sites for `_validate_*` functions
- **Recommended fix:**
  - Ensure callers use: `window_years = _validate_window_years(window_years)`
- **Tests/Verification:**
  - Grep for `_validate_` calls and verify return value used

---

### CR-0022: sdist includes `/LICENSE` but file is missing

- **Severity:** Medium
- **Category:** Config/Build
- **Component:** pyproject
- **Location:** [pyproject.toml:77](pyproject.toml#L77)
- **Source:** GPT-5.2-Codex
- **Evidence:**
  ```toml
  [tool.hatch.build.targets.sdist]
  include = [
    "/src",
    "/LICENSE",  # File does not exist
  ]
  ```
- **Impact:**
  - `hatchling` may fail the build or produce distribution missing license
- **Reproduction/Trigger:**
  - Build sdist; observe missing LICENSE file
- **Recommended fix:**
  - Add a LICENSE file or remove from sdist include list
- **Tests/Verification:**
  - Build sdist/wheel and confirm LICENSE is included

---

### CR-0023: `clear_cache()` uses undefined `OrderedDict`

- **Severity:** Low
- **Category:** Bug
- **Component:** _geo
- **Location:** [_geo.py:216](src/agentic_cba_indicators/tools/_geo.py#L216)
- **Source:** GPT-5.2-Codex
- **Evidence:**
  ```python
  def clear_cache() -> None:
      global _geocode_cache
      _geocode_cache = OrderedDict()  # OrderedDict not imported
  ```
- **Impact:**
  - Calling `clear_cache()` raises `NameError`
  - Replaces TTL cache with different type
- **Reproduction/Trigger:**
  - Call `agentic_cba_indicators.tools._geo.clear_cache()`
- **Recommended fix:**
  - Remove function or use existing TTL cache's `.clear()` method
- **Tests/Verification:**
  - Add test that calls `clear_cache()` without exceptions

---

### CR-0024: Audit logger file handle never explicitly closed

- **Severity:** Low
- **Category:** Reliability
- **Component:** audit
- **Location:** [audit.py:200+](src/agentic_cba_indicators/audit.py#L200)
- **Source:** Opus
- **Evidence:**
  File handle opened for audit logging is not explicitly closed; no `atexit` handler.
- **Impact:**
  - File may not be flushed on process exit
  - Audit entries could be lost
- **Reproduction/Trigger:**
  - Enable audit logging, run agent, force-terminate
  - Check audit log for missing entries
- **Recommended fix:**
  - Implement `close()` method
  - Use `atexit.register()` to ensure cleanup
- **Tests/Verification:**
  - Unit test verifying file handle closed on shutdown

---

### CR-0025: SoilGrids texture classification missing edge case handling

- **Severity:** Low
- **Category:** Bug
- **Component:** soilgrids
- **Location:** [soilgrids.py:45-55](src/agentic_cba_indicators/tools/soilgrids.py#L45-L55)
- **Source:** Opus
- **Evidence:**
  ```python
  def _classify_texture(sand: float, silt: float, clay: float) -> str:
      for name, condition in TEXTURE_CLASSES:
          if condition(sand, silt, clay):
              return name
      return "Loam"  # Default fallback
  ```
  Assumes sand + silt + clay ≈ 100%. Malformed data (0/0/0) returns "Loam".
- **Impact:**
  - Incorrect texture classification for edge case data
- **Reproduction/Trigger:**
  - Query location where SoilGrids returns 0/0/0 or NaN values
- **Recommended fix:**
  - Validate sum ≈ 100% within tolerance
  - Return "Unknown" if values invalid
- **Tests/Verification:**
  - Unit test with edge case values (0/0/0, negative, >100%)

---

### CR-0026: Missing concurrent access test for ChromaDB singleton

- **Severity:** Low
- **Category:** Test gap
- **Component:** tests
- **Location:** tests/test_chromadb_singleton.py
- **Source:** Opus
- **Status:** ✅ **FIXED** - Added rigorous concurrent stress test
- **Implementation:**
  - Added `test_concurrent_access_stress()` with 50 workers making 100 concurrent calls
  - Uses `ThreadPoolExecutor` for realistic concurrent access patterns
  - Simulates slow client creation (10ms delay) to increase race condition window
  - Verifies `PersistentClient` is only called once despite high concurrency
  - Includes assertion message to detect race condition in singleton initialization

---

### CR-0027: Tool lists (FULL_TOOLS, REDUCED_TOOLS) are mutable

- **Severity:** Low
- **Category:** API/Contract
- **Component:** tools/__init__
- **Location:** [tools/__init__.py:138-166](src/agentic_cba_indicators/tools/__init__.py#L138-L166)
- **Source:** Opus
- **Evidence:**
  ```python
  REDUCED_TOOLS = [...]  # Regular mutable list
  FULL_TOOLS = [...]
  ```
- **Impact:**
  - Code could accidentally mutate tool lists
  - Low risk in practice
- **Reproduction/Trigger:**
  - `from agentic_cba_indicators.tools import FULL_TOOLS; FULL_TOOLS.clear()`
- **Recommended fix:**
  - Convert to tuple or use `typing.Final`
- **Tests/Verification:**
  - Static analysis check

---

### CR-0028: Tool count claims inconsistent across docs/config

- **Severity:** Low
- **Category:** Docs mismatch
- **Component:** Multiple
- **Location:** tools/__init__.py:149, providers.yaml:74, README.md:160
- **Source:** GPT-5.2-Codex
- **Evidence:**
  - Code comments: 24/62 tools
  - Actual counts: 23/61
  - Config: 19/52
  - README: 52 total
- **Impact:**
  - Users and maintainers misled about tool capacity
- **Reproduction/Trigger:**
  - Compare counts in docs vs list sizes
- **Recommended fix:**
  - Update comments/docs to reflect actual counts
- **Tests/Verification:**
  - Add test asserting documented counts match list lengths

---

### CR-0029: Commented project.urls in pyproject.toml

- **Severity:** Low
- **Category:** Docs mismatch
- **Component:** pyproject
- **Location:** [pyproject.toml:65-68](pyproject.toml#L65-L68)
- **Source:** Opus
- **Evidence:**
  ```toml
  [project.urls]
  # Homepage = "https://github.com/yourusername/agentic-cba-indicators"
  ```
- **Impact:**
  - Package published to PyPI would have no homepage link
- **Reproduction/Trigger:**
  - `pip show agentic-cba-indicators` shows no URLs
- **Recommended fix:**
  - Uncomment and fill in actual URLs before publishing
- **Tests/Verification:**
  - Pre-publish checklist item

---

### CR-0030: Duplicate dev dependencies between optional-dependencies and dependency-groups

- **Severity:** Low
- **Category:** Config/Build
- **Component:** pyproject
- **Location:** [pyproject.toml:49-60 and 183-195](pyproject.toml#L49-L60)
- **Source:** Opus
- **Evidence:**
  ```toml
  [project.optional-dependencies]
  dev = ["pytest>=8.0.0", ...]

  [dependency-groups]
  dev = ["pytest>=9.0.2", ...]  # Different versions!
  ```
- **Impact:**
  - Version mismatch between installation methods
  - `uv sync` vs `pip install -e ".[dev]"` get different versions
- **Reproduction/Trigger:**
  - Compare `uv sync --group dev` vs `pip install -e ".[dev]"`
- **Recommended fix:**
  - Consolidate to one mechanism (prefer `[dependency-groups]` for UV)
- **Tests/Verification:**
  - CI should test both installation methods

---

### CR-0031: Duplicate returns in `search_commodity_data()`

- **Severity:** Low
- **Category:** Dead code
- **Component:** commodities
- **Location:** [commodities.py:626](src/agentic_cba_indicators/tools/commodities.py#L626)
- **Source:** GPT-5.2-Codex
- **Evidence:**
  ```python
  return "\n".join(output)
  return "\n".join(output)
  return "\n".join(output)
  ```
- **Impact:**
  - Unreachable code; indicates editing mistakes
- **Reproduction/Trigger:**
  - Static inspection
- **Recommended fix:**
  - Remove redundant returns
- **Tests/Verification:**
  - Linting

---

### CR-0032: Unused variable in socioeconomic.py

- **Severity:** Low
- **Category:** Dead code
- **Component:** socioeconomic
- **Location:** [socioeconomic.py:137-138](src/agentic_cba_indicators/tools/socioeconomic.py#L137-L138)
- **Source:** Opus
- **Evidence:**
  ```python
  _ = data.get("daily_units", {})  # Available but not currently used
  ```
- **Impact:**
  - Minor code smell; intentional per comment
- **Reproduction/Trigger:**
  - N/A
- **Recommended fix:**
  - Remove if not needed, or use the data
- **Tests/Verification:**
  - Ruff ARG rules

---

### CR-0033: Abstract cleanup regex not compiled in _crossref.py

- **Severity:** Low
- **Category:** Reliability
- **Component:** _crossref
- **Location:** [_crossref.py:170-180](src/agentic_cba_indicators/tools/_crossref.py#L170-L180)
- **Source:** Opus
- **Evidence:**
  ```python
  import re
  abstract = re.sub(r"<[^>]+>", "", abstract)  # Compiled each call
  ```
- **Impact:**
  - Minor performance impact from repeated compilation
- **Reproduction/Trigger:**
  - Profile under load
- **Recommended fix:**
  - Move pattern to module level: `_JATS_TAG_PATTERN = re.compile(r"<[^>]+>")`
- **Tests/Verification:**
  - Performance benchmark

---

### CR-0034: Control characters/mojibake in user-visible output

- **Severity:** Low
- **Category:** Broken behaviour
- **Component:** cli, tools
- **Location:** cli.py:201, labor.py:228, agriculture.py:157, sdg.py:185, README.md:154
- **Source:** GPT-5.2-Codex
- **Evidence:**
  ```python
  print("  \x07 What's the weather in Tokyo?")  # Bell character
  ```
- **Impact:**
  - Terminal beeps/garbled text
  - Reduced readability of output and docs
- **Reproduction/Trigger:**
  - Run CLI or tools and view output
- **Recommended fix:**
  - Replace control characters with ASCII bullets or standard Unicode
- **Tests/Verification:**
  - Add tests asserting no control characters in output strings

---

### CR-0035: No CI workflows found for tests/linting

- **Severity:** Low
- **Category:** Test gap
- **Component:** CI
- **Location:** .github/
- **Source:** GPT-5.2-Codex
- **Evidence:**
  `.github/` contains only `copilot-instructions.md`; no `.github/workflows/` directory.
- **Impact:**
  - Test and lint regressions can ship unnoticed
  - Secret leaks easier to miss
- **Reproduction/Trigger:**
  - Inspect `.github` directory
- **Recommended fix:**
  - Add CI workflows for tests, linting, and secret scanning
- **Tests/Verification:**
  - Ensure CI runs on PRs and main branch

---

## Cross-cutting Concerns

### Architectural/Systemic Risks

1. **Error Handling Inconsistency:** Tools vary between returning error strings and raising exceptions. The docstring for `format_error()` encourages string returns, but some tools still raise. Codify in CONTRIBUTING.md or lint rule.

2. **Singleton Lifecycle:** Multiple singletons (ChromaDB client, metrics collector, audit logger) lack coordinated shutdown. A central `shutdown()` function or context manager would improve reliability.

3. **Thread Safety Verification:** Several modules claim thread safety in docstrings but lack stress tests. Add `pytest-timeout` and concurrent test utilities.

### API Consistency and Contracts

1. **Tool Return Types:** All tools return `str`, which is good for consistency. However, structured data (JSON) would enable better downstream processing.

2. **Tool Parameter Validation:** Some tools validate parameters early and return error strings; others let exceptions propagate. Standardize on early validation.

### Config and Deployment Posture

1. **Secrets Management:** Consider adding support for secret managers (AWS Secrets Manager, HashiCorp Vault) for production deployments.

2. **12-Factor Compliance:** Good use of environment variables. Consider externalizing more defaults (timeouts, cache sizes) for container deployments.

3. **Observability:** `setup_logging()` is documented but not called by CLI/UI entry points, so structured logging and correlation IDs may not be active by default.

### Testing Strategy Gaps

1. **Integration Tests:** Most tests are unit tests with mocks. Add integration tests verifying tool chains work end-to-end.

2. **Error Path Coverage:** Many exception handlers are not tested. Use `pytest.raises` with specific exception types.

3. **Concurrent Test Coverage:** Add stress tests for shared resources (caches, singletons, rate limiters).

4. **Output Validation:** Add contract tests for API payload shapes and output snapshots to catch encoding regressions.

---

## Appendix

### Questionable Areas Requiring Human Confirmation

1. **Ingestion Script Error Handling:** Exact behavior when embeddings fail needs verification by running with Ollama down (CR-0013)

2. **ChromaDB Persistence Semantics:** Confirm whether `PersistentClient` auto-flushes on normal exit or requires explicit `persist()` (CR-0003)

3. **Open-Meteo Array Lengths:** Confirm whether API can return mismatched array lengths (CR-0019)

4. **Output Encoding Issues:** Confirm whether mojibake stems from source file encoding or rendering environment (CR-0011, CR-0034)

5. **`.env` Git History:** Confirm no prior commits exposed secrets (CR-0001)

### Hypotheses and Evidence Required

| Hypothesis | Evidence to Confirm |
|------------|---------------------|
| Ingestion silently drops failed embeddings | Run ingestion with Ollama stopped; check KB for documents without embeddings |
| Tool result truncation loses important context | Trigger context overflow in conversation; observe agent confusion |
| Concurrent embedding calls bypass rate limit | Load test with multiple threads; monitor Ollama request rate |
| Weather forecast throws on mismatched arrays | Sample Open-Meteo responses with missing/partial fields |
| Longitude formula produces invalid bounds | Call biodiversity tool at lat=0 and inspect request |

### Severity Summary

| Severity | Count |
|----------|-------|
| Blocker | 1 |
| High | 7 |
| Medium | 14 |
| Low | 13 |
| **Total** | **35** |

---

*Combined review generated from Claude Opus 4.5 and GPT-5.2-Codex reviews dated 2026-01-19.*
