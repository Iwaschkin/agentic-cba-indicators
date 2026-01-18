## Plan: Unpaywall + CrossRef Batched Enrichment (Final)

**TL;DR**: Create `_unpaywall.py` module, integrate both APIs into secrets system, batch enrichment calls during ingestion, and add OA-aware features to KB tools. PDF downloads will be Phase 2 via separate `--download-pdfs` command.

### Steps
1. **Add to secrets registry** in [_secrets.py](src/agentic_cba_indicators/config/_secrets.py#L17-L24): Add `"crossref": "CROSSREF_EMAIL"` and `"unpaywall": "UNPAYWALL_EMAIL"` to `SUPPORTED_KEYS`
2. **Create** [src/agentic_cba_indicators/tools/_unpaywall.py](src/agentic_cba_indicators/tools/_unpaywall.py): `UnpaywallMetadata` dataclass (`is_oa`, `oa_status`, `pdf_url`, `license`, `version`, `host_type`) and `fetch_unpaywall_metadata()` function
3. **Update** [_crossref.py](src/agentic_cba_indicators/tools/_crossref.py#L25): Replace `os.environ.get("CROSSREF_MAILTO")` with `get_api_key("crossref")`
4. **Create batched enricher** in [ingest_excel.py](scripts/ingest_excel.py): `enrich_dois_batch()` calls CrossRef + Unpaywall per DOI with 0.1s delay between DOIs
5. **Extend Citation class**: Add OA fields and `enrich_from_unpaywall()` method; update `to_embed_string()` and `to_display_string()`
6. **Add `--preview-oa` flag**: Show OA coverage stats before ingestion
7. **Enhance KB tools**: OA stats in `list_knowledge_base_stats()`, `oa_only` filter in `search_methods()`, PDF links in `export_indicator_selection()`
8. **Store OA metadata**: Add `oa_count`, `has_oa_citations` to ChromaDB method group metadata

### Phase 2 (Separate Command)
- **`--download-pdfs`**: Download OA PDFs to local cache
- **`--ingest-pdfs`**: Chunk downloaded PDFs and add to KB as separate collection
- Requires: PDF parsing library (pypdf2 or pdfplumber), text chunking strategy
