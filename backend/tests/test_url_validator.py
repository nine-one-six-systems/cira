"""Tests for URL validation and reachability checking service.

Tests URL format validation and reachability checks per Task 9.6.
"""

import pytest
from unittest.mock import patch, MagicMock
from requests.exceptions import Timeout, ConnectionError as RequestsConnectionError

from app.services.url_validator import (
    validate_url,
    validate_url_format,
    normalize_url,
    check_url_reachability,
    validate_url_batch,
    ValidationResult,
    REACHABILITY_TIMEOUT,
)


class TestNormalizeUrl:
    """Tests for URL normalization."""

    def test_adds_https_to_bare_domain(self):
        """Test that https:// is added to bare domains."""
        result = normalize_url("example.com")
        assert result == "https://example.com/"

    def test_preserves_http(self):
        """Test that http:// is preserved if present."""
        result = normalize_url("http://example.com")
        assert result.startswith("http://")

    def test_preserves_https(self):
        """Test that https:// is preserved if present."""
        result = normalize_url("https://example.com")
        assert result.startswith("https://")

    def test_adds_trailing_slash_to_root(self):
        """Test that trailing slash is added to root URLs."""
        result = normalize_url("https://example.com")
        assert result == "https://example.com/"

    def test_preserves_path(self):
        """Test that paths are preserved."""
        result = normalize_url("https://example.com/path/to/page")
        assert result == "https://example.com/path/to/page"

    def test_preserves_query_string(self):
        """Test that query strings are preserved."""
        result = normalize_url("https://example.com/page?foo=bar")
        assert "?foo=bar" in result

    def test_strips_whitespace(self):
        """Test that whitespace is stripped."""
        result = normalize_url("  https://example.com  ")
        assert result == "https://example.com/"


class TestValidateUrlFormat:
    """Tests for URL format validation."""

    def test_valid_https_url(self):
        """Test valid HTTPS URL passes."""
        is_valid, error = validate_url_format("https://example.com")
        assert is_valid is True
        assert error is None

    def test_valid_http_url(self):
        """Test valid HTTP URL passes."""
        is_valid, error = validate_url_format("http://example.com")
        assert is_valid is True
        assert error is None

    def test_valid_url_with_path(self):
        """Test URL with path passes."""
        is_valid, error = validate_url_format("https://example.com/page")
        assert is_valid is True

    def test_valid_url_with_subdomain(self):
        """Test URL with subdomain passes."""
        is_valid, error = validate_url_format("https://www.example.com")
        assert is_valid is True

    def test_valid_url_with_port(self):
        """Test URL with port passes."""
        is_valid, error = validate_url_format("https://example.com:8080")
        assert is_valid is True

    def test_empty_url_fails(self):
        """Test empty URL fails."""
        is_valid, error = validate_url_format("")
        assert is_valid is False
        assert "required" in error.lower()

    def test_invalid_format_fails(self):
        """Test invalid URL format fails."""
        is_valid, error = validate_url_format("not-a-url")
        assert is_valid is False
        assert "invalid" in error.lower()

    def test_missing_tld_fails(self):
        """Test URL without TLD fails."""
        # Single-word domains without TLD should fail validation
        is_valid, error = validate_url_format("https://example")
        assert is_valid is False
        assert error is not None

    def test_localhost_passes(self):
        """Test localhost is allowed."""
        is_valid, error = validate_url_format("http://localhost:5000")
        assert is_valid is True

    def test_ip_address_passes(self):
        """Test IP address URLs pass."""
        is_valid, error = validate_url_format("http://192.168.1.1")
        assert is_valid is True


