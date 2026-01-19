"""Company control API routes (pause, resume, rescan)."""

from flask import request

from app import db
from app.api import api_bp
from app.api.routes.companies import make_error_response, make_success_response
from app.models.company import Company, CrawlSession, Analysis, utcnow
from app.models.enums import CompanyStatus, CrawlStatus, ProcessingPhase
from app.schemas import (
    PauseResponse,
    ResumeResponse,
    ResumeFromData,
    RescanResponse,
)


@api_bp.route('/companies/<company_id>/pause', methods=['POST'])
def pause_company(company_id: str):
    """Pause an in-progress analysis."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Validate state
    if company.status != CompanyStatus.IN_PROGRESS:
        return make_error_response(
            'INVALID_STATE',
            f'Cannot pause company with status: {company.status.value}',
            {'currentStatus': company.status.value},
            status=422
        )

    # Update company status
    company.status = CompanyStatus.PAUSED
    company.paused_at = utcnow()

    # Update active crawl session if any
    active_session = (
        CrawlSession.query
        .filter_by(company_id=company_id, status=CrawlStatus.ACTIVE)
        .first()
    )

    checkpoint_saved = False
    if active_session:
        active_session.status = CrawlStatus.PAUSED
        # Save checkpoint data
        active_session.checkpoint_data = {
            'pagesCrawled': active_session.pages_crawled,
            'pagesQueued': active_session.pages_queued,
            'crawlDepthReached': active_session.crawl_depth_reached,
            'externalLinksFollowed': active_session.external_links_followed,
            'pausedAt': company.paused_at.isoformat(),
        }
        checkpoint_saved = True

    db.session.commit()

    response = PauseResponse(
        status='paused',
        checkpointSaved=checkpoint_saved,
        pausedAt=company.paused_at
    )

    return make_success_response(response.model_dump(by_alias=True))


@api_bp.route('/companies/<company_id>/resume', methods=['POST'])
def resume_company(company_id: str):
    """Resume a paused analysis."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Validate state
    if company.status != CompanyStatus.PAUSED:
        return make_error_response(
            'INVALID_STATE',
            f'Cannot resume company with status: {company.status.value}',
            {'currentStatus': company.status.value},
            status=422
        )

    # Calculate paused duration
    if company.paused_at:
        # Handle both timezone-aware and naive datetimes from DB
        now = utcnow()
        paused_at = company.paused_at
        if paused_at.tzinfo is None:
            # DB returned naive datetime, strip timezone from now
            now = now.replace(tzinfo=None)
        paused_duration = int((now - paused_at).total_seconds() * 1000)
        company.total_paused_duration_ms += paused_duration

    # Get paused session to resume from
    paused_session = (
        CrawlSession.query
        .filter_by(company_id=company_id, status=CrawlStatus.PAUSED)
        .first()
    )

    # Build resume data
    pages_crawled = 0
    entities_extracted = 0
    phase = ProcessingPhase.CRAWLING

    if paused_session:
        paused_session.status = CrawlStatus.ACTIVE
        pages_crawled = paused_session.pages_crawled

        # Determine phase based on checkpoint
        if paused_session.checkpoint_data:
            checkpoint = paused_session.checkpoint_data
            pages_crawled = checkpoint.get('pagesCrawled', 0)

    # Count extracted entities
    from app.models.company import Entity
    entities_extracted = Entity.query.filter_by(company_id=company_id).count()

    # Determine current phase
    if company.processing_phase:
        phase = company.processing_phase

    # Update company status
    company.status = CompanyStatus.IN_PROGRESS
    company.paused_at = None

    db.session.commit()

    resumed_from = ResumeFromData(
        pagesCrawled=pages_crawled,
        entitiesExtracted=entities_extracted,
        phase=phase
    )

    response = ResumeResponse(
        status='in_progress',
        resumedFrom=resumed_from
    )

    return make_success_response(response.model_dump(by_alias=True, mode='json'))


