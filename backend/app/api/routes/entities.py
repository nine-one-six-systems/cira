"""Entity and Page API routes."""

from flask import request

from app import db
from app.api import api_bp
from app.api.routes.companies import make_error_response, make_success_response
from app.models.company import Company, Entity, Page
from app.models.enums import EntityType, PageType
from app.schemas import (
    EntityItem,
    PageItem,
    PaginatedResponse,
    PaginationMeta,
)


@api_bp.route('/companies/<company_id>/entities', methods=['GET'])
def list_entities(company_id: str):
    """Get extracted entities for a company."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Parse query parameters
    entity_type = request.args.get('type')
    min_confidence = request.args.get('minConfidence', 0.0, type=float)
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 50, type=int)

    # Validate pagination
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    # Build query
    query = Entity.query.filter_by(company_id=company_id)

    # Apply type filter
    if entity_type:
        try:
            type_enum = EntityType(entity_type)
            query = query.filter(Entity.entity_type == type_enum)
        except ValueError:
            pass  # Ignore invalid type

    # Apply confidence filter
    query = query.filter(Entity.confidence_score >= min_confidence)

    # Order by confidence descending
    query = query.order_by(Entity.confidence_score.desc())

    # Get total count
    total = query.count()

    # Apply pagination
    entities = query.offset((page - 1) * page_size).limit(page_size).all()

    # Build response
    items = []
    for e in entities:
        item = EntityItem(
            id=e.id,
            entityType=e.entity_type,
            entityValue=e.entity_value,
            contextSnippet=e.context_snippet,
            sourceUrl=e.source_url,
            confidenceScore=e.confidence_score
        )
        items.append(item.model_dump(by_alias=True, mode='json'))

    total_pages = (total + page_size - 1) // page_size if total > 0 else 1
    meta = PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )

    response = PaginatedResponse[dict](data=items, meta=meta)
    return response.model_dump(by_alias=True)


@api_bp.route('/companies/<company_id>/pages', methods=['GET'])
def list_pages(company_id: str):
    """Get crawled pages for a company."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Parse query parameters
    page_type = request.args.get('pageType')
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('pageSize', 50, type=int)

    # Validate pagination
    page = max(1, page)
    page_size = min(max(1, page_size), 100)

    # Build query
    query = Page.query.filter_by(company_id=company_id)

    # Apply page type filter
    if page_type:
        try:
            type_enum = PageType(page_type)
            query = query.filter(Page.page_type == type_enum)
        except ValueError:
            pass  # Ignore invalid type

    # Order by crawled_at descending
    query = query.order_by(Page.crawled_at.desc())

    # Get total count
    total = query.count()

    # Apply pagination
    pages = query.offset((page - 1) * page_size).limit(page_size).all()

    # Build response
    items = []
    for p in pages:
        item = PageItem(
            id=p.id,
            url=p.url,
            pageType=p.page_type,
            crawledAt=p.crawled_at,
            isExternal=p.is_external
        )
        items.append(item.model_dump(by_alias=True, mode='json'))

    total_pages_count = (total + page_size - 1) // page_size if total > 0 else 1
    meta = PaginationMeta(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages_count
    )

    response = PaginatedResponse[dict](data=items, meta=meta)
    return response.model_dump(by_alias=True)
