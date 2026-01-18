"""Tests for observability module (TASK104).

Validates metrics collection, instrumentation, and thread safety.
"""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from agentic_cba_indicators.observability import (
    MetricsCollector,
    ToolMetrics,
    get_metrics,
    get_metrics_summary,
    instrument_tool,
    reset_metrics,
)


class TestToolMetrics:
    """Test ToolMetrics dataclass."""

    def test_default_values(self) -> None:
        """Verify default metric values."""
        metrics = ToolMetrics()
        assert metrics.call_count == 0
        assert metrics.success_count == 0
        assert metrics.failure_count == 0
        assert metrics.latencies == []

    def test_avg_latency_empty(self) -> None:
        """Average latency should be 0 for no calls."""
        metrics = ToolMetrics()
        assert metrics.avg_latency_ms == 0.0

    def test_avg_latency_calculation(self) -> None:
        """Average latency should be calculated correctly."""
        metrics = ToolMetrics(latencies=[0.1, 0.2, 0.3])
        assert abs(metrics.avg_latency_ms - 200.0) < 0.1  # 0.2s = 200ms

    def test_percentile_calculation(self) -> None:
        """Percentiles should be calculated correctly."""
        # 100 samples from 0.01 to 1.0
        latencies = [i / 100 for i in range(1, 101)]
        metrics = ToolMetrics(latencies=latencies)

        # p50 should be around 0.5s = 500ms
        assert 490 < metrics.p50_latency_ms < 510

        # p95 should be around 0.95s = 950ms
        assert 940 < metrics.p95_latency_ms < 960

    def test_success_rate(self) -> None:
        """Success rate should be calculated correctly."""
        metrics = ToolMetrics(call_count=10, success_count=8, failure_count=2)
        assert metrics.success_rate == 0.8

    def test_success_rate_no_calls(self) -> None:
        """Success rate should be 0 for no calls."""
        metrics = ToolMetrics()
        assert metrics.success_rate == 0.0


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_record_successful_call(self) -> None:
        """Record a successful call."""
        collector = MetricsCollector()
        collector.record_call("test_tool", latency=0.1, success=True)

        metrics = collector.get_tool_metrics("test_tool")
        assert metrics.call_count == 1
        assert metrics.success_count == 1
        assert metrics.failure_count == 0
        assert len(metrics.latencies) == 1
        assert metrics.latencies[0] == 0.1

    def test_record_failed_call(self) -> None:
        """Record a failed call."""
        collector = MetricsCollector()
        collector.record_call("test_tool", latency=0.5, success=False)

        metrics = collector.get_tool_metrics("test_tool")
        assert metrics.call_count == 1
        assert metrics.success_count == 0
        assert metrics.failure_count == 1

    def test_multiple_calls(self) -> None:
        """Record multiple calls to the same tool."""
        collector = MetricsCollector()
        collector.record_call("test_tool", latency=0.1, success=True)
        collector.record_call("test_tool", latency=0.2, success=True)
        collector.record_call("test_tool", latency=0.3, success=False)

        metrics = collector.get_tool_metrics("test_tool")
        assert metrics.call_count == 3
        assert metrics.success_count == 2
        assert metrics.failure_count == 1
        assert len(metrics.latencies) == 3

    def test_multiple_tools(self) -> None:
        """Record calls to different tools."""
        collector = MetricsCollector()
        collector.record_call("tool_a", latency=0.1, success=True)
        collector.record_call("tool_b", latency=0.2, success=True)

        all_metrics = collector.get_all_metrics()
        assert len(all_metrics) == 2
        assert "tool_a" in all_metrics
        assert "tool_b" in all_metrics

    def test_get_unknown_tool(self) -> None:
        """Getting metrics for unknown tool returns empty metrics."""
        collector = MetricsCollector()
        metrics = collector.get_tool_metrics("nonexistent")
        assert metrics.call_count == 0

    def test_reset(self) -> None:
        """Reset should clear all metrics."""
        collector = MetricsCollector()
        collector.record_call("test_tool", latency=0.1, success=True)
        collector.reset()

        metrics = collector.get_tool_metrics("test_tool")
        assert metrics.call_count == 0

    def test_total_calls(self) -> None:
        """Total calls should sum across all tools."""
        collector = MetricsCollector()
        collector.record_call("tool_a", latency=0.1, success=True)
        collector.record_call("tool_a", latency=0.1, success=True)
        collector.record_call("tool_b", latency=0.1, success=True)

        assert collector.total_calls == 3

    def test_total_errors(self) -> None:
        """Total errors should sum failures across all tools."""
        collector = MetricsCollector()
        collector.record_call("tool_a", latency=0.1, success=False)
        collector.record_call("tool_a", latency=0.1, success=True)
        collector.record_call("tool_b", latency=0.1, success=False)

        assert collector.total_errors == 2

    def test_get_summary(self) -> None:
        """Summary should include tool metrics."""
        collector = MetricsCollector()
        collector.record_call("test_tool", latency=0.1, success=True)

        summary = collector.get_summary()
        assert "test_tool" in summary
        assert "Calls:" in summary

    def test_latency_samples_bounded(self) -> None:
        """Latency samples should be bounded to prevent unbounded growth."""
        collector = MetricsCollector()

        # Record more samples than the limit
        for _i in range(MetricsCollector.MAX_LATENCY_SAMPLES + 100):
            collector.record_call("test_tool", latency=0.001, success=True)

        metrics = collector.get_tool_metrics("test_tool")
        assert len(metrics.latencies) <= MetricsCollector.MAX_LATENCY_SAMPLES


