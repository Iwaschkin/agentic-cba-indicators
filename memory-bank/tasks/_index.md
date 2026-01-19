# Tasks Index

## In Progress

*No tasks currently in progress*

## Pending
*No pending tasks*

## Completed

### Code Review v2 Action Plan - Phase 3 (Medium Priority)
- [TASK127] Standardize tool context usage - P3 - ATI-004 ✅
- [TASK128] Add knowledge base query caching - P3 - KBI-001 ✅
- [TASK129] Add tool error classification - P3 - Action Plan ✅
- [TASK130] Add request correlation IDs - P3 - Action Plan ✅

### Code Review v4 Remediation - Phase 1-6 (COMPLETE)
- [TASK117] Add debug logging to tool context discovery - P2 - ATI-001 ✅
- [TASK118] Create CONTRIBUTING.md with tool docs - P3 - DCG-001 ✅
- [TASK119] Add __version__ constant to package - P3 - DCG-002 ✅
- [TASK120] Make geocoding cache thread-safe - P1 - PNR-001 ✅
- [TASK121] Evaluate tiktoken for accurate token estimation - P1 - MSM-001 ✅
- [TASK122] Account for system prompt in token budget - P2 - MSM-002 ✅
- [TASK123] Add tool execution timeout decorator - P1 - PNR-003 ✅
- [TASK124] Review tool categories for keyword overlap - P2 - ATI-002 ✅
- [TASK125] Audit tool context discovery logic - P3 - ATI-003 ✅
- [TASK126] Update known-limitations document - P3 - Closure ✅

### Code Review v3 Remediation - Phase 6 (Documentation & Deferrals) - COMPLETE
- [TASK115] Architecture decision records - P1 - P1-004, P1-006, P2-* ✅
- [TASK116] Document P3 limitations - P2 - P3-001 to P3-023 ✅

### Code Review v3 Remediation - Phase 5 (Performance Optimization) - COMPLETE
- [TASK112] External API response caching - P1 - P2-023 ✅
- [TASK113] Tool output truncation - P2 - P3-003 ✅
- [TASK114] Document tool caching deferral (ADR) - P2 - P2-024 ✅

### Code Review v3 Remediation - Phase 4 (Security Hardening) - COMPLETE
- [TASK110] Input sanitization security module - P0 - P1-009, P2-027 ✅
- [TASK111] PDF context sanitization - P1 - P2-029 ✅

### Code Review v3 Remediation - Phase 3 (Memory Architecture) - COMPLETE
- [TASK108] Token-budget conversation manager - P0 - P1-003, P1-005 ✅
- [TASK109] Document memory limitations (ADR) - P2 - P2-012, P2-015 ✅

### Code Review v3 Remediation - Phase 2 (Observability Core) - COMPLETE
- [TASK104] Basic metrics collection - P0 - P1-008 ✅
- [TASK105] Audit logging module - P0 - P1-010, P3-019 ✅
- [TASK106] Structured JSON logging - P1 - P2-026 ✅
- [TASK107] Document tracing deferral (ADR) - P2 - P2-025 ✅

### Code Review v3 Remediation - Phase 1 (Storage Foundation) - COMPLETE
- [TASK101] ChromaDB connection pooling singleton - P0 - P1-001 ✅
- [TASK102] Knowledge versioning metadata - P1 - P1-002 ✅
- [TASK103] Document sync embedding limitation (ADR) - P2 - P1-007, P2-009 ✅

### Streamlit UI Implementation - COMPLETE (TASK090-TASK100)
- [TASK090] Add Streamlit dependency - Added streamlit>=1.40.0 to pyproject.toml ✅
- [TASK091] Add UI entry point - Added agentic-cba-ui script entry point ✅
- [TASK092] Create UI module scaffold - Created src/agentic_cba_indicators/ui.py ✅
- [TASK093] Implement PDF extraction helper - extract_text_from_pdf() function ✅
- [TASK094] Implement config helpers - get_available_providers() and detect_report_in_response() ✅
- [TASK095] Implement agent factory for UI - create_agent_for_ui() function ✅
- [TASK096] Implement response streaming - stream_agent_response() generator ✅
- [TASK097] Implement session state management - init_session_state() function ✅
- [TASK098] Implement sidebar UI - render_sidebar() with all controls ✅
- [TASK099] Implement main application - main() entry point ✅
- [TASK100] Verify Streamlit UI implementation - uv sync, imports, 220 tests pass ✅

### Bug Fixes (2026-01-18)
- [TASK088] DOI regex truncation fix - Pattern now handles parentheses/brackets ✅
- [TASK089] enrich_dois_batch API call fix - Renamed preview_only to skip_mutation ✅

