"""Tests for CLI logging setup wiring."""

from __future__ import annotations

from unittest.mock import MagicMock


def test_cli_calls_setup_logging(monkeypatch) -> None:
    import builtins
    import sys

    from agentic_cba_indicators import cli
    from agentic_cba_indicators.config import AgentConfig, ProviderConfig

    called = {"value": False}

    def fake_setup_logging() -> None:
        called["value"] = True

    def fake_create_agent_from_config(**_):
        return (
            MagicMock(),
            ProviderConfig(name="ollama", model_id="llama3.1:latest"),
            AgentConfig(),
        )

    monkeypatch.setattr(cli, "setup_logging", fake_setup_logging)
    monkeypatch.setattr(cli, "create_agent_from_config", fake_create_agent_from_config)
    monkeypatch.setattr(cli, "print_banner", lambda **_: None)
    monkeypatch.setattr(cli, "print_help", lambda: None)
    monkeypatch.setattr(
        builtins, "input", lambda _: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    monkeypatch.setattr(sys, "argv", ["agentic-cba"])

    cli.main()

    assert called["value"] is True
