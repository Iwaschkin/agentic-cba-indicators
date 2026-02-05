"""Integration tests for CLI and ChromaDB operations.

These tests verify that components work together correctly:
- CLI argument parsing and configuration loading
- ChromaDB knowledge base operations
- Agent creation workflow (mocked LLM)

Note: These tests don't require a running Ollama server as the LLM calls are mocked.
"""

from __future__ import annotations

from unittest.mock import MagicMock

# Note: Uses temp_data_dir fixture from conftest.py for ChromaDB tests


# ============================================================================
# CLI Integration Tests
# ============================================================================


class TestConfigurationLoading:
    """Test configuration loading integration."""

    def test_load_bundled_config(self):
        """Test that bundled configuration can be loaded."""
        from agentic_cba_indicators.config import load_config

        config = load_config()
        assert config is not None
        assert "active_provider" in config

    def test_get_provider_config(self):
        """Test that provider configuration can be retrieved."""
        from agentic_cba_indicators.config import get_provider_config, load_config

        config = load_config()
        provider_config = get_provider_config(config)

        assert provider_config is not None
        # Default provider should be ollama
        assert provider_config.name in [
            "ollama",
            "anthropic",
            "openai",
            "bedrock",
            "gemini",
        ]

    def test_get_agent_config(self):
        """Test that agent configuration can be retrieved."""
        from agentic_cba_indicators.config import get_agent_config, load_config

        config = load_config()
        agent_config = get_agent_config(config)

        assert agent_config is not None
        assert agent_config.tool_set in ["reduced", "full"]
        assert isinstance(agent_config.parallel_tool_calls, bool)
        assert isinstance(agent_config.prompt_name, str)


class TestAgentCreation:
    """Test agent creation workflow (mocked LLM)."""

    def test_create_agent_from_config_structure(self, monkeypatch):
        """Test that create_agent_from_config returns expected structure."""
        from agentic_cba_indicators.cli import create_agent_from_config
        from agentic_cba_indicators.config import AgentConfig, ProviderConfig

        # Mock create_model to avoid needing a real LLM
        mock_model = MagicMock()
        monkeypatch.setattr(
            "agentic_cba_indicators.cli.create_model", lambda x: mock_model
        )

        agent, provider_config, agent_config = create_agent_from_config()

        assert agent is not None
        assert isinstance(provider_config, ProviderConfig)
        assert isinstance(agent_config, AgentConfig)

    def test_provider_override(self, monkeypatch, tmp_path):
        """Test that provider_override parameter works."""
        from agentic_cba_indicators.cli import create_agent_from_config

        # Create a minimal config with multiple providers
        config_content = """
active_provider: ollama

providers:
  ollama:
    host: "http://localhost:11434"
    model_id: "llama3.1:latest"
  anthropic:
    model_id: "claude-3-sonnet"
    max_tokens: 8192

agent:
  tool_set: reduced
  conversation_window: 5
"""
        config_path = tmp_path / "test_config.yaml"
        config_path.write_text(config_content)

        # Mock create_model and environment
        mock_model = MagicMock()
        monkeypatch.setattr(
            "agentic_cba_indicators.cli.create_model", lambda x: mock_model
        )
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        _, provider_config, _ = create_agent_from_config(
            config_path=config_path, provider_override="anthropic"
        )

        assert provider_config.name == "anthropic"

        def test_parallel_tool_included_when_enabled(self, monkeypatch, tmp_path):
            from agentic_cba_indicators.cli import create_agent_from_config

            config_content = """
active_provider: ollama

providers:
    ollama:
        host: "http://localhost:11434"
        model_id: "llama3.1:latest"

agent:
    tool_set: reduced
    conversation_window: 5
    parallel_tool_calls: true
"""
            config_path = tmp_path / "test_config.yaml"
            config_path.write_text(config_content)

            mock_model = MagicMock()
            monkeypatch.setattr(
                "agentic_cba_indicators.cli.create_model", lambda x: mock_model
            )

            agent, _, _ = create_agent_from_config(config_path=config_path)
            assert any(t.__name__ == "run_tools_parallel" for t in agent.tools)  # type: ignore[attr-defined]

        def test_parallel_tool_excluded_when_disabled(self, monkeypatch, tmp_path):
            from agentic_cba_indicators.cli import create_agent_from_config

            config_content = """
active_provider: ollama

providers:
    ollama:
        host: "http://localhost:11434"
        model_id: "llama3.1:latest"

agent:
    tool_set: reduced
    conversation_window: 5
    parallel_tool_calls: false
"""
            config_path = tmp_path / "test_config.yaml"
            config_path.write_text(config_content)

            mock_model = MagicMock()
            monkeypatch.setattr(
                "agentic_cba_indicators.cli.create_model", lambda x: mock_model
            )

            agent, _, _ = create_agent_from_config(config_path=config_path)
            assert all(t.__name__ != "run_tools_parallel" for t in agent.tools)  # type: ignore[attr-defined]


