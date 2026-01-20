"""Integration tests for Export API endpoint.

Tests GET /api/v1/companies/:id/export endpoint per API-08 requirement.
Verifies HTTP behavior, content types, headers, and parameter handling.

Requirements covered:
- API-08: Export endpoint
- EXP-01: Markdown export
- EXP-02: Word export
- EXP-03: PDF export
- EXP-04: JSON export
"""

import json
import pytest
from io import BytesIO
from datetime import datetime, timezone

from docx import Document
from PyPDF2 import PdfReader

from app import db
from app.models.company import Company, Analysis, Entity, Page, TokenUsage
from app.models.enums import (
    CompanyStatus,
    AnalysisMode,
    EntityType,
    PageType,
    ApiCallType,
)


def create_completed_company_with_name(app, name: str = "Integration Test Corp") -> str:
    """Create a completed company with analysis data and return its ID."""
    with app.app_context():
        company = Company(
            company_name=name,
            website_url="https://integrationtest.com",
            industry="Technology",
            analysis_mode=AnalysisMode.THOROUGH,
            status=CompanyStatus.COMPLETED,
            total_tokens_used=10000,
            estimated_cost=0.05,
            completed_at=datetime.now(timezone.utc),
        )
        db.session.add(company)
        db.session.flush()

        # Add analysis version 1
        analysis1 = Analysis(
            company_id=company.id,
            version_number=1,
            executive_summary="Version 1: Integration Test Corp is a technology company.",
            full_analysis={
                "companyOverview": {
                    "content": "Version 1 company overview.",
                    "sources": ["https://integrationtest.com/about"],
                    "confidence": 0.9,
                },
                "businessModel": {
                    "content": "B2B services model.",
                    "sources": [],
                    "confidence": 0.85,
                },
                "teamLeadership": {"content": "Small team.", "sources": [], "confidence": 0.8},
                "marketPosition": {"content": "Niche market.", "sources": [], "confidence": 0.75},
                "keyInsights": {"content": "Growing.", "sources": [], "confidence": 0.8},
                "redFlags": {"content": "None identified.", "sources": [], "confidence": 0.9},
            },
        )
        db.session.add(analysis1)

        # Add analysis version 2
        analysis2 = Analysis(
            company_id=company.id,
            version_number=2,
            executive_summary="Version 2: Updated executive summary.",
            full_analysis={
                "companyOverview": {"content": "Version 2 overview.", "sources": [], "confidence": 0.95},
                "businessModel": {"content": "Updated B2B model.", "sources": [], "confidence": 0.9},
            },
        )
        db.session.add(analysis2)

        # Add entities
        entity = Entity(
            company_id=company.id,
            entity_type=EntityType.PERSON,
            entity_value="Test Person",
            context_snippet="Test Person is the CEO.",
            source_url="https://integrationtest.com/team",
            confidence_score=0.95,
            extra_data={"role": "CEO"},
        )
        db.session.add(entity)

        # Add pages
        page = Page(
            company_id=company.id,
            url="https://integrationtest.com/about",
            page_type=PageType.ABOUT,
            is_external=False,
        )
        db.session.add(page)

        # Add token usage
        usage = TokenUsage(
            company_id=company.id,
            api_call_type=ApiCallType.ANALYSIS,
            input_tokens=5000,
            output_tokens=5000,
        )
        db.session.add(usage)

        db.session.commit()
        return company.id


class TestExportFormatResponses:
    """Tests for export format response types (API-08).

    Verifies that each export format returns the correct content-type
    and appropriate content magic bytes.
    """

    def test_markdown_response_content_type(self, client, app):
        """Test Markdown export returns correct content-type (API-08, EXP-01).

        Verifies:
        - Status code 200
        - Content-Type contains 'text/markdown'
        - Response body starts with '# ' (markdown heading)
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 200
        assert "text/markdown" in response.content_type
        content = response.data.decode("utf-8")
        assert content.startswith("# "), f"Expected markdown heading, got: {content[:50]}"

    def test_word_response_content_type(self, client, app):
        """Test Word export returns correct content-type (API-08, EXP-02).

        Verifies:
        - Status code 200
        - Content-Type contains 'openxmlformats'
        - Response body starts with PK (ZIP/DOCX magic bytes)
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=word")

        assert response.status_code == 200
        assert "openxmlformats" in response.content_type
        # DOCX files are ZIP archives and start with 'PK' (0x50, 0x4B)
        assert response.data[:2] == b"PK", "Word document should start with PK magic bytes"

    def test_pdf_response_content_type(self, client, app):
        """Test PDF export returns correct content-type (API-08, EXP-03).

        Verifies:
        - Status code 200
        - Content-Type is 'application/pdf'
        - Response body starts with %PDF (PDF magic bytes)
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=pdf")

        assert response.status_code == 200
        assert "application/pdf" in response.content_type
        assert response.data[:4] == b"%PDF", "PDF document should start with %PDF magic bytes"

    def test_json_response_content_type(self, client, app):
        """Test JSON export returns correct content-type (API-08, EXP-04).

        Verifies:
        - Status code 200
        - Content-Type contains 'application/json'
        - Response body is valid JSON with company and analysis keys
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json")

        assert response.status_code == 200
        assert "application/json" in response.content_type
        data = json.loads(response.data.decode("utf-8"))
        assert "company" in data
        assert "analysis" in data


