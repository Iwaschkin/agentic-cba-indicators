"""
Security module for input sanitization and prompt injection defense.

This module provides functions to sanitize user input before sending to the LLM agent,
helping to prevent prompt injection attacks and protect against malicious input.

Defense Layers:
1. Length limiting - Prevents context overflow attacks
2. Control character removal - Removes potentially harmful invisible characters
3. Optional delimiter wrapping - Clearly separates user input from system instructions

Usage:
    from agentic_cba_indicators.security import sanitize_user_input

    user_input = input("You: ")
    safe_input = sanitize_user_input(user_input)
    agent(safe_input)

Thread Safety:
    All functions in this module are stateless and thread-safe.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

from agentic_cba_indicators.logging_config import get_logger

# Module logger
logger = get_logger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Maximum allowed length for user input (characters)
# 10000 chars ≈ 2500 tokens, leaves room for system prompt and response
MAX_QUERY_LENGTH: Final[int] = 10000

# Maximum allowed length for PDF context (characters)
# 50000 chars ≈ 12500 tokens, allows room for substantial document context
MAX_PDF_CONTEXT_LENGTH: Final[int] = 50000

# Default delimiters for wrapping user input
DEFAULT_START_DELIMITER: Final[str] = "<<<USER_INPUT>>>"
DEFAULT_END_DELIMITER: Final[str] = "<<<END_USER_INPUT>>>"

# Unicode categories to remove (control characters, format characters)
# See: https://www.unicode.org/reports/tr44/#General_Category_Values
_DANGEROUS_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "Cc",  # Control characters (U+0000-U+001F, U+007F-U+009F)
        "Cf",  # Format characters (zero-width, directional overrides, etc.)
        "Co",  # Private use (undefined behavior)
        "Cs",  # Surrogates (invalid in UTF-8)
    }
)

# Allowed control characters (common whitespace)
_ALLOWED_CONTROLS: Final[frozenset[str]] = frozenset(
    {
        "\n",  # Newline
        "\r",  # Carriage return (will be normalized)
        "\t",  # Tab
    }
)

# Pattern to normalize multiple newlines to max 2
_MULTIPLE_NEWLINES_PATTERN: Final[re.Pattern[str]] = re.compile(r"\n{3,}")

# Pattern to detect potential prompt injection markers
# These patterns are common in prompt injection attempts
_INJECTION_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    re.compile(r"ignore\s+(previous|above|all)\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(previous|above|all)\s+instructions?", re.IGNORECASE),
    re.compile(r"new\s+instructions?:", re.IGNORECASE),
    re.compile(r"system\s*:\s*", re.IGNORECASE),
    re.compile(r"<\|?(system|assistant|user)\|?>", re.IGNORECASE),
    re.compile(r"\[INST\]|\[/INST\]", re.IGNORECASE),  # Llama format
    re.compile(r"Human:|Assistant:", re.IGNORECASE),  # Claude format
)


# =============================================================================
# Core Functions
# =============================================================================


def sanitize_user_input(
    text: str,
    max_length: int = MAX_QUERY_LENGTH,
    strip_control_chars: bool = True,
    normalize_whitespace: bool = True,
    log_warnings: bool = True,
) -> str:
    """
    Sanitize user input for safe use with LLM agents.

    Applies multiple defense layers:
    1. Strips leading/trailing whitespace
    2. Removes dangerous Unicode control characters (optional)
    3. Normalizes excessive whitespace (optional)
    4. Truncates to maximum length

    Args:
        text: Raw user input string
        max_length: Maximum allowed length (default: 10000 characters)
        strip_control_chars: Remove control/format Unicode characters
        normalize_whitespace: Replace multiple newlines with double newline
        log_warnings: Log warnings when sanitization is applied

    Returns:
        Sanitized string safe for LLM input

    Examples:
        >>> sanitize_user_input("  Hello, world!  ")
        'Hello, world!'

        >>> sanitize_user_input("Hi\\x00there")  # Null character removed
        'Hithere'

        >>> sanitize_user_input("a" * 20000, max_length=100)
        'aaa...' # Truncated to 100 chars

    Note:
        This function is defensive, not exhaustive. It cannot prevent all
        prompt injection attacks. Use in combination with:
        - Clear system prompts with role boundaries
        - Output validation
        - User authentication and rate limiting
    """
    if not text:
        return ""

    # Strip leading/trailing whitespace
    result = text.strip()

    original_length = len(result)

    # Remove dangerous control characters
    if strip_control_chars:
        result = _remove_control_characters(result)
        if log_warnings and len(result) < original_length:
            removed = original_length - len(result)
            logger.debug("Removed %d control character(s) from input", removed)

    # Normalize whitespace (multiple newlines → double newline)
    if normalize_whitespace:
        # Normalize line endings to Unix style
        result = result.replace("\r\n", "\n").replace("\r", "\n")
        # Collapse multiple blank lines
        result = _MULTIPLE_NEWLINES_PATTERN.sub("\n\n", result)

    # Truncate to max length
    if len(result) > max_length:
        if log_warnings:
            logger.warning(
                "Truncating user input from %d to %d characters",
                len(result),
                max_length,
            )
        result = result[:max_length]
        # Avoid cutting mid-word if possible
        if " " in result[-50:]:
            # Find last space in final 50 chars
            last_space = result.rfind(" ", max_length - 50)
            if last_space > max_length - 100:
                result = result[:last_space] + "..."

    return result


def _remove_control_characters(text: str) -> str:
    """Remove dangerous Unicode control characters from text.

    Preserves common whitespace (newline, tab, carriage return).

    Args:
        text: Input string

    Returns:
        String with control characters removed
    """
    result = []
    for char in text:
        # Keep allowed control characters
        if char in _ALLOWED_CONTROLS:
            result.append(char)
            continue

        # Check Unicode category
        category = unicodedata.category(char)
        if category not in _DANGEROUS_CATEGORIES:
            result.append(char)

    return "".join(result)


def wrap_with_delimiters(
    text: str,
    start_delimiter: str = DEFAULT_START_DELIMITER,
    end_delimiter: str = DEFAULT_END_DELIMITER,
) -> str:
    """
    Wrap user input with delimiters to clearly separate from system instructions.

    This is an optional defense layer that makes it harder for injected text
    to escape the "user input" context in the prompt.

    Args:
        text: User input (should already be sanitized)
        start_delimiter: Opening delimiter string
        end_delimiter: Closing delimiter string

    Returns:
        Text wrapped with delimiters

    Example:
        >>> wrap_with_delimiters("Hello!")
        '<<<USER_INPUT>>>\\nHello!\\n<<<END_USER_INPUT>>>'

    Note:
        For this to be effective, the system prompt must reference these
        delimiters and instruct the model to treat content within them
        as untrusted user input.
    """
    return f"{start_delimiter}\n{text}\n{end_delimiter}"


def detect_injection_patterns(text: str) -> list[str]:
    """
    Detect potential prompt injection patterns in text.

    This is a heuristic detector for common injection attempts. It will have
    both false positives (legitimate text that looks suspicious) and false
    negatives (novel injection techniques).

    Args:
        text: Text to scan for injection patterns

    Returns:
        List of matched pattern descriptions (empty if none detected)

    Example:
        >>> detect_injection_patterns("Ignore previous instructions and do X")
        ['ignore previous instructions']

    Note:
        This function is for logging/monitoring, not blocking. Many legitimate
        queries may trigger detection. Use for awareness, not enforcement.
    """
    return [
        match.group(0).lower().strip()
        for pattern in _INJECTION_PATTERNS
        if (match := pattern.search(text))
    ]


def sanitize_for_logging(text: str, max_length: int = 200) -> str:
    """
    Sanitize text for safe inclusion in log messages.

    Truncates and escapes text to prevent log injection attacks.

    Args:
        text: Text to sanitize
        max_length: Maximum length for log entry

    Returns:
        Safe string for logging
    """
    if not text:
        return "<empty>"

    # Truncate
    if len(text) > max_length:
        text = text[:max_length] + "..."

    # Escape newlines and other control characters for single-line logging
    text = text.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")

    return text


# =============================================================================
# Input Validation
# =============================================================================


class InputValidationError(ValueError):
    """Raised when user input fails validation."""


def validate_user_input(
    text: str,
    min_length: int = 1,
    max_length: int = MAX_QUERY_LENGTH,
    allow_empty: bool = False,
) -> str:
    """
    Validate user input and raise exception if invalid.

    This combines sanitization with strict validation. Use when you want
    to reject invalid input rather than silently sanitize it.

    Args:
        text: Raw user input
        min_length: Minimum required length after sanitization
        max_length: Maximum allowed length
        allow_empty: Whether to allow empty input

    Returns:
        Sanitized input string

    Raises:
        InputValidationError: If input fails validation

    Example:
        >>> validate_user_input("Hello!")
        'Hello!'

        >>> validate_user_input("")
        InputValidationError: Input cannot be empty

        >>> validate_user_input("a" * 20000)
        InputValidationError: Input exceeds maximum length of 10000 characters
    """
    if not text and not allow_empty:
        raise InputValidationError("Input cannot be empty")

    if not text:
        return ""

    # Check length before sanitization (potential DoS with huge input)
    if len(text) > max_length * 2:
        raise InputValidationError(
            f"Input exceeds maximum length of {max_length} characters"
        )

    # Sanitize
    sanitized = sanitize_user_input(text, max_length=max_length, log_warnings=False)

    # Validate length after sanitization
    if len(sanitized) < min_length:
        raise InputValidationError(
            f"Input too short (minimum {min_length} character(s) after sanitization)"
        )

    return sanitized


# =============================================================================
# PDF Context Sanitization
# =============================================================================


def sanitize_pdf_context(
    text: str,
    max_length: int = MAX_PDF_CONTEXT_LENGTH,
) -> tuple[str, bool]:
    """
    Sanitize PDF-extracted text for safe use with LLM agents.

    Applies the same sanitization as user input but with a larger default
    length limit appropriate for document context.

    Args:
        text: Raw text extracted from PDF
        max_length: Maximum allowed length (default: 50000 characters)

    Returns:
        Tuple of (sanitized_text, was_truncated) where was_truncated indicates
        if the text was shortened.

    Examples:
        >>> text, truncated = sanitize_pdf_context("Normal document text")
        >>> truncated
        False

        >>> text, truncated = sanitize_pdf_context("a" * 60000)
        >>> truncated
        True
        >>> len(text) <= 50000
        True

    Note:
        PDF text may contain injection attempts like "Ignore above instructions".
        This function removes control characters but does NOT block such text,
        as legitimate documents may coincidentally contain these phrases.
        Rely on clear system prompts and delimiters for defense.
    """
    if not text:
        return "", False

    original_length = len(text)

    # Apply standard sanitization with PDF-appropriate max length
    sanitized = sanitize_user_input(
        text,
        max_length=max_length,
        strip_control_chars=True,
        normalize_whitespace=True,
        log_warnings=True,
    )

    was_truncated = len(sanitized) < original_length and original_length > max_length

    if was_truncated:
        logger.info(
            "PDF context truncated from %d to %d characters",
            original_length,
            len(sanitized),
        )

    return sanitized, was_truncated


# =============================================================================
# Tool Output Truncation
# =============================================================================

# Maximum allowed length for tool output (characters)
# 50000 chars ≈ 12500 tokens, prevents context overflow from verbose tools
MAX_TOOL_OUTPUT_LENGTH: Final[int] = 50000

# Truncation suffix to indicate output was cut off
TRUNCATION_SUFFIX: Final[str] = "\n\n...(output truncated)"


def truncate_tool_output(
    text: str,
    max_length: int = MAX_TOOL_OUTPUT_LENGTH,
    suffix: str = TRUNCATION_SUFFIX,
) -> tuple[str, bool]:
    """
    Truncate tool output to prevent context overflow.

    Some tools (e.g., export_indicator_selection, compare_indicators) can
    produce very long outputs that may exceed LLM context limits. This function
    truncates output while preserving as much content as possible and adding
    a clear truncation indicator.

    Args:
        text: Tool output string to potentially truncate
        max_length: Maximum allowed length (default: 50000 characters)
        suffix: Suffix to append when truncating (default: "...(output truncated)")

    Returns:
        Tuple of (text, was_truncated) where:
        - text: Original or truncated output string
        - was_truncated: True if output was truncated

    Examples:
        >>> output, truncated = truncate_tool_output("Short output")
        >>> truncated
        False
        >>> output
        'Short output'

        >>> output, truncated = truncate_tool_output("a" * 60000, max_length=100)
        >>> truncated
        True
        >>> output.endswith("...(output truncated)")
        True
        >>> len(output) <= 100
        True

    Note:
        The function accounts for the suffix length when truncating,
        ensuring the final output (text + suffix) does not exceed max_length.
    """
    if not text or len(text) <= max_length:
        return text, False

    # Account for suffix length when truncating
    truncate_at = max_length - len(suffix)
    if truncate_at < 0:
        # Edge case: suffix longer than max_length
        truncate_at = 0

    truncated_text = text[:truncate_at] + suffix

    logger.debug(
        "Tool output truncated from %d to %d characters",
        len(text),
        len(truncated_text),
    )

    return truncated_text, True
