"""Progress API route."""

from app import db
from app.api import api_bp
from app.api.routes.companies import make_error_response, make_success_response
from app.models.company import Company, CrawlSession, Entity, Page, utcnow
from app.models.enums import CompanyStatus, CrawlStatus
from app.schemas import ProgressResponse


@api_bp.route('/companies/<company_id>/progress', methods=['GET'])
def get_progress(company_id: str):
    """Get real-time progress for a company."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Get active or most recent crawl session
    session = (
        CrawlSession.query
        .filter_by(company_id=company_id)
        .order_by(CrawlSession.created_at.desc())
        .first()
    )

    # Calculate stats
    pages_crawled = 0
    pages_total = 0

    if session:
        pages_crawled = session.pages_crawled
        pages_total = session.pages_crawled + session.pages_queued

    # Get entity count
    entities_extracted = Entity.query.filter_by(company_id=company_id).count()

    # Calculate time elapsed (in seconds)
    time_elapsed = 0
    if company.started_at:
        # Handle both timezone-aware and naive datetimes from DB
        now = utcnow()
        started_at = company.started_at
        if started_at.tzinfo is None:
            # DB returned naive datetime, strip timezone from now
            now = now.replace(tzinfo=None)
        elapsed_delta = now - started_at
        # Subtract paused duration
        paused_ms = company.total_paused_duration_ms or 0
        time_elapsed = int(elapsed_delta.total_seconds()) - (paused_ms // 1000)
        time_elapsed = max(0, time_elapsed)

    # Estimate time remaining (rough estimate based on progress)
    estimated_time_remaining = None
    if pages_crawled > 0 and pages_total > pages_crawled:
        rate = time_elapsed / pages_crawled
        remaining_pages = pages_total - pages_crawled
        estimated_time_remaining = int(rate * remaining_pages)

    # Determine current activity
    current_activity = None
    if company.status == CompanyStatus.IN_PROGRESS:
        phase = company.processing_phase
        if phase:
            current_activity = f'{phase.value.title()} company data...'

    response = ProgressResponse(
        companyId=company.id,
        status=company.status,
        phase=company.processing_phase,
        pagesCrawled=pages_crawled,
        pagesTotal=pages_total,
        entitiesExtracted=entities_extracted,
        tokensUsed=company.total_tokens_used,
        timeElapsed=time_elapsed,
        estimatedTimeRemaining=estimated_time_remaining,
        currentActivity=current_activity
    )

    return make_success_response(response.model_dump(by_alias=True, mode='json'))
