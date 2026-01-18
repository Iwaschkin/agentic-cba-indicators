# Citation Normalization & Embedding Model Strategy

**Status:** Planning
**Created:** 2026-01-17
**Related:** Knowledge Base RAG optimization, agentic retrieval alignment

---

## Executive Summary

This document outlines a comprehensive strategy to:
1. **Normalize citation data** during ingestion for consistent, actionable references
2. **Evaluate embedding models** to improve retrieval quality for CBA indicators
3. **Structure for URL enrichment** to enable future citation resolution

The strategy aligns with the project's core objectives: *reliable first-run experience*, *high-integrity ingestion*, and *predictable tool outputs*.

---

## Part 1: Citation Normalization Strategy

### 1.1 Current State Analysis

**How citations are stored today:**
```python
# scripts/ingest_excel.py - extract_citations()
def extract_citations(row: pd.Series) -> list[str]:
    """Extract and clean citations from row."""
    citations = []
    for i in range(1, 6):
        doi = safe_str(row.get(f"DOI.{i}" if i > 1 else "DOI", ""))
        cite = safe_str(row.get(f"Citation.{i}" if i > 1 else "Citation", ""))
        if cite and doi:
            citations.append(f"{cite} [DOI: {doi}]")
        elif cite:
            citations.append(cite)
        elif doi:
            citations.append(f"[DOI: {doi}]")
    return citations
```

**Problems with current approach:**
| Issue | Impact | Example |
|-------|--------|---------|
| Unstructured strings | Agent can't extract DOI for lookup | `"Smith et al. 2020 [DOI: 10.1234/abc]"` |
| Inconsistent DOI formats | Duplicate detection fails | `"doi.org/10.1234"` vs `"10.1234"` vs `"https://doi.org/10.1234"` |
| No URL generation | Agent can't provide clickable links | Missing `https://doi.org/{doi}` |
| Citations embedded in document text | Pollutes semantic search with non-technical content | "References: Smith et al..." affects similarity |
| Spillover columns unstructured | Lost context from Unnamed:32/33 | Raw text without DOI association |

### 1.2 Normalization Goals

**G1: Structured Citation Objects**
- Parse raw citation text into `Citation` dataclass with `text`, `doi`, `url` fields
- Enable programmatic access to citation components

**G2: DOI Normalization**
- Canonical form: lowercase, no prefix, validated format
- Input: `"https://doi.org/10.1234/ABC"` → Output: `"10.1234/abc"`

**G3: URL Generation**
- Auto-generate `https://doi.org/{doi}` for valid DOIs
- Future: enrich with full-text links, PubMed, institutional repos

**G4: Separate Embedding from Display**
- Embed: `"Method: Soil sampling at 0-30cm depth for organic carbon measurement"`
- Display: Same text + citation with URL

**G5: Preserve Original Data**
- Store raw citation text for traceability
- Enable re-normalization as rules improve

### 1.3 Implementation Phases

#### Phase 1: Citation Data Structures (This PR)

