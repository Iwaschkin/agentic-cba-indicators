# [TASK021] - Citation Normalization & Embedding Model Strategy

**Status:** Completed
**Added:** 2026-01-17
**Updated:** 2026-01-17

## Original Request
Develop a detailed strategy to normalize citation data during the ingest process, structured to:
1. Align agentic retrieval with repo objectives
2. Set up for URL enrichment at a later stage
3. Evaluate if there are better embedding models for the ingestion phase

## Thought Process
The knowledge base currently stores citations as unstructured strings like `"Smith et al. 2020 [DOI: 10.1234/abc]"`. This creates several problems:
- Agent can't extract DOI programmatically to provide clickable links
- Inconsistent DOI formats prevent deduplication
- Citation text in embeddings pollutes semantic search with non-technical content

The solution involves:
1. **Phase 1**: Normalize citations during ingestion (structured `Citation` dataclass)
2. **Phase 2**: Store citation metadata in ChromaDB for filtering
3. **Phase 3**: Evaluate embedding models for potential quality improvements
4. **Phase 4**: Enable on-demand URL enrichment via CrossRef API

For embedding models, `nomic-embed-text` remains appropriate for now:
- 8k context handles our document lengths
- Well-tested with Ollama
- Migration to better models (snowflake-arctic-embed, qwen3-embedding) can happen later if needed

## Implementation Plan
1. Create `Citation` dataclass with `from_raw()`, `to_embed_string()`, `to_display_string()`
2. Add DOI normalization functions (`normalize_doi()`, `extract_doi_from_text()`, `doi_to_url()`)
3. Update `extract_citations()` to return `list[Citation]`
4. Update `MethodDoc` to use `list[Citation]` instead of `list[str]`
5. Add `--preview-citations` CLI flag for validation
6. Add unit tests for DOI edge cases
7. Document embedding model migration path

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 21.1 | Create strategy document | Complete | 2026-01-17 | docs/dev/plan-citation-normalization-strategy.md |
| 21.2 | Create Citation dataclass | Complete | 2026-01-17 | TASK054 - with from_raw(), to_embed/display_string() |
| 21.3 | Add DOI normalization functions | Complete | 2026-01-17 | TASK053 - normalize_doi(), extract_doi_from_text(), etc. |
| 21.4 | Update extract_citations() | Complete | 2026-01-17 | TASK056 - Return list[Citation] |
| 21.5 | Update MethodDoc class | Complete | 2026-01-17 | TASK055 - Change citations type, add to_display_text() |
| 21.6 | Add --preview-citations flag | Complete | 2026-01-17 | TASK057 - CLI validation tool |
| 21.7 | Add unit tests | Complete | 2026-01-17 | TASK059 - 49 tests for DOI normalization |
| 21.8 | Run ingestion and verify | Complete | 2026-01-17 | TASK060 - KB rebuilt, 196 tests pass |
| 21.9 | Document embedding migration | Complete | 2026-01-17 | TASK061 - EMBEDDING_DIMENSIONS dict |

## Progress Log
### 2026-01-17
- Created comprehensive strategy document at docs/dev/plan-citation-normalization-strategy.md
- Researched embedding models via Ollama, Context7, and MTEB leaderboard
- Analyzed current citation handling in ingest_excel.py
- Determined nomic-embed-text remains appropriate, documented migration path
- Key decisions:
  - Use `Citation` dataclass for structured storage
  - Separate embedding text (minimal) from display text (with URLs)
  - DOI normalization: lowercase, no prefix, validate format
  - Auto-generate `https://doi.org/{doi}` URLs
  - Store raw text for traceability

### 2026-01-17 (Update 2)
- Enhanced strategy with API selection matrix based on user-provided documentation links
- Added CrossRef API as primary enrichment source (no auth, polite pool)
- Added OpenAlex as fallback for CrossRef misses
- Identified zbMATH, INSPIRE-HEP, DBLP as not relevant for CBA domain
- Updated DOI validation rules per DOI Handbook (ISO 26324)
- Added real CBA-relevant publisher prefixes (Elsevier, Nature, MDPI, Zenodo)
- Added fallback chain architecture: CrossRef → OpenAlex → basic DOI URL
- Added environment variables section: CROSSREF_MAILTO, SEMANTIC_SCHOLAR_API_KEY
- Updated test cases with real-world CBA literature DOI patterns

### 2026-01-17 (Implementation Complete)
- Executed full implementation per opus-review-memorybank.prompt.md
- Created 9 child tasks (TASK053-TASK061) for granular tracking
- All 6 phases implemented and validated:
  - Phase 1: DOI normalization functions (DOI_PATTERN regex, normalize_doi(), etc.)
  - Phase 2: Citation dataclass with factory and formatting methods
  - Phase 3: MethodDoc updated to use list[Citation]
  - Phase 4: Pipeline integration + CLI flag + metadata enhancement
  - Phase 5: 49 new tests in test_citation_normalization.py
  - Phase 6: KB rebuilt (224/223/801 counts), 196 tests pass
- Citation stats: 1153 total citations, 991 with DOIs (85.9%)

## Deliverables
- [x] docs/dev/plan-citation-normalization-strategy.md - Full strategy document
- [ ] Citation dataclass implementation
- [ ] Updated extract_citations() function
- [ ] Updated MethodDoc class
- [ ] --preview-citations CLI flag
- [ ] Unit tests for DOI normalization
- [ ] Updated KB after full rebuild

## Dependencies
- No blocking dependencies
- Future phases depend on this normalization being in place

## Notes
- Embedding model change would require full KB rebuild
- Current nomic-embed-text is adequate; migration is optional optimization
- URL enrichment (CrossRef API) deferred to Phase 4
