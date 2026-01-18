"""Export API routes for generating analysis exports.

Provides endpoints for downloading company analysis in various formats:
- Markdown (.md)
- Word (.docx)
- PDF (.pdf)
- JSON (.json)

Security: Implements NFR-SEC-005 secure download headers.
"""

from flask import Response, request

from app.api import api_bp
from app import db
from app.models.company import Company, Analysis
from app.models.enums import CompanyStatus
from app.services.export_service import generate_export
from app.middleware.security import get_secure_download_headers


VALID_FORMATS = ["markdown", "word", "pdf", "json"]


@api_bp.route("/companies/<company_id>/export", methods=["GET"])
def export_company(company_id: str) -> Response | tuple[dict, int]:
    """
    Export company analysis in the specified format.

    GET /api/v1/companies/:id/export?format=<format>&includeRawData=<bool>&version=<int>

    Query Parameters:
        format: Export format - 'markdown', 'word', 'pdf', or 'json' (required)
        includeRawData: Include entities/pages in export (JSON only, default: true)
        version: Specific analysis version to export (default: latest)

    Returns:
        File download with appropriate Content-Type and Content-Disposition headers.

    Errors:
        400: Invalid format specified
        404: Company not found
        422: Company analysis not yet complete
    """
    # Validate format parameter
    export_format = request.args.get("format", "").lower()
    if not export_format:
        return {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Export format is required. Use ?format=markdown|word|pdf|json",
            },
        }, 400

    if export_format not in VALID_FORMATS:
        return {
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"Invalid export format '{export_format}'. Valid formats: {', '.join(VALID_FORMATS)}",
            },
        }, 400

    # Get company with related data
    company = db.session.query(Company).filter(Company.id == company_id).first()

    if not company:
        return {
            "success": False,
            "error": {
                "code": "NOT_FOUND",
                "message": f"Company with id '{company_id}' not found",
            },
        }, 404

    # Check if analysis is complete
    if company.status != CompanyStatus.COMPLETED:
        return {
            "success": False,
            "error": {
                "code": "CONFLICT",
                "message": f"Cannot export analysis for company with status '{company.status.value}'. Analysis must be completed first.",
            },
        }, 422

    # Parse optional parameters
    include_raw_data = request.args.get("includeRawData", "true").lower() == "true"
    version_param = request.args.get("version")

    # Get specific analysis version if requested
    analysis = None
    if version_param:
        try:
            version_num = int(version_param)
            for a in company.analyses:
                if a.version_number == version_num:
                    analysis = a
                    break
            if not analysis:
                return {
                    "success": False,
                    "error": {
                        "code": "NOT_FOUND",
                        "message": f"Analysis version {version_num} not found for this company",
                    },
                }, 404
        except ValueError:
            return {
                "success": False,
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Version parameter must be a valid integer",
                },
            }, 400

    # Generate export
    try:
        content, content_type, filename = generate_export(
            company=company,
            format=export_format,
            include_raw_data=include_raw_data,
            analysis=analysis,
        )
    except Exception as e:
        return {
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"Failed to generate export: {str(e)}",
            },
        }, 500

    # Return file response with secure headers (NFR-SEC-005)
    response = Response(content, content_type=content_type)
    secure_headers = get_secure_download_headers(filename, content_type)
    for header, value in secure_headers.items():
        response.headers[header] = value

    return response
