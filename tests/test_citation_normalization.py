"""
Tests for citation normalization and DOI handling.

Tests DOI normalization per DOI Handbook (ISO 26324) and Citation class functionality.
"""

import sys
from pathlib import Path

import pytest

# Add scripts to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from ingest_excel import (  # type: ignore[import-not-found]
    DOI_PATTERN,
    Citation,
    clean_citation_text,
    doi_to_url,
    extract_doi_from_text,
    normalize_doi,
)

# =============================================================================
# DOI Pattern Tests
# =============================================================================


class TestDOIPattern:
    """Tests for DOI_PATTERN regex."""

    def test_matches_standard_doi(self):
        """DOI pattern matches standard 10.XXXX/suffix format."""
        assert DOI_PATTERN.search("10.1234/abc")
        assert DOI_PATTERN.search("10.12345/abc-def")

    def test_matches_url_format(self):
        """DOI pattern matches URL formats."""
        assert DOI_PATTERN.search("https://doi.org/10.1234/abc")
        assert DOI_PATTERN.search("http://dx.doi.org/10.1234/abc")

    def test_rejects_short_prefix(self):
        """DOI pattern rejects prefix shorter than 4 digits."""
        assert DOI_PATTERN.search("10.123/abc") is None

    def test_rejects_non_doi(self):
        """DOI pattern rejects non-DOI strings."""
        assert DOI_PATTERN.search("not a doi") is None
        assert DOI_PATTERN.search("http://example.com") is None


# =============================================================================
# normalize_doi Tests
# =============================================================================


class TestNormalizeDOI:
    """Tests for normalize_doi() function."""

    @pytest.mark.parametrize(
        "input_doi,expected",
        [
            # Standard formats
            ("10.1234/abc", "10.1234/abc"),
            ("10.1234/ABC", "10.1234/abc"),  # Case-insensitive
            ("10.12345/abc-def_123", "10.12345/abc-def_123"),
            # With doi: prefix
            ("doi: 10.1234/abc", "10.1234/abc"),
            ("DOI:10.1234/abc", "10.1234/abc"),
            ("doi:10.1234/abc", "10.1234/abc"),
            # URL formats
            ("https://doi.org/10.1234/abc", "10.1234/abc"),
            ("http://doi.org/10.1234/ABC", "10.1234/abc"),
            ("https://dx.doi.org/10.1234/abc", "10.1234/abc"),
            ("doi.org/10.1234/abc", "10.1234/abc"),  # No scheme
            # Real CBA-relevant publishers
            ("10.1016/j.agee.2020.106989", "10.1016/j.agee.2020.106989"),  # Elsevier
            ("10.1038/s41586-020-2649-2", "10.1038/s41586-020-2649-2"),  # Nature
            ("10.3390/su12041234", "10.3390/su12041234"),  # MDPI
            ("10.5281/zenodo.1234567", "10.5281/zenodo.1234567"),  # Zenodo
            # Special characters in suffix (per DOI Handbook)
            ("10.1234/abc-def_123", "10.1234/abc-def_123"),
            ("10.1234/abc.def", "10.1234/abc.def"),
            # Edge cases - invalid
            ("", None),
            ("   ", None),
            ("not a doi", None),
            ("10.123/too-short-prefix", None),  # Prefix < 4 digits
            ("http://example.com/paper", None),
        ],
    )
    def test_normalize_doi(self, input_doi, expected):
        """Test DOI normalization with various formats."""
        assert normalize_doi(input_doi) == expected


# =============================================================================
# extract_doi_from_text Tests
# =============================================================================


