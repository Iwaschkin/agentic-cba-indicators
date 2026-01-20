"""Tests for batch embedding JSON error handling."""

from __future__ import annotations

import json


class FakeResponse:
    def __init__(self, status_code: int, payload=None, json_error: bool = False):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise json.JSONDecodeError("Expecting value", "", 0)
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.calls = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        self.calls += 1
        if self.calls == 1:
            return FakeResponse(200, json_error=True)
        return FakeResponse(200, payload={"embeddings": [[0.1, 0.2]]})


def test_get_embeddings_batch_handles_invalid_json(monkeypatch) -> None:
    from agentic_cba_indicators.tools import _embedding

    monkeypatch.setattr(_embedding.httpx, "Client", FakeClient)

    result = _embedding.get_embeddings_batch(["one", "two"], strict=False)

    assert result == [[0.1, 0.2], [0.1, 0.2]]
