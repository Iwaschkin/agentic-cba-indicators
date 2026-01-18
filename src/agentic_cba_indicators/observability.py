"""
Observability module for the Agentic CBA Indicators chatbot.

Provides metrics collection, instrumentation, and optional export capabilities.

Thread Safety:
    The MetricsCollector uses threading.Lock for thread-safe updates to counters
    and histograms. Safe for use in multi-threaded environments.

Usage:
    from agentic_cba_indicators.observability import get_metrics, instrument_tool

    @instrument_tool
    def my_tool(arg: str) -> str:
        return f"Result: {arg}"

    # Get current metrics
    metrics = get_metrics()
    print(metrics.get_summary())
"""

from __future__ import annotations

import functools
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from agentic_cba_indicators.logging_config import get_logger

# Module logger
logger = get_logger(__name__)

# Type variable for generic decorator
F = TypeVar("F", bound=Callable[..., Any])


@dataclass
class ToolMetrics:
    """Metrics for a single tool.

    Attributes:
        call_count: Total number of times the tool was called
        success_count: Number of successful invocations
        failure_count: Number of failed invocations
        latencies: List of latency measurements in seconds
    """

    call_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    latencies: list[float] = field(default_factory=list)

    @property
    def avg_latency_ms(self) -> float:
        """Average latency in milliseconds."""
        if not self.latencies:
            return 0.0
        return (sum(self.latencies) / len(self.latencies)) * 1000

    @property
    def p50_latency_ms(self) -> float:
        """50th percentile (median) latency in milliseconds."""
        return self._percentile(50) * 1000

    @property
    def p95_latency_ms(self) -> float:
        """95th percentile latency in milliseconds."""
        return self._percentile(95) * 1000

    @property
    def p99_latency_ms(self) -> float:
        """99th percentile latency in milliseconds."""
        return self._percentile(99) * 1000

    @property
    def success_rate(self) -> float:
        """Success rate as a fraction (0.0 to 1.0)."""
        if self.call_count == 0:
            return 0.0
        return self.success_count / self.call_count

    def _percentile(self, p: int) -> float:
        """Calculate percentile from latencies."""
        if not self.latencies:
            return 0.0
        sorted_latencies = sorted(self.latencies)
        k = (len(sorted_latencies) - 1) * (p / 100)
        f = int(k)
        c = min(f + 1, len(sorted_latencies) - 1)
        if f == c:
            return sorted_latencies[f]
        return sorted_latencies[f] * (c - k) + sorted_latencies[c] * (k - f)