**New data structures:**
```python
# scripts/ingest_excel.py

import re
from dataclasses import dataclass
from typing import Optional

# DOI regex: matches 10.XXXX/anything format
DOI_PATTERN = re.compile(
    r"""
    (?:https?://)?           # Optional https:// or http://
    (?:dx\.)?                # Optional dx. prefix
    (?:doi\.org/)?           # Optional doi.org/
    (10\.\d{4,}/[^\s\]]+)    # Capture group: 10.XXXX/identifier
    """,
    re.VERBOSE | re.IGNORECASE,
)


@dataclass
class Citation:
    """Structured citation with normalized DOI and URL."""

    raw_text: str                    # Original text from Excel
    text: str                        # Cleaned citation text (author, year, title)
    doi: Optional[str] = None        # Normalized DOI (e.g., "10.1234/abc")
    url: Optional[str] = None        # Canonical URL (e.g., "https://doi.org/10.1234/abc")

    @classmethod
    def from_raw(cls, cite_text: str, doi_text: str = "") -> "Citation":
        """Parse raw citation and DOI strings into structured Citation."""
        raw = f"{cite_text} {doi_text}".strip()

        # Normalize DOI
        doi = normalize_doi(doi_text) or extract_doi_from_text(cite_text)

        # Clean citation text (remove embedded DOI if we extracted it)
        text = clean_citation_text(cite_text)

        # Generate URL
        url = doi_to_url(doi) if doi else None

        return cls(raw_text=raw, text=text, doi=doi, url=url)

    def to_display_string(self) -> str:
        """Format for display to user (includes URL if available)."""
        if self.url:
            return f"{self.text} [{self.url}]"
        elif self.doi:
            return f"{self.text} [DOI: {self.doi}]"
        return self.text

    def to_embed_string(self) -> str:
        """Format for embedding (minimal, semantic content only)."""
        return self.text  # Just the citation text, no DOI/URL noise


def normalize_doi(raw: str) -> Optional[str]:
    """
    Normalize a DOI to canonical lowercase form.

    Input formats handled:
    - "10.1234/abc"
    - "doi: 10.1234/abc"
    - "https://doi.org/10.1234/ABC"
    - "http://dx.doi.org/10.1234/abc"
    - "DOI:10.1234/abc" (no space)

    Returns:
        Normalized DOI (e.g., "10.1234/abc") or None if invalid
    """
    if not raw:
        return None

    # Strip and normalize
    raw = raw.strip()

    # Remove common prefixes
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE)

    # Try to match DOI pattern
    match = DOI_PATTERN.search(raw)
    if match:
        # Return lowercase canonical form
        return match.group(1).lower()

    return None


def extract_doi_from_text(text: str) -> Optional[str]:
    """Extract DOI embedded in citation text."""
    match = DOI_PATTERN.search(text)
    if match:
        return match.group(1).lower()
    return None


def clean_citation_text(text: str) -> str:
    """Remove DOI patterns and clean up citation text."""
    if not text:
        return ""

    # Remove [DOI: ...] patterns
    text = re.sub(r"\[DOI:\s*[^\]]+\]", "", text)

    # Remove standalone DOI URLs
    text = DOI_PATTERN.sub("", text)

    # Clean up whitespace
    text = " ".join(text.split())

    return text.strip()


def doi_to_url(doi: str) -> str:
    """Convert normalized DOI to canonical HTTPS URL."""
    return f"https://doi.org/{doi}"
```

**Updated MethodDoc:**
```python
@dataclass
class MethodDoc:
    """Represents a single method row."""

    indicator_id: int
    indicator_text: str
    unit: str
    method_general: str
    method_specific: str
    notes: str
    accuracy: str
    ease: str
    cost: str
    citations: list[Citation] = field(default_factory=list)  # Changed from list[str]

    def to_text(self) -> str:
        """Generate text for embedding (semantic content only)."""
        parts = []

        if self.method_general:
            parts.append(f"Method (General): {self.method_general}")
        if self.method_specific:
            parts.append(f"Method (Specific): {self.method_specific}")
        if self.notes:
            parts.append(f"Notes: {self.notes}")

        eval_parts = []
        if self.accuracy:
            eval_parts.append(f"Accuracy: {self.accuracy}")
        if self.ease:
            eval_parts.append(f"Ease: {self.ease}")
        if self.cost:
            eval_parts.append(f"Cost: {self.cost}")

        if eval_parts:
            parts.append(f"Evaluation: {', '.join(eval_parts)}")

        # For embedding: use minimal citation text (no DOI/URL noise)
        if self.citations:
            cite_texts = [c.to_embed_string() for c in self.citations if c.text]
            if cite_texts:
                parts.append(f"References: {'; '.join(cite_texts)}")

        return "\n".join(parts)

    def to_display_text(self) -> str:
        """Generate text for display to user (includes URLs)."""
        parts = []

        if self.method_general:
            parts.append(f"Method (General): {self.method_general}")
        if self.method_specific:
            parts.append(f"Method (Specific): {self.method_specific}")
        if self.notes:
            parts.append(f"Notes: {self.notes}")

        eval_parts = []
        if self.accuracy:
            eval_parts.append(f"Accuracy: {self.accuracy}")
        if self.ease:
            eval_parts.append(f"Ease: {self.ease}")
        if self.cost:
            eval_parts.append(f"Cost: {self.cost}")

        if eval_parts:
            parts.append(f"Evaluation: {', '.join(eval_parts)}")

        # For display: full citation with URL
        if self.citations:
            parts.append("References:")
            for c in self.citations:
                parts.append(f"  - {c.to_display_string()}")

        return "\n".join(parts)
```

