"""Tests for knowledge base query caching."""

from __future__ import annotations

from typing import Any

from agentic_cba_indicators.tools import knowledge_base as kb


def test_search_indicators_cache_hit(monkeypatch):
    kb.reset_kb_query_cache()
    calls = {"embed": 0, "query": 0}

    class DummyCollection:
        def count(self) -> int:
            return 1

        def query(self, **kwargs: Any):
            calls["query"] += 1
            return {
                "documents": [["Indicator: Test indicator"]],
                "metadatas": [
                    [
                        {
                            "id": 1,
                            "component": "Abiotic",
                            "class": "Soil",
                            "unit": "kg",
                            "total_principles": 0,
                            "total_criteria": 0,
                        }
                    ]
                ],
                "distances": [[0.1]],
            }

    def fake_embed(_: str):
        calls["embed"] += 1
        return [0.0]

    monkeypatch.setattr(kb, "_get_collection", lambda name: DummyCollection())
    monkeypatch.setattr(kb, "_get_embedding", fake_embed)

    result1 = kb.search_indicators("soil", n_results=1)
    result2 = kb.search_indicators("soil", n_results=1)

    assert result1 == result2
    assert calls["embed"] == 1
    assert calls["query"] == 1


def test_search_methods_cache_hit(monkeypatch):
    kb.reset_kb_query_cache()
    calls = {"embed": 0, "query": 0}

    class DummyCollection:
        def count(self) -> int:
            return 1

        def query(self, **kwargs: Any):
            calls["query"] += 1
            return {
                "documents": [["Method: Test method"]],
                "metadatas": [
                    [
                        {
                            "indicator_id": 1,
                            "indicator": "Test",
                            "method_count": 1,
                            "has_high_accuracy": False,
                            "has_low_cost": False,
                            "has_high_ease": False,
                        }
                    ]
                ],
                "distances": [[0.1]],
            }

    def fake_embed(_: str):
        calls["embed"] += 1
        return [0.0]

    monkeypatch.setattr(kb, "_get_collection", lambda name: DummyCollection())
    monkeypatch.setattr(kb, "_get_embedding", fake_embed)

    result1 = kb.search_methods("soil", n_results=1)
    result2 = kb.search_methods("soil", n_results=1)

    assert result1 == result2
    assert calls["embed"] == 1
    assert calls["query"] == 1
