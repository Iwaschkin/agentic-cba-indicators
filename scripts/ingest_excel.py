"""
Deterministic Excel ingestion script for CBA ME Indicators knowledge base.

This script follows a predictable, repeatable workflow:
1. Load workbook - Read Indicators and Methods sheets
2. Normalise - Convert flags to booleans, clean citations
3. Build RAG documents - Create stable document IDs
4. Embed - Generate embeddings via Ollama
5. Upsert - Safe incremental updates to ChromaDB
6. Persist - Local storage that survives restarts

Usage:
    python scripts/ingest_excel.py
    python scripts/ingest_excel.py --file path/to/file.xlsx
    python scripts/ingest_excel.py --clear       # Clear and rebuild
    python scripts/ingest_excel.py --dry-run     # Show what would be indexed
    python scripts/ingest_excel.py --verbose     # Detailed output

Collections created:
    - indicators: One document per indicator (224 docs)
    - methods: One document per indicator with ALL methods grouped (223 docs, id=105 has none)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

import chromadb

if TYPE_CHECKING:
    from chromadb.api import ClientAPI

import pandas as pd


class IngestionSummary(TypedDict):
    """Type definition for ingestion summary dictionary."""

    indicators_count: int
    methods_groups_count: int
    total_methods: int
    missing_methods_indicator_ids: list[int]
    errors: list[str]


# Add src to path for agentic_cba_indicators imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
from agentic_cba_indicators.config._secrets import get_api_key
from agentic_cba_indicators.paths import get_kb_path
from agentic_cba_indicators.tools._crossref import (
    CrossRefMetadata,
    fetch_crossref_batch,
)
from agentic_cba_indicators.tools._embedding import (
    EMBEDDING_MODEL,
    get_embeddings_batch,
)
from agentic_cba_indicators.tools._unpaywall import (
    UnpaywallMetadata,
    fetch_unpaywall_metadata,
)

# =============================================================================
# Configuration
# =============================================================================

DEFAULT_EXCEL_FILE = (
    Path(__file__).parent.parent / "cba_inputs" / "CBA ME Indicators List.xlsx"
)
KB_PATH = get_kb_path()

BATCH_SIZE = 5  # Embedding batch size (smaller for large documents)


# =============================================================================
# Data Classes
# =============================================================================

# Principle and Criteria definitions (from Excel column headers)
PRINCIPLES = {
    "1": "Natural Environment",
    "2": "Social Well-being",
    "3": "Economic Prosperity",
    "4": "Diversity",
    "5": "Connectivity",
    "6": "Adaptive Capacity",
    "7": "Harmony",
}

CRITERIA = {
    "1.1": "Avoid ecosystem degradation",
    "1.2": "Minimize GHG emissions and enhance sinks",
    "1.3": "Shift to environmentally sustainable practices",
    "1.4": "Shift to renewable and bio-based processes",
    "2.1": "Enhance human health and wellbeing",
    "2.2": "Enhance equity and inclusion",
    "2.3": "Shift to just governance",
    "3.1": "Enhance economic prosperity",
    "3.2": "Enhance livelihoods",
    "4.1": "Conserve and restore ecological diversity",
    "4.2": "Support and enhance social and cultural diversity",
    "4.3": "Enhance economic diversity",
    "5.1": "Restore ecological connectivity",
    "5.2": "Enhance social connectivity",
    "6.1": "Reduce socioecological risks",
    "6.2": "Enhance innovation capacity",
    "7.1": "Enhance nature-based solutions",
    "7.2": "Balance trade-offs between and among humans and nature",
    "7.3": "Harness local context, culture, and knowledge",
    "7.4": "Enhance multi-level compliance",
}

# Excel column mappings for principles and criteria
PRINCIPLE_COLUMNS = {
    "1": "Principle: 1. Natural Environment",
    "2": "Principle: 2. Social Well-being",
    "3": "Principle: 3. Economic Prosperity",
    "4": "Principle: 4. Diversity",
    "5": "Principle: 5. Connectivity",
    "6": "Principle: 6. Adaptive Capacity",
    "7": "Principle: 7. Harmony",
}

CRITERIA_COLUMNS = {
    "1.1": "1.1 Avoid ecosystem degradation",
    "1.2": "1.2 Minimize GHG emissions and enhance sinks",
    "1.3": "1.3. Shift to environmentally sustainable practices",
    "1.4": "1.4. Shift to renewable and bio-based processes",
    "2.1": "2.1 Enhance human health and wellbeing",
    "2.2": "2.2 Enhance equity and inclusion",
    "2.3": "2.3 Shift to just governance",
    "3.1": "3.1 Enhance economic prosperity",
    "3.2": "3.2 Enhance livelihoods",
    "4.1": "4.1 Conserve and restore ecological diversity",
    "4.2": "4.2. Support and enhance social and cultural diversity",
    "4.3": "4.3 Enhance economic diversity",
    "5.1": "5.1 Restore ecological connectivity",
    "5.2": "5.2 Enhance social connectivity",
    "6.1": "6.1 Reduce socioecological risks",
    "6.2": "6.2 Enhance innovation capacity",
    "7.1": "7.1 Enhance nature-based solutions",
    "7.2": "7.2. Balance trade-offs between and among humans and nature",
    "7.3": "7.3. Harness local context, culture, and knowledge",
    "7.4": "7.4 Enhance multi-level compliance",
}


# =============================================================================
# DOI Normalization (ISO 26324 / DOI Handbook)
# =============================================================================

# DOI regex: matches 10.XXXX/anything format per DOI Handbook (ISO 26324)
# Prefix must be 4+ digits after "10.", suffix can contain any printable chars
# NOTE: The spec allows parentheses and brackets in DOIs (e.g., old Elsevier format
# "10.1016/0011-7471(64)90001-4"), so we only exclude whitespace and angle brackets.
# Trailing punctuation (.,;:) is stripped in normalize_doi() after capture.
DOI_PATTERN = re.compile(
    r"""
    (?:https?://)?           # Optional https:// or http://
    (?:dx\.)?                # Optional legacy dx. prefix
    (?:doi\.org/)?           # Optional doi.org/
    (10\.\d{4,}/[^\s<>]+)    # Capture: 10.XXXX/identifier (allow parens/brackets)
    """,
    re.VERBOSE | re.IGNORECASE,
)


def normalize_doi(raw: str) -> str | None:
    """
    Normalize a DOI to canonical lowercase form.

    Handles various input formats per DOI Handbook (ISO 26324):
    - "10.1234/abc"
    - "doi: 10.1234/abc"
    - "https://doi.org/10.1234/ABC"
    - "http://dx.doi.org/10.1234/abc"
    - "DOI:10.1234/abc" (no space)

    Args:
        raw: Raw DOI string in any common format

    Returns:
        Normalized DOI (e.g., "10.1234/abc") or None if invalid
    """
    if not raw:
        return None

    # Strip whitespace
    raw = raw.strip()

    # Remove common "doi:" prefix (case-insensitive)
    raw = re.sub(r"^doi:\s*", "", raw, flags=re.IGNORECASE)

    # Try to match DOI pattern
    match = DOI_PATTERN.search(raw)
    if match:
        # Get raw DOI and strip trailing punctuation (.,;:) which may be
        # captured when DOI appears at end of sentence
        doi = match.group(1).rstrip(".,;:")
        # Return lowercase canonical form (DOIs are case-insensitive per spec)
        return doi.lower()

    return None


def extract_doi_from_text(text: str) -> str | None:
    """
    Extract DOI embedded in citation text.

    Args:
        text: Citation text that may contain an embedded DOI

    Returns:
        Normalized DOI if found, None otherwise
    """
    if not text:
        return None
    match = DOI_PATTERN.search(text)
    if match:
        # Strip trailing punctuation and return lowercase
        return match.group(1).rstrip(".,;:").lower()
    return None


def clean_citation_text(text: str) -> str:
    """
    Remove DOI patterns and clean up citation text.

    Args:
        text: Citation text potentially containing DOI

    Returns:
        Cleaned text with DOI removed and whitespace normalized
    """
    if not text:
        return ""

    # Remove [DOI: ...] patterns
    text = re.sub(r"\[DOI:\s*[^\]]+\]", "", text)

    # Remove standalone DOI URLs/patterns
    text = DOI_PATTERN.sub("", text)

    # Clean up whitespace (collapse multiple spaces, strip)
    text = " ".join(text.split())

    return text.strip()


def doi_to_url(doi: str) -> str:
    """
    Convert normalized DOI to canonical HTTPS URL.

    Args:
        doi: Normalized DOI (e.g., "10.1234/abc")

    Returns:
        Canonical URL (e.g., "https://doi.org/10.1234/abc")
    """
    return f"https://doi.org/{doi}"


# =============================================================================
# Citation Data Structure
# =============================================================================


@dataclass
class Citation:
    """
    Structured citation with normalized DOI and URL.

    Separates semantic content (for embeddings) from display content (for users).
    Supports optional enrichment from CrossRef and Unpaywall APIs.

    Fields:
        raw_text: Original text from Excel (for traceability)
        text: Cleaned citation text (author, year, title)
        doi: Normalized DOI (e.g., "10.1234/abc")
        url: Canonical URL (e.g., "https://doi.org/10.1234/abc")
        enriched_title: Full title from CrossRef
        enriched_authors: Author list from CrossRef
        enriched_journal: Journal name from CrossRef
        enriched_year: Publication year from CrossRef
        enriched_abstract: Abstract text from CrossRef
        enrichment_source: API source ("crossref", "openalex", etc.)
        is_oa: Whether article is Open Access (from Unpaywall)
        oa_status: OA type - "gold", "green", "hybrid", "bronze", "closed"
        pdf_url: Best available OA PDF URL
        license: Open license type (e.g., "CC-BY", "CC-BY-NC")
        version: Article version (publishedVersion, acceptedVersion, submittedVersion)
        host_type: OA location type ("publisher", "repository")
    """

    raw_text: str  # Original text from Excel (for traceability)
    text: str  # Cleaned citation text (author, year, title)
    doi: str | None = None  # Normalized DOI (e.g., "10.1234/abc")
    url: str | None = None  # Canonical URL (e.g., "https://doi.org/10.1234/abc")

    # Enrichment fields (from CrossRef API)
    enriched_title: str | None = None
    enriched_authors: list[str] = field(default_factory=list)
    enriched_journal: str | None = None
    enriched_year: int | None = None
    enriched_abstract: str | None = None
    enrichment_source: str | None = None  # "crossref", "openalex", etc.

    # Open Access metadata (from Unpaywall API)
    is_oa: bool = False
    oa_status: str | None = None  # gold, green, hybrid, bronze, closed
    pdf_url: str | None = None  # Best OA PDF location
    license: str | None = None  # CC-BY, CC-BY-NC, etc.
    version: str | None = None  # publishedVersion, acceptedVersion, submittedVersion
    host_type: str | None = None  # publisher, repository

    @classmethod
    def from_raw(cls, cite_text: str, doi_text: str = "") -> Citation:
        """
        Parse raw citation and DOI strings into structured Citation.

        Args:
            cite_text: Citation text from Excel (may contain embedded DOI)
            doi_text: Explicit DOI from DOI column (may be empty)

        Returns:
            Citation with normalized DOI and generated URL
        """
        raw = f"{cite_text} {doi_text}".strip()

        # Normalize DOI: prefer explicit DOI column, fall back to embedded
        doi = normalize_doi(doi_text) or extract_doi_from_text(cite_text)

        # Clean citation text (remove embedded DOI if we extracted it)
        text = clean_citation_text(cite_text)

        # Generate URL for valid DOIs
        url = doi_to_url(doi) if doi else None

        return cls(raw_text=raw, text=text, doi=doi, url=url)

    def to_embed_string(self) -> str:
        """
        Format for embedding (minimal, semantic content only).

        If enriched, uses enriched metadata for richer semantic matching.
        Includes license info if OA.
        Returns text without DOI or URL to avoid polluting semantic search.
        """
        if self.enrichment_source and self.enriched_title:
            # Use enriched data for better embeddings
            parts = []
            if self.enriched_title:
                parts.append(self.enriched_title)
            if self.enriched_journal:
                parts.append(self.enriched_journal)
            if self.enriched_abstract:
                # Truncate abstract to avoid overly long embeddings
                abstract = self.enriched_abstract[:500]
                parts.append(abstract)
            # Include license for OA content (helps semantic matching)
            if self.is_oa and self.license:
                parts.append(f"License: {self.license}")
            return " | ".join(parts) if parts else self.text
        return self.text

    def to_display_string(self) -> str:
        """
        Format for display to user (includes URL if available).

        If enriched, shows formatted citation with full metadata.
        Shows OA badge and PDF link if Open Access.
        Returns text with clickable DOI URL when available.
        """
        if self.enrichment_source and self.enriched_title:
            # Use enriched format
            parts = []

            # Authors
            if self.enriched_authors:
                if len(self.enriched_authors) <= 3:
                    parts.append(", ".join(self.enriched_authors))
                else:
                    parts.append(f"{self.enriched_authors[0]} et al.")

            # Year
            if self.enriched_year:
                parts.append(f"({self.enriched_year})")

            # Title
            if self.enriched_title:
                title = (
                    self.enriched_title[:150] + "..."
                    if len(self.enriched_title) > 150
                    else self.enriched_title
                )
                parts.append(f'"{title}"')

            # Journal
            if self.enriched_journal:
                parts.append(f"*{self.enriched_journal}*")

            # URL
            if self.url:
                parts.append(self.url)

            # OA badge and PDF link
            if self.is_oa and self.pdf_url:
                parts.append(f"🔓 [PDF]({self.pdf_url})")
            elif self.is_oa:
                parts.append("🔓 OA")

            return " ".join(parts) if parts else self.text

        # Fallback to basic format
        base_text = self.text

        # Add URL
        if self.url:
            base_text = f"{base_text} [{self.url}]"
        elif self.doi:
            base_text = f"{base_text} [DOI: {self.doi}]"

        # Add OA badge if available
        if self.is_oa and self.pdf_url:
            base_text = f"{base_text} 🔓 [PDF]({self.pdf_url})"
        elif self.is_oa:
            base_text = f"{base_text} 🔓 OA"

        return base_text

    def enrich_from_crossref(self, metadata: CrossRefMetadata) -> None:
        """
        Populate enrichment fields from CrossRef API response.

        Args:
            metadata: CrossRefMetadata from fetch_crossref_metadata()
        """
        self.enriched_title = metadata.title
        self.enriched_authors = metadata.authors.copy() if metadata.authors else []
        self.enriched_journal = metadata.journal
        self.enriched_year = metadata.year
        self.enriched_abstract = metadata.abstract
        self.enrichment_source = "crossref"

    def enrich_from_unpaywall(self, metadata: UnpaywallMetadata | None) -> None:
        """
        Populate Open Access fields from Unpaywall API response.

        Args:
            metadata: UnpaywallMetadata from fetch_unpaywall_metadata(), or None
        """
        if metadata is None:
            return
        self.is_oa = metadata.is_oa
        self.oa_status = metadata.oa_status
        self.pdf_url = metadata.pdf_url
        self.license = metadata.license
        self.version = metadata.version
        self.host_type = metadata.host_type


@dataclass
class IndicatorDoc:
    """Represents a single indicator document for RAG."""

    id: int
    component: str
    indicator_class: str
    indicator_text: str
    unit: str
    field_methods: bool
    lab_methods: bool
    remote_sensing: bool
    social_participatory: bool
    production_audits: bool
    principles: list[str]  # List of principle IDs: ["1", "4", "7"]
    criteria: dict[str, str]  # Criteria ID -> marking: {"1.1": "P", "4.1": "x"}

    @property
    def doc_id(self) -> str:
        return f"indicator:{self.id}"

    @property
    def total_principles(self) -> int:
        return len(self.principles)

    @property
    def total_criteria(self) -> int:
        return len(self.criteria)

    def to_document_text(self) -> str:
        """Generate searchable document text."""
        parts = [
            f"Indicator: {self.indicator_text}",
            f"Component: {self.component}",
            f"Class: {self.indicator_class}",
            f"Unit: {self.unit}",
        ]

        categories = []
        if self.field_methods:
            categories.append("Field methods")
        if self.lab_methods:
            categories.append("Lab methods")
        if self.remote_sensing:
            categories.append("Remote sensing & modelling")
        if self.social_participatory:
            categories.append("Social and participatory methods")
        if self.production_audits:
            categories.append("Production assessments and audits")

        if categories:
            parts.append(f"Measurement approaches: {', '.join(categories)}")

        # Add principle coverage with names
        if self.principles:
            principle_names = [
                f"{pid}. {PRINCIPLES[pid]}" for pid in sorted(self.principles)
            ]
            parts.append(
                f"Principles covered ({len(self.principles)}): {', '.join(principle_names)}"
            )

        # Add criteria coverage with names and markings
        if self.criteria:
            criteria_parts = []
            for cid in sorted(self.criteria.keys()):
                marking = self.criteria[cid]
                marking_label = "(Primary)" if marking == "P" else ""
                criteria_parts.append(
                    f"{cid} {CRITERIA.get(cid, '')} {marking_label}".strip()
                )
            parts.append(f"Criteria covered ({len(self.criteria)}):")
            parts.extend(f"  - {cp}" for cp in criteria_parts)

        return "\n".join(parts)

    def to_metadata(self) -> dict:
        """Generate metadata for filtering."""
        import json

        return {
            "id": self.id,
            "component": self.component,
            "class": self.indicator_class,
            "unit": self.unit,
            "field_methods": self.field_methods,
            "lab_methods": self.lab_methods,
            "remote_sensing": self.remote_sensing,
            "social_participatory": self.social_participatory,
            "production_audits": self.production_audits,
            "total_principles": self.total_principles,
            "total_criteria": self.total_criteria,
            # Store as JSON strings for ChromaDB compatibility
            "principles_json": json.dumps(self.principles),
            "criteria_json": json.dumps(self.criteria),
            # Individual principle flags for filtering
            "principle_1": "1" in self.principles,
            "principle_2": "2" in self.principles,
            "principle_3": "3" in self.principles,
            "principle_4": "4" in self.principles,
            "principle_5": "5" in self.principles,
            "principle_6": "6" in self.principles,
            "principle_7": "7" in self.principles,
        }


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
    citations: list[Citation] = field(default_factory=list)

    def to_text(self) -> str:
        """
        Generate text for embedding (semantic content only).

        Citations use to_embed_string() to avoid DOI/URL noise in embeddings.
        """
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

        # Use embed format for citations (text only, no DOI/URL)
        if self.citations:
            cite_texts = [c.to_embed_string() for c in self.citations if c.text]
            if cite_texts:
                parts.append(f"References: {'; '.join(cite_texts)}")

        return "\n".join(parts)

    def to_display_text(self) -> str:
        """
        Generate text for display to user (includes URLs).

        Citations use to_display_string() to provide clickable DOI links.
        """
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

        # Use display format for citations (with URLs)
        if self.citations:
            parts.append("References:")
            parts.extend(f"  - {c.to_display_string()}" for c in self.citations)

        return "\n".join(parts)


@dataclass
class MethodsGroupDoc:
    """All methods for a single indicator, grouped for RAG retrieval."""

    indicator_id: int
    indicator_text: str
    unit: str
    methods: list[MethodDoc] = field(default_factory=list)

    @property
    def doc_id(self) -> str:
        return f"methods_for_indicator:{self.indicator_id}"

    def to_document_text(self) -> str:
        """Generate searchable document with all methods."""
        if not self.methods:
            return ""

        parts = [
            f"Measurement Methods for Indicator {self.indicator_id}:",
            f"Indicator: {self.indicator_text}",
            f"Unit: {self.unit}",
            f"Number of methods: {len(self.methods)}",
            "",
        ]

        for i, method in enumerate(self.methods, 1):
            parts.append(f"--- Method {i} ---")
            parts.append(method.to_text())
            parts.append("")

        return "\n".join(parts)

    def to_metadata(self) -> dict:
        """Generate metadata for filtering, including citation statistics."""
        import json

        # Collect unique accuracy/ease/cost levels across all methods
        accuracies = list({m.accuracy for m in self.methods if m.accuracy})
        eases = list({m.ease for m in self.methods if m.ease})
        costs = list({m.cost for m in self.methods if m.cost})

        # Collect citation statistics
        all_dois: list[str] = []
        total_citations = 0
        oa_count = 0
        for method in self.methods:
            total_citations += len(method.citations)
            for cite in method.citations:
                if cite.doi and cite.doi not in all_dois:
                    all_dois.append(cite.doi)
                if cite.is_oa:
                    oa_count += 1

        return {
            "indicator_id": self.indicator_id,
            "indicator": self.indicator_text,
            "unit": self.unit,
            "method_count": len(self.methods),
            "has_high_accuracy": "High" in accuracies,
            "has_low_cost": "Low" in costs,
            "has_high_ease": "High" in eases,
            # Citation metadata
            "citation_count": total_citations,
            "doi_count": len(all_dois),
            "dois_json": json.dumps(all_dois),
            # Open Access metadata
            "oa_count": oa_count,
            "has_oa_citations": oa_count > 0,
        }


# =============================================================================
# Normalisation Helpers
# =============================================================================


def normalize_flag(value) -> bool:
    """Convert x/(x)/blank to boolean. Treats x and (x) as equivalent."""
    if pd.isna(value):
        return False
    val = str(value).strip().lower()
    return val in ["x", "(x)"]


def safe_str(value) -> str:
    """Convert value to string, handling NaN."""
    if pd.isna(value):
        return ""
    return str(value).strip()


def safe_int(value, default: int = 0) -> int:
    """Convert value to int, handling NaN."""
    if pd.isna(value):
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def extract_citations(row: pd.Series) -> list[Citation]:
    """
    Extract and normalize citations from row, including unnamed spillover columns.

    Uses Citation.from_raw() to:
    - Normalize DOIs to canonical lowercase form
    - Extract DOIs embedded in citation text
    - Generate canonical https://doi.org URLs
    - Clean citation text for embedding

    Args:
        row: pandas Series containing citation and DOI columns

    Returns:
        List of Citation objects with normalized DOIs and URLs
    """
    citations: list[Citation] = []

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
        if spillover and len(spillover) > 5:  # Avoid noise
            # Check if it looks like a DOI (has 10. prefix)
            if DOI_PATTERN.search(spillover):
                citations.append(Citation.from_raw("", spillover))
            else:
                citations.append(Citation.from_raw(spillover, ""))

    return citations


# =============================================================================
# Data Loading and Transformation
# =============================================================================


def extract_principles_and_criteria(row: pd.Series) -> tuple[list[str], dict[str, str]]:
    """Extract principle and criteria coverage from a row.

    Returns:
        Tuple of (principles list, criteria dict)
        - principles: List of principle IDs that apply (e.g., ["1", "4", "7"])
        - criteria: Dict of criteria ID -> marking (e.g., {"1.1": "P", "4.1": "x"})
    """
    principles = []
    criteria = {}

    # Extract principles (marked with x, S, or ?)
    for pid, col_name in PRINCIPLE_COLUMNS.items():
        val = safe_str(row.get(col_name, "")).lower()
        if val in ["x", "s", "?"]:
            principles.append(pid)

    # Extract criteria (marked with P, x, S, or ?)
    for cid, col_name in CRITERIA_COLUMNS.items():
        val = safe_str(row.get(col_name, ""))
        if val.upper() in ["P", "X", "S", "?"]:
            criteria[cid] = val.upper()

    return principles, criteria


def load_indicators(df: pd.DataFrame) -> list[IndicatorDoc]:
    """Load and normalise indicators from dataframe."""
    indicators = []

    for _, row in df.iterrows():
        indicator_id = safe_int(row.get("id"))
        if indicator_id == 0:
            continue

        # Extract principle and criteria coverage
        principles, criteria = extract_principles_and_criteria(row)

        doc = IndicatorDoc(
            id=indicator_id,
            component=safe_str(row.get("Component", "")),
            indicator_class=safe_str(row.get("Class", "")),
            indicator_text=safe_str(row.get("Indicator", "")),
            unit=safe_str(row.get("Unit", "")),
            field_methods=normalize_flag(row.get("Field methods")),
            lab_methods=normalize_flag(row.get("Lab methods")),
            remote_sensing=normalize_flag(row.get("Remote sensing & modelling")),
            social_participatory=normalize_flag(row.get("Social and partcipatory")),
            production_audits=normalize_flag(
                row.get("Production assessments and audits")
            ),
            principles=principles,
            criteria=criteria,
        )
        indicators.append(doc)

    return indicators


def load_methods(df: pd.DataFrame) -> dict[int, list[MethodDoc]]:
    """Load and normalise methods, grouped by indicator ID."""
    methods_by_indicator: dict[int, list[MethodDoc]] = {}

    for _, row in df.iterrows():
        indicator_id = safe_int(row.get("id"))
        if indicator_id == 0:
            continue

        method = MethodDoc(
            indicator_id=indicator_id,
            indicator_text=safe_str(row.get("Indicator", "")),
            unit=safe_str(row.get("Unit", "")),
            method_general=safe_str(row.get("Method  (General)", "")),
            method_specific=safe_str(row.get("Method  (Specific)", "")),
            notes=safe_str(row.get("Notes", "")),
            accuracy=safe_str(row.get("Accuracy (High/Medium/Low)", "")),
            ease=safe_str(row.get("Ease of Use (High/Medium/Low)", "")),
            cost=safe_str(row.get("Financial Cost (High/Medium/Low)", "")),
            citations=extract_citations(row),
        )

        # Only include if method has meaningful content
        if method.method_general or method.method_specific or method.notes:
            if indicator_id not in methods_by_indicator:
                methods_by_indicator[indicator_id] = []
            methods_by_indicator[indicator_id].append(method)

    return methods_by_indicator


def build_methods_group_docs(
    indicators: list[IndicatorDoc], methods_by_indicator: dict[int, list[MethodDoc]]
) -> tuple[list[MethodsGroupDoc], list[int]]:
    """Build grouped method documents and track indicators with no methods."""
    grouped_docs = []
    missing_methods = []

    for indicator in indicators:
        methods = methods_by_indicator.get(indicator.id, [])

        if not methods:
            missing_methods.append(indicator.id)
            continue

        group = MethodsGroupDoc(
            indicator_id=indicator.id,
            indicator_text=indicator.indicator_text,
            unit=indicator.unit,
            methods=methods,
        )
        grouped_docs.append(group)

    return grouped_docs, missing_methods


# =============================================================================
# Embedding
# =============================================================================


def embed_documents(
    documents: list[str], verbose: bool = False, strict: bool = False
) -> list[list[float] | None]:
    """Embed all documents in batches."""
    all_embeddings: list[list[float] | None] = []
    total_batches = (len(documents) + BATCH_SIZE - 1) // BATCH_SIZE

    for i in range(0, len(documents), BATCH_SIZE):
        batch = documents[i : i + BATCH_SIZE]
        batch_num = i // BATCH_SIZE + 1

        if verbose:
            print(f"    Embedding batch {batch_num}/{total_batches}...")

        embeddings = get_embeddings_batch(batch, strict=strict)
        all_embeddings.extend(embeddings)

    return all_embeddings


# =============================================================================
# ChromaDB Operations
# =============================================================================


def get_chroma_client() -> ClientAPI:
    """Get or create persistent ChromaDB client."""
    KB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(KB_PATH))


def upsert_indicators(
    client: ClientAPI,
    indicators: list[IndicatorDoc],
    verbose: bool = False,
    dry_run: bool = False,
    strict: bool = False,
) -> tuple[int, list[str]]:
    """Upsert indicator documents to ChromaDB."""
    # Use cosine distance space for normalized embeddings (bge-m3)
    # This provides proper similarity scoring in range [0, 1]
    collection = client.get_or_create_collection(
        name="indicators",
        metadata={"hnsw:space": "cosine"},
    )

    ids = [ind.doc_id for ind in indicators]
    documents = [ind.to_document_text() for ind in indicators]
    metadatas = [ind.to_metadata() for ind in indicators]

    if dry_run:
        print(f"  [DRY RUN] Would upsert {len(indicators)} indicators")
        if verbose and indicators:
            print(f"    Sample ID: {ids[0]}")
            print(f"    Sample doc (first 200 chars): {documents[0][:200]}...")
        return len(indicators), []

    print(f"  Embedding {len(documents)} indicator documents...")
    embeddings = embed_documents(documents, verbose=verbose, strict=strict)

    filtered_ids: list[str] = []
    filtered_docs: list[str] = []
    filtered_metas: list[dict] = []
    filtered_embeddings: list[list[float]] = []
    failed_ids: list[str] = []

    for doc_id, doc, meta, embedding in zip(
        ids, documents, metadatas, embeddings, strict=False
    ):
        if embedding is None:
            failed_ids.append(doc_id)
            continue
        filtered_ids.append(doc_id)
        filtered_docs.append(doc)
        filtered_metas.append(meta)
        filtered_embeddings.append(embedding)

    if failed_ids:
        print(
            f"  WARNING: Skipping {len(failed_ids)} indicators due to embedding failures"
        )

    print("  Upserting to 'indicators' collection...")
    collection.upsert(
        ids=filtered_ids,
        embeddings=filtered_embeddings,  # type: ignore[arg-type]
        documents=filtered_docs,
        metadatas=filtered_metas,  # type: ignore[arg-type]
    )

    return len(filtered_ids), failed_ids


def upsert_methods(
    client: ClientAPI,
    methods_groups: list[MethodsGroupDoc],
    verbose: bool = False,
    dry_run: bool = False,
    strict: bool = False,
) -> tuple[int, list[str]]:
    """Upsert grouped method documents to ChromaDB."""
    # Use cosine distance space for normalized embeddings (bge-m3)
    collection = client.get_or_create_collection(
        name="methods",
        metadata={"hnsw:space": "cosine"},
    )

    ids = [mg.doc_id for mg in methods_groups]
    documents = [mg.to_document_text() for mg in methods_groups]
    metadatas = [mg.to_metadata() for mg in methods_groups]

    if dry_run:
        print(f"  [DRY RUN] Would upsert {len(methods_groups)} method groups")
        if verbose and methods_groups:
            print(f"    Sample ID: {ids[0]}")
            print(f"    Sample methods count: {metadatas[0]['method_count']}")
        return len(methods_groups), []

    print(f"  Embedding {len(documents)} method group documents...")
    embeddings = embed_documents(documents, verbose=verbose, strict=strict)

    filtered_ids: list[str] = []
    filtered_docs: list[str] = []
    filtered_metas: list[dict] = []
    filtered_embeddings: list[list[float]] = []
    failed_ids: list[str] = []

    for doc_id, doc, meta, embedding in zip(
        ids, documents, metadatas, embeddings, strict=False
    ):
        if embedding is None:
            failed_ids.append(doc_id)
            continue
        filtered_ids.append(doc_id)
        filtered_docs.append(doc)
        filtered_metas.append(meta)
        filtered_embeddings.append(embedding)

    if failed_ids:
        print(
            f"  WARNING: Skipping {len(failed_ids)} method groups due to embedding failures"
        )

    print("  Upserting to 'methods' collection...")
    collection.upsert(
        ids=filtered_ids,
        embeddings=filtered_embeddings,  # type: ignore[arg-type]
        documents=filtered_docs,
        metadatas=filtered_metas,  # type: ignore[arg-type]
    )

    return len(filtered_ids), failed_ids


# =============================================================================
# Main Ingestion Logic
# =============================================================================


def collect_all_dois(methods_by_indicator: dict[int, list[MethodDoc]]) -> list[str]:
    """Collect all unique DOIs from method documents."""
    unique_dois: set[str] = set()
    for methods in methods_by_indicator.values():
        for method in methods:
            for cite in method.citations:
                if cite.doi:
                    unique_dois.add(cite.doi)
    return sorted(unique_dois)


def apply_enrichment(
    methods_by_indicator: dict[int, list[MethodDoc]],
    enrichment_data: dict[str, CrossRefMetadata | None],
) -> int:
    """Apply enrichment data to all citations in method documents.

    Returns count of citations enriched.
    """
    enriched_count = 0
    for methods in methods_by_indicator.values():
        for method in methods:
            for cite in method.citations:
                if cite.doi and cite.doi in enrichment_data:
                    meta = enrichment_data[cite.doi]
                    if meta:
                        cite.enrich_from_crossref(meta)
                        enriched_count += 1
    return enriched_count


def ingest(
    excel_file: Path,
    clear: bool = False,
    verbose: bool = False,
    dry_run: bool = False,
    strict: bool = False,
    enrich: bool = False,
) -> IngestionSummary:
    """
    Main ingestion function.

    Args:
        excel_file: Path to the Excel file
        clear: Clear existing collections before ingesting
        verbose: Enable verbose output
        dry_run: Preview without making changes
        strict: Fail on any embedding error
        enrich: Fetch DOI metadata from CrossRef API

    Returns:
        Summary dict with counts and any issues found.
    """
    summary: IngestionSummary = {
        "indicators_count": 0,
        "methods_groups_count": 0,
        "total_methods": 0,
        "missing_methods_indicator_ids": [],
        "errors": [],
    }

    # Step 1: Test Ollama connection
    if not dry_run:
        print("Testing Ollama connection...")
        try:
            test_emb = get_embeddings_batch(["test"], strict=True)
            emb_dim = len(test_emb[0]) if test_emb[0] is not None else 0
            print(f"  OK: Ollama ready (embedding dim: {emb_dim})")
        except Exception as e:
            summary["errors"].append(f"Ollama connection failed: {e}")
            print(f"  ERROR: Ollama error: {e}")
            print("  Make sure Ollama is running: ollama serve")
            print(f"  And the model is pulled: ollama pull {EMBEDDING_MODEL}")
            return summary

    # Step 2: Initialize ChromaDB
    print(f"\nInitializing ChromaDB at {KB_PATH}...")
    client = get_chroma_client()

    if clear:
        print("  Clearing existing collections...")
        for coll in client.list_collections():
            client.delete_collection(coll.name)
        print("  OK: Collections cleared")

    # Step 3: Load workbook
    print(f"\nLoading workbook: {excel_file}")
    xlsx = pd.ExcelFile(excel_file)
    print(f"  Sheets found: {xlsx.sheet_names}")

    indicators_df = pd.read_excel(xlsx, sheet_name="Indicators")
    methods_df = pd.read_excel(xlsx, sheet_name="Methods")
    print(f"  Indicators: {len(indicators_df)} rows")
    print(f"  Methods: {len(methods_df)} rows")

    # Step 4: Normalise and build documents
    print("\nNormalising data...")
    indicators = load_indicators(indicators_df)
    methods_by_indicator = load_methods(methods_df)

    print(f"  Loaded {len(indicators)} indicators")
    print(f"  Loaded methods for {len(methods_by_indicator)} indicators")

    # Step 4.5: Optionally enrich citations with CrossRef metadata
    if enrich and not dry_run:
        all_dois = collect_all_dois(methods_by_indicator)
        if all_dois:
            print(f"\nEnriching {len(all_dois)} DOIs from CrossRef...")
            crossref_email = get_api_key("crossref")
            if not crossref_email:
                print("  TIP: Set CROSSREF_EMAIL for faster rates (polite pool)")

            # Progress callback for verbose mode
            enrichment_count = 0

            def progress_cb(i: int, total: int, doi: str, found: bool) -> None:
                nonlocal enrichment_count
                if found:
                    enrichment_count += 1
                if verbose:
                    status = "OK" if found else "--"
                    print(f"  [{i}/{total}] {status} {doi}")
                elif i % 20 == 0 or i == total:
                    print(f"  Progress: {i}/{total} DOIs ({enrichment_count} found)")

            # Fetch metadata from CrossRef
            enrichment_data = fetch_crossref_batch(
                all_dois, progress_callback=progress_cb
            )

            # Apply enrichment to citation objects
            citations_enriched = apply_enrichment(methods_by_indicator, enrichment_data)
            print(
                f"  OK: Enriched {citations_enriched} citations with CrossRef metadata"
            )
        else:
            print("\n  No DOIs found to enrich")

    # Step 5: Build grouped method documents
    print("\nBuilding RAG documents...")
    methods_groups, missing_methods = build_methods_group_docs(
        indicators, methods_by_indicator
    )

    summary["missing_methods_indicator_ids"] = missing_methods
    if missing_methods:
        print(f"  WARNING: Indicators with no methods: {missing_methods}")

    total_methods = sum(len(mg.methods) for mg in methods_groups)
    print(f"  Built {len(indicators)} indicator documents")
    print(
        f"  Built {len(methods_groups)} method group documents ({total_methods} total methods)"
    )

    # Step 6: Upsert to ChromaDB
    print("\n[1/2] Processing indicators...")
    try:
        indicators_count, indicator_failures = upsert_indicators(
            client, indicators, verbose=verbose, dry_run=dry_run, strict=strict
        )
        summary["indicators_count"] = indicators_count
        if indicator_failures:
            summary["errors"].append(
                f"Embedding failed for {len(indicator_failures)} indicator documents"
            )
    except RuntimeError as e:
        summary["errors"].append(str(e))
        return summary

    print("\n[2/2] Processing methods...")
    try:
        methods_count, methods_failures = upsert_methods(
            client, methods_groups, verbose=verbose, dry_run=dry_run, strict=strict
        )
        summary["methods_groups_count"] = methods_count
        if methods_failures:
            summary["errors"].append(
                f"Embedding failed for {len(methods_failures)} method group documents"
            )
    except RuntimeError as e:
        summary["errors"].append(str(e))
        return summary
    summary["total_methods"] = total_methods

    return summary


def enrich_dois_batch(
    citations: list[Citation],
    skip_mutation: bool = False,
    verbose: bool = False,
) -> tuple[int, int, int]:
    """
    Enrich citations with CrossRef + Unpaywall metadata in batch.

    Fetches metadata from both APIs for each unique DOI:
    1. CrossRef - title, authors, journal, year, abstract
    2. Unpaywall - OA status, PDF URL, license

    Rate limited with 0.1s delay between DOIs.

    Args:
        citations: List of Citation objects to enrich
        skip_mutation: If True, still call APIs but don't modify Citation objects
        verbose: If True, show per-DOI progress

    Returns:
        Tuple of (crossref_found, unpaywall_found, total_enriched)
    """
    import time

    # Collect unique DOIs
    doi_to_citations: dict[str, list[Citation]] = {}
    for cite in citations:
        if cite.doi:
            if cite.doi not in doi_to_citations:
                doi_to_citations[cite.doi] = []
            doi_to_citations[cite.doi].append(cite)

    unique_dois = sorted(doi_to_citations.keys())
    total_dois = len(unique_dois)

    if total_dois == 0:
        print("No DOIs found to enrich")
        return (0, 0, 0)

    print(f"Enriching {total_dois} unique DOIs via CrossRef + Unpaywall...")
    if skip_mutation:
        print("(Preview mode - citations will not be modified)")

    crossref_found = 0
    unpaywall_found = 0
    total_enriched = 0

    for i, doi in enumerate(unique_dois, 1):
        # Progress logging every 10 DOIs
        if verbose or i % 10 == 0 or i == 1 or i == total_dois:
            print(f"  [{i}/{total_dois}] Processing DOI: {doi}")

        enriched_this_doi = False

        # CrossRef enrichment - always fetch
        from agentic_cba_indicators.tools._crossref import fetch_crossref_metadata

        cf_meta = fetch_crossref_metadata(doi)
        if cf_meta:
            crossref_found += 1
            if not skip_mutation:
                for cite in doi_to_citations[doi]:
                    cite.enrich_from_crossref(cf_meta)
            enriched_this_doi = True
            if verbose and cf_meta.title:
                print(f"    CrossRef: Found - {cf_meta.title[:60]}...")

        # Unpaywall enrichment - always fetch
        uw_meta = fetch_unpaywall_metadata(doi)
        if uw_meta:
            unpaywall_found += 1
            if not skip_mutation:
                for cite in doi_to_citations[doi]:
                    cite.enrich_from_unpaywall(uw_meta)
            enriched_this_doi = True
            if verbose and uw_meta.is_oa:
                print(f"    Unpaywall: OA ({uw_meta.oa_status}) - {uw_meta.pdf_url}")

        if enriched_this_doi:
            total_enriched += 1

        # Rate limiting: 0.1s delay between DOIs
        if i < total_dois:
            time.sleep(0.1)

    print("\nEnrichment Results:")
    print(
        f"  CrossRef found: {crossref_found}/{total_dois} ({crossref_found / total_dois:.1%})"
    )
    print(
        f"  Unpaywall found: {unpaywall_found}/{total_dois} ({unpaywall_found / total_dois:.1%})"
    )
    print(
        f"  Total enriched: {total_enriched}/{total_dois} ({total_enriched / total_dois:.1%})"
    )

    return (crossref_found, unpaywall_found, total_enriched)


def enrich_citations(
    excel_file: Path, verbose: bool = False, limit: int | None = None
) -> None:
    """
    Enrich DOI citations with metadata from CrossRef API.

    Fetches title, authors, journal, year, and abstract for each DOI found
    in the Methods sheet. Results are displayed (not saved to KB).

    To save enriched citations to KB, run regular ingestion after enrichment
    data has been cached (future improvement).

    Args:
        excel_file: Path to the Excel file
        verbose: If True, show individual citation details
        limit: Max DOIs to fetch (for testing). None = all DOIs.
    """
    print("=" * 60)
    print("Citation Enrichment via CrossRef API")
    print("=" * 60)
    print(f"Source: {excel_file}")
    print()

    if not excel_file.exists():
        print(f"Error: File not found: {excel_file}")
        return

    # Load methods sheet and collect citations
    df = pd.read_excel(excel_file, sheet_name="Methods")
    all_citations: list[Citation] = []

    for _, row in df.iterrows():
        indicator_id = safe_int(row.get("id"))
        if indicator_id == 0:
            continue
        citations = extract_citations(row)
        all_citations.extend(citations)

    # Limit if requested
    if limit:
        all_citations = all_citations[:limit]

    # Run batch enrichment (preview - fetch APIs but don't modify citations)
    enrich_dois_batch(all_citations, skip_mutation=True, verbose=verbose)


def preview_oa_coverage(
    excel_file: Path, verbose: bool = False, limit: int | None = None
) -> None:
    """
    Preview Open Access coverage for DOIs via Unpaywall API.

    Shows OA stats without modifying the knowledge base.

    Args:
        excel_file: Path to the Excel file
        verbose: If True, show individual DOI details
        limit: Max DOIs to check (for testing). None = all DOIs.
    """
    print("=" * 60)
    print("Open Access Coverage via Unpaywall API")
    print("=" * 60)
    print(f"Source: {excel_file}")
    print()

    if not excel_file.exists():
        print(f"Error: File not found: {excel_file}")
        return

    # Load methods sheet and collect citations
    df = pd.read_excel(excel_file, sheet_name="Methods")
    all_citations: list[Citation] = []

    for _, row in df.iterrows():
        indicator_id = safe_int(row.get("id"))
        if indicator_id == 0:
            continue
        citations = extract_citations(row)
        all_citations.extend(citations)

    # Limit if requested
    if limit:
        all_citations = all_citations[:limit]

    # Run batch enrichment (both APIs - mutate citations for OA stats)
    _crossref_found, _unpaywall_found, _total_enriched = enrich_dois_batch(
        all_citations, skip_mutation=False, verbose=verbose
    )

    # Calculate OA stats
    oa_count = sum(1 for c in all_citations if c.is_oa)
    total_citations = len(all_citations)

    print("\nOpen Access Statistics:")
    print(f"  Total citations: {total_citations}")
    print(f"  OA citations: {oa_count} ({oa_count / total_citations:.1%})")

    # Breakdown by OA status
    from collections import Counter

    oa_statuses = Counter(c.oa_status for c in all_citations if c.is_oa)
    if oa_statuses:
        print("\nOA Status Breakdown:")
        for status, count in oa_statuses.most_common():
            print(f"    {status}: {count}")


def preview_citations(excel_file: Path, verbose: bool = False) -> None:
    """
    Preview citation normalization without modifying KB.

    Shows statistics about DOI extraction and normalization to validate
    the citation parsing before running a full ingestion.

    Args:
        excel_file: Path to the Excel file
        verbose: If True, show individual citation details
    """
    print("=" * 60)
    print("Citation Normalization Preview")
    print("=" * 60)
    print(f"Source: {excel_file}")
    print()

    if not excel_file.exists():
        print(f"Error: File not found: {excel_file}")
        return

    # Load methods sheet
    df = pd.read_excel(excel_file, sheet_name="Methods")

    total_citations = 0
    with_doi = 0
    without_doi = 0
    doi_from_text = 0  # DOIs extracted from citation text (not DOI column)

    # Sample citations for verbose output
    sample_citations: list[tuple[int, Citation]] = []

    for _, row in df.iterrows():
        indicator_id = safe_int(row.get("id"))
        if indicator_id == 0:
            continue

        citations = extract_citations(row)
        for cite in citations:
            total_citations += 1

            if cite.doi:
                with_doi += 1
                # Check if DOI was extracted from text (not explicit column)
                raw_doi_cols = [
                    safe_str(row.get(col, ""))
                    for col in ["DOI", "DOI.2", "DOI.3", "DOI.4", "DOI.5"]
                ]
                if cite.doi and not any(
                    normalize_doi(d) == cite.doi for d in raw_doi_cols
                ):
                    doi_from_text += 1
            else:
                without_doi += 1

            # Collect samples for verbose output
            if verbose and len(sample_citations) < 10:
                sample_citations.append((indicator_id, cite))

    # Print statistics
    print("=== Summary ===")
    print(f"Total citations: {total_citations}")
    print(f"With DOI: {with_doi} ({100 * with_doi / max(1, total_citations):.1f}%)")
    pct_no_doi = 100 * without_doi / max(1, total_citations)
    print(f"Without DOI: {without_doi} ({pct_no_doi:.1f}%)")
    pct_from_text = 100 * doi_from_text / max(1, total_citations)
    print(f"DOI extracted from text: {doi_from_text} ({pct_from_text:.1f}%)")

    if verbose and sample_citations:
        print("\n=== Sample Citations ===")
        for indicator_id, cite in sample_citations:
            print(f"\nIndicator {indicator_id}:")
            raw_trunc = cite.raw_text[:80] + ("..." if len(cite.raw_text) > 80 else "")
            print(f"  Raw: {raw_trunc}")
            txt_trunc = cite.text[:60] + ("..." if len(cite.text) > 60 else "")
            print(f"  Text: {txt_trunc}")
            print(f"  DOI: {cite.doi or 'None'}")
            print(f"  URL: {cite.url or 'None'}")

    print("\nOK: Preview complete (no changes made to KB)")


def main():
    parser = argparse.ArgumentParser(
        description="Deterministic ingestion of CBA ME Indicators into ChromaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python scripts/ingest_excel.py                    # Standard ingestion
    python scripts/ingest_excel.py --clear            # Clear and rebuild
    python scripts/ingest_excel.py --dry-run          # Preview without changes
    python scripts/ingest_excel.py --verbose          # Detailed output
    python scripts/ingest_excel.py --preview-citations # Preview DOI normalization
    python scripts/ingest_excel.py --enrich-citations  # Fetch metadata from CrossRef
    python scripts/ingest_excel.py --enrich-citations --limit 10  # Test with 10 DOIs
        """,
    )
    parser.add_argument(
        "--file",
        "-f",
        type=Path,
        default=DEFAULT_EXCEL_FILE,
        help="Path to Excel file",
    )
    parser.add_argument(
        "--clear",
        "-c",
        action="store_true",
        help="Clear existing collections before ingesting",
    )
    parser.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail ingestion on any embedding error",
    )
    parser.add_argument(
        "--preview-citations",
        action="store_true",
        help="Preview citation normalization without modifying KB",
    )
    parser.add_argument(
        "--enrich-citations",
        action="store_true",
        help="Fetch DOI metadata from CrossRef API (preview only)",
    )
    parser.add_argument(
        "--enrich",
        action="store_true",
        help="Fetch DOI metadata from CrossRef during ingestion",
    )
    parser.add_argument(
        "--preview-oa",
        action="store_true",
        help="Preview Open Access coverage via Unpaywall without modifying KB",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of DOIs to enrich (for testing)",
    )
    args = parser.parse_args()

    # Handle --preview-citations early exit
    if args.preview_citations:
        preview_citations(args.file, args.verbose)
        sys.exit(0)

    # Handle --preview-oa early exit
    if args.preview_oa:
        preview_oa_coverage(args.file, args.verbose, args.limit)
        sys.exit(0)

    # Handle --enrich-citations early exit
    if args.enrich_citations:
        enrich_citations(args.file, args.verbose, args.limit)
        sys.exit(0)

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    print("=" * 60)
    print("CBA ME Indicators - Deterministic Ingestion")
    print("=" * 60)
    print(f"Source: {args.file}")
    print(f"Target: {KB_PATH}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")
    print()

    summary = ingest(
        excel_file=args.file,
        clear=args.clear,
        verbose=args.verbose,
        dry_run=args.dry_run,
        strict=args.strict,
        enrich=args.enrich,
    )

    # Print summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Indicators indexed: {summary['indicators_count']}")
    print(f"Method groups indexed: {summary['methods_groups_count']}")
    print(f"Total individual methods: {summary['total_methods']}")

    if summary["missing_methods_indicator_ids"]:
        print(f"Indicators without methods: {summary['missing_methods_indicator_ids']}")

    if summary["errors"]:
        print("\nErrors encountered:")
        for err in summary["errors"]:
            print(f"  - {err}")
        sys.exit(1)

    print(f"\nOK: Knowledge base ready at: {KB_PATH}")


if __name__ == "__main__":
    main()
