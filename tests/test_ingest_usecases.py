"""Tests for use case ingestion embedding handling."""

from __future__ import annotations

import sys
from pathlib import Path


def _import_ingest_usecases():
    scripts_dir = Path(__file__).resolve().parents[1] / "scripts"
    sys.path.insert(0, str(scripts_dir))
    import ingest_usecases  # type: ignore

    return ingest_usecases


def test_upsert_usecase_docs_skips_failed_embeddings(monkeypatch):
    ingest_usecases = _import_ingest_usecases()

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

    def fake_get_embeddings_batch(texts, strict=False):
        return [None, [0.2, 0.3]]

    monkeypatch.setattr(
        ingest_usecases, "get_embeddings_batch", fake_get_embeddings_batch
    )

    overview = ingest_usecases.UseCaseOverviewDoc(
        use_case_slug="slug",
        use_case_name="Name",
        country="Country",
        region="Region",
        commodity="Commodity",
        summary_text="Summary",
        outcome_count=1,
    )
    outcome = ingest_usecases.UseCaseOutcomeDoc(
        use_case_slug="slug",
        use_case_name="Name",
        country="Country",
        region="Region",
        commodity="Commodity",
        outcome_id="1",
        outcome_text="Outcome",
    )

    client = DummyClient()
    count, failed = ingest_usecases.upsert_usecase_docs(client, overview, [outcome])

    assert count == 1
    assert failed == ["usecase:slug:overview"]
    assert client.collection.upserted["ids"] == ["usecase:slug:outcome:1"]