class TestCheckUrlReachability:
    """Tests for URL reachability checking."""

    @patch('app.services.url_validator.requests.head')
    def test_reachable_url_returns_true(self, mock_head):
        """Test that reachable URL returns is_reachable=True."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        is_reachable, status, error = check_url_reachability("https://example.com")

        assert is_reachable is True
        assert status == 200
        assert error is None

    @patch('app.services.url_validator.requests.head')
    def test_redirect_is_reachable(self, mock_head):
        """Test that redirect (3xx) is considered reachable."""
        mock_response = MagicMock()
        mock_response.status_code = 301
        mock_head.return_value = mock_response

        is_reachable, status, error = check_url_reachability("https://example.com")

        assert is_reachable is True
        assert status == 301

    @patch('app.services.url_validator.requests.head')
    def test_404_is_not_reachable(self, mock_head):
        """Test that 404 is not considered reachable."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_head.return_value = mock_response

        is_reachable, status, error = check_url_reachability("https://example.com")

        assert is_reachable is False
        assert status == 404
        assert "404" in error

    @patch('app.services.url_validator.requests.head')
    @patch('app.services.url_validator.requests.get')
    def test_head_not_allowed_falls_back_to_get(self, mock_get, mock_head):
        """Test that 405 from HEAD falls back to GET."""
        mock_head_response = MagicMock()
        mock_head_response.status_code = 405
        mock_head.return_value = mock_head_response

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get.return_value = mock_get_response

        is_reachable, status, error = check_url_reachability("https://example.com")

        assert is_reachable is True
        assert status == 200

    @patch('app.services.url_validator.requests.head')
    def test_timeout_returns_not_reachable(self, mock_head):
        """Test that timeout returns not reachable with error."""
        mock_head.side_effect = Timeout("Connection timed out")

        is_reachable, status, error = check_url_reachability("https://example.com")

        assert is_reachable is False
        assert status is None
        assert "timed out" in error.lower()
        assert str(REACHABILITY_TIMEOUT) in error

    @patch('app.services.url_validator.requests.head')
    def test_dns_failure_returns_not_reachable(self, mock_head):
        """Test that DNS failure returns not reachable with error."""
        mock_head.side_effect = RequestsConnectionError("Name or service not known")

        is_reachable, status, error = check_url_reachability("https://nonexistent.invalid")

        assert is_reachable is False
        assert status is None
        assert "DNS" in error or "resolve" in error.lower()

    @patch('app.services.url_validator.requests.head')
    def test_connection_refused_returns_not_reachable(self, mock_head):
        """Test that connection refused returns not reachable."""
        mock_head.side_effect = RequestsConnectionError("Connection refused")

        is_reachable, status, error = check_url_reachability("https://example.com")

        assert is_reachable is False
        assert "refused" in error.lower()

    @patch('app.services.url_validator.requests.head')
    def test_uses_correct_timeout(self, mock_head):
        """Test that the correct timeout is used."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        check_url_reachability("https://example.com")

        mock_head.assert_called_once()
        _, kwargs = mock_head.call_args
        assert kwargs['timeout'] == REACHABILITY_TIMEOUT

    @patch('app.services.url_validator.requests.head')
    def test_uses_correct_user_agent(self, mock_head):
        """Test that CIRA Bot user agent is used."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response

        check_url_reachability("https://example.com")

        _, kwargs = mock_head.call_args
        assert "CIRA Bot" in kwargs['headers']['User-Agent']


