"""Unit tests for TokenBudgetConversationManager."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from strands.types.exceptions import ContextWindowOverflowException

from agentic_cba_indicators.memory import (
    DEFAULT_MAX_TOKENS,
    MIN_MESSAGES_TO_PRESERVE,
    TokenBudgetConversationManager,
    _message_to_text,
    estimate_message_tokens,
    estimate_messages_tokens,
    estimate_tokens_heuristic,
)

# =============================================================================
# Token Estimation Tests
# =============================================================================


class TestEstimateTokensHeuristic:
    """Tests for the heuristic token estimation function."""

    def test_empty_string_returns_zero(self) -> None:
        assert estimate_tokens_heuristic("") == 0

    def test_short_string_returns_at_least_one(self) -> None:
        assert (
            estimate_tokens_heuristic("hi") == 1
        )  # 2 chars / 4 = 0.5 -> max(1, 0) = 1

    def test_typical_english_text(self) -> None:
        # "Hello world" = 11 chars -> 11/4 = 2.75 -> 2 tokens
        assert estimate_tokens_heuristic("Hello world") == 2

    def test_longer_text(self) -> None:
        # 100 chars -> 25 tokens
        text = "a" * 100
        assert estimate_tokens_heuristic(text) == 25

    def test_realistic_sentence(self) -> None:
        text = "The quick brown fox jumps over the lazy dog."
        # 44 chars -> 11 tokens
        assert estimate_tokens_heuristic(text) == 11


class TestMessageToText:
    """Tests for message-to-text conversion."""

    def test_simple_text_message(self) -> None:
        msg: dict[str, Any] = {"role": "user", "content": [{"text": "Hello"}]}
        text = _message_to_text(msg)
        assert "user" in text
        assert "Hello" in text

    def test_tool_use_message(self) -> None:
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": [
                {
                    "toolUse": {
                        "toolUseId": "123",
                        "name": "get_weather",
                        "input": {"city": "London"},
                    }
                }
            ],
        }
        text = _message_to_text(msg)
        assert "assistant" in text
        assert "get_weather" in text
        assert "London" in text

    def test_tool_result_message(self) -> None:
        msg: dict[str, Any] = {
            "role": "user",
            "content": [
                {
                    "toolResult": {
                        "toolUseId": "123",
                        "content": [{"text": "Weather: sunny, 22°C"}],
                        "status": "success",
                    }
                }
            ],
        }
        text = _message_to_text(msg)
        assert "Weather" in text
        assert "22°C" in text

    def test_empty_content(self) -> None:
        msg: dict[str, Any] = {"role": "assistant", "content": []}
        text = _message_to_text(msg)
        assert "assistant" in text

    def test_string_content(self) -> None:
        msg: dict[str, Any] = {"role": "user", "content": "Plain text content"}
        text = _message_to_text(msg)
        assert "Plain text content" in text


class TestEstimateMessageTokens:
    """Tests for message token estimation."""

    def test_simple_message(self) -> None:
        msg: dict[str, Any] = {"role": "user", "content": [{"text": "Hello world"}]}
        tokens = estimate_message_tokens(msg)
        assert tokens > 0

    def test_custom_estimator(self) -> None:
        def custom_estimator(text: str) -> int:
            return len(text)  # 1 char = 1 token

        msg: dict[str, Any] = {"role": "user", "content": [{"text": "test"}]}
        tokens = estimate_message_tokens(msg, custom_estimator)
        # "user test" = 9 chars
        assert tokens == 9


class TestEstimateMessagesTokens:
    """Tests for batch message token estimation."""

    def test_multiple_messages(self) -> None:
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": "Hello"}]},
            {"role": "assistant", "content": [{"text": "Hi there!"}]},
        ]
        tokens = estimate_messages_tokens(messages)
        assert tokens > 0

    def test_empty_list(self) -> None:
        assert estimate_messages_tokens([]) == 0


# =============================================================================
# TokenBudgetConversationManager Tests
# =============================================================================


class TestTokenBudgetConversationManagerInit:
    """Tests for manager initialization."""

    def test_default_initialization(self) -> None:
        manager = TokenBudgetConversationManager()
        assert manager.max_tokens == DEFAULT_MAX_TOKENS
        assert manager.per_turn is False
        assert manager.should_truncate_results is True

    def test_custom_max_tokens(self) -> None:
        manager = TokenBudgetConversationManager(max_tokens=4000)
        assert manager.max_tokens == 4000

    def test_custom_token_estimator(self) -> None:
        custom_est = lambda x: len(x)  # noqa: E731
        manager = TokenBudgetConversationManager(token_estimator=custom_est)
        assert manager.token_estimator == custom_est

    def test_per_turn_true(self) -> None:
        manager = TokenBudgetConversationManager(per_turn=True)
        assert manager.per_turn is True

    def test_per_turn_integer(self) -> None:
        manager = TokenBudgetConversationManager(per_turn=3)
        assert manager.per_turn == 3

    def test_invalid_max_tokens_raises(self) -> None:
        with pytest.raises(ValueError, match="max_tokens must be positive"):
            TokenBudgetConversationManager(max_tokens=0)

        with pytest.raises(ValueError, match="max_tokens must be positive"):
            TokenBudgetConversationManager(max_tokens=-100)

    def test_invalid_per_turn_raises(self) -> None:
        with pytest.raises(ValueError, match="per_turn must be positive"):
            TokenBudgetConversationManager(per_turn=0)


class TestTokenBudgetConversationManagerState:
    """Tests for state persistence."""

    def test_get_state(self) -> None:
        manager = TokenBudgetConversationManager(max_tokens=5000)
        manager._model_call_count = 10

        state = manager.get_state()

        assert state["model_call_count"] == 10
        assert state["max_tokens"] == 5000
        assert state["__name__"] == "TokenBudgetConversationManager"

    def test_restore_from_session(self) -> None:
        manager = TokenBudgetConversationManager()
        state = {
            "model_call_count": 15,
            "max_tokens": 6000,
            "__name__": "TokenBudgetConversationManager",
            "removed_message_count": 5,  # Required by base class
        }

        manager.restore_from_session(state)

        assert manager._model_call_count == 15
        # max_tokens from state is informational only
        assert manager.max_tokens == DEFAULT_MAX_TOKENS


class TestTokenBudgetApplyManagement:
    """Tests for apply_management."""

    def _make_agent(self, messages: list[dict[str, Any]]) -> MagicMock:
        """Create a mock agent with given messages.

        Uses a real list for messages so in-place modifications work.
        """
        agent = MagicMock()
        # Use a real list to allow in-place modifications
        agent.messages = messages
        return agent

    def test_empty_messages_no_op(self) -> None:
        manager = TokenBudgetConversationManager(max_tokens=1000)
        messages: list[dict[str, Any]] = []
        agent = self._make_agent(messages)

        manager.apply_management(agent)

        assert agent.messages == []

    def test_within_budget_no_change(self) -> None:
        manager = TokenBudgetConversationManager(max_tokens=10000)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": "Hello"}]},
            {"role": "assistant", "content": [{"text": "Hi!"}]},
        ]
        agent = self._make_agent(messages)

        manager.apply_management(agent)

        assert len(agent.messages) == 2

    def test_over_budget_trims_oldest(self) -> None:
        # Very small budget to force trimming
        manager = TokenBudgetConversationManager(max_tokens=30)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": "First message is long"}]},
            {"role": "assistant", "content": [{"text": "First response is long"}]},
            {"role": "user", "content": [{"text": "Second message is long"}]},
            {"role": "assistant", "content": [{"text": "Second response is long"}]},
            {"role": "user", "content": [{"text": "Third message is long"}]},
            {"role": "assistant", "content": [{"text": "Third response"}]},
        ]
        agent = self._make_agent(messages)
        original_count = len(messages)

        manager.apply_management(agent)

        # Should have trimmed to fit budget, keeping newest
        assert len(agent.messages) < original_count
        # Should preserve MIN_MESSAGES_TO_PRESERVE
        assert len(agent.messages) >= MIN_MESSAGES_TO_PRESERVE

    def test_preserves_minimum_messages(self) -> None:
        # Very tiny budget
        manager = TokenBudgetConversationManager(max_tokens=1)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": "A" * 1000}]},
            {"role": "assistant", "content": [{"text": "B" * 1000}]},
            {"role": "user", "content": [{"text": "C" * 1000}]},
        ]
        agent = self._make_agent(messages)

        manager.apply_management(agent)

        # Should preserve at least MIN_MESSAGES_TO_PRESERVE
        assert len(agent.messages) >= MIN_MESSAGES_TO_PRESERVE


class TestTokenBudgetReduceContext:
    """Tests for reduce_context (called on overflow)."""

    def _make_agent(self, messages: list[dict[str, Any]]) -> MagicMock:
        """Create a mock agent with given messages.

        Uses a real list for messages so in-place modifications work.
        """
        agent = MagicMock()
        agent.messages = messages
        return agent

    def test_reduces_budget_aggressively(self) -> None:
        # Use a larger budget that still requires trimming but leaves room for 2+ messages
        manager = TokenBudgetConversationManager(max_tokens=500)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": "A" * 400}]},
            {"role": "assistant", "content": [{"text": "B" * 400}]},
            {"role": "user", "content": [{"text": "C" * 400}]},
            {"role": "assistant", "content": [{"text": "D" * 400}]},
            {"role": "user", "content": [{"text": "E" * 400}]},
            {"role": "assistant", "content": [{"text": "F" * 400}]},
        ]
        agent = self._make_agent(messages)
        original_count = len(messages)

        manager.reduce_context(agent)

        # Should have removed some messages (reduce_context uses 70% of max_tokens = 350)
        # Each message is ~100 tokens, so we should keep ~3-4 messages
        assert len(agent.messages) < original_count
        assert len(agent.messages) >= MIN_MESSAGES_TO_PRESERVE

    def test_truncates_tool_results_first(self) -> None:
        manager = TokenBudgetConversationManager(max_tokens=100)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": "Query"}]},
            {
                "role": "assistant",
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "123",
                            "name": "test",
                            "input": {},
                        }
                    }
                ],
            },
            {
                "role": "user",
                "content": [
                    {
                        "toolResult": {
                            "toolUseId": "123",
                            "content": [{"text": "X" * 2000}],  # Very large result
                            "status": "success",
                        }
                    }
                ],
            },
        ]
        agent = self._make_agent(messages)

        manager.reduce_context(agent)

        # Tool result should be truncated
        tool_result_content = agent.messages[2]["content"][0]["toolResult"]["content"]
        assert "truncated" in tool_result_content[0]["text"].lower()

    def test_raises_when_cannot_reduce_further(self) -> None:
        manager = TokenBudgetConversationManager(max_tokens=1)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": "Hi"}]},
            {"role": "assistant", "content": [{"text": "Hello"}]},
        ]
        agent = self._make_agent(messages)

        with pytest.raises(ContextWindowOverflowException):
            manager.reduce_context(agent)


class TestTokenBudgetToolPairHandling:
    """Tests for tool use/result pair preservation."""

    def _make_agent(self, messages: list[dict[str, Any]]) -> MagicMock:
        agent = MagicMock()
        agent.messages = messages
        return agent

    def test_does_not_orphan_tool_result(self) -> None:
        manager = TokenBudgetConversationManager(max_tokens=200)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": "First"}]},
            {
                "role": "assistant",
                "content": [{"toolUse": {"toolUseId": "1", "name": "t1", "input": {}}}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "toolResult": {
                            "toolUseId": "1",
                            "content": [{"text": "Result"}],
                            "status": "success",
                        }
                    }
                ],
            },
            {"role": "assistant", "content": [{"text": "Done"}]},
        ]
        agent = self._make_agent(messages)

        manager.apply_management(agent)

        # If tool result is kept, its toolUse must also be kept
        has_tool_result = any(
            "toolResult" in str(m.get("content", [])) for m in agent.messages
        )
        has_tool_use = any(
            "toolUse" in str(m.get("content", [])) for m in agent.messages
        )

        # Either both are kept or neither
        if has_tool_result:
            assert has_tool_use


class TestTokenBudgetPerTurn:
    """Tests for per-turn conversation management."""

    def test_per_turn_false_no_hook_action(self) -> None:
        manager = TokenBudgetConversationManager(per_turn=False)
        agent = MagicMock()
        agent.messages = [
            {"role": "user", "content": [{"text": "Test"}]},
        ]

        event = MagicMock()
        event.agent = agent

        # Should not apply management
        with patch.object(manager, "apply_management") as mock_apply:
            manager._on_before_model_call(event)
            mock_apply.assert_not_called()

    def test_per_turn_true_applies_every_call(self) -> None:
        manager = TokenBudgetConversationManager(per_turn=True, max_tokens=10000)
        agent = MagicMock()
        agent.messages = [{"role": "user", "content": [{"text": "Test"}]}]

        event = MagicMock()
        event.agent = agent

        with patch.object(manager, "apply_management") as mock_apply:
            manager._on_before_model_call(event)
            mock_apply.assert_called_once()

    def test_per_turn_integer_applies_on_interval(self) -> None:
        manager = TokenBudgetConversationManager(per_turn=3, max_tokens=10000)
        agent = MagicMock()
        agent.messages = [{"role": "user", "content": [{"text": "Test"}]}]

        event = MagicMock()
        event.agent = agent

        with patch.object(manager, "apply_management") as mock_apply:
            # First 2 calls - no application
            manager._on_before_model_call(event)
            manager._on_before_model_call(event)
            assert mock_apply.call_count == 0

            # 3rd call - should apply
            manager._on_before_model_call(event)
            assert mock_apply.call_count == 1

            # 4th and 5th - no application
            manager._on_before_model_call(event)
            manager._on_before_model_call(event)
            assert mock_apply.call_count == 1

            # 6th call - should apply again
            manager._on_before_model_call(event)
            assert mock_apply.call_count == 2


class TestTokenBudgetHookRegistration:
    """Tests for hook registration."""

    def test_registers_before_model_call_hook(self) -> None:
        from strands.hooks import BeforeModelCallEvent

        manager = TokenBudgetConversationManager()
        registry = MagicMock()

        manager.register_hooks(registry)

        registry.add_callback.assert_called_once()
        call_args = registry.add_callback.call_args
        assert call_args[0][0] == BeforeModelCallEvent


class TestRemovedMessageTracking:
    """Tests for removed_message_count tracking."""

    def _make_agent(self, messages: list[dict[str, Any]]) -> MagicMock:
        agent = MagicMock()
        agent.messages = messages
        return agent

    def test_tracks_removed_messages(self) -> None:
        manager = TokenBudgetConversationManager(max_tokens=50)
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": "A" * 100}]},
            {"role": "assistant", "content": [{"text": "B" * 100}]},
            {"role": "user", "content": [{"text": "C" * 100}]},
            {"role": "assistant", "content": [{"text": "D" * 100}]},
        ]
        agent = self._make_agent(messages)

        original_count = len(messages)
        manager.apply_management(agent)
        remaining_count = len(agent.messages)

        expected_removed = original_count - remaining_count
        assert manager.removed_message_count == expected_removed
