"""Tests for Excel ingestion embedding handling."""

from __future__ import annotations

import sys
from pathlib import Path


def _import_ingest_excel():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    sys.path.insert(0, str(scripts_dir))
    import ingest_excel  # type: ignore

    return ingest_excel


def test_upsert_indicators_skips_failed_embeddings(monkeypatch):
    ingest_excel = _import_ingest_excel()

    class DummyCollection:
        def __init__(self):
            self.upserted = None

        def upsert(self, ids, embeddings, documents, metadatas):
            self.upserted = {
                "ids": ids,
                "embeddings": embeddings,
                "documents": documents,
                "metadatas": metadatas,
            }

    class DummyClient:
        def __init__(self):
            self.collection = DummyCollection()

        def get_or_create_collection(self, name, metadata=None):
            return self.collection

    def fake_embed_documents(documents, verbose=False, strict=False):
        return [None, [0.1, 0.2, 0.3]]

    monkeypatch.setattr(ingest_excel, "embed_documents", fake_embed_documents)

    indicators = [
        ingest_excel.IndicatorDoc(
            id=1,
            component="Abiotic",
            indicator_class="Soil",
            indicator_text="Test 1",
            unit="unit",
            field_methods=True,
            lab_methods=False,
            remote_sensing=False,
            social_participatory=False,
            production_audits=False,
            principles=["1"],
            criteria={"1.1": "P"},
        ),
        ingest_excel.IndicatorDoc(
            id=2,
            component="Abiotic",
            indicator_class="Soil",
            indicator_text="Test 2",
            unit="unit",
            field_methods=True,
            lab_methods=False,
            remote_sensing=False,
            social_participatory=False,
            production_audits=False,
            principles=["1"],
            criteria={"1.1": "P"},
        ),
    ]

    client = DummyClient()
    count, failed = ingest_excel.upsert_indicators(client, indicators)

    assert count == 1
    assert failed == ["indicator:1"]
    assert client.collection.upserted is not None
    assert client.collection.upserted["ids"] == ["indicator:2"]


# =============================================================================
# OA Enrichment Tests
# =============================================================================


def test_citation_enrich_from_unpaywall():
    """Test Citation.enrich_from_unpaywall() method."""
    ingest_excel = _import_ingest_excel()

    # Create mock Unpaywall metadata
    class MockUnpaywallMetadata:
        doi = "10.1234/test"
        is_oa = True
        oa_status = "gold"
        pdf_url = "https://example.com/paper.pdf"
        license = "cc-by"
        version = "publishedVersion"
        host_type = "publisher"

    citation = ingest_excel.Citation(
        raw_text="Test et al. (2023)",
        text="Test et al. (2023)",
        doi="10.1234/test",
    )
    citation.enrich_from_unpaywall(MockUnpaywallMetadata())

    assert citation.is_oa is True
    assert citation.oa_status == "gold"
    assert citation.pdf_url == "https://example.com/paper.pdf"
    assert citation.license == "cc-by"
    assert citation.version == "publishedVersion"
    assert citation.host_type == "publisher"


def test_citation_enrich_from_unpaywall_none():
    """Test Citation.enrich_from_unpaywall() with None metadata."""
    ingest_excel = _import_ingest_excel()

    citation = ingest_excel.Citation(
        raw_text="Test et al. (2023)", text="Test et al. (2023)"
    )
    citation.enrich_from_unpaywall(None)

    # Should remain at default values
    assert citation.is_oa is False
    assert citation.oa_status is None
    assert citation.pdf_url is None
    assert citation.license is None
    assert citation.version is None
    assert citation.host_type is None


def test_citation_to_embed_string_with_oa():
    """Test Citation.to_embed_string() includes OA information when enriched."""
    ingest_excel = _import_ingest_excel()

    citation = ingest_excel.Citation(
        raw_text="Smith et al. (2023). Test Paper.",
        text="Smith et al. (2023). Test Paper.",
        doi="10.1234/test",
        url="https://doi.org/10.1234/test",
        enriched_title="Test Paper",
        enriched_authors=["Smith, J.", "Doe, A."],
        enriched_year=2023,
        enrichment_source="crossref",  # Required for enriched output
        is_oa=True,
        oa_status="gold",
        license="cc-by",
    )

    embed_str = citation.to_embed_string()

    # Enriched embedding includes title and license
    assert "Test Paper" in embed_str
    assert "License: cc-by" in embed_str