class TestValidateUrl:
    """Tests for the main validate_url function."""

    @patch('app.services.url_validator.check_url_reachability')
    def test_valid_reachable_url(self, mock_reachability):
        """Test valid and reachable URL."""
        mock_reachability.return_value = (True, 200, None)

        result = validate_url("https://example.com")

        assert result.is_valid is True
        assert result.is_reachable is True
        assert result.error_message is None
        assert result.warning_message is None

    @patch('app.services.url_validator.check_url_reachability')
    def test_valid_unreachable_url_returns_warning(self, mock_reachability):
        """Test that valid but unreachable URL returns warning not error."""
        mock_reachability.return_value = (False, None, "Connection timed out")

        result = validate_url("https://unreachable.example.com")

        assert result.is_valid is True  # Format is still valid
        assert result.is_reachable is False
        assert result.error_message is None  # No error
        assert result.warning_message is not None  # But has warning
        assert "Connection timed out" in result.warning_message

    def test_invalid_format_returns_error(self):
        """Test that invalid format returns error."""
        result = validate_url("not-a-valid-url")

        assert result.is_valid is False
        assert result.error_message is not None

    @patch('app.services.url_validator.check_url_reachability')
    def test_skip_reachability_check(self, mock_reachability):
        """Test that reachability check can be skipped."""
        result = validate_url("https://example.com", check_reachability=False)

        mock_reachability.assert_not_called()
        assert result.is_valid is True
        assert result.is_reachable is True  # Assumed reachable

    def test_normalized_url_in_result(self):
        """Test that result contains normalized URL."""
        result = validate_url("example.com", check_reachability=False)

        assert result.normalized_url.startswith("https://")

    def test_has_warnings_property(self):
        """Test has_warnings property."""
        result_no_warning = ValidationResult(
            is_valid=True,
            is_reachable=True,
            normalized_url="https://example.com",
        )
        assert result_no_warning.has_warnings is False

        result_with_warning = ValidationResult(
            is_valid=True,
            is_reachable=False,
            normalized_url="https://example.com",
            warning_message="Test warning",
        )
        assert result_with_warning.has_warnings is True


class TestValidateUrlBatch:
    """Tests for batch URL validation."""

    @patch('app.services.url_validator.validate_url')
    def test_validates_all_urls(self, mock_validate):
        """Test that all URLs in batch are validated."""
        mock_validate.return_value = ValidationResult(
            is_valid=True,
            is_reachable=True,
            normalized_url="https://example.com",
        )

        urls = ["https://a.com", "https://b.com", "https://c.com"]
        results = validate_url_batch(urls)

        assert len(results) == 3
        assert mock_validate.call_count == 3

    @patch('app.services.url_validator.validate_url')
    def test_batch_respects_reachability_flag(self, mock_validate):
        """Test that batch validation respects reachability flag."""
        mock_validate.return_value = ValidationResult(
            is_valid=True,
            is_reachable=True,
            normalized_url="https://example.com",
        )

        validate_url_batch(["https://example.com"], check_reachability=False)

        mock_validate.assert_called_with("https://example.com", False)


class TestUrlValidatorIntegration:
    """Integration tests using real (but safe) URLs."""

    def test_normalize_preserves_valid_url(self):
        """Test that normalization doesn't break valid URLs."""
        valid_urls = [
            "https://example.com",
            "https://www.example.com",
            "https://example.com/path",
            "https://example.com:8080/path",
            "http://localhost:5000",
        ]
        for url in valid_urls:
            result = normalize_url(url)
            is_valid, _ = validate_url_format(result)
            assert is_valid, f"URL became invalid after normalization: {url}"

    def test_edge_case_urls(self):
        """Test edge case URLs."""
        # URL with unusual but valid characters
        is_valid, _ = validate_url_format("https://example.com/path-with-dash_and_underscore")
        assert is_valid

        # URL with query params
        is_valid, _ = validate_url_format("https://example.com?foo=bar&baz=qux")
        assert is_valid

        # URL with fragment
        is_valid, _ = validate_url_format("https://example.com#section")
        assert is_valid

    def test_clearly_invalid_urls(self):
        """Test clearly invalid URLs are rejected."""
        invalid_urls = [
            "",
            "   ",
            "just-text",
            "ftp://example.com",  # Not http/https
            "javascript:alert(1)",
            "data:text/html,<h1>hello</h1>",
        ]
        for url in invalid_urls:
            is_valid, error = validate_url_format(url)
            assert not is_valid, f"URL should be invalid: {url}"


class TestTimeoutConfiguration:
    """Tests for timeout configuration."""

    def test_timeout_is_10_seconds(self):
        """Test that timeout is set to 10 seconds as per spec."""
        assert REACHABILITY_TIMEOUT == 10
