"""Timeout utilities for tool execution."""

from __future__ import annotations

import atexit
import os
import threading
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError
from functools import wraps
from typing import TYPE_CHECKING, Any, TypeVar

from agentic_cba_indicators.logging_config import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

T = TypeVar("T")

# CR-0008: Shared bounded executor to prevent unbounded thread spawning
# Using 4 workers as a balance between parallelism and resource usage
_MAX_TIMEOUT_WORKERS = 4
_timeout_executor: ThreadPoolExecutor | None = None
_timeout_failures = 0
_timeout_failure_lock = threading.Lock()
_MAX_TIMEOUT_FAILURES = int(os.environ.get("AGENTIC_CBA_TIMEOUT_FAILURES", "3"))


def _get_executor() -> ThreadPoolExecutor:
    """Get or create the shared timeout executor."""
    global _timeout_executor
    if _timeout_executor is None:
        _timeout_executor = ThreadPoolExecutor(
            max_workers=_MAX_TIMEOUT_WORKERS,
            thread_name_prefix="tool_timeout_",
        )
        # Register cleanup on exit
        atexit.register(_shutdown_executor)
    return _timeout_executor


def _shutdown_executor() -> None:
    """Shutdown the timeout executor gracefully."""
    global _timeout_executor
    if _timeout_executor is not None:
        _timeout_executor.shutdown(wait=False, cancel_futures=True)
        _timeout_executor = None


class ToolTimeoutError(RuntimeError):
    """Raised when a tool exceeds its execution timeout."""


def timeout(seconds: float) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to enforce a wall-clock timeout for tool execution.

    Uses a shared ThreadPoolExecutor for bounded thread spawning.

    Args:
        seconds: Maximum allowed execution time in seconds.

    Raises:
        ToolTimeoutError: If the decorated function exceeds the timeout.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            global _timeout_failures
            executor = _get_executor()
            future: Future[T] = executor.submit(func, *args, **kwargs)
            try:
                result = future.result(timeout=seconds)
                with _timeout_failure_lock:
                    _timeout_failures = 0
                return result
            except TimeoutError as e:
                # CR-0008: Cancel the future on timeout (best effort)
                future.cancel()
                logger.warning(
                    "Tool timeout: %s exceeded %ss",
                    getattr(func, "__name__", str(func)),
                    seconds,
                )
                with _timeout_failure_lock:
                    _timeout_failures += 1
                    if _timeout_failures >= _MAX_TIMEOUT_FAILURES:
                        logger.warning(
                            "Resetting timeout executor after %d consecutive timeouts",
                            _timeout_failures,
                        )
                        _shutdown_executor()
                        _timeout_failures = 0
                raise ToolTimeoutError(
                    f"Tool '{getattr(func, '__name__', 'unknown')}' exceeded {seconds}s timeout"
                ) from e

        wrapper.__tool_timeout_seconds__ = seconds  # type: ignore[attr-defined]
        wrapper.__tool_timeout_wrapped__ = True  # type: ignore[attr-defined]

        return wrapper

    return decorator
