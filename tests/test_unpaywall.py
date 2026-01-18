"""Tests for Unpaywall API integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agentic_cba_indicators.tools._unpaywall import (
    _parse_unpaywall_response,
    fetch_unpaywall_metadata,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_unpaywall_response() -> dict:
    """Mock successful Unpaywall API response."""
    return {
        "doi": "10.1234/example",
        "is_oa": True,
        "oa_status": "gold",
        "best_oa_location": {
            "url_for_pdf": "https://example.com/paper.pdf",
            "license": "cc-by",
            "version": "publishedVersion",
            "host_type": "publisher",
        },
    }


@pytest.fixture
def mock_unpaywall_response_bronze() -> dict:
    """Mock Unpaywall API response for bronze OA."""
    return {
        "doi": "10.1234/bronze",
        "is_oa": True,
        "oa_status": "bronze",
        "best_oa_location": {
            "url_for_pdf": None,
            "license": None,
            "version": "publishedVersion",
            "host_type": "publisher",
        },
    }


@pytest.fixture
def mock_unpaywall_response_closed() -> dict:
    """Mock Unpaywall API response for closed access paper."""
    return {
        "doi": "10.1234/closed",
        "is_oa": False,
        "oa_status": "closed",
        "best_oa_location": None,
    }


# =============================================================================
# Test UnpaywallMetadata Parsing
# =============================================================================


def test_parse_unpaywall_response_gold(mock_unpaywall_response: dict) -> None:
    """Test _parse_unpaywall_response() with gold OA response."""
    metadata = _parse_unpaywall_response("10.1234/example", mock_unpaywall_response)

    assert metadata is not None
    assert metadata.doi == "10.1234/example"
    assert metadata.is_oa is True
    assert metadata.oa_status == "gold"
    assert metadata.pdf_url == "https://example.com/paper.pdf"
    assert metadata.license == "cc-by"
    assert metadata.version == "publishedVersion"
    assert metadata.host_type == "publisher"


def test_parse_unpaywall_response_bronze(
    mock_unpaywall_response_bronze: dict,
) -> None:
    """Test _parse_unpaywall_response() with bronze OA response."""
    metadata = _parse_unpaywall_response(
        "10.1234/bronze", mock_unpaywall_response_bronze
    )

    assert metadata is not None
    assert metadata.doi == "10.1234/bronze"
    assert metadata.is_oa is True
    assert metadata.oa_status == "bronze"
    assert metadata.pdf_url is None
    assert metadata.license is None
    assert metadata.version == "publishedVersion"
    assert metadata.host_type == "publisher"


def test_parse_unpaywall_response_closed(
    mock_unpaywall_response_closed: dict,
) -> None:
    """Test _parse_unpaywall_response() with closed access response."""
    metadata = _parse_unpaywall_response(
        "10.1234/closed", mock_unpaywall_response_closed
    )

    assert metadata is not None
    assert metadata.doi == "10.1234/closed"
    assert metadata.is_oa is False
    assert metadata.oa_status == "closed"
    assert metadata.pdf_url is None
    assert metadata.license is None
    assert metadata.version is None
    assert metadata.host_type is None


# =============================================================================
# Test fetch_unpaywall_metadata()
# =============================================================================


@patch("agentic_cba_indicators.tools._unpaywall.httpx.Client")
@patch("agentic_cba_indicators.tools._unpaywall.get_api_key")
def test_fetch_unpaywall_metadata_success(
    mock_get_key: MagicMock,
    mock_client_class: MagicMock,
    mock_unpaywall_response: dict,
) -> None:
    """Test fetch_unpaywall_metadata() with successful response."""
    mock_get_key.return_value = "test@example.com"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_unpaywall_response

    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.return_value = mock_response
    mock_client_class.return_value = mock_client

    metadata = fetch_unpaywall_metadata("10.1234/example")

    assert metadata is not None
    assert metadata.doi == "10.1234/example"
    assert metadata.is_oa is True
    assert metadata.oa_status == "gold"
    assert metadata.pdf_url == "https://example.com/paper.pdf"


@patch("agentic_cba_indicators.tools._unpaywall.httpx.Client")
@patch("agentic_cba_indicators.tools._unpaywall.get_api_key")
def test_fetch_unpaywall_metadata_404(
    mock_get_key: MagicMock, mock_client_class: MagicMock
) -> None:
    """Test fetch_unpaywall_metadata() with 404 not found."""
    mock_get_key.return_value = "test@example.com"

    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.return_value = mock_response
    mock_client_class.return_value = mock_client

    metadata = fetch_unpaywall_metadata("10.1234/notfound")

    assert metadata is None


@patch("agentic_cba_indicators.tools._unpaywall.httpx.Client")
@patch("agentic_cba_indicators.tools._unpaywall.get_api_key")
def test_fetch_unpaywall_metadata_429_rate_limit(
    mock_get_key: MagicMock, mock_client_class: MagicMock
) -> None:
    """Test fetch_unpaywall_metadata() with 429 rate limit."""
    import httpx

    mock_get_key.return_value = "test@example.com"

    mock_response = MagicMock()
    mock_response.status_code = 429
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Rate limit", request=MagicMock(), response=mock_response
    )

    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.return_value = mock_response
    mock_client_class.return_value = mock_client

    metadata = fetch_unpaywall_metadata("10.1234/ratelimit")

    assert metadata is None


@patch("agentic_cba_indicators.tools._unpaywall.httpx.Client")
@patch("agentic_cba_indicators.tools._unpaywall.get_api_key")
def test_fetch_unpaywall_metadata_timeout(
    mock_get_key: MagicMock, mock_client_class: MagicMock
) -> None:
    """Test fetch_unpaywall_metadata() with timeout."""
    import httpx

    mock_get_key.return_value = "test@example.com"

    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.side_effect = httpx.TimeoutException(
        "Timeout"
    )
    mock_client_class.return_value = mock_client

    metadata = fetch_unpaywall_metadata("10.1234/timeout")

    assert metadata is None


@patch("agentic_cba_indicators.tools._unpaywall.get_api_key")
def test_fetch_unpaywall_metadata_no_email(mock_get_key: MagicMock) -> None:
    """Test fetch_unpaywall_metadata() without email configured."""
    mock_get_key.return_value = None

    metadata = fetch_unpaywall_metadata("10.1234/noemail")

    assert metadata is None


@patch("agentic_cba_indicators.tools._unpaywall.httpx.Client")
@patch("agentic_cba_indicators.tools._unpaywall.get_api_key")
def test_fetch_unpaywall_metadata_invalid_json(
    mock_get_key: MagicMock, mock_client_class: MagicMock
) -> None:
    """Test fetch_unpaywall_metadata() with invalid JSON response."""
    mock_get_key.return_value = "test@example.com"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = ValueError("Invalid JSON")

    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.return_value = mock_response
    mock_client_class.return_value = mock_client

    metadata = fetch_unpaywall_metadata("10.1234/badjson")

    assert metadata is None
