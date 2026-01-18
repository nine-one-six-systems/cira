"""URL validation and reachability checking service.

Provides URL format validation and reachability checks before accepting
company website URLs for analysis.
"""

import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException, Timeout, ConnectionError


# Timeout for HEAD requests (in seconds)
REACHABILITY_TIMEOUT = 10

# Common URL patterns
URL_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
    r'localhost|'  # localhost
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP address
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


@dataclass
class ValidationResult:
    """Result of URL validation and reachability check."""

    is_valid: bool
    is_reachable: bool
    normalized_url: str
    error_message: Optional[str] = None
    warning_message: Optional[str] = None
    http_status: Optional[int] = None

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings."""
        return self.warning_message is not None


def normalize_url(url: str) -> str:
    """
    Normalize URL by adding scheme if missing and cleaning up.

    Args:
        url: The URL to normalize.

    Returns:
        Normalized URL with https:// prefix if no scheme present.
    """
    url = url.strip()

    # Add scheme if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Parse and reconstruct to normalize
    parsed = urlparse(url)

    # Ensure there's a path (at least /)
    path = parsed.path or '/'

    # Reconstruct URL
    normalized = f"{parsed.scheme}://{parsed.netloc}{path}"

    # Add query string if present
    if parsed.query:
        normalized += f"?{parsed.query}"

    return normalized


def validate_url_format(url: str) -> tuple[bool, str | None]:
    """
    Validate URL format.

    Args:
        url: URL string to validate.

    Returns:
        Tuple of (is_valid, error_message).
    """
    if not url:
        return False, "URL is required"

    # Normalize first
    normalized = normalize_url(url)

    # Check pattern
    if not URL_PATTERN.match(normalized):
        return False, f"Invalid URL format: {url}"

    # Parse for additional validation
    try:
        parsed = urlparse(normalized)

        if not parsed.netloc:
            return False, "URL must include a domain"

        # Check for valid domain structure
        domain = parsed.netloc.split(':')[0]  # Remove port
        if not domain or domain.startswith('.') or domain.endswith('.'):
            return False, "Invalid domain in URL"

        # Check domain has at least one dot (unless localhost)
        if domain != 'localhost' and '.' not in domain:
            return False, "Domain must include a TLD (e.g., .com, .org)"

    except Exception as e:
        return False, f"URL parsing error: {str(e)}"

    return True, None


def check_url_reachability(url: str) -> tuple[bool, int | None, str | None]:
    """
    Check if URL is reachable via HEAD request.

    Args:
        url: URL to check (should be normalized).

    Returns:
        Tuple of (is_reachable, http_status, error_message).
    """
    try:
        # Use HEAD request to minimize data transfer
        response = requests.head(
            url,
            timeout=REACHABILITY_TIMEOUT,
            allow_redirects=True,
            headers={
                'User-Agent': 'CIRA Bot/1.0 (+https://cira.example.com/bot)',
                'Accept': '*/*',
            }
        )

        # Consider 2xx and 3xx as reachable
        if response.status_code < 400:
            return True, response.status_code, None

        # Some servers don't support HEAD, try GET
        if response.status_code in (405, 501):
            response = requests.get(
                url,
                timeout=REACHABILITY_TIMEOUT,
                allow_redirects=True,
                stream=True,  # Don't download body
                headers={
                    'User-Agent': 'CIRA Bot/1.0 (+https://cira.example.com/bot)',
                    'Accept': '*/*',
                }
            )
            if response.status_code < 400:
                return True, response.status_code, None

        return False, response.status_code, f"Server returned HTTP {response.status_code}"

    except Timeout:
        return False, None, f"Connection timed out after {REACHABILITY_TIMEOUT} seconds"

    except ConnectionError as e:
        error_msg = str(e)
        if "Name or service not known" in error_msg or "getaddrinfo failed" in error_msg:
            return False, None, "Domain could not be resolved (DNS lookup failed)"
        elif "Connection refused" in error_msg:
            return False, None, "Connection refused by server"
        else:
            return False, None, f"Connection error: {error_msg[:100]}"

    except RequestException as e:
        return False, None, f"Request failed: {str(e)[:100]}"


def validate_url(url: str, check_reachability: bool = True) -> ValidationResult:
    """
    Validate URL format and optionally check reachability.

    This is the main entry point for URL validation. It:
    1. Normalizes the URL (adds https:// if needed)
    2. Validates the URL format
    3. Optionally checks if the URL is reachable

    Unreachable URLs produce warnings, not errors, allowing the user
    to proceed if they're confident the URL is correct.

    Args:
        url: URL string to validate.
        check_reachability: Whether to perform reachability check.

    Returns:
        ValidationResult with validation status and any messages.
    """
    # Normalize URL
    normalized = normalize_url(url)

    # Validate format
    is_valid, error_message = validate_url_format(normalized)

    if not is_valid:
        return ValidationResult(
            is_valid=False,
            is_reachable=False,
            normalized_url=normalized,
            error_message=error_message,
        )

    # Skip reachability check if not requested
    if not check_reachability:
        return ValidationResult(
            is_valid=True,
            is_reachable=True,  # Assume reachable
            normalized_url=normalized,
        )

    # Check reachability
    is_reachable, http_status, reach_error = check_url_reachability(normalized)

    if is_reachable:
        return ValidationResult(
            is_valid=True,
            is_reachable=True,
            normalized_url=normalized,
            http_status=http_status,
        )

    # URL is valid but not reachable - return warning, not error
    return ValidationResult(
        is_valid=True,  # Format is valid
        is_reachable=False,
        normalized_url=normalized,
        warning_message=f"URL may not be reachable: {reach_error}",
        http_status=http_status,
    )


def validate_url_batch(urls: list[str], check_reachability: bool = True) -> list[ValidationResult]:
    """
    Validate a batch of URLs.

    Args:
        urls: List of URL strings to validate.
        check_reachability: Whether to perform reachability checks.

    Returns:
        List of ValidationResult for each URL.
    """
    return [validate_url(url, check_reachability) for url in urls]
