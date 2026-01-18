# Tasks Index

## In Progress

## Pending

### Unpaywall + CrossRef OA Enrichment (TASK062-TASK076)
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

## Completed

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

### Remediation Plan Statistics
- **Total Tasks:** 30 (TASK008-TASK037)
- **Completed:** 30
- **False Positives:** 6 (already implemented or not applicable)
- **Total Test Count:** 75 (up from ~35 at start)

### Key Improvements Made
1. **Security:** Error sanitization, TLS enforcement, path validation
2. **Reliability:** Retry logic, error handling, coordinate validation
3. **Maintainability:** Code consolidation, logging, constants extraction
4. **Testing:** Error path coverage, integration tests, fixture cleanup
