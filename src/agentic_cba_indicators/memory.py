"""
Token-budget conversation manager for controlling context window size.

Provides a token-aware alternative to the fixed-window SlidingWindowConversationManager.
Estimates token counts using a configurable function (defaults to chars/4 heuristic)
and trims oldest messages to stay within budget while preserving most recent context.

Thread Safety:
    This module is thread-safe for single-agent use. Token estimation and message
    trimming operations are deterministic and do not maintain shared state.

Example:
    >>> from agentic_cba_indicators.memory import TokenBudgetConversationManager
    >>> manager = TokenBudgetConversationManager(max_tokens=8000)
    >>> agent = Agent(conversation_manager=manager)
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, cast

from strands.agent.conversation_manager import ConversationManager
from strands.hooks import BeforeModelCallEvent, HookRegistry
from strands.types.exceptions import ContextWindowOverflowException

if TYPE_CHECKING:
    from collections.abc import Callable

    from strands.agent.agent import Agent

logger = logging.getLogger(__name__)

# Default token budget (conservative for most models)
DEFAULT_MAX_TOKENS = 8000

# Minimum messages to preserve (avoids empty context)
MIN_MESSAGES_TO_PRESERVE = 2


def estimate_tokens_heuristic(text: str) -> int:
    """Estimate token count using chars/4 heuristic.

    This is a fast approximation suitable for most use cases.
    Accuracy varies by language and content type but is generally
    within 20-30% of actual token counts for English text.

    Args:
        text: The text to estimate tokens for.

    Returns:
        Estimated token count (always >= 1 for non-empty strings).
    """
    if not text:
        return 0
    # Average English word is ~5 chars, average token is ~4 chars
    return max(1, len(text) // 4)


def _message_to_text(message: dict[str, Any]) -> str:
    """Convert a message dict to plain text for token estimation.

    Handles various content types including text, tool use, and tool results.

    Args:
        message: A message dictionary with 'role' and 'content' keys.

    Returns:
        Plain text representation of the message content.
    """
    parts: list[str] = []

    # Include role in estimation (it's part of the prompt)
    role = message.get("role", "")
    if role:
        parts.append(role)

    content = message.get("content", [])
    if isinstance(content, str):
        parts.append(content)
    elif isinstance(content, list):
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                # Handle text content
                if "text" in item:
                    parts.append(str(item["text"]))
                # Handle tool use
                elif "toolUse" in item:
                    tool_use = item["toolUse"]
                    parts.append(f"toolUse:{tool_use.get('name', '')}")
                    # Tool input can be large - estimate it
                    tool_input = tool_use.get("input", {})
                    if tool_input:
                        parts.append(json.dumps(tool_input, default=str))
                # Handle tool result
                elif "toolResult" in item:
                    tool_result = item["toolResult"]
                    result_content = tool_result.get("content", [])
                    if isinstance(result_content, str):
                        parts.append(result_content)
                    elif isinstance(result_content, list):
                        for rc in result_content:
                            if isinstance(rc, dict) and "text" in rc:
                                parts.append(str(rc["text"]))
                            elif isinstance(rc, str):
                                parts.append(rc)

    return " ".join(parts)


def estimate_message_tokens(
    message: dict[str, Any],
    token_estimator: Callable[[str], int] | None = None,
) -> int:
    """Estimate tokens for a single message.

    Args:
        message: A message dictionary with 'role' and 'content' keys.
        token_estimator: Optional custom token estimation function.
            Defaults to estimate_tokens_heuristic.

    Returns:
        Estimated token count for the message.
    """
    estimator = token_estimator or estimate_tokens_heuristic
    text = _message_to_text(message)
    return estimator(text)


def estimate_messages_tokens(
    messages: list[dict[str, Any]],
    token_estimator: Callable[[str], int] | None = None,
) -> int:
    """Estimate total tokens for a list of messages.

    Args:
        messages: List of message dictionaries.
        token_estimator: Optional custom token estimation function.

    Returns:
        Total estimated token count.
    """
    return sum(estimate_message_tokens(m, token_estimator) for m in messages)


class TokenBudgetConversationManager(ConversationManager):
    """Token-aware conversation manager that enforces a token budget.

    Unlike SlidingWindowConversationManager which uses a fixed message count,
    this manager estimates token usage and trims messages to stay within budget.
    This provides better control over context window utilization.

    The manager:
    - Estimates tokens using a configurable function (default: chars/4)
    - Preserves most recent messages (newest context is most relevant)
    - Handles tool use/result pairs correctly (won't orphan results)
    - Can apply management per-turn or only when context overflows

    Attributes:
        max_tokens: Maximum token budget for conversation history.
        token_estimator: Function to estimate tokens from text.
        per_turn: When to apply management (False=only on overflow, True=every call,
            int=every N calls).
        should_truncate_results: Whether to truncate large tool results on overflow.

    Example:
        >>> manager = TokenBudgetConversationManager(
        ...     max_tokens=8000,
        ...     per_turn=True  # Apply on every model call
        ... )
        >>> agent = Agent(conversation_manager=manager)
    """

    def __init__(
        self,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        token_estimator: Callable[[str], int] | None = None,
        *,
        per_turn: bool | int = False,
        should_truncate_results: bool = True,
    ) -> None:
        """Initialize the token budget conversation manager.

        Args:
            max_tokens: Maximum token budget for conversation history.
                Defaults to 8000 tokens.
            token_estimator: Optional custom function to estimate tokens from text.
                Should accept a string and return an integer token count.
                Defaults to estimate_tokens_heuristic (chars/4).
            per_turn: Controls when to apply token management.
                - False (default): Only apply when context overflow occurs
                - True: Apply before every model call
                - int (e.g., 3): Apply before every N model calls
            should_truncate_results: Whether to truncate large tool results
                when context overflow occurs. Defaults to True.

        Raises:
            ValueError: If max_tokens <= 0 or per_turn is 0 or negative.
        """
        super().__init__()

        if max_tokens <= 0:
            raise ValueError(f"max_tokens must be positive, got {max_tokens}")

        if isinstance(per_turn, int) and per_turn <= 0 and per_turn is not False:
            raise ValueError(
                f"per_turn must be positive integer or False, got {per_turn}"
            )

        self.max_tokens = max_tokens
        self.token_estimator = token_estimator or estimate_tokens_heuristic
        self.per_turn = per_turn
        self.should_truncate_results = should_truncate_results
        self._model_call_count = 0

    def register_hooks(self, registry: HookRegistry, **kwargs: Any) -> None:
        """Register hooks for per-turn conversation management.

        Args:
            registry: The hook registry to register with.
            **kwargs: Additional keyword arguments for future extensibility.
        """
        del kwargs
        registry.add_callback(BeforeModelCallEvent, self._on_before_model_call)

    def _on_before_model_call(self, event: BeforeModelCallEvent) -> None:
        """Handle before model call event for per-turn management.

        Args:
            event: The before model call event.
        """
        if self.per_turn is False:
            return

        self._model_call_count += 1

        should_apply = False
        if self.per_turn is True:
            should_apply = True
        elif isinstance(self.per_turn, int) and self.per_turn > 0:
            should_apply = self._model_call_count % self.per_turn == 0

        if should_apply:
            logger.debug(
                "model_call_count=<%d>, per_turn=<%s> | applying per-turn token budget management",
                self._model_call_count,
                self.per_turn,
            )
            self.apply_management(event.agent)

    def get_state(self) -> dict[str, Any]:
        """Get the current state for session persistence.

        Returns:
            Dictionary containing manager state.
        """
        state = super().get_state()
        state["model_call_count"] = self._model_call_count
        state["max_tokens"] = self.max_tokens
        state["__name__"] = self.__class__.__name__
        return state

    def restore_from_session(self, state: dict[str, Any]) -> list[Any] | None:
        """Restore state from a previous session.

        Args:
            state: Previous state dictionary.

        Returns:
            Optional list of messages to prepend.
        """
        result = super().restore_from_session(state)
        self._model_call_count = state.get("model_call_count", 0)
        # Note: max_tokens from state is informational only - use constructor value
        return result

    def apply_management(self, agent: Agent, **kwargs: Any) -> None:
        """Apply token budget management to the agent's messages.

        Estimates current token usage and trims oldest messages if over budget.
        Preserves tool use/result pairs to maintain conversation coherence.

        Args:
            agent: The agent whose messages will be managed.
            **kwargs: Additional keyword arguments for future extensibility.
        """
        del kwargs
        messages = cast("list[dict[str, Any]]", agent.messages)
        if not messages:
            return

        current_tokens = self._estimate_total_tokens(messages)

        if current_tokens <= self.max_tokens:
            logger.debug(
                "current_tokens=<%d>, max_tokens=<%d> | within budget, no trimming needed",
                current_tokens,
                self.max_tokens,
            )
            return

        logger.debug(
            "current_tokens=<%d>, max_tokens=<%d> | over budget, trimming messages",
            current_tokens,
            self.max_tokens,
        )

        self._trim_to_budget(messages)

    def reduce_context(
        self, agent: Agent, e: Exception | None = None, **kwargs: Any
    ) -> None:
        """Reduce context when overflow exception occurs.

        Called by the agent when a ContextWindowOverflowException is caught.
        Attempts to truncate tool results first, then trims messages.

        Args:
            agent: The agent whose context needs reduction.
            e: The exception that triggered the reduction.
            **kwargs: Additional keyword arguments.

        Raises:
            ContextWindowOverflowException: If context cannot be reduced further.
        """
        del kwargs
        messages = cast("list[dict[str, Any]]", agent.messages)

        # Try truncating tool results first
        if self.should_truncate_results and self._try_truncate_tool_results(messages):
            logger.debug("tool results truncated to reduce context")
            return

        # If we still need to reduce, trim more aggressively
        if len(messages) <= MIN_MESSAGES_TO_PRESERVE:
            raise ContextWindowOverflowException(
                "Cannot reduce context: already at minimum message count"
            ) from e

        # Reduce budget temporarily for aggressive trimming
        reduced_budget = int(self.max_tokens * 0.7)  # 30% reduction
        self._trim_to_budget(messages, target_tokens=reduced_budget)

        if len(messages) <= MIN_MESSAGES_TO_PRESERVE:
            raise ContextWindowOverflowException(
                "Unable to reduce context sufficiently"
            ) from e

        logger.debug(
            "messages=<%d>, target_tokens=<%d> | context reduced",
            len(messages),
            reduced_budget,
        )

    def _estimate_total_tokens(self, messages: list[dict[str, Any]]) -> int:
        """Estimate total tokens for messages using configured estimator.

        Args:
            messages: List of messages to estimate.

        Returns:
            Estimated total token count.
        """
        return estimate_messages_tokens(messages, self.token_estimator)

    def _trim_to_budget(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int | None = None,
    ) -> None:
        """Trim messages to fit within token budget.

        Removes oldest messages first, preserving tool use/result pairs.
        Modifies the messages list in-place.

        Args:
            messages: Messages to trim (modified in-place).
            target_tokens: Target token budget (defaults to self.max_tokens).
        """
        target = target_tokens or self.max_tokens

        if len(messages) <= MIN_MESSAGES_TO_PRESERVE:
            return

        # Calculate tokens from the end (newest) to find how many we can keep
        kept_tokens = 0
        keep_from_index = len(messages)

        for i in range(len(messages) - 1, -1, -1):
            msg_tokens = estimate_message_tokens(messages[i], self.token_estimator)

            if kept_tokens + msg_tokens > target:
                # This message would exceed budget
                keep_from_index = i + 1
                break

            kept_tokens += msg_tokens
            keep_from_index = i

        # Ensure we keep at least MIN_MESSAGES_TO_PRESERVE
        max_trim_index = len(messages) - MIN_MESSAGES_TO_PRESERVE
        trim_index = min(keep_from_index, max_trim_index)

        if trim_index <= 0:
            return

        # Adjust trim_index to avoid orphaned tool results
        trim_index = self._adjust_for_tool_pairs(messages, trim_index)

        if trim_index <= 0:
            return

        # Track removed messages
        self.removed_message_count += trim_index

        # Remove oldest messages
        del messages[:trim_index]

        logger.debug(
            "trimmed=<%d>, remaining=<%d>, tokens=<%d>",
            trim_index,
            len(messages),
            self._estimate_total_tokens(messages),
        )

    def _adjust_for_tool_pairs(
        self,
        messages: list[dict[str, Any]],
        trim_index: int,
    ) -> int:
        """Adjust trim index to avoid breaking tool use/result pairs.

        If the message at trim_index is a toolResult without its toolUse,
        or a toolUse without its toolResult, adjust the index.

        Args:
            messages: The messages list.
            trim_index: Proposed trim index.

        Returns:
            Adjusted trim index that preserves tool pairs.
        """
        if trim_index >= len(messages):
            return trim_index

        # Check messages starting from trim_index
        while trim_index < len(messages) - MIN_MESSAGES_TO_PRESERVE:
            msg = messages[trim_index]
            content = msg.get("content", [])

            # Check if this message has a toolResult
            has_tool_result = any(
                isinstance(c, dict) and "toolResult" in c for c in content
            )

            # Check if this message has a toolUse
            has_tool_use = any(isinstance(c, dict) and "toolUse" in c for c in content)

            if has_tool_result:
                # Can't start with a toolResult - need the preceding toolUse
                trim_index += 1
                continue

            if has_tool_use and trim_index + 1 < len(messages):
                # Check if next message has corresponding toolResult
                next_msg = messages[trim_index + 1]
                next_content = next_msg.get("content", [])
                next_has_result = any(
                    isinstance(c, dict) and "toolResult" in c for c in next_content
                )
                if not next_has_result:
                    # toolUse without result - can start here
                    break
                # Has result - need to keep both, move past
                trim_index += 1
                continue

            # Safe to trim here
            break

        return trim_index

    def _try_truncate_tool_results(self, messages: list[dict[str, Any]]) -> bool:
        """Try to truncate large tool results to reduce context.

        Args:
            messages: Messages to process.

        Returns:
            True if any truncation was performed.
        """
        truncated = False
        truncation_message = "Tool result truncated to reduce context size."

        for msg in messages:
            content = msg.get("content", [])
            for item in content:
                if isinstance(item, dict) and "toolResult" in item:
                    tool_result = item["toolResult"]
                    result_content = tool_result.get("content", [])

                    # Check if content is large
                    if isinstance(result_content, list):
                        for rc in result_content:
                            if isinstance(rc, dict) and "text" in rc:
                                text = str(rc["text"])
                                if len(text) > 1000:  # Truncate large results
                                    rc["text"] = truncation_message
                                    truncated = True

        return truncated