**Updated extract_citations:**
```python
def extract_citations(row: pd.Series) -> list[Citation]:
    """Extract and normalize citations from row."""
    citations = []

    # Standard citation columns (DOI + Citation pairs)
    for i in range(1, 6):
        doi_col = "DOI" if i == 1 else f"DOI.{i}"
        cite_col = "Citation" if i == 1 else f"Citation.{i}"

        doi = safe_str(row.get(doi_col, ""))
        cite = safe_str(row.get(cite_col, ""))

        if cite or doi:
            citations.append(Citation.from_raw(cite, doi))

    # Handle unnamed spillover columns (32, 33)
    # These may contain either citations or DOIs
    for col in ["Unnamed: 32", "Unnamed: 33"]:
        spillover = safe_str(row.get(col, ""))
        if spillover and len(spillover) > 5:
            # Check if it looks like a DOI
            if DOI_PATTERN.search(spillover):
                citations.append(Citation.from_raw("", spillover))
            else:
                citations.append(Citation.from_raw(spillover, ""))

    return citations
```

#### Phase 2: Metadata Enrichment (Future)

**Store citation metadata in ChromaDB:**
```python
# In MethodsGroupDoc.to_metadata()
def to_metadata(self) -> dict:
    """Generate metadata including citation info."""
    import json

    # Collect all unique DOIs across methods
    all_dois = []
    all_urls = []
    for method in self.methods:
        for cite in method.citations:
            if cite.doi and cite.doi not in all_dois:
                all_dois.append(cite.doi)
            if cite.url and cite.url not in all_urls:
                all_urls.append(cite.url)

    return {
        "indicator_id": self.indicator_id,
        "indicator": self.indicator_text,
        "unit": self.unit,
        "method_count": len(self.methods),
        "has_high_accuracy": any(m.accuracy == "High" for m in self.methods),
        "has_low_cost": any(m.cost == "Low" for m in self.methods),
        "has_high_ease": any(m.ease == "High" for m in self.methods),
        # Citation metadata
        "citation_count": sum(len(m.citations) for m in self.methods),
        "doi_count": len(all_dois),
        "dois_json": json.dumps(all_dois),  # For retrieval
        "urls_json": json.dumps(all_urls),   # For display
    }
```

#### Phase 3: KB Tool Integration (Future)

**Update knowledge_base.py to use citation metadata:**
```python
@tool
def get_indicator_details(indicator_id: int) -> str:
    """Get full details including citation URLs."""
    # ... existing code ...

    # When returning methods, use display format
    if method_docs:
        for method in method_docs:
            output.append(method.to_display_text())  # Now includes URLs
```

### 1.4 Preview/Validation CLI

Add `--preview-citations` flag:
```bash
# Preview citation normalization without ingesting
python scripts/ingest_excel.py --preview-citations

# Output:
# === Citation Normalization Preview ===
#
# Indicator 107 - Soil organic carbon:
#   Method 1:
#     Raw: "Smith et al. 2020. Soil carbon methods. https://doi.org/10.1234/ABC"
#     Text: "Smith et al. 2020. Soil carbon methods."
#     DOI: 10.1234/abc
#     URL: https://doi.org/10.1234/abc
#   Method 2:
#     Raw: "No DOI available citation"
#     Text: "No DOI available citation"
#     DOI: None
#     URL: None
#
# Summary:
#   Total citations: 1,247
#   With DOI: 892 (71.5%)
#   Without DOI: 355 (28.5%)
#   DOI extraction from text: 47 (5.3%)
```