def test_citation_to_display_string_with_oa():
    """Test Citation.to_display_string() shows OA badge and PDF link."""
    ingest_excel = _import_ingest_excel()

    citation = ingest_excel.Citation(
        raw_text="Smith et al. (2023). Test Paper.",
        text="Smith et al. (2023). Test Paper.",
        doi="10.1234/test",
        is_oa=True,
        pdf_url="https://example.com/paper.pdf",
    )

    display_str = citation.to_display_string()

    assert "🔓" in display_str  # OA badge
    assert "[PDF](https://example.com/paper.pdf)" in display_str


def test_citation_to_display_string_no_oa():
    """Test Citation.to_display_string() without OA shows no badge."""
    ingest_excel = _import_ingest_excel()

    citation = ingest_excel.Citation(
        raw_text="Smith et al. (2023). Test Paper.",
        text="Smith et al. (2023). Test Paper.",
        doi="10.1234/test",
        is_oa=False,
    )

    display_str = citation.to_display_string()

    assert "🔓" not in display_str
    assert "[PDF]" not in display_str


def test_methods_group_doc_to_metadata_oa_fields():
    """Test MethodsGroupDoc.to_metadata() includes OA fields."""
    ingest_excel = _import_ingest_excel()

    # Create citations with mixed OA status
    citations = [
        ingest_excel.Citation(
            raw_text="Paper 1",
            text="Paper 1",
            doi="10.1234/oa",
            is_oa=True,
            pdf_url="http://pdf1.com",
        ),
        ingest_excel.Citation(
            raw_text="Paper 2", text="Paper 2", doi="10.1234/closed", is_oa=False
        ),
        ingest_excel.Citation(
            raw_text="Paper 3", text="Paper 3", doi="10.1234/oa2", is_oa=True
        ),
        ingest_excel.Citation(raw_text="No DOI paper", text="No DOI paper"),  # No DOI
    ]

    methods = [
        ingest_excel.MethodDoc(
            indicator_id=1,
            indicator_text="Test Indicator",
            unit="kg",
            method_general="Method 1",
            method_specific="Specific 1",
            notes="Some notes",
            accuracy="High",
            ease="Medium",
            cost="Low",
            citations=citations,
        )
    ]

    group = ingest_excel.MethodsGroupDoc(
        indicator_id=1, indicator_text="Test", unit="kg", methods=methods
    )

    metadata = group.to_metadata()

    assert "oa_count" in metadata
    assert "has_oa_citations" in metadata
    assert metadata["oa_count"] == 2  # Two OA citations
    assert metadata["has_oa_citations"] is True
    assert (
        metadata["citation_count"] == 4
    )  # Total citations (including one without DOI)
    assert metadata["doi_count"] == 3  # Three citations with DOIs


def test_methods_group_doc_to_metadata_no_oa():
    """Test MethodsGroupDoc.to_metadata() with no OA citations."""
    ingest_excel = _import_ingest_excel()

    citations = [
        ingest_excel.Citation(
            raw_text="Paper 1", text="Paper 1", doi="10.1234/closed", is_oa=False
        ),
        ingest_excel.Citation(raw_text="Paper 2", text="Paper 2"),  # No DOI
    ]

    methods = [
        ingest_excel.MethodDoc(
            indicator_id=1,
            indicator_text="Test Indicator",
            unit="kg",
            method_general="Method 1",
            method_specific="Specific 1",
            notes="Some notes",
            accuracy="High",
            ease="Medium",
            cost="Low",
            citations=citations,
        )
    ]

    group = ingest_excel.MethodsGroupDoc(
        indicator_id=1, indicator_text="Test", unit="kg", methods=methods
    )

    metadata = group.to_metadata()

    assert metadata["oa_count"] == 0
    assert metadata["has_oa_citations"] is False
    assert metadata["citation_count"] == 2  # Total citations
    assert metadata["doi_count"] == 1  # One citation with DOI