@api_bp.route('/companies/<company_id>/rescan', methods=['POST'])
def rescan_company(company_id: str):
    """Initiate re-scan for updates."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Validate state
    if company.status != CompanyStatus.COMPLETED:
        return make_error_response(
            'INVALID_STATE',
            f'Cannot rescan company with status: {company.status.value}',
            {'currentStatus': company.status.value},
            status=422
        )

    # Get current version count
    current_version = (
        Analysis.query
        .filter_by(company_id=company_id)
        .count()
    )

    # Check version limit (max 3)
    if current_version >= 3:
        # Delete oldest version
        oldest = (
            Analysis.query
            .filter_by(company_id=company_id)
            .order_by(Analysis.version_number.asc())
            .first()
        )
        if oldest:
            db.session.delete(oldest)

    # Create new analysis placeholder
    new_version_number = current_version + 1
    if current_version >= 3:
        new_version_number = 3  # Cap at 3

    new_analysis = Analysis(
        company_id=company_id,
        version_number=new_version_number
    )
    db.session.add(new_analysis)

    # Reset company for re-processing
    company.status = CompanyStatus.PENDING
    company.processing_phase = ProcessingPhase.QUEUED
    company.started_at = None
    company.completed_at = None

    db.session.commit()

    response = RescanResponse(
        newAnalysisId=new_analysis.id,
        versionNumber=new_version_number,
        status='pending'
    )

    return make_success_response(response.model_dump(by_alias=True))


# ==================== Internal Functions for Batch Operations ====================

def _pause_company_internal(company_id: str) -> dict:
    """
    Internal function to pause a company (used by batch queue service).

    Args:
        company_id: UUID of the company

    Returns:
        Dict with success status and any error
    """
    company = db.session.get(Company, company_id)
    if not company:
        return {'success': False, 'error': 'Company not found'}

    if company.status != CompanyStatus.IN_PROGRESS:
        return {'success': False, 'error': f'Cannot pause: status is {company.status.value}'}

    # Update company status
    company.status = CompanyStatus.PAUSED
    company.paused_at = utcnow()

    # Update active crawl session if any
    active_session = (
        CrawlSession.query
        .filter_by(company_id=company_id, status=CrawlStatus.ACTIVE)
        .first()
    )

    if active_session:
        active_session.status = CrawlStatus.PAUSED
        active_session.checkpoint_data = {
            'pagesCrawled': active_session.pages_crawled,
            'pagesQueued': active_session.pages_queued,
            'crawlDepthReached': active_session.crawl_depth_reached,
            'externalLinksFollowed': active_session.external_links_followed,
            'pausedAt': company.paused_at.isoformat(),
        }

    db.session.commit()
    return {'success': True, 'paused_at': company.paused_at.isoformat()}


def _resume_company_internal(company_id: str) -> dict:
    """
    Internal function to resume a company (used by batch queue service).

    Args:
        company_id: UUID of the company

    Returns:
        Dict with success status and any error
    """
    company = db.session.get(Company, company_id)
    if not company:
        return {'success': False, 'error': 'Company not found'}

    if company.status != CompanyStatus.PAUSED:
        return {'success': False, 'error': f'Cannot resume: status is {company.status.value}'}

    # Calculate paused duration
    if company.paused_at:
        # Handle both timezone-aware and naive datetimes from DB
        now = utcnow()
        paused_at = company.paused_at
        if paused_at.tzinfo is None:
            # DB returned naive datetime, strip timezone from now
            now = now.replace(tzinfo=None)
        paused_duration = int((now - paused_at).total_seconds() * 1000)
        company.total_paused_duration_ms += paused_duration

    # Get paused session to resume from
    paused_session = (
        CrawlSession.query
        .filter_by(company_id=company_id, status=CrawlStatus.PAUSED)
        .first()
    )

    if paused_session:
        paused_session.status = CrawlStatus.ACTIVE

    # Update company status
    company.status = CompanyStatus.IN_PROGRESS
    company.paused_at = None

    db.session.commit()

    # Trigger job continuation
    from app.services.job_service import job_service
    job_service._dispatch_next_phase(company_id)

    return {'success': True, 'phase': company.processing_phase.value}
