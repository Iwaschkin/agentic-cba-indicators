"""Unpaywall API integration for Open Access metadata.

Fetches OA status and PDF locations for DOIs from the Unpaywall database.

API Documentation: https://unpaywall.org/products/api

Uses polite pool when UNPAYWALL_EMAIL is set (required for production use).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import httpx

from agentic_cba_indicators.config._secrets import get_api_key
from agentic_cba_indicators.logging_config import get_logger

logger = get_logger(__name__)

# Unpaywall API configuration
UNPAYWALL_BASE = "https://api.unpaywall.org/v2"
UNPAYWALL_TIMEOUT = float(os.environ.get("UNPAYWALL_TIMEOUT", "10.0"))


@dataclass
class UnpaywallMetadata:
    """Open Access metadata from Unpaywall API."""

    doi: str
    is_oa: bool = False
    oa_status: str | None = None  # gold, green, hybrid, bronze, closed
    pdf_url: str | None = None  # Best OA PDF location
    license: str | None = None  # CC-BY, CC-BY-NC, etc.
    version: str | None = None  # publishedVersion, acceptedVersion, submittedVersion
    host_type: str | None = None  # publisher, repository


def fetch_unpaywall_metadata(doi: str) -> UnpaywallMetadata | None:
    """Fetch Open Access metadata from Unpaywall API for a single DOI.

    Requires UNPAYWALL_EMAIL to be set for API access (polite pool).

    Args:
        doi: Normalized DOI (e.g., "10.1016/j.agee.2020.106989")

    Returns:
        UnpaywallMetadata if found, None if DOI not in Unpaywall or error
    """
    email = get_api_key("unpaywall")
    if not email:
        logger.debug("UNPAYWALL_EMAIL not set, skipping OA enrichment")
        return None

    try:
        with httpx.Client(timeout=UNPAYWALL_TIMEOUT) as client:
            response = client.get(
                f"{UNPAYWALL_BASE}/{doi}",
                params={"email": email},
            )

            if response.status_code == 404:
                logger.debug("DOI not found in Unpaywall: %s", doi)
                return None

            response.raise_for_status()
            data = response.json()

            return _parse_unpaywall_response(doi, data)

    except httpx.TimeoutException:
        logger.warning("Unpaywall timeout for DOI: %s", doi)
        return None
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 429:
            logger.warning("Unpaywall rate limit exceeded for DOI: %s", doi)
        else:
            logger.warning(
                "Unpaywall HTTP error %s for DOI: %s", e.response.status_code, doi
            )
        return None
    except Exception as e:
        logger.warning("Unpaywall error for DOI %s: %s", doi, e)
        return None


def _parse_unpaywall_response(doi: str, data: dict) -> UnpaywallMetadata:
    """Parse Unpaywall API response into UnpaywallMetadata.

    Args:
        doi: The DOI being queried
        data: Raw JSON response from Unpaywall API

    Returns:
        UnpaywallMetadata with extracted fields
    """
    is_oa = data.get("is_oa", False)
    oa_status = data.get("oa_status")  # gold, green, hybrid, bronze, closed

    # Get best OA location
    best_oa = data.get("best_oa_location")
    pdf_url = None
    license_str = None
    version = None
    host_type = None

    if best_oa:
        pdf_url = best_oa.get("url_for_pdf") or best_oa.get("url")
        license_str = best_oa.get("license")
        version = best_oa.get("version")
        host_type = best_oa.get("host_type")

    return UnpaywallMetadata(
        doi=doi,
        is_oa=is_oa,
        oa_status=oa_status,
        pdf_url=pdf_url,
        license=license_str,
        version=version,
        host_type=host_type,
    )