# ============================================================================
# ChromaDB Integration Tests
# ============================================================================


class TestChromaDBIntegration:
    """Test ChromaDB knowledge base integration."""

    def test_chromadb_client_creation(self, temp_data_dir):
        """Test that ChromaDB client can be created."""
        from agentic_cba_indicators.tools.knowledge_base import _get_chroma_client

        client = _get_chroma_client()
        assert client is not None

    def test_collection_creation(self, temp_data_dir):
        """Test that collections can be created/retrieved."""
        from agentic_cba_indicators.tools.knowledge_base import _get_collection

        collection = _get_collection("test_collection")
        assert collection is not None
        assert collection.name == "test_collection"

    def test_list_knowledge_base_stats_empty(self, temp_data_dir):
        """Test stats reporting for empty knowledge base."""
        from agentic_cba_indicators.tools.knowledge_base import (
            list_knowledge_base_stats,
        )

        result = list_knowledge_base_stats()

        # Should indicate empty or show stats
        assert isinstance(result, str)
        # Empty KB returns guidance message
        assert "Knowledge base" in result or "Statistics" in result


class TestSearchFunctions:
    """Test knowledge base search functions (with mock embeddings)."""

    def test_search_indicators_empty_kb(self, temp_data_dir, monkeypatch):
        """Test search on empty knowledge base."""
        from agentic_cba_indicators.tools.knowledge_base import search_indicators

        # Mock embedding function to avoid Ollama dependency
        monkeypatch.setattr(
            "agentic_cba_indicators.tools.knowledge_base._get_embedding",
            lambda x: [0.0] * 768,  # Return dummy embedding
        )

        result = search_indicators("soil carbon")

        # Should indicate empty KB
        assert "empty" in result.lower() or "no" in result.lower()

    def test_search_methods_empty_kb(self, temp_data_dir, monkeypatch):
        """Test search methods on empty knowledge base."""
        from agentic_cba_indicators.tools.knowledge_base import search_methods

        monkeypatch.setattr(
            "agentic_cba_indicators.tools.knowledge_base._get_embedding",
            lambda x: [0.0] * 768,
        )

        result = search_methods("field survey")

        assert "empty" in result.lower() or "no" in result.lower()


# ============================================================================
# Tool Loading Tests
# ============================================================================


class TestToolLoading:
    """Test that tools can be loaded correctly."""

    def test_reduced_tools_load(self):
        """Test that reduced tool set can be loaded."""
        from agentic_cba_indicators.tools import REDUCED_TOOLS

        assert REDUCED_TOOLS is not None
        assert len(REDUCED_TOOLS) > 0
        # All items should be callable (tool functions)
        for tool in REDUCED_TOOLS:
            assert callable(tool)

    def test_full_tools_load(self):
        """Test that full tool set can be loaded."""
        from agentic_cba_indicators.tools import FULL_TOOLS

        assert FULL_TOOLS is not None
        assert len(FULL_TOOLS) > len([])  # Should have tools
        # Full should have at least as many as reduced
        from agentic_cba_indicators.tools import REDUCED_TOOLS

        assert len(FULL_TOOLS) >= len(REDUCED_TOOLS)

    def test_tools_have_docstrings(self):
        """Test that all tools have docstrings (required for LLM)."""
        from agentic_cba_indicators.tools import REDUCED_TOOLS

        for tool in REDUCED_TOOLS:
            assert tool.__doc__ is not None, f"Tool {tool.__name__} missing docstring"
            assert len(tool.__doc__) > 10, f"Tool {tool.__name__} docstring too short"


# ============================================================================
# Prompt Loading Tests
# ============================================================================


class TestPromptLoading:
    """Test that prompts can be loaded correctly."""

    def test_get_system_prompt(self):
        """Test that system prompt can be loaded."""
        from agentic_cba_indicators.prompts import get_system_prompt

        prompt = get_system_prompt()

        assert prompt is not None
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should have substantial content

    def test_load_prompt_by_name(self):
        """Test that specific prompts can be loaded by name."""
        from agentic_cba_indicators.prompts import load_prompt

        # Try to load the standard prompt (without .md extension - added by load_prompt)
        prompt = load_prompt("system_prompt")

        assert prompt is not None
        assert isinstance(prompt, str)
