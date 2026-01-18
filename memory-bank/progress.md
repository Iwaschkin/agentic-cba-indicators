# Progress

## What Works
- CLI agent creation and tooling
- Knowledge base ingestion scripts (with embedding retry/validation)
- **Citation normalization in KB** (85.9% DOI extraction rate)
  - DOI parsing and validation per DOI Handbook (ISO 26324)
  - Separate embedding vs display text (to_embed_string / to_display_string)
  - Citation metadata in ChromaDB (citation_count, doi_count, dois_json)
  - --preview-citations CLI flag for validation
  - Embedding dimension awareness for future model migration
- **DOI enrichment via CrossRef API**
  - Fetches title, authors, journal, year, abstract for each DOI
  - --enrich flag during ingestion (138 DOIs → 124 found, 880 citations enriched)
  - --enrich-citations preview flag for testing
  - Enriched data displayed in search results (full titles, abstracts)
  - Polite pool support via CROSSREF_EMAIL env var
- **Open Access enrichment via Unpaywall API**
  - Fetches OA status (gold/hybrid/bronze/green/closed)
  - PDF URLs for direct download
  - License, version, and host type metadata
  - oa_only filter in search_methods()
  - OA badges (🔓) in export_indicator_selection()
  - OA stats in list_knowledge_base_stats()
- 212 automated tests covering:
  - Configuration loading and validation
  - Path resolution with XDG support
  - HTTP utilities with retry logic and error sanitization
  - Coordinate validation and geocoding
  - Integration tests for CLI, ChromaDB, agent creation
  - Internal help tools (list_tools, describe_tool)
  - GFW forestry tools (35 tests)
  - Citation normalization (49 tests)
  - Unpaywall module (9 tests)
  - OA enrichment (8 tests)
- Security hardening:
  - Error message sanitization (no URL params/credentials leaked)
  - TLS enforcement for Ollama connections
  - Path traversal prevention for config overrides
  - Environment variable whitelist for YAML expansion
  - API key management via _secrets.py
- Reliability improvements:
  - Rate limiting for Ollama embeddings
  - Retry logic for ChromaDB operations
  - JSON decode error handling
  - Embedding validation and retry
- Code consolidation:
  - Shared _embedding.py module (removed ~300 lines duplication)
  - Centralized country mappings in _mappings.py
  - Weather code constants extracted
- Observability:
  - Structured logging via logging_config.py
  - Debug logging on retry paths
- Internal tool help system:
  - `list_tools()` - Agent self-discovery of available tools
  - `describe_tool()` - Agent access to full tool documentation
  - System prompts guide internal-only usage
- GFW Forestry Tools:
  - `get_tree_cover_loss_trends()` - Historical deforestation analysis
  - `get_tree_cover_loss_by_driver()` - Loss by driver category
  - `get_forest_carbon_stock()` - Above-ground biomass and carbon
  - `get_forest_extent()` - Current forest cover assessment

## Completed

### Open Access Enrichment via Unpaywall - COMPLETE (TASK062-TASK076)
- Phase 1: Secrets integration for CrossRef and Unpaywall ✅
- Phase 2: Created `_unpaywall.py` module with UnpaywallMetadata dataclass ✅
- Phase 3: Added OA fields to Citation class ✅
- Phase 4: Integrated enrich_from_unpaywall() method ✅
- Phase 5: ChromaDB metadata (oa_count, has_oa_citations) ✅
- Phase 6: KB tool enhancements (oa_only filter, OA stats, PDF links) ✅
- Phase 7: Testing (9 Unpaywall tests, 8 ingestion tests) ✅
- Phase 8: Code quality fixes (pyright, ruff, all 212 tests pass) ✅

### DOI Enrichment via CrossRef - COMPLETE
- Created `src/agentic_cba_indicators/tools/_crossref.py` module
- `CrossRefMetadata` dataclass with title, authors, journal, year, abstract, etc.
- `fetch_crossref_metadata()` - single DOI fetch with error handling
- `fetch_crossref_batch()` - batch fetch with rate limiting and progress callback
- Enhanced Citation class with enrichment fields (enriched_title, etc.)
- Integrated into ingest() with --enrich flag
- KB rebuilt with enriched data (124/138 DOIs found, 880 citations enriched)

### Citation Normalization - COMPLETE (TASK021, TASK053-TASK061)
- Strategy document with API selection matrix (CrossRef, OpenAlex)
- Phase 1: DOI normalization functions (DOI_PATTERN, normalize_doi, etc.) ✅
- Phase 2: Citation dataclass (from_raw, to_embed_string, to_display_string) ✅
- Phase 3: MethodDoc updated to use list[Citation] ✅
- Phase 4: Pipeline integration + CLI flag + metadata enhancement ✅
- Phase 5: 49 new tests in test_citation_normalization.py ✅
- Phase 6: KB rebuilt (224/223/801 counts), embedding dimension awareness ✅

### GFW Forestry Tools - COMPLETE (TASK042-TASK052)
- Phase 1: Infrastructure - Created helpers and validation ✅
- Phase 2: Country Tools - Implemented loss trends and driver tools ✅
- Phase 3: Geostore Tools - Implemented carbon stock and extent tools ✅
- Phase 4: Integration - Updated exports and .env.example ✅
- Phase 5: Testing - Added 35 tests, all passing ✅

### Internal Tool Help System - COMPLETE (TASK038-TASK041)
- Phase 1: Core Module - Created `_help.py` with registry and tools ✅
- Phase 2: Integration - Wired into CLI, excluded from public lists ✅
- Phase 3: Prompts & Tests - Updated prompts, added 8 tests ✅

### Remediation Plan (TASK008-TASK037) - COMPLETE
- Phase 1: Critical Security (P0) - 3 tasks ✅
- Phase 2: Input Validation (P1) - 3 tasks ✅
- Phase 3: Resource Management (P1) - 2 tasks ✅
- Phase 4: Error Handling (P1/P2) - 3 tasks ✅
- Phase 5: Code Consolidation (P1/P2) - 3 tasks ✅
- Phase 6: Configuration (P2) - 3 tasks ✅
- Phase 7: Observability (P2) - 1 task ✅
- Phase 8: Type Safety (P2) - 3 tasks ✅
- Phase 9: Code Cleanup (P3) - 6 tasks ✅
- Phase 10: Test Improvements (P2/P3) - 3 tasks ✅

**Total: 59 tasks completed (TASK008-TASK076)**

## In Progress
- None

## Remaining
- None

## Known Issues
- None identified