class TestExportContentDisposition:
    """Tests for Content-Disposition header in export responses (API-08).

    Verifies filename handling and extension matching.
    """

    def test_filename_includes_company_name(self, client, app):
        """Test filename in Content-Disposition includes company name (API-08).

        Verifies:
        - Content-Disposition header is present
        - Filename contains sanitized company name
        - Filename ends with .md for markdown format
        """
        company_id = create_completed_company_with_name(app, "Acme Corp")

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 200
        assert "Content-Disposition" in response.headers
        disposition = response.headers["Content-Disposition"]
        assert "Acme" in disposition
        assert ".md" in disposition

    def test_filename_extension_matches_format(self, client, app):
        """Test filename extension matches requested format (API-08).

        Verifies each format returns correct extension:
        - markdown -> .md
        - word -> .docx
        - pdf -> .pdf
        - json -> .json
        """
        company_id = create_completed_company_with_name(app)

        format_extensions = [
            ("markdown", ".md"),
            ("word", ".docx"),
            ("pdf", ".pdf"),
            ("json", ".json"),
        ]

        for format_name, expected_ext in format_extensions:
            response = client.get(f"/api/v1/companies/{company_id}/export?format={format_name}")
            assert response.status_code == 200, f"Failed for format {format_name}"
            disposition = response.headers.get("Content-Disposition", "")
            assert expected_ext in disposition, f"Expected {expected_ext} in disposition for {format_name}"

    def test_filename_sanitized_for_special_chars(self, client, app):
        """Test filename is sanitized for special characters (API-08).

        Verifies that special characters like '/' and '&' are handled safely.
        """
        company_id = create_completed_company_with_name(app, "Test / Company & Inc.")

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 200
        disposition = response.headers.get("Content-Disposition", "")
        # Filename should not contain raw / or \ characters
        assert "/" not in disposition.split("filename=")[-1].replace("/", "")
        assert "\\" not in disposition


class TestExportSecurityHeaders:
    """Tests for security headers in export responses (API-08).

    Verifies NFR-SEC-005 secure download headers are present.
    """

    def test_nosniff_header_present(self, client, app):
        """Test X-Content-Type-Options header is present (API-08, NFR-SEC-005).

        Verifies X-Content-Type-Options is set to 'nosniff'.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_cache_control_header_present(self, client, app):
        """Test Cache-Control header is present (API-08, NFR-SEC-005).

        Verifies Cache-Control contains 'no-cache' or 'no-store'.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=pdf")

        assert response.status_code == 200
        cache_control = response.headers.get("Cache-Control", "")
        assert "no-cache" in cache_control or "no-store" in cache_control

    def test_all_formats_have_security_headers(self, client, app):
        """Test all export formats include security headers (API-08, NFR-SEC-005).

        Verifies both X-Content-Type-Options and Cache-Control are present
        for all four export formats.
        """
        company_id = create_completed_company_with_name(app)

        for format_name in ["markdown", "word", "pdf", "json"]:
            response = client.get(f"/api/v1/companies/{company_id}/export?format={format_name}")
            assert response.status_code == 200, f"Failed for format {format_name}"
            assert response.headers.get("X-Content-Type-Options") == "nosniff", \
                f"Missing nosniff header for {format_name}"
            cache_control = response.headers.get("Cache-Control", "")
            assert "no-cache" in cache_control or "no-store" in cache_control, \
                f"Missing cache control for {format_name}"


class TestExportVersionParameter:
    """Tests for version parameter in export endpoint (API-08).

    Verifies selecting specific analysis versions for export.
    """

    def test_export_latest_version_by_default(self, client, app):
        """Test export returns latest version by default (API-08).

        Verifies that without version parameter, the latest analysis is returned.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json")

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        # Company was created with version 1 and 2, latest should be 2
        assert data["analysis"]["versionNumber"] == 2

    def test_export_specific_version_1(self, client, app):
        """Test exporting specific version 1 (API-08).

        Verifies version=1 returns version 1 analysis.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json&version=1")

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert data["analysis"]["versionNumber"] == 1

    def test_export_specific_version_2(self, client, app):
        """Test exporting specific version 2 (API-08).

        Verifies version=2 returns version 2 analysis.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json&version=2")

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert data["analysis"]["versionNumber"] == 2

    def test_export_nonexistent_version_returns_404(self, client, app):
        """Test exporting non-existent version returns 404 (API-08).

        Verifies proper error handling for invalid version numbers.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json&version=99")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "NOT_FOUND"


