"""Tests for Gemini provider configuration."""

from __future__ import annotations

import types


def test_gemini_top_p_forwarded(monkeypatch) -> None:
    from agentic_cba_indicators.config.provider_factory import (
        ProviderConfig,
        create_model,
    )

    class DummyGeminiModel:
        def __init__(self, client_args, model_id, params):
            self.client_args = client_args
            self.model_id = model_id
            self.params = params

    gemini_module = types.SimpleNamespace(GeminiModel=DummyGeminiModel)
    monkeypatch.setitem(
        __import__("sys").modules, "strands.models.gemini", gemini_module
    )

    provider_config = ProviderConfig(
        name="gemini",
        model_id="gemini-2.5-flash",
        api_key="FAKE_KEY_FOR_TESTING_ONLY",  # nosec B105
        top_p=0.9,
    )

    model = create_model(provider_config)

    assert model.params["top_p"] == 0.9
    model = create_model(provider_config)

    assert model.params["top_p"] == 0.9
