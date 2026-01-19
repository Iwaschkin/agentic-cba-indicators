"""Tests for ChromaDB connection pooling singleton pattern."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import pytest


class TestChromaDBSingleton:
    """Test ChromaDB client singleton behavior."""

    def setup_method(self) -> None:
        """Reset singleton before each test."""
        # Import here to avoid circular import issues
        from agentic_cba_indicators.tools.knowledge_base import reset_chroma_client

        reset_chroma_client()

    def teardown_method(self) -> None:
        """Reset singleton after each test."""
        from agentic_cba_indicators.tools.knowledge_base import reset_chroma_client

        reset_chroma_client()

    def test_singleton_returns_same_instance(self) -> None:
        """Verify that _get_chroma_client returns the same instance on multiple calls."""
        from agentic_cba_indicators.tools.knowledge_base import _get_chroma_client

        with patch(
            "agentic_cba_indicators.tools.knowledge_base.chromadb"
        ) as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client

            # First call should create the client
            client1 = _get_chroma_client()

            # Second call should return the same instance
            client2 = _get_chroma_client()

            # Third call should still return the same instance
            client3 = _get_chroma_client()

            # Verify same instance returned
            assert client1 is client2
            assert client2 is client3

            # Verify PersistentClient only called once
            assert mock_chromadb.PersistentClient.call_count == 1

    def test_singleton_thread_safety(self) -> None:
        """Verify thread-safe initialization of singleton."""
        from agentic_cba_indicators.tools.knowledge_base import _get_chroma_client

        results: list[object] = []
        errors: list[Exception] = []

        with patch(
            "agentic_cba_indicators.tools.knowledge_base.chromadb"
        ) as mock_chromadb:
            mock_client = MagicMock()
            mock_chromadb.PersistentClient.return_value = mock_client

            def get_client() -> None:
                try:
                    client = _get_chroma_client()
                    results.append(client)
                except Exception as e:
                    errors.append(e)

            # Create multiple threads to access the singleton concurrently
            threads = [threading.Thread(target=get_client) for _ in range(10)]

            # Start all threads
            for t in threads:
                t.start()

            # Wait for all threads to complete
            for t in threads:
                t.join()

            # Verify no errors
            assert not errors, f"Errors occurred: {errors}"

            # Verify all threads got the same instance
            assert len(results) == 10
            assert all(r is results[0] for r in results)

            # Verify PersistentClient only called once
            assert mock_chromadb.PersistentClient.call_count == 1

    def test_concurrent_access_stress(self) -> None:
        """Stress test for concurrent singleton access with simulated contention.

        CR-0026: Tests race conditions under high concurrency with artificial
        delays to increase the chance of detecting race conditions.
        """
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from agentic_cba_indicators.tools.knowledge_base import _get_chroma_client

        results: list[object] = []
        errors: list[Exception] = []
        call_count = 0
        call_lock = threading.Lock()

        with patch(
            "agentic_cba_indicators.tools.knowledge_base.chromadb"
        ) as mock_chromadb:
            mock_client = MagicMock()

            def slow_client_creation(*args: object, **kwargs: object) -> MagicMock:
                """Simulate slow client creation to increase race window."""
                nonlocal call_count
                with call_lock:
                    call_count += 1
                # Small delay to increase chance of race conditions
                time.sleep(0.01)
                return mock_client

            mock_chromadb.PersistentClient.side_effect = slow_client_creation

            def get_client_with_work() -> object:
                """Get client and do some 'work' to simulate real usage."""
                try:
                    client = _get_chroma_client()
                    # Simulate some work with the client
                    time.sleep(0.001)
                    return client
                except Exception as e:
                    errors.append(e)
                    return None

            # Use ThreadPoolExecutor for more realistic concurrent access
            num_workers = 50
            num_calls = 100

            with ThreadPoolExecutor(max_workers=num_workers) as executor:
                futures = [
                    executor.submit(get_client_with_work) for _ in range(num_calls)
                ]

                for future in as_completed(futures):
                    result = future.result()
                    if result is not None:
                        results.append(result)

            # Verify no errors occurred
            assert not errors, f"Errors during concurrent access: {errors}"

            # Verify all calls got the same instance
            assert len(results) == num_calls
            assert all(r is mock_client for r in results)

            # Verify PersistentClient was only called once despite concurrent access
            # This is the key assertion - singleton should only initialize once
            assert call_count == 1, (
                f"PersistentClient called {call_count} times, expected 1. "
                "Race condition in singleton initialization detected!"
            )

    def test_reset_allows_new_client(self) -> None:
        """Verify reset_chroma_client allows creating a new client."""
        from agentic_cba_indicators.tools.knowledge_base import (
            _get_chroma_client,
            reset_chroma_client,
        )

        with patch(
            "agentic_cba_indicators.tools.knowledge_base.chromadb"
        ) as mock_chromadb:
            mock_client1 = MagicMock(name="client1")
            mock_client2 = MagicMock(name="client2")
            mock_chromadb.PersistentClient.side_effect = [mock_client1, mock_client2]

            # First call creates client1
            client1 = _get_chroma_client()
            assert client1 is mock_client1

            # Reset the singleton
            reset_chroma_client()

            # Next call creates client2
            client2 = _get_chroma_client()
            assert client2 is mock_client2

            # Verify PersistentClient called twice
            assert mock_chromadb.PersistentClient.call_count == 2

    def test_retry_on_transient_error(self) -> None:
        """Verify retry logic for transient errors during client creation."""
        from agentic_cba_indicators.tools.knowledge_base import _get_chroma_client

        with (
            patch(
                "agentic_cba_indicators.tools.knowledge_base.chromadb"
            ) as mock_chromadb,
            patch("agentic_cba_indicators.tools.knowledge_base.time.sleep"),
        ):
            mock_client = MagicMock()
            # First call fails with transient error, second succeeds
            mock_chromadb.PersistentClient.side_effect = [
                Exception("database locked"),
                mock_client,
            ]

            client = _get_chroma_client()

            assert client is mock_client
            assert mock_chromadb.PersistentClient.call_count == 2

    def test_non_transient_error_raises_immediately(self) -> None:
        """Verify non-transient errors raise immediately without retry."""
        from agentic_cba_indicators.tools.knowledge_base import (
            ChromaDBError,
            _get_chroma_client,
        )

        with patch(
            "agentic_cba_indicators.tools.knowledge_base.chromadb"
        ) as mock_chromadb:
            mock_chromadb.PersistentClient.side_effect = Exception(
                "invalid path format"
            )

            with pytest.raises(ChromaDBError, match="invalid path format"):
                _get_chroma_client()

            # Should only try once for non-transient errors
            assert mock_chromadb.PersistentClient.call_count == 1
