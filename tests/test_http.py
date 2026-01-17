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

    def test_sanitizes_api_error_message(self):
        """Should sanitize sensitive data in APIError messages."""
        from agentic_cba_indicators.tools._http import APIError, format_error

        error = APIError("Failed at https://api.com?api_key=secret123")
        result = format_error(error)

        assert "secret123" not in result
        assert "[REDACTED]" in result

    def test_formats_generic_exception(self):
        """Should format generic exceptions."""
        from agentic_cba_indicators.tools._http import format_error

        error = ValueError("Invalid input")
        result = format_error(error, "processing")

        assert "Invalid input" in result
        assert "processing" in result


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