---

## Part 2: Embedding Model Evaluation

### 2.1 Current Model Analysis

**Current: `nomic-embed-text`**
| Property | Value |
|----------|-------|
| Dimensions | 768 |
| Context | 8,192 tokens |
| Model size | ~137M params |
| MTEB score | ~62 (retrieval) |
| Local via Ollama | ✅ |
| Matryoshka | ❌ |

**Pros:**
- Large context window (8k tokens) - good for our longer method documents
- Well-tested, stable
- Good balance of quality vs speed

**Cons:**
- Released 2024, newer models available
- No instruction-following capability
- Fixed embedding dimension

### 2.2 Alternative Models (Ollama-Compatible)

| Model | Params | Dims | Context | MTEB | Notes |
|-------|--------|------|---------|------|-------|
| `nomic-embed-text` (current) | 137M | 768 | 8k | ~62 | Stable, proven |
| `mxbai-embed-large` | 335M | 1024 | 512 | ~65 | Higher quality, short context |
| `snowflake-arctic-embed:335m` | 335M | 1024 | 8k | ~65 | Long context, high quality |
| `qwen3-embedding:0.6b` | 600M | 1024 | 32k | ~68 | Very long context, multilingual |
| `embeddinggemma` | 300M | 768 | 8k | ~64 | Google, newer architecture |
| `all-minilm:33m` | 33M | 384 | 512 | ~55 | Fast, lightweight |

### 2.3 Recommendation: Consider Migration Path

**For this project's needs (CBA indicators):**

1. **Document lengths:** Methods documents can be 2-4k characters (well within 8k limit)
2. **Query types:** Technical sustainability terms, indicator names, measurement approaches
3. **Language:** Primarily English, some technical terminology

**Recommended evaluation order:**

| Priority | Model | Why |
|----------|-------|-----|
| 1 | `nomic-embed-text` (keep) | Known working, adequate for current needs |
| 2 | `snowflake-arctic-embed:335m` | Same context, better quality if resources allow |
| 3 | `qwen3-embedding:0.6b` | If multilingual support needed later |

**Migration considerations:**
- Changing embedding model requires **full KB rebuild**
- Different dimensions require schema changes
- Recommend keeping `nomic-embed-text` for now, evaluating alternatives in Phase 3

### 2.4 Configuration for Model Flexibility

**Current environment variable:**
```env
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
```

**Proposed: Add dimension awareness:**
```python
# src/agentic_cba_indicators/tools/_embedding.py

EMBEDDING_MODEL = os.environ.get("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

# Expected dimensions by model (for validation)
EMBEDDING_DIMENSIONS = {
    "nomic-embed-text": 768,
    "mxbai-embed-large": 1024,
    "snowflake-arctic-embed:335m": 1024,
    "qwen3-embedding:0.6b": 1024,
    "embeddinggemma": 768,
    "all-minilm:33m": 384,
}

def get_expected_dimensions() -> int:
    """Get expected embedding dimensions for current model."""
    return EMBEDDING_DIMENSIONS.get(EMBEDDING_MODEL, 768)
```

---

## Part 3: URL Enrichment Roadmap

### 3.1 API Selection Strategy

Given CBA indicators cover **agriculture, sustainability, environmental science, and socio-economics**, the API selection should prioritize sources with strong coverage in these domains:

