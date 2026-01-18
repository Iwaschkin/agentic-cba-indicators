"""CrossRef API integration for DOI metadata enrichment.

Fetches citation metadata (title, authors, journal, year, abstract) from
CrossRef API to enrich DOI citations in the knowledge base.

API Documentation: https://www.crossref.org/documentation/retrieve-metadata/rest-api/

Uses "polite pool" (faster rate limits) when CROSSREF_EMAIL is set.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import httpx

from agentic_cba_indicators.config._secrets import get_api_key
from agentic_cba_indicators.logging_config import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

# CrossRef API configuration
CROSSREF_BASE = "https://api.crossref.org"
CROSSREF_TIMEOUT = float(os.environ.get("CROSSREF_TIMEOUT", "15.0"))

# Rate limiting: CrossRef polite pool allows ~50 req/sec with mailto
# Without mailto: ~1 req/sec (public pool)
# We'll be conservative with batch operations
CROSSREF_BATCH_DELAY = float(os.environ.get("CROSSREF_BATCH_DELAY", "0.1"))


@dataclass
class CrossRefMetadata:
    """Metadata fetched from CrossRef API for a DOI."""

    doi: str
    title: str | None = None
    authors: list[str] = field(default_factory=list)
    journal: str | None = None
    year: int | None = None
    doi_url: str | None = None
    license_url: str | None = None
    abstract: str | None = None
    work_type: str | None = None  # journal-article, book-chapter, etc.
    issn: str | None = None
    publisher: str | None = None

    def to_display_string(self) -> str:
        """Format metadata for display to user."""
        parts = []

        if self.authors:
            if len(self.authors) <= 3:
                parts.append(", ".join(self.authors))
            else:
                parts.append(f"{self.authors[0]} et al.")

        if self.year:
            parts.append(f"({self.year})")

        if self.title:
            # Truncate very long titles
            title = self.title[:200] + "..." if len(self.title) > 200 else self.title
            parts.append(f'"{title}"')

        if self.journal:
            parts.append(f"*{self.journal}*")

        if self.doi_url:
            parts.append(self.doi_url)

        return " ".join(parts) if parts else f"DOI: {self.doi}"

    def to_embed_string(self) -> str:
        """Format metadata for embedding (semantic search).

        Focuses on searchable content without URLs/formatting noise.
        """
        parts = []

        if self.title:
            parts.append(self.title)

        if self.journal:
            parts.append(self.journal)

        if self.abstract:
            # Include abstract for richer semantic matching
            parts.append(self.abstract)

        return " | ".join(parts) if parts else ""


def fetch_crossref_metadata(doi: str) -> CrossRefMetadata | None:
    """Fetch metadata from CrossRef API for a single DOI.

    Uses polite pool if CROSSREF_EMAIL is set (recommended for batch operations).

    Args:
        doi: Normalized DOI (e.g., "10.1016/j.agee.2020.106989")

    Returns:
        CrossRefMetadata if found, None if DOI not in CrossRef or error
    """
    params: dict[str, str] = {}
    crossref_email = get_api_key("crossref")
    if crossref_email:
        params["mailto"] = crossref_email

    try:
        with httpx.Client(timeout=CROSSREF_TIMEOUT) as client:
            response = client.get(
                f"{CROSSREF_BASE}/works/{doi}",
                params=params,
            )

            if response.status_code == 404:
                logger.debug("DOI not found in CrossRef: %s", doi)
                return None

            response.raise_for_status()
            data = response.json().get("message", {})

            return _parse_crossref_response(doi, data)

    except httpx.TimeoutException:
        logger.warning("CrossRef timeout for DOI: %s", doi)
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("CrossRef HTTP error for %s: %s", doi, e.response.status_code)
        return None
    except Exception as e:
        logger.warning("CrossRef fetch failed for %s: %s", doi, e)
        return None


def _parse_crossref_response(doi: str, data: dict[str, Any]) -> CrossRefMetadata:
    """Parse CrossRef API response into CrossRefMetadata."""
    # Extract authors
    authors = []
    for author in data.get("author", []):
        given = author.get("given", "")
        family = author.get("family", "")
        name = f"{given} {family}".strip()
        if name:
            authors.append(name)

    # Extract year from various date fields
    year = None
    for date_field in ["published", "published-print", "published-online", "issued"]:
        if date_field in data:
            date_parts = data[date_field].get("date-parts", [[]])
            if date_parts and date_parts[0] and len(date_parts[0]) > 0:
                year = int(date_parts[0][0])
                break

    # Extract abstract (may contain HTML/XML)
    abstract = data.get("abstract")
    if abstract:
        # Basic cleanup of JATS XML tags
        import re

        abstract = re.sub(r"<[^>]+>", "", abstract)
        abstract = abstract.strip()

    # Extract ISSN (prefer print, then electronic)
    issn = None
    issn_list = data.get("ISSN", [])
    if issn_list:
        issn = issn_list[0]

    # Safely extract fields that might be empty arrays
    title_list = data.get("title", [])
    title = title_list[0] if title_list else None

    journal_list = data.get("container-title", [])
    journal = journal_list[0] if journal_list else None

    license_list = data.get("license", [])
    license_url = license_list[0].get("URL") if license_list else None

    return CrossRefMetadata(
        doi=doi,
        title=title,
        authors=authors,
        journal=journal,
        year=year,
        doi_url=data.get("URL"),
        license_url=license_url,
        abstract=abstract,
        work_type=data.get("type"),
        issn=issn,
        publisher=data.get("publisher"),
    )


def fetch_crossref_batch(
    dois: list[str],
    progress_callback: Callable[..., None] | None = None,
) -> dict[str, CrossRefMetadata | None]:
    """Fetch metadata for multiple DOIs with rate limiting.

    Args:
        dois: List of normalized DOIs
        progress_callback: Optional callback for progress reporting.
            Can accept 2 args: (current, total)
            Or 4 args: (current, total, doi, found)

    Returns:
        Dict mapping DOI -> CrossRefMetadata (or None if not found)
    """
    import inspect
    import time

    results: dict[str, CrossRefMetadata | None] = {}
    total = len(dois)

    # Detect callback signature
    use_extended_callback = False
    if progress_callback:
        try:
            sig = inspect.signature(progress_callback)
            use_extended_callback = len(sig.parameters) >= 4
        except (ValueError, TypeError):
            pass

    for i, doi in enumerate(dois):
        metadata = fetch_crossref_metadata(doi)
        results[doi] = metadata
        found = metadata is not None

        if progress_callback:
            if use_extended_callback:
                progress_callback(i + 1, total, doi, found)
            else:
                progress_callback(i + 1, total)

        # Rate limiting between requests
        if i < total - 1 and CROSSREF_BATCH_DELAY > 0:
            time.sleep(CROSSREF_BATCH_DELAY)

    return results
