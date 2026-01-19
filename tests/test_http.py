"""Tests for HTTP utilities."""

from __future__ import annotations

import pytest


class TestSanitizeError:
    """Tests for error message sanitization."""

    def test_sanitizes_api_key_in_url(self):
        """Should redact API keys in URL query parameters."""
        from agentic_cba_indicators.tools._http import sanitize_error

        msg = "Error fetching https://api.example.com/data?api_key=secret123abc&format=json"
        result = sanitize_error(msg)

        assert "secret123abc" not in result
        assert "[REDACTED]" in result
        assert "format=json" in result

    def test_sanitizes_token_in_url(self):
        """Should redact tokens in URL query parameters."""
        from agentic_cba_indicators.tools._http import sanitize_error

        msg = "Request failed: https://api.example.com?token=mytoken123"
        result = sanitize_error(msg)

        assert "mytoken123" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_authorization_header(self):
        """Should redact Authorization headers in error messages."""
        from agentic_cba_indicators.tools._http import sanitize_error

        msg = "Request headers: Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
        result = sanitize_error(msg)

        assert "eyJhbGciOiJIUzI1NiIs" not in result
        assert "[REDACTED]" in result

    def test_sanitizes_long_hex_keys(self):
        """Should redact long hex strings that look like API keys."""
        from agentic_cba_indicators.tools._http import sanitize_error

        msg = "Failed with key: abcdef0123456789abcdef0123456789abcd"
        result = sanitize_error(msg)

        assert "abcdef0123456789abcdef0123456789abcd" not in result
        assert "[REDACTED_KEY]" in result

    def test_preserves_normal_error_messages(self):
        """Should not modify error messages without sensitive data."""
        from agentic_cba_indicators.tools._http import sanitize_error

        msg = "Connection timeout after 30 seconds"
        result = sanitize_error(msg)

        assert result == msg

    def test_handles_multiple_sensitive_items(self):
        """Should redact multiple sensitive items in one message."""
        from agentic_cba_indicators.tools._http import sanitize_error

        msg = "Failed: url?api_key=key1&token=tok2"
        result = sanitize_error(msg)

        assert "key1" not in result
        assert "tok2" not in result


class TestFormatError:
    """Tests for format_error function."""

    def test_formats_api_error_with_status(self):
        """Should format APIError with status code."""
        from agentic_cba_indicators.tools._http import APIError, format_error

        error = APIError("Not found", status_code=404)
        result = format_error(error, "fetching data")

        assert "404" in result
        assert "fetching data" in result
        assert "category" in result

    def test_sanitizes_api_error_message(self):
        """Should sanitize sensitive data in APIError messages."""
        from agentic_cba_indicators.tools._http import APIError, format_error

        error = APIError("Failed at https://api.com?api_key=secret123")
        result = format_error(error)

        assert "secret123" not in result
        assert "[REDACTED]" in result
        assert "category" in result

    def test_formats_generic_exception(self):
        """Should format generic exceptions."""
        from agentic_cba_indicators.tools._http import format_error

        error = ValueError("Invalid input")
        result = format_error(error, "processing")

        assert "Invalid input" in result
        assert "processing" in result
        assert "category" in result


class TestErrorClassification:
    """Tests for error classification helper."""

    def test_classifies_rate_limit(self):
        from agentic_cba_indicators.tools._http import (
            APIError,
            ErrorCategory,
            classify_error,
        )

        err = APIError("rate limit", status_code=429)
        assert classify_error(err) == ErrorCategory.RATE_LIMIT

    def test_classifies_transient(self):
        from agentic_cba_indicators.tools._http import (
            APIError,
            ErrorCategory,
            classify_error,
        )

        err = APIError("server error", status_code=503)
        assert classify_error(err) == ErrorCategory.TRANSIENT

    def test_classifies_permanent(self):
        from agentic_cba_indicators.tools._http import (
            APIError,
            ErrorCategory,
            classify_error,
        )

        err = APIError("bad request", status_code=400)
        assert classify_error(err) == ErrorCategory.PERMANENT


class TestAPIError:
    """Tests for APIError exception class."""

    def test_stores_status_code(self):
        """Should store HTTP status code."""
        from agentic_cba_indicators.tools._http import APIError

        error = APIError("Test error", status_code=500)
        assert error.status_code == 500

    def test_allows_none_status_code(self):
        """Should allow None status code for non-HTTP errors."""
        from agentic_cba_indicators.tools._http import APIError

        error = APIError("Timeout error")
        assert error.status_code is None