### Code Review v2 Remediation - ALL PHASES COMPLETE (TASK078-TASK087)
**Phase 1 - Exception Handling Hardening:**
- [TASK078] Narrow exception handling in knowledge_base.py - P1 ✅
- [TASK079] Narrow exception handling in forestry.py - P1 ✅
- [TASK080] Narrow exception handling in nasa_power.py - P1 ✅
- [TASK081] Narrow exception handling in sdg.py - P1 ✅
- [TASK082] Narrow exception handling in remaining tools - P1 ✅
  - Fixed: soilgrids.py, labor.py, gender.py, commodities.py, biodiversity.py, agriculture.py
  - Fixed: _crossref.py, _unpaywall.py, _embedding.py
  - Reduced `except Exception` from 64 to 17 (intentional per-item/retry handlers)

**Phase 2 - Input Validation & Resource Limits:**
- [TASK083] PDF text length limit - Already addressed by existing code (4000 char summary + 6000 char embedding truncation) ✅
- [TASK084] n_results parameter validation - Already addressed by `min(max(1, n_results), MAX)` pattern in 7 functions ✅

**Phase 3 - Documentation & Constants:**
- [TASK085] Add docstrings to KB internal helpers - Enhanced `_resolve_indicator_id()` with full Google-style docstring ✅
- [TASK086] Extract embedding dimension constant - Added `_MIN_EMBEDDING_DIMENSION = 64` constant ✅

**Phase 4 - Deferred Items:**
- [TASK087] Document thread-safety constraint - Added Thread Safety section to `_geo.py` module docstring ✅

**All 212 tests pass after remediation.**

### Code Review v2 - COMPLETE (TASK077)
- [TASK077] Architecture & Module Discovery - Full 5-phase code review with findings report ✅

### Unpaywall + CrossRef OA Enrichment - COMPLETE (TASK062-TASK076)
- [TASK062] Migrate CrossRef to secrets and add Unpaywall - Secrets integration for both APIs ✅
- [TASK063] Create _unpaywall.py module - OA metadata dataclass and fetch function ✅
- [TASK064] Add OA fields to Citation class - is_oa, oa_status, pdf_url, license, version, host_type ✅
- [TASK065] Add enrich_from_unpaywall() method - Citation enrichment from Unpaywall ✅
- [TASK066] Create enrich_dois_batch() function - Dual-API batch enrichment ✅
- [TASK067] Add --preview-oa CLI flag - Preview OA coverage before ingestion ✅
- [TASK068] Add OA metadata to ChromaDB - oa_count, has_oa_citations fields ✅
- [TASK069] Add OA stats to list_knowledge_base_stats() - Display OA metrics ✅
- [TASK070] Add oa_only filter to search_methods() - Filter by OA availability ✅
- [TASK071] Add PDF links to export_indicator_selection() - PDF links in exports ✅
- [TASK072] Create test_unpaywall.py - 9 tests for Unpaywall module ✅
- [TASK073] Add OA enrichment tests to test_ingest_excel.py - 8 tests for ingestion ✅
- [TASK074] Fix all pre-commit/pyright/test issues - All 212 tests passing ✅
- [TASK075] Update techContext.md with Unpaywall API - API documentation ✅
- [TASK076] Update Memory Bank with OA completion - Progress and context updates ✅

### Citation Normalization Implementation - COMPLETE (TASK021, TASK053-TASK061)
- [TASK021] Citation Normalization & Embedding Model Strategy - Strategy + full implementation ✅
- [TASK053] DOI normalization functions - DOI_PATTERN, normalize_doi(), extract_doi_from_text() ✅
- [TASK054] Citation dataclass - from_raw(), to_embed_string(), to_display_string() ✅
- [TASK055] Update MethodDoc for Citation type - list[Citation], to_display_text() ✅
- [TASK056] Integrate citations into pipeline - extract_citations() returns list[Citation] ✅
- [TASK057] Preview citations CLI flag - --preview-citations (85.9% DOI rate) ✅
- [TASK058] Citation metadata in ChromaDB - citation_count, doi_count, dois_json ✅
- [TASK059] Citation normalization tests - 49 tests covering all DOI functions ✅
- [TASK060] KB rebuild validation - 224/223/801 counts, 196 tests pass ✅
- [TASK061] Embedding dimension awareness - EMBEDDING_DIMENSIONS dict, migration docs ✅

### GFW Forestry Tools Implementation - COMPLETE (TASK042-TASK052)
- [TASK042] Create GFW API request helper - Created _gfw_get(), _gfw_post() ✅
- [TASK043] Create circular geostore helper - Created _create_circular_geostore() ✅
- [TASK044] Add input validation helpers - Country, window, radius, coordinates validation ✅
- [TASK045] Implement tree cover loss trends tool - get_tree_cover_loss_trends() ✅
- [TASK046] Implement loss by driver tool - get_tree_cover_loss_by_driver() ✅
- [TASK047] Implement forest carbon stock tool - get_forest_carbon_stock() ✅
- [TASK048] Implement forest extent tool - get_forest_extent() ✅
- [TASK049] Update tool exports - All 4 tools in __all__ and FULL_TOOLS ✅
- [TASK050] Update .env.example - GFW API key guidance improved ✅
- [TASK051] Create forestry tests - 35 tests covering all helpers and tools ✅
- [TASK052] Final validation - pytest/ruff/pyright all green, committed ✅

## Completed

