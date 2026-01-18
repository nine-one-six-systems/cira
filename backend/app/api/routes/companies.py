"""Company API routes."""

from flask import request, jsonify
from pydantic import ValidationError
from sqlalchemy import or_

from app import db
from app.api import api_bp
from app.models.company import Company, Page, Entity, Analysis
from app.models.enums import CompanyStatus
from app.schemas import (
    ApiResponse,
    ApiError,
    ApiErrorResponse,
    CreateCompanyRequest,
    CreateCompanyResponse,
    CompanyListItem,
    CompanyDetail,
    CompanyDetailResponse,
    AnalysisSummary,
    PaginatedResponse,
    PaginationMeta,
    DeleteResponse,
    DeletedRecords,
)
from app.services.url_validator import validate_url


def make_error_response(code: str, message: str, details: dict | None = None, status: int = 400):
    """Create a standard error response."""
    error = ApiError(code=code, message=message, details=details)
    response = ApiErrorResponse(error=error)
    return jsonify(response.model_dump(by_alias=True)), status


def make_success_response(data, status: int = 200, warnings: list[str] | None = None):
    """Create a standard success response, optionally with warnings."""
    response = ApiResponse[dict](data=data)
    response_dict = response.model_dump(by_alias=True)
    if warnings:
        response_dict['warnings'] = warnings
    return jsonify(response_dict), status


def normalize_url(url: str) -> str:
    """Normalize URL for comparison (remove trailing slash)."""
    url_str = str(url)
    return url_str.rstrip('/')


@api_bp.route('/companies', methods=['POST'])
def create_company():
    """Create a single company analysis job."""
    try:
        request_data = CreateCompanyRequest.model_validate(request.json)
    except ValidationError as e:
        errors = e.errors()
        return make_error_response(
            'VALIDATION_ERROR',
            'Request validation failed',
            {'errors': [{'field': err['loc'][0], 'message': err['msg']} for err in errors]}
        )

    # Validate and normalize URL with reachability check
    # Skip reachability check if explicitly disabled or in testing
    skip_reachability = request.args.get('skipReachabilityCheck', 'false').lower() == 'true'
    url_result = validate_url(str(request_data.website_url), check_reachability=not skip_reachability)

    if not url_result.is_valid:
        return make_error_response(
            'VALIDATION_ERROR',
            url_result.error_message or 'Invalid URL format',
            {'field': 'websiteUrl'}
        )

    # Use the normalized URL
    normalized_url = url_result.normalized_url.rstrip('/')

    # Collect warnings
    warnings = []
    if url_result.warning_message:
        warnings.append(url_result.warning_message)

    # Check for existing company with same URL (normalized)
    existing = None
    for company in Company.query.all():
        if normalize_url(company.website_url) == normalized_url:
            existing = company
            break

    if existing:
        return make_error_response(
            'CONFLICT',
            f'Company with URL {request_data.website_url} already exists',
            {'existingCompanyId': existing.id},
            status=409
        )

    # Create company
    company = Company(
        company_name=request_data.company_name,
        website_url=normalized_url,
        industry=request_data.industry,
    )

    # Apply config if provided
    if request_data.config:
        company.analysis_mode = request_data.config.analysis_mode
        company.config = {
            'timeLimitMinutes': request_data.config.time_limit_minutes,
            'maxPages': request_data.config.max_pages,
            'maxDepth': request_data.config.max_depth,
            'followLinkedIn': request_data.config.follow_linkedin,
            'followTwitter': request_data.config.follow_twitter,
            'followFacebook': request_data.config.follow_facebook,
            'exclusionPatterns': request_data.config.exclusion_patterns,
        }

    db.session.add(company)
    db.session.commit()

    response_data = CreateCompanyResponse(
        companyId=company.id,
        status=company.status.value,
        createdAt=company.created_at
    )

    return make_success_response(
        response_data.model_dump(by_alias=True),
        status=201,
        warnings=warnings if warnings else None
    )


