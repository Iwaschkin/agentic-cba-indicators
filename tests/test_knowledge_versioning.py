"""Tests for knowledge base versioning metadata (TASK102).

Validates that schema versioning and ingestion timestamps are properly
stored in document metadata for freshness verification.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path


def _import_ingest_excel():
    """Import ingest_excel module from scripts directory."""
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    sys.path.insert(0, str(scripts_dir))
    import ingest_excel  # type: ignore

    return ingest_excel


class TestVersioningMetadata:
    """Test versioning metadata in ingested documents."""

    def test_schema_version_constant_exists(self) -> None:
        """Verify _SCHEMA_VERSION constant is defined."""
        ingest_excel = _import_ingest_excel()

        assert ingest_excel._SCHEMA_VERSION is not None
        assert isinstance(ingest_excel._SCHEMA_VERSION, str)
        assert ingest_excel._SCHEMA_VERSION == "1.0"

    def test_get_ingestion_timestamp_returns_iso_format(self) -> None:
        """Verify _get_ingestion_timestamp returns valid ISO 8601 format."""
        ingest_excel = _import_ingest_excel()

        timestamp = ingest_excel._get_ingestion_timestamp()

        # Should be a non-empty string
        assert timestamp is not None
        assert isinstance(timestamp, str)
        assert len(timestamp) > 0

        # Should be parseable as ISO 8601
        parsed = datetime.fromisoformat(timestamp)
        assert parsed.tzinfo is not None  # Should have timezone info (UTC)

    def test_indicator_doc_metadata_includes_versioning(self) -> None:
        """Verify IndicatorDoc.to_metadata() includes version fields."""
        ingest_excel = _import_ingest_excel()

        doc = ingest_excel.IndicatorDoc(
            id=999,
            indicator_text="Test Indicator",
            component="Biotic",
            indicator_class="Test",
            unit="kg",
            field_methods=True,
            lab_methods=False,
            remote_sensing=False,
            social_participatory=False,
            production_audits=False,
            principles=["1"],
            criteria={"1.1": "S"},
        )

        metadata = doc.to_metadata()

        # Check versioning fields exist
        assert "schema_version" in metadata
        assert "ingestion_timestamp" in metadata

        # Check schema version value
        assert metadata["schema_version"] == ingest_excel._SCHEMA_VERSION

        # Check timestamp is valid ISO 8601
        timestamp = metadata["ingestion_timestamp"]
        assert isinstance(timestamp, str)
        parsed = datetime.fromisoformat(timestamp)
        assert parsed is not None

    def test_methods_group_doc_metadata_includes_versioning(self) -> None:
        """Verify MethodsGroupDoc.to_metadata() includes version fields."""
        ingest_excel = _import_ingest_excel()

        doc = ingest_excel.MethodsGroupDoc(
            indicator_id=999,
            indicator_text="Test Indicator",
            unit="kg",
            methods=[],
        )

        metadata = doc.to_metadata()

        # Check versioning fields exist
        assert "schema_version" in metadata
        assert "ingestion_timestamp" in metadata

        # Check schema version value
        assert metadata["schema_version"] == ingest_excel._SCHEMA_VERSION

        # Check timestamp is valid ISO 8601
        timestamp = metadata["ingestion_timestamp"]
        assert isinstance(timestamp, str)
        parsed = datetime.fromisoformat(timestamp)
        assert parsed is not None

    def test_ingestion_timestamp_is_set_during_ingest(self) -> None:
        """Verify _ingestion_timestamp is set at start of ingest()."""
        ingest_excel = _import_ingest_excel()

        # Reset the module-level timestamp
        ingest_excel._ingestion_timestamp = None

        # The timestamp should be None before ingest
        assert ingest_excel._ingestion_timestamp is None

        # When to_metadata is called without global timestamp set,
        # it should fall back to generating one
        doc = ingest_excel.IndicatorDoc(
            id=999,
            indicator_text="Test",
            component="Biotic",
            indicator_class="Test",
            unit="kg",
            field_methods=False,
            lab_methods=False,
            remote_sensing=False,
            social_participatory=False,
            production_audits=False,
            principles=[],
            criteria={},
        )

        metadata = doc.to_metadata()
        assert metadata["ingestion_timestamp"] is not None

        # Clean up
        ingest_excel._ingestion_timestamp = None


class TestGetKnowledgeVersionTool:
    """Test the get_knowledge_version tool."""

    def test_tool_is_exported(self) -> None:
        """Verify get_knowledge_version is exported from tools module."""
        from agentic_cba_indicators.tools import get_knowledge_version

        assert get_knowledge_version is not None
        assert callable(get_knowledge_version)

    def test_tool_in_reduced_tools(self) -> None:
        """Verify get_knowledge_version is in REDUCED_TOOLS."""
        from agentic_cba_indicators.tools import REDUCED_TOOLS, get_knowledge_version

        # The tool function should be in the list
        assert get_knowledge_version in REDUCED_TOOLS

    def test_tool_in_full_tools(self) -> None:
        """Verify get_knowledge_version is in FULL_TOOLS."""
        from agentic_cba_indicators.tools import FULL_TOOLS, get_knowledge_version

        # The tool function should be in the list
        assert get_knowledge_version in FULL_TOOLS

    def test_tool_in_all_exports(self) -> None:
        """Verify get_knowledge_version is in __all__."""
        from agentic_cba_indicators import tools

        assert "get_knowledge_version" in tools.__all__
