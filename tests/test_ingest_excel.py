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

        def get_or_create_collection(self, name):
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
    assert client.collection.upserted["ids"] == ["indicator:2"]