class TestMetricsCollectorThreadSafety:
    """Test thread safety of MetricsCollector."""

    def test_concurrent_writes(self) -> None:
        """Concurrent writes should not corrupt data."""
        collector = MetricsCollector()
        num_threads = 10
        calls_per_thread = 100

        def record_calls(thread_id: int) -> None:
            for i in range(calls_per_thread):
                collector.record_call(
                    f"tool_{thread_id % 3}",  # 3 different tools
                    latency=0.001,
                    success=i % 5 != 0,  # 80% success rate
                )

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(record_calls, i) for i in range(num_threads)]
            for f in futures:
                f.result()

        # Verify totals
        assert collector.total_calls == num_threads * calls_per_thread

        # Verify no data corruption (all metrics should be positive)
        for metrics in collector.get_all_metrics().values():
            assert metrics.call_count > 0
            assert metrics.call_count == metrics.success_count + metrics.failure_count


class TestInstrumentToolDecorator:
    """Test instrument_tool decorator."""

    def test_instrument_successful_call(self) -> None:
        """Decorator should record successful calls."""
        reset_metrics()

        @instrument_tool
        def test_function() -> str:
            return "success"

        result = test_function()
        assert result == "success"

        metrics = get_metrics().get_tool_metrics("test_function")
        assert metrics.call_count == 1
        assert metrics.success_count == 1
        assert metrics.failure_count == 0

    def test_instrument_failed_call(self) -> None:
        """Decorator should record failed calls."""
        reset_metrics()

        @instrument_tool
        def failing_function() -> str:
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            failing_function()

        metrics = get_metrics().get_tool_metrics("failing_function")
        assert metrics.call_count == 1
        assert metrics.success_count == 0
        assert metrics.failure_count == 1

    def test_instrument_preserves_function_metadata(self) -> None:
        """Decorator should preserve function name and docstring."""

        @instrument_tool
        def documented_function() -> str:
            """This is the docstring."""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ == "This is the docstring."

    def test_instrument_measures_latency(self) -> None:
        """Decorator should measure call latency."""
        reset_metrics()

        @instrument_tool
        def slow_function() -> str:
            time.sleep(0.05)  # 50ms
            return "done"

        slow_function()

        metrics = get_metrics().get_tool_metrics("slow_function")
        assert len(metrics.latencies) == 1
        assert metrics.latencies[0] >= 0.05  # At least 50ms

    def test_instrument_with_args_kwargs(self) -> None:
        """Decorator should work with args and kwargs."""
        reset_metrics()

        @instrument_tool
        def parameterized_function(a: int, b: str, c: bool = False) -> str:
            return f"{a}-{b}-{c}"

        result = parameterized_function(1, "test", c=True)
        assert result == "1-test-True"

        metrics = get_metrics().get_tool_metrics("parameterized_function")
        assert metrics.call_count == 1


class TestGlobalMetrics:
    """Test global metrics functions."""

    def test_get_metrics_singleton(self) -> None:
        """get_metrics should return the same instance."""
        collector1 = get_metrics()
        collector2 = get_metrics()
        assert collector1 is collector2

    def test_reset_metrics(self) -> None:
        """reset_metrics should clear the global collector."""
        collector = get_metrics()
        collector.record_call("test", latency=0.1, success=True)

        reset_metrics()

        assert collector.total_calls == 0

    def test_get_metrics_summary(self) -> None:
        """get_metrics_summary should return summary string."""
        reset_metrics()
        get_metrics().record_call("test", latency=0.1, success=True)

        summary = get_metrics_summary()
        assert isinstance(summary, str)
        assert "test" in summary