| Priority | API | Domain Coverage | Rate Limits | Why Use |
|----------|-----|-----------------|-------------|---------|
| **1** | [CrossRef](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | Universal (150M+ DOIs) | Polite pool: unlimited with email | Primary source for all DOIs. Free, comprehensive, no auth required. |
| **2** | [OpenAlex](https://docs.openalex.org/) | Universal (250M+ works) | 100k/day free | Fallback for CrossRef misses. Open dataset, good for citation graphs. |
| **3** | [Semantic Scholar](https://www.semanticscholar.org/product/api) | General academic | 5k/5min (free tier) | Abstracts, influential citations, related papers. Good for context. |
| **4** | [PubMed](https://www.ncbi.nlm.nih.gov/home/develop/api/) | Biomedical/health | 3 req/sec (no key) | Health-related CBA indicators (human well-being, nutrition). |
| - | [zbMATH](https://zbmath.org/api/), [INSPIRE-HEP](https://github.com/inspirehep/rest-api-doc), [DBLP](https://dblp.org/faq/How+to+use+the+dblp+search+API.html) | Math/Physics/CS | Varies | **Not relevant** for CBA domain. Skip. |
| - | [ERIC](https://eric.ed.gov/?api=), [HAL](https://api.archives-ouvertes.fr/docs/) | Education/French | Varies | Low relevance. Consider only if specific need arises. |

### 3.2 CrossRef API Integration (Primary)

**Endpoint:** `https://api.crossref.org/works/{doi}`

**Example request:**
```bash
curl "https://api.crossref.org/works/10.1016/j.agee.2020.106989?mailto=your@email.com"
```

**Response fields to extract:**
| Field | Path | Use |
|-------|------|-----|
| Title | `message.title[0]` | Display, search |
| Authors | `message.author[].given + family` | Display |
| Journal | `message.container-title[0]` | Display |
| Year | `message.published.date-parts[0][0]` | Display, sort |
| Abstract | `message.abstract` | Optional enrichment |
| License | `message.license[0].URL` | Open access detection |
| Type | `message.type` | Filter (journal-article, book-chapter, etc.) |

**Implementation pattern:**
```python
# src/agentic_cba_indicators/tools/_crossref.py (future)

import httpx
from typing import Optional
from dataclasses import dataclass

CROSSREF_BASE = "https://api.crossref.org"
CROSSREF_MAILTO = os.environ.get("CROSSREF_MAILTO", "")  # Polite pool

@dataclass
class CrossRefMetadata:
    """Metadata fetched from CrossRef API."""
    title: Optional[str] = None
    authors: list[str] = field(default_factory=list)
    journal: Optional[str] = None
    year: Optional[int] = None
    doi_url: Optional[str] = None
    license_url: Optional[str] = None
    abstract: Optional[str] = None

def fetch_crossref_metadata(doi: str) -> Optional[CrossRefMetadata]:
    """Fetch metadata from CrossRef API for a DOI.

    Uses polite pool if CROSSREF_MAILTO is set.
    Falls back gracefully on errors.
    """
    params = {}
    if CROSSREF_MAILTO:
        params["mailto"] = CROSSREF_MAILTO

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(
                f"{CROSSREF_BASE}/works/{doi}",
                params=params,
            )
            if response.status_code == 404:
                return None  # DOI not in CrossRef
            response.raise_for_status()

            data = response.json().get("message", {})

            # Extract authors
            authors = []
            for author in data.get("author", []):
                name = f"{author.get('given', '')} {author.get('family', '')}".strip()
                if name:
                    authors.append(name)

            # Extract year
            year = None
            published = data.get("published", {}).get("date-parts", [[]])
            if published and published[0]:
                year = published[0][0]

            return CrossRefMetadata(
                title=data.get("title", [None])[0],
                authors=authors,
                journal=data.get("container-title", [None])[0],
                year=year,
                doi_url=data.get("URL"),
                license_url=data.get("license", [{}])[0].get("URL"),
                abstract=data.get("abstract"),
            )
    except Exception as e:
        logger.warning(f"CrossRef fetch failed for {doi}: {e}")
        return None
```

### 3.3 Fallback Chain Architecture

```
DOI → CrossRef API
        ↓ (404 or timeout)
      OpenAlex API
        ↓ (404 or timeout)
      Basic DOI URL only (https://doi.org/{doi})
```

### 3.4 Future Enrichment Sources

| Source | Data | Implementation |
|--------|------|----------------|
| DOI.org | Canonical URL | ✅ Direct generation (Phase 1) |
| CrossRef API | Full metadata (title, authors, journal, year, abstract) | Phase 4: on-demand enrichment |
| OpenAlex API | Fallback metadata + citation counts | Phase 4: fallback |
| Semantic Scholar | Related papers, influential citations | Phase 5+: discovery features |
| Unpaywall | Open access PDF links | Phase 5+: full-text access |

### 3.5 Enrichment Architecture (Phase 4+)

```python
@dataclass
class EnrichedCitation(Citation):
    """Citation with additional fetched metadata."""

    # From CrossRef
    title: Optional[str] = None
    authors: Optional[list[str]] = None
    journal: Optional[str] = None
    year: Optional[int] = None
    abstract: Optional[str] = None

    # From Unpaywall
    open_access_url: Optional[str] = None

    # Enrichment metadata
    enriched_at: Optional[str] = None
    enrichment_source: Optional[str] = None
```

**Enrichment approaches:**
1. **On-demand (runtime):** Fetch when agent requests citation details
2. **Batch (ingestion):** Pre-fetch during KB build (slower, but offline-capable)
3. **Hybrid:** Store DOI, fetch metadata lazily on first request, cache

**Recommended:** Start with option 1 (on-demand) to avoid API rate limits during ingestion.

---

## Part 4: Implementation Checklist

### Phase 1: Citation Normalization (This PR)
- [ ] Create `Citation` dataclass with `from_raw()`, `to_embed_string()`, `to_display_string()`
- [ ] Add `normalize_doi()`, `extract_doi_from_text()`, `clean_citation_text()`, `doi_to_url()`
- [ ] Update `extract_citations()` to return `list[Citation]`
- [ ] Update `MethodDoc.citations` type from `list[str]` to `list[Citation]`
- [ ] Update `MethodDoc.to_text()` for embedding (minimal citations)
- [ ] Add `MethodDoc.to_display_text()` for user output (full URLs)
- [ ] Add `--preview-citations` CLI flag
- [ ] Add unit tests for DOI normalization edge cases
- [ ] Run ingestion and verify KB integrity

### Phase 2: Metadata & KB Tools (Next PR)
- [ ] Update `MethodsGroupDoc.to_metadata()` with citation counts, DOIs
- [ ] Update `knowledge_base.py` tools to use display format when returning
- [ ] Add `search_by_doi()` tool for direct citation lookup

### Phase 3: Embedding Model Evaluation (Future)
- [ ] Create benchmark script comparing retrieval quality
- [ ] Test with real indicator queries
- [ ] Document migration path if switching models

### Phase 4: URL Enrichment (Future)
- [ ] Add `CROSSREF_MAILTO` env var for polite pool access
- [ ] Implement `fetch_crossref_metadata()` in `_crossref.py`
- [ ] Implement `fetch_openalex_metadata()` as fallback
- [ ] Add `enrich_citation()` tool with caching
- [ ] Add tool for agent to request citation enrichment on demand

---

## Part 5: Test Cases for DOI Normalization

Test cases informed by [DOI Handbook](https://www.doi.org/the-identifier/resources/handbook/) (ISO 26324) and real-world CBA literature patterns.

```python
# tests/test_citation_normalization.py

import pytest
from scripts.ingest_excel import normalize_doi, Citation, extract_doi_from_text

@pytest.mark.parametrize("input_doi,expected", [
    # Standard formats (per DOI Handbook)
    ("10.1234/abc", "10.1234/abc"),
    ("10.1234/ABC", "10.1234/abc"),  # Case-insensitive per spec
    ("doi: 10.1234/abc", "10.1234/abc"),
    ("DOI:10.1234/abc", "10.1234/abc"),

    # URL formats (common in citations)
    ("https://doi.org/10.1234/abc", "10.1234/abc"),
    ("http://doi.org/10.1234/abc", "10.1234/abc"),
    ("https://dx.doi.org/10.1234/abc", "10.1234/abc"),  # Legacy dx. prefix
    ("doi.org/10.1234/abc", "10.1234/abc"),  # No scheme

    # Real CBA-relevant publishers
    ("10.1016/j.agee.2020.106989", "10.1016/j.agee.2020.106989"),  # Elsevier
    ("10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),    # Nature
    ("10.3390/su12041234", "10.3390/su12041234"),                   # MDPI Sustainability
    ("10.5281/zenodo.1234567", "10.5281/zenodo.1234567"),           # Zenodo datasets

    # Special characters in suffix (allowed per spec)
    ("10.1234/abc-def_123", "10.1234/abc-def_123"),
    ("10.1234/abc.def(2020)", "10.1234/abc.def(2020)"),
    ("10.1000/xyz123(2020)01.02", "10.1000/xyz123(2020)01.02"),  # From DOI Handbook

    # Edge cases
    ("", None),
    ("   ", None),
    ("not a doi", None),
    ("10.123/too-short-prefix", None),  # Prefix must be 4+ digits (10.XXXX)
    ("10./missing-suffix", None),        # Empty prefix after 10.
    ("http://example.com/paper", None),  # Not a DOI
])
def test_normalize_doi(input_doi, expected):
    assert normalize_doi(input_doi) == expected


@pytest.mark.parametrize("text,expected", [
    ("Smith et al. https://doi.org/10.1234/abc", "10.1234/abc"),
    ("Available at doi:10.1234/abc", "10.1234/abc"),
    ("No DOI here", None),
])
def test_extract_doi_from_text(text, expected):
    assert extract_doi_from_text(text) == expected


def test_citation_from_raw_with_doi():
    cite = Citation.from_raw("Smith et al. 2020", "10.1234/ABC")
    assert cite.text == "Smith et al. 2020"
    assert cite.doi == "10.1234/abc"
    assert cite.url == "https://doi.org/10.1234/abc"


def test_citation_from_raw_doi_in_text():
    cite = Citation.from_raw("Smith et al. https://doi.org/10.1234/abc", "")
    assert "Smith et al." in cite.text
    assert cite.doi == "10.1234/abc"
    assert cite.url == "https://doi.org/10.1234/abc"


def test_citation_to_embed_string():
    cite = Citation.from_raw("Smith et al. 2020", "10.1234/abc")
    embed = cite.to_embed_string()
    assert "10.1234" not in embed  # No DOI in embedding
    assert "doi.org" not in embed  # No URL in embedding
    assert "Smith et al. 2020" in embed


def test_citation_to_display_string():
    cite = Citation.from_raw("Smith et al. 2020", "10.1234/abc")
    display = cite.to_display_string()
    assert "https://doi.org/10.1234/abc" in display
    assert "Smith et al. 2020" in display
```

---

## Part 6: Alignment with Project Objectives

| Objective | How This Strategy Supports It |
|-----------|-------------------------------|
| Reliable first-run experience | Citations normalize consistently regardless of Excel input format |
| Robust HTTP interactions | DOI URLs use canonical HTTPS, future CrossRef API follows existing `_http.py` patterns |
| Deterministic ingestion | Same input → same normalized citations, stable document IDs |
| High-integrity data | DOI validation catches malformed references |
| Centralized utilities | `Citation` class reusable across ingestion scripts |
| Predictable tool outputs | Agent receives consistent citation format with actionable URLs |
| Safe error handling | Invalid DOIs degrade gracefully (text-only, no URL) |

---

## Appendix A: DOI Format Specification

Per the [DOI Handbook](https://www.doi.org/the-identifier/resources/handbook/) (ISO 26324):

**DOI Syntax:**
```
doi = "10." prefix "/" suffix
prefix = 4+ digits (registrant code, assigned by registration agency)
suffix = any printable characters (case-insensitive per spec)
```

**Key validation rules:**
1. **Prefix must be 4+ digits** - e.g., `10.1000`, `10.12345` (not `10.12`)
2. **Suffix can contain any characters** - including `/`, `.`, `-`, `(`, `)`, etc.
3. **Case-insensitive** - `10.1234/ABC` and `10.1234/abc` resolve to same resource
4. **No length limit** - suffixes can be very long (100+ chars in some registries)

**Common registrant prefixes in CBA-relevant literature:**
| Prefix | Publisher/Registry |
|--------|-------------------|
| `10.1016` | Elsevier (Agriculture, Ecosystems & Environment, etc.) |
| `10.1038` | Nature Publishing Group |
| `10.1126` | Science/AAAS |
| `10.1111` | Wiley |
| `10.1007` | Springer |
| `10.3390` | MDPI (Sustainability, Agriculture, etc.) |
| `10.1080` | Taylor & Francis |
| `10.1371` | PLOS |
| `10.5281` | Zenodo (datasets) |

**Valid DOI examples:**
- `10.1038/nature12373` (Nature)
- `10.1126/science.1259855` (Science)
- `10.1016/j.agee.2020.106989` (Elsevier journal article)
- `10.5281/zenodo.1234567` (Zenodo dataset)
- `10.1000/xyz123(2020)01.02` (special characters in suffix)

**Invalid DOI examples:**
- `10.123/abc` - Prefix too short (only 3 digits)
- `doi:abc` - Missing `10.` prefix
- `http://example.com/paper` - Not a DOI at all
- `10./missing-prefix` - Empty prefix after `10.`

---

## Appendix B: Embedding Model Migration Checklist

If switching from `nomic-embed-text` to another model:

1. **Update environment:**
   ```env
   OLLAMA_EMBEDDING_MODEL=snowflake-arctic-embed:335m
   ```

2. **Pull new model:**
   ```bash
   ollama pull snowflake-arctic-embed:335m
   ```

3. **Clear and rebuild KB:**
   ```bash
   python scripts/ingest_excel.py --clear
   python scripts/ingest_usecases.py --clear
   ```

4. **Update dimension validation** (if dimensions differ):
   ```python
   # _embedding.py - update MIN_EMBEDDING_DIM if needed
   ```

5. **Test retrieval quality** with representative queries

6. **Document model version** in README for reproducibility

---

## Appendix C: API Reference & Resources

### Recommended APIs (by priority)

| API | Documentation | Auth | Rate Limits |
|-----|---------------|------|-------------|
| **CrossRef** | [REST API Docs](https://www.crossref.org/documentation/retrieve-metadata/rest-api/) | None (polite pool with email) | Unlimited with `mailto=` param |
| **OpenAlex** | [API Docs](https://docs.openalex.org/) | None | 100k/day, 10/sec |
| **Semantic Scholar** | [API Docs](https://www.semanticscholar.org/product/api) | API key (free tier) | 5k requests per 5 min |
| **PubMed/NCBI** | [E-utilities](https://www.ncbi.nlm.nih.gov/home/develop/api/) | API key (optional) | 3/sec without key, 10/sec with |

### Specialized APIs (low priority for CBA)

| API | Documentation | Domain | Notes |
|-----|---------------|--------|-------|
| zbMATH | [API](https://zbmath.org/api/) | Mathematics | Skip for CBA |
| ERIC | [API](https://eric.ed.gov/?api=) | Education | Rarely relevant |
| HAL | [Docs](https://api.archives-ouvertes.fr/docs/) | French repositories | Regional focus |
| INSPIRE-HEP | [Docs](https://github.com/inspirehep/rest-api-doc) | High-energy physics | Not relevant |
| DBLP | [API](https://dblp.org/faq/How+to+use+the+dblp+search+API.html) | Computer science | Not relevant |

### Standards & References

| Resource | URL | Use |
|----------|-----|-----|
| DOI Handbook | [doi.org/handbook](https://www.doi.org/the-identifier/resources/handbook) | DOI syntax, validation rules |
| DOI Handbook PDF | [September 2025 PDF](https://www.doi.org/doi-handbook/DOI_Handbook_Final.pdf) | Authoritative reference |
| ISO 26324 | [ISO standard](https://www.iso.org/standard/81599.html) | DOI system specification |
| CrossRef schema | [Schema library](https://www.crossref.org/documentation/schema-library/) | Metadata field definitions |

### Environment Variables for Enrichment

```env
# CrossRef (recommended for polite pool)
CROSSREF_MAILTO=your.email@organization.org

# Semantic Scholar (optional, for higher limits)
SEMANTIC_SCHOLAR_API_KEY=your_key_here

# PubMed (optional, for higher limits)
NCBI_API_KEY=your_key_here
```