@api_bp.route('/companies', methods=['GET'])
def list_companies():
    """List companies with filtering, sorting, and pagination."""
    # Parse query parameters
    status_filter = request.args.get('status')
    sort_field = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 20, type=int)
    search = request.args.get('search')

    # Validate pagination
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    # Build query
    query = Company.query

    # Apply status filter
    if status_filter:
        try:
            status_enum = CompanyStatus(status_filter)
            query = query.filter(Company.status == status_enum)
        except ValueError:
            pass  # Ignore invalid status

    # Apply search filter
    if search:
        search_term = f'%{search}%'
        query = query.filter(
            or_(
                Company.company_name.ilike(search_term),
                Company.website_url.ilike(search_term)
            )
        )

    # Apply sorting
    sort_column = getattr(Company, sort_field, Company.created_at)
    if sort_order == 'asc':
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Get total count
    total = query.count()

    # Apply pagination
    companies = query.offset((page - 1) * page_size).limit(page_size).all()

    # Build response - convert enums to values for JSON serialization
    items = []
    for c in companies:
        item = CompanyListItem(
            id=c.id,
            companyName=c.company_name,
            websiteUrl=c.website_url,
            status=c.status,
            totalTokensUsed=c.total_tokens_used,
            estimatedCost=c.estimated_cost,
            createdAt=c.created_at,
            completedAt=c.completed_at
        )
        item_dict = item.model_dump(by_alias=True, mode='json')
        items.append(item_dict)

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    meta = PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    response = PaginatedResponse[dict](data=items, meta=meta)
    return jsonify(response.model_dump(by_alias=True))


@api_bp.route('/companies/<company_id>', methods=['GET'])
def get_company(company_id: str):
    """Get company details with latest analysis."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Get latest analysis
    latest_analysis = (
        Analysis.query
        .filter_by(company_id=company_id)
        .order_by(Analysis.version_number.desc())
        .first()
    )

    # Get counts
    entity_count = Entity.query.filter_by(company_id=company_id).count()
    page_count = Page.query.filter_by(company_id=company_id).count()

    # Build company detail
    company_detail = CompanyDetail(
        id=company.id,
        companyName=company.company_name,
        websiteUrl=company.website_url,
        industry=company.industry,
        analysisMode=company.analysis_mode,
        status=company.status,
        totalTokensUsed=company.total_tokens_used,
        estimatedCost=company.estimated_cost,
        createdAt=company.created_at,
        completedAt=company.completed_at
    )

    # Build analysis summary if exists
    analysis_summary = None
    if latest_analysis:
        analysis_summary = AnalysisSummary(
            id=latest_analysis.id,
            versionNumber=latest_analysis.version_number,
            executiveSummary=latest_analysis.executive_summary,
            fullAnalysis=latest_analysis.full_analysis,
            createdAt=latest_analysis.created_at
        )

    response_data = CompanyDetailResponse(
        company=company_detail,
        analysis=analysis_summary,
        entityCount=entity_count,
        pageCount=page_count
    )

    # Use mode='json' to properly serialize enums
    return make_success_response(response_data.model_dump(by_alias=True, mode='json'))


@api_bp.route('/companies/<company_id>', methods=['DELETE'])
def delete_company(company_id: str):
    """Delete company and all associated data."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Count related records before deletion
    page_count = Page.query.filter_by(company_id=company_id).count()
    entity_count = Entity.query.filter_by(company_id=company_id).count()
    analysis_count = Analysis.query.filter_by(company_id=company_id).count()

    # Delete company (cascade deletes related records)
    db.session.delete(company)
    db.session.commit()

    response_data = DeleteResponse(
        deleted=True,
        deletedRecords=DeletedRecords(
            pages=page_count,
            entities=entity_count,
            analyses=analysis_count
        )
    )

    return make_success_response(response_data.model_dump(by_alias=True))
