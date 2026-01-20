"""Tests for UI prompt selection behavior."""

from __future__ import annotations

from unittest.mock import MagicMock


def test_create_agent_for_ui_uses_prompt_name(monkeypatch) -> None:
    from agentic_cba_indicators import ui

    config = {
        "active_provider": "ollama",
        "providers": {
            "ollama": {
                "host": "http://localhost:11434",
                "model_id": "llama3.1:latest",
            }
        },
        "agent": {
            "tool_set": "reduced",
            "conversation_window": 5,
            "prompt_name": "system_prompt",
        },
    }

    captured: dict[str, str | None] = {"name": None}

    def fake_get_system_prompt(name: str | None = None) -> str:
        captured["name"] = name
        return "prompt"

    monkeypatch.setattr(ui, "load_config", lambda _: config)
    monkeypatch.setattr(ui, "create_model", lambda _: MagicMock())
    monkeypatch.setattr(ui, "get_system_prompt", fake_get_system_prompt)

    _, _, agent_config = ui.create_agent_for_ui("ollama", "reduced")

    assert captured["name"] == agent_config.prompt_name