class TestExtractDOIFromText:
    """Tests for extract_doi_from_text() function."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            # DOI at end of citation
            ("Smith et al. 2020 https://doi.org/10.1234/abc", "10.1234/abc"),
            ("Smith et al. doi:10.1234/abc", "10.1234/abc"),
            # DOI in middle
            ("See doi:10.1234/abc for details", "10.1234/abc"),
            # Multiple DOIs (returns first)
            ("10.1234/first and 10.5678/second", "10.1234/first"),
            # No DOI
            ("No DOI here", None),
            ("", None),
        ],
    )
    def test_extract_doi_from_text(self, text, expected):
        """Test DOI extraction from citation text."""
        assert extract_doi_from_text(text) == expected


# =============================================================================
# clean_citation_text Tests
# =============================================================================


class TestCleanCitationText:
    """Tests for clean_citation_text() function."""

    @pytest.mark.parametrize(
        "text,expected",
        [
            # Remove [DOI: ...] patterns
            ("Smith et al. 2020 [DOI: 10.1234/abc]", "Smith et al. 2020"),
            ("Smith [DOI:10.1234/abc] et al.", "Smith et al."),
            # Remove URL DOIs
            (
                "Smith et al. https://doi.org/10.1234/abc",
                "Smith et al.",
            ),
            # Whitespace cleanup
            ("Smith   et   al.  2020", "Smith et al. 2020"),
            ("  leading and trailing  ", "leading and trailing"),
            # Empty/None
            ("", ""),
        ],
    )
    def test_clean_citation_text(self, text, expected):
        """Test citation text cleaning."""
        assert clean_citation_text(text) == expected


# =============================================================================
# doi_to_url Tests
# =============================================================================


class TestDOIToURL:
    """Tests for doi_to_url() function."""

    def test_generates_https_url(self):
        """doi_to_url generates canonical HTTPS URL."""
        assert doi_to_url("10.1234/abc") == "https://doi.org/10.1234/abc"

    def test_preserves_doi_exactly(self):
        """doi_to_url preserves the DOI without modification."""
        assert doi_to_url("10.1016/j.agee.2020.106989") == (
            "https://doi.org/10.1016/j.agee.2020.106989"
        )


# =============================================================================
# Citation Class Tests
# =============================================================================


class TestCitation:
    """Tests for Citation dataclass."""

    def test_from_raw_with_explicit_doi(self):
        """Citation.from_raw handles explicit DOI from column."""
        cite = Citation.from_raw("Smith et al. 2020", "10.1234/ABC")
        assert cite.text == "Smith et al. 2020"
        assert cite.doi == "10.1234/abc"
        assert cite.url == "https://doi.org/10.1234/abc"
        assert cite.raw_text == "Smith et al. 2020 10.1234/ABC"

    def test_from_raw_with_doi_in_text(self):
        """Citation.from_raw extracts DOI from citation text."""
        cite = Citation.from_raw("Smith et al. https://doi.org/10.1234/abc", "")
        assert "Smith et al." in cite.text
        assert cite.doi == "10.1234/abc"
        assert cite.url == "https://doi.org/10.1234/abc"

    def test_from_raw_no_doi(self):
        """Citation.from_raw handles citations without DOI."""
        cite = Citation.from_raw("Smith et al. 2020", "")
        assert cite.text == "Smith et al. 2020"
        assert cite.doi is None
        assert cite.url is None

    def test_from_raw_doi_only(self):
        """Citation.from_raw handles DOI-only input."""
        cite = Citation.from_raw("", "10.1234/abc")
        assert cite.text == ""
        assert cite.doi == "10.1234/abc"
        assert cite.url == "https://doi.org/10.1234/abc"

    def test_to_embed_string_no_doi(self):
        """to_embed_string returns text without DOI/URL."""
        cite = Citation.from_raw("Smith et al. 2020", "10.1234/abc")
        embed = cite.to_embed_string()
        assert "Smith et al." in embed
        assert "10.1234" not in embed
        assert "doi.org" not in embed

    def test_to_display_string_with_url(self):
        """to_display_string includes URL when available."""
        cite = Citation.from_raw("Smith et al. 2020", "10.1234/abc")
        display = cite.to_display_string()
        assert "Smith et al. 2020" in display
        assert "https://doi.org/10.1234/abc" in display

    def test_to_display_string_without_doi(self):
        """to_display_string returns text only when no DOI."""
        cite = Citation.from_raw("Smith et al. 2020", "")
        display = cite.to_display_string()
        assert display == "Smith et al. 2020"


# =============================================================================
# Integration Tests
# =============================================================================


class TestCitationIntegration:
    """Integration tests for citation normalization workflow."""

    def test_full_workflow_with_doi(self):
        """Test complete workflow from raw to display."""
        # Simulate Excel data
        raw_cite = "Nomani et al., 2012"
        raw_doi = "DOI:10.2174/1874213001205010025"

        cite = Citation.from_raw(raw_cite, raw_doi)

        # Embedding should be clean
        embed = cite.to_embed_string()
        assert embed == "Nomani et al., 2012"
        assert "DOI" not in embed

        # Display should have URL
        display = cite.to_display_string()
        assert "Nomani et al., 2012" in display
        assert "https://doi.org/10.2174/1874213001205010025" in display

    def test_full_workflow_embedded_doi(self):
        """Test workflow when DOI is embedded in citation text."""
        raw_cite = "Glennie et al., 2015 https://doi.org/10.1371/journal.pone.0121333"
        raw_doi = ""

        cite = Citation.from_raw(raw_cite, raw_doi)

        # DOI should be extracted
        assert cite.doi == "10.1371/journal.pone.0121333"

        # Text should be cleaned
        assert "Glennie et al., 2015" in cite.text
        assert "doi.org" not in cite.text

    def test_preserves_raw_for_traceability(self):
        """Test that raw_text preserves original input."""
        cite = Citation.from_raw("Smith 2020 doi:10.1234/abc", "10.5678/def")

        # raw_text should contain both inputs
        assert "Smith 2020" in cite.raw_text
        assert "10.5678/def" in cite.raw_text