### Internal Tool Help System - COMPLETE
- [TASK038] Create internal help tools module - Created `_help.py` with `list_tools()` and `describe_tool()` ✅
- [TASK039] Integrate help tools into CLI - Wired help tools into agent creation ✅
- [TASK040] Update prompts for internal tool guidance - Added internal-only usage guidelines ✅
- [TASK041] Add help tools tests - Added 8 unit tests for help tools ✅

### Phase 10: Test Improvements (P2/P3) - COMPLETE
- [TASK035] Increase test coverage - Added 25 error path tests for _http.py and _geo.py ✅
- [TASK036] Integration test suite - Created test_integration.py with 15 tests ✅
- [TASK037] Clean up test files - Consolidated fixtures, removed 1 duplicate ✅

### Phase 9: Code Cleanup (P3) - COMPLETE
- [TASK029] Remove unused imports - Removed 6 unused imports via ruff ✅
- [TASK030] Standardize docstrings - Already using Google style (false positive) ✅
- [TASK031] Fix typos - Added noqa comment for intentional naming ✅
- [TASK032] Update placeholder URLs - Commented out pyproject.toml placeholders ✅
- [TASK033] Improve comments - Added km-to-degrees calculation comments ✅
- [TASK034] Organize imports - Fixed 2 files via ruff isort ✅

### Phase 8: Type Safety (P2) - COMPLETE
- [TASK026] CLI type hints - Already had full type hints (false positive) ✅
- [TASK027] Script type hints - Fixed EMBEDDING_MODEL import, null checks ✅
- [TASK028] Knowledge base type hints - Already had full type hints (false positive) ✅

### Phase 7: Observability (P2) - COMPLETE
- [TASK025] Add logging framework - Created logging_config.py, added debug logging to retry paths ✅

### Phase 6: Configuration (P2) - COMPLETE
- [TASK022] Configurable timeouts - HTTP_TIMEOUT, OLLAMA_*_TIMEOUT env vars ✅
- [TASK023] Magic numbers to constants - Added 7 constants to knowledge_base/biodiversity ✅
- [TASK024] CLI framework - Replaced manual parsing with argparse ✅

### Phase 5: Code Consolidation (P1/P2) - COMPLETE
- [TASK019] Consolidate country mappings - Added COUNTRY_CODES_ISO3 + get_iso3_code() to _mappings.py ✅
- [TASK020] Consolidate weather codes - Extracted WEATHER_CODE_DESCRIPTIONS + WEATHER_CODE_EMOJI constants ✅
- [TASK021] Consolidate embedding functions - Created _embedding.py, removed ~300 lines of duplicates ✅

### Phase 4: Error Handling (P1/P2) - COMPLETE
- [TASK016] JSON decode error handling - Added JSONDecodeError handling in fetch_json() ✅
- [TASK017] Embedding failure handling - Added EmbeddingError, retry logic, validation ✅
- [TASK018] ChromaDB retry logic - Added ChromaDBError, retry for client/collection ✅

### Phase 3: Resource Management (P1) - COMPLETE
- [TASK014] HTTP context managers - Already implemented (false positive) ✅
- [TASK015] Add rate limiting - Added rate limiter for Ollama embeddings ✅

### Phase 2: Input Validation (P1) - COMPLETE
- [TASK011] Add coordinate validation - Validate lat/lon ranges ✅
- [TASK012] Environment variable whitelist - Prevent injection via config ✅
- [TASK013] Path traversal prevention - Validate path overrides ✅

### Phase 1: Critical Security (P0) - COMPLETE
- [TASK008] Sanitize error messages - Added sanitize_error() + tests ✅
- [TASK009] Enforce TLS for Ollama - Added _validate_ollama_tls() to 3 files ✅
- [TASK010] Bound geocode cache - Already implemented (false positive) ✅

### Prior Tasks (Pre-Remediation)
- [TASK001] Fix bundled config lookup + schema validation
- [TASK002] Standardize HTTP handling across tools + retries
- [TASK003] Improve ingestion embedding failure handling
- [TASK004] Implement bounded geocode cache + centralize geocoding
- [TASK005] Centralize country/indicator code maps
- [TASK006] Expand tests for tools and ingestion workflows
- [TASK007] Move pyright to dev dependencies only

## Abandoned

## Summary

### Overall Statistics
- **Total Tasks Completed:** 100 (TASK001-TASK100)
- **Total Tests:** 220
- **Streamlit UI:** 11 tasks (TASK090-TASK100)
- **Code Review Remediation:** 10 tasks (TASK078-TASK087)
- **Bug Fixes:** 2 tasks (TASK088-TASK089)

### Key Improvements Made
1. **Streamlit Web UI:** Full chat interface with provider selection, PDF upload, report export
2. **Security:** Error sanitization, TLS enforcement, path validation
3. **Reliability:** Retry logic, error handling, coordinate validation, DOI regex fix
4. **Maintainability:** Code consolidation, logging, constants extraction
5. **Testing:** Error path coverage, integration tests, regression tests
6. **Data Quality:** Citation normalization, OA enrichment, DOI extraction (85.9%)
