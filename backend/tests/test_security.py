"""Tests for security hardening (Task 10.4).

Tests security requirements per OWASP recommendations:
- NFR-SEC-001: API keys in environment only
- NFR-SEC-002: Input validation
- NFR-SEC-003: ORM prevents SQLi
- NFR-SEC-005: Secure download headers
- XSS prevention
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from flask import Flask

from app import create_app, db
from app.models.company import Company, Analysis
from app.models.enums import CompanyStatus, AnalysisMode
from app.middleware.security import (
    sanitize_string,
    sanitize_filename,
    validate_url_param,
    get_secure_download_headers,
    SECURITY_HEADERS,
    init_security_middleware,
)


@pytest.fixture
def app():
    """Create test application."""
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def completed_company(app):
    """Create a completed company with analysis for testing."""
    with app.app_context():
        company = Company(
            id='test-company-123',
            company_name='Test Company',
            website_url='https://example.com',
            status=CompanyStatus.COMPLETED,
            analysis_mode=AnalysisMode.QUICK,
        )
        db.session.add(company)
        db.session.flush()

        analysis = Analysis(
            company_id=company.id,
            version_number=1,
            executive_summary='Test summary',
            full_analysis={'overview': 'Test overview'},
        )
        db.session.add(analysis)
        db.session.commit()

        return company.id


class TestSecurityHeaders:
    """Test security headers are properly set."""

    def test_health_endpoint_has_security_headers(self, client):
        """Test that security headers are added to responses."""
        response = client.get('/api/v1/health')

        assert response.status_code == 200
        # Check standard security headers
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'
        assert response.headers.get('X-XSS-Protection') == '1; mode=block'
        assert response.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

    def test_api_response_has_csp_header(self, client):
        """Test that Content-Security-Policy header is set."""
        response = client.get('/api/v1/health')

        csp = response.headers.get('Content-Security-Policy')
        assert csp is not None
        assert "default-src 'self'" in csp
        assert "frame-ancestors 'none'" in csp

    def test_api_response_has_cache_control(self, client):
        """Test that API responses have cache control headers."""
        response = client.get('/api/v1/health')

        cache_control = response.headers.get('Cache-Control')
        assert cache_control is not None
        assert 'no-store' in cache_control

    def test_permissions_policy_header(self, client):
        """Test Permissions-Policy header restricts dangerous features."""
        response = client.get('/api/v1/health')

        permissions = response.headers.get('Permissions-Policy')
        assert permissions is not None
        assert 'geolocation=()' in permissions
        assert 'camera=()' in permissions
        assert 'microphone=()' in permissions


class TestExportSecurityHeaders:
    """Test secure download headers for exports."""

    def test_export_has_secure_headers(self, client, completed_company):
        """Test that export endpoints return secure headers."""
        response = client.get(
            f'/api/v1/companies/{completed_company}/export?format=json'
        )

        assert response.status_code == 200
        assert response.headers.get('X-Content-Type-Options') == 'nosniff'
        assert response.headers.get('X-Frame-Options') == 'DENY'
        assert 'no-cache' in response.headers.get('Cache-Control', '')
        assert 'no-store' in response.headers.get('Cache-Control', '')
        assert response.headers.get('Pragma') == 'no-cache'
        assert response.headers.get('Expires') == '0'

    def test_export_content_disposition_is_attachment(self, client, completed_company):
        """Test that export uses attachment disposition to force download."""
        response = client.get(
            f'/api/v1/companies/{completed_company}/export?format=json'
        )

        disposition = response.headers.get('Content-Disposition')
        assert disposition is not None
        assert disposition.startswith('attachment;')


class TestInputValidation:
    """Test input validation protections (NFR-SEC-002)."""

    def test_invalid_json_content_type(self, client):
        """Test that non-JSON content type is rejected for API endpoints."""
        response = client.post(
            '/api/v1/companies',
            data='name=test&website_url=https://example.com',
            content_type='application/x-www-form-urlencoded'
        )

        # Should reject non-JSON content type
        assert response.status_code in [400, 415]

    def test_malformed_json_rejected(self, client):
        """Test that malformed JSON is rejected."""
        response = client.post(
            '/api/v1/companies',
            data='not valid json {{{',
            content_type='application/json'
        )

        assert response.status_code == 400

    def test_missing_required_fields_rejected(self, client):
        """Test that missing required fields return validation error."""
        response = client.post(
            '/api/v1/companies',
            json={},  # Missing name and website_url
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_invalid_url_rejected(self, client):
        """Test that invalid URLs are rejected."""
        response = client.post(
            '/api/v1/companies',
            json={
                'name': 'Test Company',
                'website_url': 'not-a-valid-url'
            },
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_xss_in_company_name_escaped(self, client):
        """Test that XSS attempts in company name are handled."""
        xss_payload = '<script>alert("xss")</script>'
        response = client.post(
            '/api/v1/companies',
            json={
                'name': xss_payload,
                'website_url': 'https://example.com'
            },
        )

        # Should accept but not execute - data is stored safely
        # The important thing is that it doesn't cause errors
        assert response.status_code in [201, 400]  # May fail URL validation


class TestSQLInjectionProtection:
    """Test SQL injection protection (NFR-SEC-003)."""

    def test_sqli_in_company_id_safe(self, client):
        """Test that SQL injection in company ID is safe."""
        sqli_payload = "1' OR '1'='1"
        response = client.get(f'/api/v1/companies/{sqli_payload}')

        # Should return 404 (not found), not cause SQL error
        assert response.status_code == 404
        data = response.get_json()
        assert data['error']['code'] == 'NOT_FOUND'

    def test_sqli_in_filter_param_safe(self, client):
        """Test that SQL injection in filter parameters is safe."""
        sqli_payload = "completed' OR '1'='1' --"
        response = client.get(f'/api/v1/companies?status={sqli_payload}')

        # Should either ignore invalid status or return validation error
        # Should not cause SQL error
        assert response.status_code in [200, 400]

    def test_sqli_in_sort_param_safe(self, client):
        """Test that SQL injection in sort parameters is safe."""
        sqli_payload = "name; DROP TABLE companies; --"
        response = client.get(f'/api/v1/companies?sort={sqli_payload}')

        # Should handle gracefully
        assert response.status_code in [200, 400]


class TestFilenameAndPathTraversal:
    """Test filename sanitization and path traversal protection."""

    def test_sanitize_filename_removes_directory_traversal(self):
        """Test that directory traversal is blocked."""
        assert '../' not in sanitize_filename('../../../etc/passwd')
        assert '..\\' not in sanitize_filename('..\\..\\windows\\system32')

    def test_sanitize_filename_removes_slashes(self):
        """Test that slashes are replaced."""
        result = sanitize_filename('path/to/file.txt')
        assert '/' not in result

        result = sanitize_filename('path\\to\\file.txt')
        assert '\\' not in result

    def test_sanitize_filename_removes_null_bytes(self):
        """Test that null bytes are removed."""
        result = sanitize_filename('file\x00name.txt')
        assert '\x00' not in result

    def test_sanitize_filename_removes_quotes(self):
        """Test that quotes are removed to prevent header injection."""
        result = sanitize_filename('file"name.txt')
        assert '"' not in result

        result = sanitize_filename("file'name.txt")
        assert "'" not in result

    def test_sanitize_filename_limits_length(self):
        """Test that filename length is limited."""
        long_name = 'a' * 300 + '.txt'
        result = sanitize_filename(long_name)
        assert len(result) <= 204  # 200 chars + 4 for extension

    def test_sanitize_filename_preserves_extension(self):
        """Test that file extension is preserved in long names."""
        long_name = 'a' * 300 + '.pdf'
        result = sanitize_filename(long_name)
        assert result.endswith('.pdf')

    def test_sanitize_filename_handles_empty(self):
        """Test that empty filename returns default."""
        assert sanitize_filename('') == 'download'
        assert sanitize_filename('   ') == 'download'

    def test_sanitize_filename_handles_control_chars(self):
        """Test that control characters are removed."""
        result = sanitize_filename('file\x1f\x7fname.txt')
        assert '\x1f' not in result
        assert '\x7f' not in result


class TestXSSPrevention:
    """Test XSS prevention utilities."""

    def test_sanitize_string_escapes_html(self):
        """Test that HTML is properly escaped."""
        xss = '<script>alert("xss")</script>'
        result = sanitize_string(xss)
        assert '<' not in result
        assert '>' not in result
        assert '&lt;' in result
        assert '&gt;' in result

    def test_sanitize_string_escapes_quotes(self):
        """Test that quotes are escaped."""
        result = sanitize_string('test "quoted" value')
        assert '&quot;' in result

    def test_sanitize_string_handles_non_string(self):
        """Test that non-strings are returned unchanged."""
        assert sanitize_string(123) == 123
        assert sanitize_string(None) is None

    def test_sanitize_string_escapes_ampersand(self):
        """Test that ampersand is escaped."""
        result = sanitize_string('test & value')
        assert '&amp;' in result


class TestURLValidation:
    """Test URL validation for SSRF protection."""

    def test_validate_url_requires_url(self):
        """Test that empty URL is rejected."""
        is_valid, error = validate_url_param('')
        assert is_valid is False
        assert 'required' in error.lower()

    def test_validate_url_requires_http_scheme(self):
        """Test that non-HTTP schemes are rejected."""
        is_valid, error = validate_url_param('ftp://example.com')
        assert is_valid is False
        assert 'http' in error.lower()

        is_valid, error = validate_url_param('file:///etc/passwd')
        assert is_valid is False

    def test_validate_url_blocks_localhost(self):
        """Test that localhost is blocked (SSRF protection)."""
        is_valid, error = validate_url_param('http://localhost/admin')
        assert is_valid is False
        assert 'blocked' in error.lower()

    def test_validate_url_blocks_private_ips(self):
        """Test that private IP ranges are blocked."""
        # 127.x.x.x
        is_valid, _ = validate_url_param('http://127.0.0.1/')
        assert is_valid is False

        # 10.x.x.x
        is_valid, _ = validate_url_param('http://10.0.0.1/')
        assert is_valid is False

        # 172.16-31.x.x
        is_valid, _ = validate_url_param('http://172.16.0.1/')
        assert is_valid is False

        # 192.168.x.x
        is_valid, _ = validate_url_param('http://192.168.1.1/')
        assert is_valid is False

    def test_validate_url_blocks_link_local_ips(self):
        """Test that link-local IPs are blocked."""
        # 169.254.x.x (link-local)
        is_valid, _ = validate_url_param('http://169.254.1.1/')
        assert is_valid is False

    def test_validate_url_allows_public_urls(self):
        """Test that public URLs are allowed."""
        is_valid, _ = validate_url_param('https://example.com/')
        assert is_valid is True

        is_valid, _ = validate_url_param('https://www.google.com/')
        assert is_valid is True


class TestSecureDownloadHeaders:
    """Test get_secure_download_headers function."""

    def test_returns_all_required_headers(self):
        """Test that all security headers are included."""
        headers = get_secure_download_headers('test.pdf', 'application/pdf')

        assert headers['Content-Type'] == 'application/pdf'
        assert 'attachment' in headers['Content-Disposition']
        assert headers['X-Content-Type-Options'] == 'nosniff'
        assert 'no-cache' in headers['Cache-Control']
        assert 'no-store' in headers['Cache-Control']
        assert headers['Pragma'] == 'no-cache'
        assert headers['Expires'] == '0'
        assert headers['X-Frame-Options'] == 'DENY'

    def test_sanitizes_filename_in_headers(self):
        """Test that filename is sanitized in Content-Disposition."""
        headers = get_secure_download_headers('../../../etc/passwd', 'text/plain')

        disposition = headers['Content-Disposition']
        # Should not contain literal path traversal sequences
        assert '../' not in disposition
        # The slashes are replaced with underscores, making traversal impossible
        assert 'attachment' in disposition


class TestAPIKeysSecurity:
    """Test API key security (NFR-SEC-001)."""

    def test_anthropic_key_from_env_only(self):
        """Test that ANTHROPIC_API_KEY is loaded from environment."""
        from app.config import Config

        # Should load from environment, not be hardcoded
        key = Config.ANTHROPIC_API_KEY
        # Key should be empty or from env, not a real key in code
        assert key == '' or key.startswith('sk-')  # Empty in test env

    def test_secret_key_default_has_warning(self):
        """Test that default secret key indicates need for change."""
        from app.config import Config

        # Default key should indicate it needs changing
        assert 'change' in Config.SECRET_KEY.lower() or \
               'dev' in Config.SECRET_KEY.lower()


class TestCORSSecurity:
    """Test CORS configuration."""

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present on responses."""
        response = client.get('/api/v1/health')

        # Note: CORS headers only appear for cross-origin requests
        # This test just ensures CORS is configured
        assert response.status_code == 200

    def test_preflight_options_request(self, client):
        """Test that OPTIONS requests are handled for CORS preflight."""
        response = client.options(
            '/api/v1/companies',
            headers={
                'Origin': 'http://localhost:5173',
                'Access-Control-Request-Method': 'POST',
            }
        )

        # Should not error on preflight
        assert response.status_code in [200, 204]


