"""Tests for Export API endpoints.

Tests GET /api/v1/companies/:id/export endpoint per spec 05-api-endpoints.md.
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


def create_completed_company(app) -> str:
    """Create a completed company with analysis data and return its ID."""
    with app.app_context():
        company = Company(
            company_name="Export Test Corp",
            website_url="https://exporttest.com",
            industry="Technology",
            analysis_mode=AnalysisMode.THOROUGH,
            status=CompanyStatus.COMPLETED,
            total_tokens_used=10000,
            estimated_cost=0.05,
            completed_at=datetime.now(timezone.utc),
        )
        db.session.add(company)
        db.session.flush()

        # Add analysis
        analysis = Analysis(
            company_id=company.id,
            version_number=1,
            executive_summary="Export Test Corp is a technology company specializing in exports.",
            full_analysis={
                "companyOverview": {
                    "content": "A test company for export functionality.",
                    "sources": ["https://exporttest.com/about"],
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
        db.session.add(analysis)

        # Add a second analysis version
        analysis2 = Analysis(
            company_id=company.id,
            version_number=2,
            executive_summary="Version 2 executive summary.",
            full_analysis={
                "companyOverview": {"content": "Updated overview.", "sources": [], "confidence": 0.9},
            },
        )
        db.session.add(analysis2)

        # Add entities
        entity = Entity(
            company_id=company.id,
            entity_type=EntityType.PERSON,
            entity_value="Test Person",
            context_snippet="Test Person is the CEO.",
            source_url="https://exporttest.com/team",
            confidence_score=0.95,
            extra_data={"role": "CEO"},
        )
        db.session.add(entity)

        # Add pages
        page = Page(
            company_id=company.id,
            url="https://exporttest.com/about",
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


class TestExportEndpointValidation:
    """Tests for export endpoint validation."""

    def test_export_requires_format_parameter(self, client, app):
        """Test export requires format query parameter."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "format" in data["error"]["message"].lower()

    def test_export_rejects_invalid_format(self, client, app):
        """Test export rejects invalid format parameter."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=invalid")

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"
        assert "invalid" in data["error"]["message"].lower()

    def test_export_nonexistent_company_returns_404(self, client):
        """Test export for non-existent company returns 404."""
        response = client.get("/api/v1/companies/nonexistent-id/export?format=markdown")

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "NOT_FOUND"

    def test_export_pending_company_returns_422(self, client, app):
        """Test export for pending company returns 422."""
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
        assert "pending" in data["error"]["message"].lower()

    def test_export_in_progress_company_returns_422(self, client, app):
        """Test export for in-progress company returns 422."""
        with app.app_context():
            company = Company(
                company_name="InProgress Corp",
                website_url="https://inprogress.com",
                status=CompanyStatus.IN_PROGRESS,
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f"/api/v1/companies/{company_id}/export?format=pdf")

        assert response.status_code == 422
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "CONFLICT"

    def test_export_failed_company_returns_422(self, client, app):
        """Test export for failed company returns 422."""
        with app.app_context():
            company = Company(
                company_name="Failed Corp",
                website_url="https://failed.com",
                status=CompanyStatus.FAILED,
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f"/api/v1/companies/{company_id}/export?format=word")

        assert response.status_code == 422
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "CONFLICT"


class TestMarkdownExportEndpoint:
    """Tests for Markdown export endpoint."""

    def test_markdown_export_returns_correct_content_type(self, client, app):
        """Test Markdown export returns correct Content-Type."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 200
        assert "text/markdown" in response.content_type

    def test_markdown_export_returns_correct_disposition(self, client, app):
        """Test Markdown export returns Content-Disposition header."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 200
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert ".md" in response.headers["Content-Disposition"]

    def test_markdown_export_content(self, client, app):
        """Test Markdown export contains expected content."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 200
        content = response.data.decode("utf-8")
        assert "Export Test Corp - Intelligence Brief" in content
        assert "Executive Summary" in content