class TestExportIncludeRawDataParameter:
    """Tests for includeRawData parameter in JSON export (API-08).

    Verifies entities and pages inclusion/exclusion based on parameter.
    """

    def test_json_includes_entities_by_default(self, client, app):
        """Test JSON export includes entities by default (API-08).

        Verifies 'entities' array is present in response.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json")

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert "entities" in data
        assert isinstance(data["entities"], list)

    def test_json_includes_pages_by_default(self, client, app):
        """Test JSON export includes pages by default (API-08).

        Verifies 'pages' array is present in response.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json")

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert "pages" in data
        assert isinstance(data["pages"], list)

    def test_json_excludes_entities_when_false(self, client, app):
        """Test JSON export excludes entities when includeRawData=false (API-08).

        Verifies 'entities' is NOT in response.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(
            f"/api/v1/companies/{company_id}/export?format=json&includeRawData=false"
        )

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert "entities" not in data

    def test_json_excludes_pages_when_false(self, client, app):
        """Test JSON export excludes pages when includeRawData=false (API-08).

        Verifies 'pages' is NOT in response.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(
            f"/api/v1/companies/{company_id}/export?format=json&includeRawData=false"
        )

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert "pages" not in data


class TestExportStatusValidation:
    """Tests for company status validation in export endpoint (API-08).

    Verifies only COMPLETED companies can be exported (returns 422 otherwise).
    """

    def test_export_pending_company_returns_422(self, client, app):
        """Test export for PENDING company returns 422 (API-08).

        Verifies proper rejection with CONFLICT error code.
        """
        with app.app_context():
            company = Company(
                company_name="Pending Corp",
                website_url="https://pending.com",
                status=CompanyStatus.PENDING,
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 422
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "CONFLICT"

    def test_export_in_progress_company_returns_422(self, client, app):
        """Test export for IN_PROGRESS company returns 422 (API-08).

        Verifies proper rejection with CONFLICT error code.
        """
        with app.app_context():
            company = Company(
                company_name="InProgress Corp",
                website_url="https://inprogress.com",
                status=CompanyStatus.IN_PROGRESS,
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 422
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "CONFLICT"

    def test_export_paused_company_returns_422(self, client, app):
        """Test export for PAUSED company returns 422 (API-08).

        Verifies proper rejection with CONFLICT error code.
        """
        with app.app_context():
            company = Company(
                company_name="Paused Corp",
                website_url="https://paused.com",
                status=CompanyStatus.PAUSED,
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 422
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "CONFLICT"

    def test_export_failed_company_returns_422(self, client, app):
        """Test export for FAILED company returns 422 (API-08).

        Verifies proper rejection with CONFLICT error code.
        """
        with app.app_context():
            company = Company(
                company_name="Failed Corp",
                website_url="https://failed.com",
                status=CompanyStatus.FAILED,
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 422
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "CONFLICT"

    def test_export_completed_company_succeeds(self, client, app):
        """Test export for COMPLETED company succeeds (API-08).

        Verifies COMPLETED status allows export.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 200


class TestExportCaseInsensitivity:
    """Tests for case-insensitive format parameter handling (API-08).

    Verifies the format parameter accepts mixed case values.
    """

    def test_uppercase_format_accepted(self, client, app):
        """Test uppercase format parameter is accepted (API-08).

        Verifies format=MARKDOWN returns 200.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=MARKDOWN")

        assert response.status_code == 200
        assert "text/markdown" in response.content_type

    def test_mixed_case_format_accepted(self, client, app):
        """Test mixed case format parameter is accepted (API-08).

        Verifies format=Pdf returns 200 with correct content-type.
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=Pdf")

        assert response.status_code == 200
        assert "application/pdf" in response.content_type

    def test_word_format_variations(self, client, app):
        """Test Word format accepts various case variations (API-08).

        Verifies 'word', 'WORD', and 'Word' all return 200 with docx content-type.
        """
        company_id = create_completed_company_with_name(app)

        for format_case in ["word", "WORD", "Word"]:
            response = client.get(f"/api/v1/companies/{company_id}/export?format={format_case}")
            assert response.status_code == 200, f"Failed for format={format_case}"
            assert "openxmlformats" in response.content_type, f"Wrong content-type for format={format_case}"


class TestExportErrorResponses:
    """Tests for error response handling in export endpoint (API-08).

    Verifies proper error codes and messages for invalid requests.
    """

    def test_missing_format_returns_400(self, client, app):
        """Test missing format parameter returns 400 (API-08).

        Verifies:
        - Status code 400
        - Error code is VALIDATION_ERROR
        - Error message mentions 'format'
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "format" in data["error"]["message"].lower()

    def test_invalid_format_returns_400(self, client, app):
        """Test invalid format value returns 400 (API-08).

        Verifies:
        - Status code 400
        - Error code is VALIDATION_ERROR
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=xlsx")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_nonexistent_company_returns_404(self, client):
        """Test export for non-existent company returns 404 (API-08).

        Verifies:
        - Status code 404
        - Error code is NOT_FOUND
        """
        response = client.get("/api/v1/companies/nonexistent-uuid/export?format=markdown")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "NOT_FOUND"

    def test_invalid_version_format_returns_400(self, client, app):
        """Test invalid version parameter format returns 400 (API-08).

        Verifies:
        - Status code 400
        - Error code is VALIDATION_ERROR
        - Error message mentions version
        """
        company_id = create_completed_company_with_name(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json&version=abc")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "version" in data["error"]["message"].lower()