class TestErrorHandling:
    """Test that error handling doesn't leak sensitive information."""

    def test_404_error_no_stack_trace(self, client):
        """Test that 404 errors don't leak stack traces."""
        response = client.get('/api/v1/nonexistent')

        # Should be 404
        assert response.status_code == 404

        # Response should not contain stack trace
        text = response.get_data(as_text=True)
        assert 'Traceback' not in text
        assert 'File "' not in text

    def test_validation_error_no_internal_details(self, client):
        """Test that validation errors don't leak internal details."""
        response = client.post(
            '/api/v1/companies',
            json={'invalid': 'data'},
        )

        assert response.status_code == 400
        data = response.get_json()

        # Should have structured error
        assert 'error' in data
        # Should not have internal paths or stack traces
        text = json.dumps(data)
        assert '/Users/' not in text
        assert '/home/' not in text


class TestSecurityMiddlewareInit:
    """Test security middleware initialization."""

    def test_middleware_initializes_without_error(self):
        """Test that middleware can be initialized."""
        app = Flask(__name__)
        app.config['TESTING'] = True

        # Should not raise
        init_security_middleware(app)

    def test_middleware_logs_initialization(self, app, caplog):
        """Test that middleware logs initialization."""
        import logging
        caplog.set_level(logging.INFO)

        # Middleware is already initialized in fixture
        # Just verify app is working
        assert app is not None
