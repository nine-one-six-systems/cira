"""Security middleware for CIRA application.

Implements security headers and protections per OWASP recommendations:
- NFR-SEC-001: API keys in environment only (enforced in config)
- NFR-SEC-002: Input validation (handled by Pydantic schemas)
- NFR-SEC-003: ORM prevents SQLi (SQLAlchemy parameterized queries)
- NFR-SEC-005: Secure download headers
- XSS prevention headers
"""

from flask import Flask, request, Response
from functools import wraps
import re
import html
from typing import Any


# Security header constants
SECURITY_HEADERS = {
    # Prevent MIME type sniffing
    'X-Content-Type-Options': 'nosniff',
    # Prevent clickjacking
    'X-Frame-Options': 'DENY',
    # XSS Protection (legacy but still useful for older browsers)
    'X-XSS-Protection': '1; mode=block',
    # Referrer policy - don't leak URLs
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    # Permissions policy - restrict browser features
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
    # Content Security Policy - restrict resource loading
    'Content-Security-Policy': (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'"
    ),
}

# Additional headers for HTTPS in production
HTTPS_HEADERS = {
    # HSTS - force HTTPS
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
}


def init_security_middleware(app: Flask) -> None:
    """
    Initialize security middleware for the Flask application.

    Adds security headers to all responses and implements
    additional security protections.

    Args:
        app: Flask application instance
    """
    @app.after_request
    def add_security_headers(response: Response) -> Response:
        """Add security headers to every response."""
        # Add standard security headers
        for header, value in SECURITY_HEADERS.items():
            # Don't override if already set
            if header not in response.headers:
                response.headers[header] = value

        # Add HTTPS headers in production
        if not app.debug and not app.testing:
            for header, value in HTTPS_HEADERS.items():
                if header not in response.headers:
                    response.headers[header] = value

        # Add cache control for API responses (unless already set)
        if 'Cache-Control' not in response.headers:
            if request.path.startswith('/api/'):
                response.headers['Cache-Control'] = 'no-store, max-age=0'

        return response

    @app.before_request
    def validate_content_type():
        """Validate Content-Type header for POST/PUT/PATCH requests."""
        if request.method in ['POST', 'PUT', 'PATCH']:
            # Skip content type check for file uploads
            if request.content_type and 'multipart/form-data' in request.content_type:
                return None

            # For JSON endpoints, ensure proper content type
            if request.path.startswith('/api/') and request.data:
                content_type = request.content_type or ''
                if 'application/json' not in content_type and 'multipart/form-data' not in content_type:
                    # Allow requests without body
                    if len(request.data) > 0:
                        return {
                            'success': False,
                            'error': {
                                'code': 'VALIDATION_ERROR',
                                'message': 'Content-Type must be application/json for API requests'
                            }
                        }, 415

        return None

    app.logger.info('Security middleware initialized')


def sanitize_string(value: str) -> str:
    """
    Sanitize a string value to prevent XSS attacks.

    Args:
        value: String to sanitize

    Returns:
        Sanitized string with HTML entities escaped
    """
    if not isinstance(value, str):
        return value

    # HTML escape to prevent XSS
    return html.escape(value, quote=True)


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe download.

    Prevents directory traversal and removes dangerous characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for Content-Disposition header
    """
    if not filename:
        return 'download'

    # Remove directory components
    filename = filename.replace('/', '_').replace('\\', '_')

    # Remove null bytes and other control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)

    # Remove quotes and other problematic characters
    filename = re.sub(r'["\']', '', filename)

    # Limit length
    if len(filename) > 200:
        # Preserve extension if present
        if '.' in filename:
            name, ext = filename.rsplit('.', 1)
            filename = name[:195] + '.' + ext[:4]
        else:
            filename = filename[:200]

    # Ensure we have something
    if not filename or filename.isspace():
        return 'download'

    return filename


def validate_url_param(url: str) -> tuple[bool, str]:
    """
    Validate a URL parameter to prevent SSRF and open redirect attacks.

    Args:
        url: URL to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, 'URL is required'

    # Basic scheme check
    url_lower = url.lower()
    if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
        return False, 'URL must start with http:// or https://'

    # Prevent local/private network access (SSRF protection)
    blocked_patterns = [
        r'localhost',
        r'127\.',
        r'10\.',
        r'172\.(1[6-9]|2[0-9]|3[01])\.',
        r'192\.168\.',
        r'::1',
        r'0\.0\.0\.0',
        r'169\.254\.',  # Link-local
        r'\.local$',
        r'\.internal$',
    ]

    for pattern in blocked_patterns:
        if re.search(pattern, url_lower):
            return False, 'URL points to a blocked network address'

    return True, ''


def require_json(f):
    """
    Decorator to require JSON content type for a route.

    Args:
        f: Route function to wrap

    Returns:
        Wrapped function that validates Content-Type
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.content_type or ''
            if 'application/json' not in content_type:
                return {
                    'success': False,
                    'error': {
                        'code': 'VALIDATION_ERROR',
                        'message': 'Content-Type must be application/json'
                    }
                }, 415
        return f(*args, **kwargs)
    return decorated_function


def get_secure_download_headers(filename: str, content_type: str) -> dict[str, str]:
    """
    Get secure headers for file downloads.

    Args:
        filename: Sanitized filename
        content_type: MIME type of the file

    Returns:
        Dictionary of headers for secure download
    """
    safe_filename = sanitize_filename(filename)

    return {
        'Content-Type': content_type,
        'Content-Disposition': f'attachment; filename="{safe_filename}"',
        'X-Content-Type-Options': 'nosniff',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Expires': '0',
        'X-Frame-Options': 'DENY',
    }