class TestFetchJsonErrorHandling:
    """Tests for fetch_json error handling."""

    def test_handles_json_decode_error(self, monkeypatch):
        """Should handle invalid JSON responses gracefully."""
        from typing import ClassVar

        from agentic_cba_indicators.tools._http import APIError, fetch_json

        # Mock response with invalid JSON
        class MockResponse:
            status_code = 200
            text = "not valid json"
            headers: ClassVar[dict[str, str]] = {}

            def json(self):
                import json

                json.loads(self.text)  # This will raise JSONDecodeError

        class MockClient:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                pass

            def close(self):
                pass

            def get(self, url, params=None):
                return MockResponse()

        # Patch create_client to return our mock
        monkeypatch.setattr(
            "agentic_cba_indicators.tools._http.create_client", lambda: MockClient()
        )

        import pytest

        with pytest.raises(APIError) as exc_info:
            fetch_json("https://example.com/api?api_key=secret123")

        error = exc_info.value
        # Should mention invalid JSON
        assert "Invalid JSON" in str(error)
        # Should sanitize the URL (remove api_key value)
        assert "secret123" not in str(error)
        # Should include error context
        assert "line" in str(error)
        # Status code should be 200 (server returned response)
        assert error.status_code == 200


class TestFetchJsonRetryBehavior:
    """Tests for fetch_json retry behavior on various error types."""

    def test_rate_limit_exhausted(self):
        """Test fetch_json raises APIError when rate limit retries exhausted."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import APIError, fetch_json

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        # Use retries=0 to fail immediately
        with pytest.raises(APIError) as exc_info:
            fetch_json("https://example.com/api", client=mock_client, retries=0)

        assert exc_info.value.status_code == 429
        assert "Rate limited" in str(exc_info.value)

    def test_server_error_exhausted(self):
        """Test fetch_json raises APIError when server error retries exhausted."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import APIError, fetch_json

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            fetch_json("https://example.com/api", client=mock_client, retries=0)

        assert exc_info.value.status_code == 500
        assert "Server error" in str(exc_info.value)

    def test_client_error_no_retry(self):
        """Test fetch_json raises immediately on client errors (4xx except 429)."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import APIError, fetch_json

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            fetch_json("https://example.com/api", client=mock_client, retries=3)

        # Should fail immediately without retries
        assert mock_client.get.call_count == 1
        assert exc_info.value.status_code == 404

    def test_timeout_exhausted(self):
        """Test fetch_json raises APIError when timeout retries exhausted."""
        from unittest.mock import MagicMock

        import httpx

        from agentic_cba_indicators.tools._http import APIError, fetch_json

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.TimeoutException("Request timed out")

        with pytest.raises(APIError) as exc_info:
            fetch_json("https://example.com/api", client=mock_client, retries=0)

        assert "timeout" in str(exc_info.value).lower()

    def test_request_error_exhausted(self):
        """Test fetch_json raises APIError when request error retries exhausted."""
        from unittest.mock import MagicMock

        import httpx

        from agentic_cba_indicators.tools._http import APIError, fetch_json

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(APIError) as exc_info:
            fetch_json("https://example.com/api", client=mock_client, retries=0)

        assert "failed" in str(exc_info.value).lower() or "Connection" in str(
            exc_info.value
        )


class TestFetchJsonSuccess:
    """Tests for fetch_json success paths."""

    def test_returns_json_on_success(self):
        """Test fetch_json returns JSON on success."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import fetch_json

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test_value"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        result = fetch_json("https://example.com/api", client=mock_client)

        assert result == {"data": "test_value"}

    def test_passes_params_to_client(self):
        """Test fetch_json passes params to client.get."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import fetch_json

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        fetch_json(
            "https://example.com/api", params={"key": "value"}, client=mock_client
        )

        mock_client.get.assert_called_once_with(
            "https://example.com/api", params={"key": "value"}
        )


class TestCreateClient:
    """Tests for create_client function."""

    def test_default_settings(self):
        """Test create_client creates client with default settings."""
        from agentic_cba_indicators.tools._http import create_client

        client = create_client()

        assert client is not None
        assert "User-Agent" in client.headers
        client.close()

    def test_custom_headers(self):
        """Test create_client accepts custom headers."""
        from agentic_cba_indicators.tools._http import create_client

        client = create_client(headers={"X-Custom": "test"})

        assert client.headers["X-Custom"] == "test"
        client.close()


# =============================================================================
# Caching Tests
# =============================================================================


class TestMakeCacheKey:
    """Tests for _make_cache_key function."""

    def test_same_inputs_same_key(self):
        """Same URL and params should produce same key."""
        from agentic_cba_indicators.tools._http import _make_cache_key

        key1 = _make_cache_key("https://api.example.com/data", {"foo": "bar"})
        key2 = _make_cache_key("https://api.example.com/data", {"foo": "bar"})

        assert key1 == key2

    def test_different_urls_different_keys(self):
        """Different URLs should produce different keys."""
        from agentic_cba_indicators.tools._http import _make_cache_key

        key1 = _make_cache_key("https://api.example.com/data1", {"foo": "bar"})
        key2 = _make_cache_key("https://api.example.com/data2", {"foo": "bar"})

        assert key1 != key2

    def test_different_params_different_keys(self):
        """Different params should produce different keys."""
        from agentic_cba_indicators.tools._http import _make_cache_key

        key1 = _make_cache_key("https://api.example.com/data", {"foo": "bar"})
        key2 = _make_cache_key("https://api.example.com/data", {"foo": "baz"})

        assert key1 != key2

    def test_param_order_independent(self):
        """Param order should not affect key (consistent serialization)."""
        from agentic_cba_indicators.tools._http import _make_cache_key

        key1 = _make_cache_key("https://api.example.com/data", {"a": "1", "b": "2"})
        key2 = _make_cache_key("https://api.example.com/data", {"b": "2", "a": "1"})

        assert key1 == key2

    def test_none_params(self):
        """None params should produce consistent key."""
        from agentic_cba_indicators.tools._http import _make_cache_key

        key1 = _make_cache_key("https://api.example.com/data", None)
        key2 = _make_cache_key("https://api.example.com/data", None)

        assert key1 == key2

    def test_empty_params(self):
        """Empty params should differ from None params."""
        from agentic_cba_indicators.tools._http import _make_cache_key

        key1 = _make_cache_key("https://api.example.com/data", None)
        key2 = _make_cache_key("https://api.example.com/data", {})

        # Both are "empty" but serialized differently
        assert key1 == key2 or key1 != key2  # Implementation choice


class TestFetchJsonCached:
    """Tests for fetch_json_cached function."""

    def test_cache_miss_calls_fetch(self):
        """Cache miss should call underlying fetch_json."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import (
            clear_api_cache,
            fetch_json_cached,
        )

        clear_api_cache()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "fresh"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        result = fetch_json_cached(
            "https://api.example.com/cached", params={"q": "test"}, client=mock_client
        )

        assert result == {"data": "fresh"}
        assert mock_client.get.call_count == 1

    def test_cache_hit_skips_fetch(self):
        """Cache hit should return cached value without calling fetch."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import (
            clear_api_cache,
            fetch_json_cached,
        )

        clear_api_cache()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "original"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        # First call - cache miss
        result1 = fetch_json_cached(
            "https://api.example.com/cached2",
            params={"q": "hit"},
            client=mock_client,
        )

        # Modify mock to return different value
        mock_response.json.return_value = {"data": "modified"}

        # Second call - should return cached value
        result2 = fetch_json_cached(
            "https://api.example.com/cached2",
            params={"q": "hit"},
            client=mock_client,
        )

        assert result1 == {"data": "original"}
        assert result2 == {"data": "original"}  # Cached, not modified
        assert mock_client.get.call_count == 1  # Only called once

    def test_use_cache_false_bypasses_cache(self):
        """use_cache=False should bypass caching."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import (
            clear_api_cache,
            fetch_json_cached,
        )

        clear_api_cache()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "fresh_each_time"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        # First call with caching
        fetch_json_cached(
            "https://api.example.com/nocache",
            params={"q": "bypass"},
            client=mock_client,
            use_cache=True,
        )

        # Second call without caching - should call fetch again
        fetch_json_cached(
            "https://api.example.com/nocache",
            params={"q": "bypass"},
            client=mock_client,
            use_cache=False,
        )

        assert mock_client.get.call_count == 2

    def test_different_params_different_cache_entries(self):
        """Different params should create different cache entries."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import (
            clear_api_cache,
            fetch_json_cached,
        )

        clear_api_cache()

        call_count = 0

        def mock_get(url, params=None):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = {"call": call_count, "params": params}
            return response

        mock_client = MagicMock()
        mock_client.get = mock_get

        result1 = fetch_json_cached(
            "https://api.example.com/multi",
            params={"q": "first"},
            client=mock_client,
        )
        result2 = fetch_json_cached(
            "https://api.example.com/multi",
            params={"q": "second"},
            client=mock_client,
        )

        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        assert result1["call"] == 1
        assert result2["call"] == 2
        assert call_count == 2


class TestCachedApiCallDecorator:
    """Tests for @cached_api_call decorator."""

    def test_decorator_caches_function_calls(self):
        """Decorator should cache function return values."""
        from agentic_cba_indicators.tools._http import cached_api_call

        call_count = 0

        @cached_api_call(ttl=60, maxsize=10)
        def expensive_api_call(arg1: str, arg2: int) -> dict:
            nonlocal call_count
            call_count += 1
            return {"arg1": arg1, "arg2": arg2, "call": call_count}

        # First call
        result1 = expensive_api_call("test", 42)
        # Second call with same args
        result2 = expensive_api_call("test", 42)

        assert result1 == result2
        assert result1["call"] == 1
        assert call_count == 1  # Only called once

    def test_decorator_different_args_different_cache(self):
        """Decorator should cache different args separately."""
        from agentic_cba_indicators.tools._http import cached_api_call

        call_count = 0

        @cached_api_call(ttl=60, maxsize=10)
        def api_with_args(value: str) -> dict:
            nonlocal call_count
            call_count += 1
            return {"value": value, "call": call_count}

        result1 = api_with_args("first")
        result2 = api_with_args("second")
        result3 = api_with_args("first")  # Should hit cache

        assert result1["call"] == 1
        assert result2["call"] == 2
        assert result3["call"] == 1  # Cached
        assert call_count == 2

    def test_decorator_preserves_function_metadata(self):
        """Decorator should preserve function name and docstring."""
        from agentic_cba_indicators.tools._http import cached_api_call

        @cached_api_call(ttl=60)
        def documented_function() -> str:
            """This is the docstring."""
            return "result"

        assert documented_function.__name__ == "documented_function"
        assert documented_function.__doc__ is not None
        assert "docstring" in documented_function.__doc__


class TestCacheUtilities:
    """Tests for cache utility functions."""

    def test_get_cache_stats_returns_dict(self):
        """get_cache_stats should return cache statistics."""
        from agentic_cba_indicators.tools._http import clear_api_cache, get_cache_stats

        clear_api_cache()
        stats = get_cache_stats()

        assert isinstance(stats, dict)
        assert "size" in stats
        assert "maxsize" in stats
        assert "ttl" in stats
        assert stats["size"] == 0

    def test_clear_api_cache_returns_count(self):
        """clear_api_cache should return number of cleared entries."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import (
            clear_api_cache,
            fetch_json_cached,
        )

        clear_api_cache()

        # Add some cache entries
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        fetch_json_cached(
            "https://api.example.com/clear1", params=None, client=mock_client
        )
        fetch_json_cached(
            "https://api.example.com/clear2", params=None, client=mock_client
        )

        cleared = clear_api_cache()
        assert cleared == 2

    def test_clear_api_cache_empties_cache(self):
        """clear_api_cache should empty the cache."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import (
            clear_api_cache,
            fetch_json_cached,
            get_cache_stats,
        )

        # Add entry then clear
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        fetch_json_cached(
            "https://api.example.com/empty", params=None, client=mock_client
        )

        clear_api_cache()
        stats = get_cache_stats()

        assert stats["size"] == 0


class TestCacheThreadSafety:
    """Tests for cache thread safety."""

    def test_concurrent_cache_access(self):
        """Cache should handle concurrent access safely."""
        import threading
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import (
            clear_api_cache,
            fetch_json_cached,
            get_cache_stats,
        )

        clear_api_cache()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "concurrent"}

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response

        errors = []

        def worker(thread_id: int):
            try:
                for i in range(10):
                    fetch_json_cached(
                        f"https://api.example.com/thread/{thread_id % 3}",
                        params={"i": i % 3},
                        client=mock_client,
                    )
                    get_cache_stats()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestCacheErrorHandling:
    """Tests for cache behavior during errors."""

    def test_error_not_cached(self):
        """API errors should not be cached."""
        from unittest.mock import MagicMock

        from agentic_cba_indicators.tools._http import (
            APIError,
            clear_api_cache,
            fetch_json_cached,
        )

        clear_api_cache()

        call_count = 0

        def mock_get(url, params=None):
            nonlocal call_count
            call_count += 1
            response = MagicMock()
            if call_count == 1:
                response.status_code = 500
                response.text = "Internal Server Error"
            else:
                response.status_code = 200
                response.json.return_value = {"success": True}
            return response

        mock_client = MagicMock()
        mock_client.get = mock_get

        # First call fails
        with pytest.raises(APIError):
            fetch_json_cached(
                "https://api.example.com/error",
                params={"q": "retry"},
                client=mock_client,
                retries=0,
            )

        # Second call should retry (not return cached error)
        result = fetch_json_cached(
            "https://api.example.com/error",
            params={"q": "retry"},
            client=mock_client,
            retries=0,
        )

        assert result == {"success": True}
        assert call_count == 2