class MetricsCollector:
    """Thread-safe metrics collector for tool invocations.

    Collects:
    - Call counts (total, success, failure) per tool
    - Latency measurements per tool

    Thread Safety:
        All public methods are protected by a threading.Lock to ensure
        safe concurrent access from multiple threads.

    Example:
        collector = MetricsCollector()
        collector.record_call("my_tool", latency=0.123, success=True)
        metrics = collector.get_tool_metrics("my_tool")
        print(f"Calls: {metrics.call_count}, Avg: {metrics.avg_latency_ms}ms")
    """

    # Maximum number of latency samples to keep per tool (prevents unbounded growth)
    MAX_LATENCY_SAMPLES = 10000

    def __init__(self) -> None:
        """Initialize the metrics collector."""
        self._metrics: dict[str, ToolMetrics] = {}
        self._lock = threading.Lock()
        self._start_time = time.time()

    def record_call(self, tool_name: str, latency: float, success: bool = True) -> None:
        """Record a tool call with its latency and outcome.

        Args:
            tool_name: Name of the tool that was called
            latency: Call latency in seconds
            success: Whether the call succeeded (True) or failed (False)
        """
        with self._lock:
            if tool_name not in self._metrics:
                self._metrics[tool_name] = ToolMetrics()

            metrics = self._metrics[tool_name]
            metrics.call_count += 1

            if success:
                metrics.success_count += 1
            else:
                metrics.failure_count += 1

            # Add latency with bounded size
            metrics.latencies.append(latency)
            if len(metrics.latencies) > self.MAX_LATENCY_SAMPLES:
                # Remove oldest samples when limit exceeded
                metrics.latencies = metrics.latencies[-self.MAX_LATENCY_SAMPLES :]

    def get_tool_metrics(self, tool_name: str) -> ToolMetrics:
        """Get metrics for a specific tool.

        Args:
            tool_name: Name of the tool to get metrics for

        Returns:
            ToolMetrics object with current metrics (or empty metrics if tool not found)
        """
        with self._lock:
            if tool_name not in self._metrics:
                return ToolMetrics()

            # Return a copy to avoid external mutation
            m = self._metrics[tool_name]
            return ToolMetrics(
                call_count=m.call_count,
                success_count=m.success_count,
                failure_count=m.failure_count,
                latencies=m.latencies.copy(),
            )

    def get_all_metrics(self) -> dict[str, ToolMetrics]:
        """Get metrics for all tools.

        Returns:
            Dictionary mapping tool names to their metrics (copies)
        """
        with self._lock:
            return {
                name: ToolMetrics(
                    call_count=m.call_count,
                    success_count=m.success_count,
                    failure_count=m.failure_count,
                    latencies=m.latencies.copy(),
                )
                for name, m in self._metrics.items()
            }

    def reset(self) -> None:
        """Reset all metrics.

        Clears all collected metrics and resets the start time.
        """
        with self._lock:
            self._metrics.clear()
            self._start_time = time.time()

    def get_summary(self) -> str:
        """Get a human-readable summary of all metrics.

        Returns:
            Formatted string with metrics summary
        """
        with self._lock:
            if not self._metrics:
                return "No metrics collected yet."

            uptime = time.time() - self._start_time
            lines = [
                f"=== Metrics Summary (uptime: {uptime:.1f}s) ===",
                "",
            ]

            # Sort by call count descending
            sorted_tools = sorted(
                self._metrics.items(),
                key=lambda x: x[1].call_count,
                reverse=True,
            )

            for tool_name, metrics in sorted_tools:
                lines.append(f"📊 {tool_name}")
                lines.append(
                    f"   Calls: {metrics.call_count} (✓{metrics.success_count} ✗{metrics.failure_count})"
                )
                lines.append(f"   Success rate: {metrics.success_rate:.1%}")
                if metrics.latencies:
                    lines.append(
                        f"   Latency: avg={metrics.avg_latency_ms:.1f}ms, p50={metrics.p50_latency_ms:.1f}ms, p95={metrics.p95_latency_ms:.1f}ms"
                    )
                lines.append("")

            return "\n".join(lines)

    @property
    def total_calls(self) -> int:
        """Total number of calls across all tools."""
        with self._lock:
            return sum(m.call_count for m in self._metrics.values())

    @property
    def total_errors(self) -> int:
        """Total number of failed calls across all tools."""
        with self._lock:
            return sum(m.failure_count for m in self._metrics.values())


# Global singleton metrics collector
_metrics_collector: MetricsCollector | None = None
_metrics_collector_lock = threading.Lock()


def get_metrics() -> MetricsCollector:
    """Get the global metrics collector singleton.

    Returns:
        The global MetricsCollector instance
    """
    global _metrics_collector

    if _metrics_collector is not None:
        return _metrics_collector

    with _metrics_collector_lock:
        if _metrics_collector is None:
            _metrics_collector = MetricsCollector()
        return _metrics_collector


def reset_metrics() -> None:
    """Reset the global metrics collector.

    Primarily for testing purposes.
    """
    global _metrics_collector
    with _metrics_collector_lock:
        if _metrics_collector is not None:
            _metrics_collector.reset()


def instrument_tool(func: F) -> F:
    """Decorator to instrument a tool function with metrics collection.

    Records:
    - Call count
    - Latency
    - Success/failure status

    The tool name is derived from the function's __name__ attribute.

    Args:
        func: The tool function to instrument

    Returns:
        Wrapped function with metrics instrumentation

    Example:
        @instrument_tool
        def search_indicators(query: str) -> str:
            # ... implementation
            return results
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        tool_name = func.__name__
        start_time = time.perf_counter()
        success = True

        try:
            result = func(*args, **kwargs)
            return result
        except Exception:
            success = False
            raise
        finally:
            latency = time.perf_counter() - start_time
            collector = get_metrics()
            collector.record_call(tool_name, latency=latency, success=success)

            # Debug logging for slow calls
            if latency > 5.0:  # Log calls taking more than 5 seconds
                logger.debug(
                    "Slow tool call: %s took %.2fs (success=%s)",
                    tool_name,
                    latency,
                    success,
                )

    return wrapper  # type: ignore[return-value]


def get_metrics_summary() -> str:
    """Get a human-readable summary of all collected metrics.

    Convenience function that calls get_metrics().get_summary().

    Returns:
        Formatted string with metrics summary
    """
    return get_metrics().get_summary()
