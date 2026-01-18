# Tech Context

## Stack
- Python 3.11+
- Strands Agents SDK
- httpx for HTTP
- ChromaDB for vector store
- pandas/openpyxl for ingestion

## Tooling
- uv package manager
- pytest for tests
- ruff/black/mypy for quality (dev)

## Constraints
- CLI must be robust without API keys for public sources
- Knowledge base should be deterministic and reproducible

## External APIs

### CrossRef API (Citation Enrichment)
- **Base URL**: `https://api.crossref.org/works/{doi}`
- **Auth**: None required (public)
- **Polite Pool**: Set `CROSSREF_EMAIL` env var for faster rates
- **Timeout**: 15 seconds (configurable via `CROSSREF_TIMEOUT`)
- **Rate Limiting**: 0.1s delay between requests (configurable via `CROSSREF_BATCH_DELAY`)
- **Data Retrieved**: title, authors, journal, year, abstract, publisher, ISSN, license_url
- **Module**: `src/agentic_cba_indicators/tools/_crossref.py`

### Unpaywall API (Open Access Enrichment)
- **Base URL**: `https://api.unpaywall.org/v2/{doi}`
- **Auth**: Email required (set `UNPAYWALL_EMAIL` env var)
- **Timeout**: 10 seconds (configurable via `UNPAYWALL_TIMEOUT`)
- **Rate Limiting**: 100,000 requests/day limit
- **Data Retrieved**:
  - `is_oa`: Boolean Open Access status
  - `oa_status`: OA type (gold, hybrid, bronze, green, closed)
  - `pdf_url`: Direct PDF link (from best_oa_location)
  - `license`: License URL (e.g., CC-BY)
  - `version`: Article version (publishedVersion, acceptedVersion, submittedVersion)
  - `host_type`: Source type (publisher, repository)
- **Module**: `src/agentic_cba_indicators/tools/_unpaywall.py`

### OA Status Definitions
| Status | Description |
|--------|-------------|
| gold | Published OA with open license |
| hybrid | Subscription journal with OA option used |
| bronze | Free to read on publisher site (no open license) |
| green | OA copy in repository (pre/post print) |
| closed | Not openly accessible |