class TestWordExportEndpoint:
    """Tests for Word (.docx) export endpoint."""

    def test_word_export_returns_correct_content_type(self, client, app):
        """Test Word export returns correct Content-Type."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=word")

        assert response.status_code == 200
        assert "openxmlformats" in response.content_type

    def test_word_export_returns_correct_disposition(self, client, app):
        """Test Word export returns Content-Disposition header."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=word")

        assert response.status_code == 200
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert ".docx" in response.headers["Content-Disposition"]

    def test_word_export_is_valid_docx(self, client, app):
        """Test Word export is a valid .docx file."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=word")

        assert response.status_code == 200
        # Should be able to open with python-docx
        doc = Document(BytesIO(response.data))
        assert doc is not None
        assert len(doc.paragraphs) > 0


class TestPdfExportEndpoint:
    """Tests for PDF export endpoint."""

    def test_pdf_export_returns_correct_content_type(self, client, app):
        """Test PDF export returns correct Content-Type."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=pdf")

        assert response.status_code == 200
        assert "application/pdf" in response.content_type

    def test_pdf_export_returns_correct_disposition(self, client, app):
        """Test PDF export returns Content-Disposition header."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=pdf")

        assert response.status_code == 200
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert ".pdf" in response.headers["Content-Disposition"]

    def test_pdf_export_is_valid_pdf(self, client, app):
        """Test PDF export is a valid PDF file."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=pdf")

        assert response.status_code == 200
        # Should be able to read with PyPDF2
        reader = PdfReader(BytesIO(response.data))
        assert len(reader.pages) > 0


class TestJsonExportEndpoint:
    """Tests for JSON export endpoint."""

    def test_json_export_returns_correct_content_type(self, client, app):
        """Test JSON export returns correct Content-Type."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json")

        assert response.status_code == 200
        assert "application/json" in response.content_type

    def test_json_export_returns_correct_disposition(self, client, app):
        """Test JSON export returns Content-Disposition header."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json")

        assert response.status_code == 200
        assert "Content-Disposition" in response.headers
        assert "attachment" in response.headers["Content-Disposition"]
        assert ".json" in response.headers["Content-Disposition"]

    def test_json_export_is_valid_json(self, client, app):
        """Test JSON export is valid JSON."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json")

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert "company" in data
        assert "analysis" in data

    def test_json_export_includes_raw_data_by_default(self, client, app):
        """Test JSON export includes entities and pages by default."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=json")

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert "entities" in data
        assert "pages" in data

    def test_json_export_excludes_raw_data_when_requested(self, client, app):
        """Test JSON export excludes raw data when includeRawData=false."""
        company_id = create_completed_company(app)

        response = client.get(
            f"/api/v1/companies/{company_id}/export?format=json&includeRawData=false"
        )

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert "entities" not in data
        assert "pages" not in data


class TestExportVersionParameter:
    """Tests for version parameter in export endpoint."""

    def test_export_specific_version(self, client, app):
        """Test exporting a specific analysis version."""
        company_id = create_completed_company(app)

        response = client.get(
            f"/api/v1/companies/{company_id}/export?format=json&version=1"
        )

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert data["analysis"]["versionNumber"] == 1

    def test_export_version_2(self, client, app):
        """Test exporting version 2 of analysis."""
        company_id = create_completed_company(app)

        response = client.get(
            f"/api/v1/companies/{company_id}/export?format=json&version=2"
        )

        assert response.status_code == 200
        data = json.loads(response.data.decode("utf-8"))
        assert data["analysis"]["versionNumber"] == 2

    def test_export_nonexistent_version_returns_404(self, client, app):
        """Test exporting non-existent version returns 404."""
        company_id = create_completed_company(app)

        response = client.get(
            f"/api/v1/companies/{company_id}/export?format=json&version=99"
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "NOT_FOUND"

    def test_export_invalid_version_format_returns_400(self, client, app):
        """Test invalid version parameter format returns 400."""
        company_id = create_completed_company(app)

        response = client.get(
            f"/api/v1/companies/{company_id}/export?format=json&version=abc"
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert data["error"]["code"] == "VALIDATION_ERROR"


class TestExportSecurityHeaders:
    """Tests for security headers in export responses."""

    def test_export_has_nosniff_header(self, client, app):
        """Test export response has X-Content-Type-Options header."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=markdown")

        assert response.status_code == 200
        assert response.headers.get("X-Content-Type-Options") == "nosniff"

    def test_export_has_cache_control(self, client, app):
        """Test export response has Cache-Control header."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=pdf")

        assert response.status_code == 200
        cache_control = response.headers.get("Cache-Control", "")
        assert "no-cache" in cache_control or "no-store" in cache_control


class TestExportCaseInsensitiveFormat:
    """Tests for case-insensitive format parameter."""

    def test_uppercase_format(self, client, app):
        """Test uppercase format parameter works."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=MARKDOWN")

        assert response.status_code == 200
        assert "text/markdown" in response.content_type

    def test_mixed_case_format(self, client, app):
        """Test mixed case format parameter works."""
        company_id = create_completed_company(app)

        response = client.get(f"/api/v1/companies/{company_id}/export?format=Pdf")

        assert response.status_code == 200
        assert "application/pdf" in response.content_type
