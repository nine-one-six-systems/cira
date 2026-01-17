"""Celery task definitions."""

import logging
from datetime import datetime
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError

from app.workers.celery_app import celery_app
from app.services import redis_service

logger = logging.getLogger(__name__)


class TaskError(Exception):
    """Base exception for task errors."""
    pass


class RetryableError(TaskError):
    """Error that should trigger task retry."""
    pass


class PermanentError(TaskError):
    """Error that should not be retried."""
    pass


# ==================== Crawl Tasks ====================

@celery_app.task(
    bind=True,
    name='app.workers.tasks.crawl_company',
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
)
def crawl_company(self, company_id: str, config: dict | None = None):
    """
    Main task to crawl a company website.

    This task orchestrates the crawling process for a single company,
    discovering pages, respecting robots.txt, and managing the crawl queue.

    Args:
        company_id: UUID of the company to crawl
        config: Optional crawl configuration overrides

    Returns:
        Dict with crawl results summary

    Raises:
        RetryableError: For transient failures that should be retried
        PermanentError: For failures that should not be retried
    """
    from app import db
    from app.models import Company, CrawlSession
    from app.models.enums import CompanyStatus, ProcessingPhase, CrawlStatus

    logger.info(f"Starting crawl task for company {company_id}")

    try:
        # Get the company from database
        company = db.session.get(Company, company_id)
        if not company:
            raise PermanentError(f"Company {company_id} not found")

        # Update status to in_progress if not already
        if company.status == CompanyStatus.PENDING:
            company.status = CompanyStatus.IN_PROGRESS
            company.processing_phase = ProcessingPhase.CRAWLING
            company.started_at = datetime.utcnow()
            db.session.commit()

        # Create or get crawl session
        crawl_session = company.crawl_sessions[-1] if company.crawl_sessions else None
        if not crawl_session or crawl_session.status == CrawlStatus.COMPLETED:
            crawl_session = CrawlSession(
                company_id=company_id,
                status=CrawlStatus.ACTIVE
            )
            db.session.add(crawl_session)
            db.session.commit()

        # Update Redis progress
        redis_service.set_progress(company_id, {
            'phase': 'crawling',
            'pages_crawled': 0,
            'pages_queued': 0,
            'current_activity': 'Initializing crawler...'
        })

        # TODO: Actual crawling logic will be implemented in Phase 4
        # For now, this is a placeholder that demonstrates the task structure

        logger.info(f"Crawl task completed for company {company_id}")
        return {
            'company_id': company_id,
            'status': 'completed',
            'pages_crawled': 0
        }

    except PermanentError:
        raise
    except Exception as e:
        logger.error(f"Crawl task failed for company {company_id}: {e}")
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            logger.error(f"Max retries exceeded for company {company_id}")
            # Mark as failed in database
            company = db.session.get(Company, company_id)
            if company:
                company.status = CompanyStatus.FAILED
                db.session.commit()
            raise


@celery_app.task(
    bind=True,
    name='app.workers.tasks.crawl_page',
    max_retries=3,
    default_retry_delay=10,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
)
def crawl_page(self, company_id: str, url: str, depth: int = 0):
    """
    Task to crawl a single page.

    Args:
        company_id: UUID of the company
        url: URL to crawl
        depth: Current crawl depth

    Returns:
        Dict with page crawl results
    """
    logger.info(f"Crawling page {url} for company {company_id} at depth {depth}")

    # TODO: Actual page crawling logic will be implemented in Phase 4
    return {
        'company_id': company_id,
        'url': url,
        'status': 'completed'
    }


# ==================== Extraction Tasks ====================

@celery_app.task(
    bind=True,
    name='app.workers.tasks.extract_entities',
    max_retries=3,
    default_retry_delay=15,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
)
def extract_entities(self, company_id: str, page_ids: list[str] | None = None):
    """
    Task to extract entities from crawled pages.

    Args:
        company_id: UUID of the company
        page_ids: Optional list of specific page IDs to process

    Returns:
        Dict with extraction results
    """
    from app import db
    from app.models import Company
    from app.models.enums import ProcessingPhase

    logger.info(f"Starting entity extraction for company {company_id}")

    try:
        company = db.session.get(Company, company_id)
        if not company:
            raise PermanentError(f"Company {company_id} not found")

        # Update phase
        company.processing_phase = ProcessingPhase.EXTRACTING
        db.session.commit()

        # Update Redis progress
        redis_service.set_progress(company_id, {
            'phase': 'extracting',
            'entities_extracted': 0,
            'current_activity': 'Extracting entities from pages...'
        })

        # TODO: Actual extraction logic will be implemented in Phase 5
        logger.info(f"Entity extraction completed for company {company_id}")
        return {
            'company_id': company_id,
            'status': 'completed',
            'entities_extracted': 0
        }

    except PermanentError:
        raise
    except Exception as e:
        logger.error(f"Entity extraction failed for company {company_id}: {e}")
        raise


# ==================== Analysis Tasks ====================

@celery_app.task(
    bind=True,
    name='app.workers.tasks.analyze_content',
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
    retry_backoff_max=600,
)
def analyze_content(self, company_id: str, sections: list[str] | None = None):
    """
    Task to analyze content using Claude API.

    Args:
        company_id: UUID of the company
        sections: Optional list of specific sections to analyze

    Returns:
        Dict with analysis results
    """
    from app import db
    from app.models import Company
    from app.models.enums import ProcessingPhase

    logger.info(f"Starting content analysis for company {company_id}")

    try:
        company = db.session.get(Company, company_id)
        if not company:
            raise PermanentError(f"Company {company_id} not found")

        # Update phase
        company.processing_phase = ProcessingPhase.ANALYZING
        db.session.commit()

        # Update Redis progress
        redis_service.set_progress(company_id, {
            'phase': 'analyzing',
            'sections_completed': 0,
            'current_activity': 'Analyzing content with AI...'
        })

        # TODO: Actual analysis logic will be implemented in Phase 6
        logger.info(f"Content analysis completed for company {company_id}")
        return {
            'company_id': company_id,
            'status': 'completed',
            'sections_analyzed': []
        }

    except PermanentError:
        raise
    except Exception as e:
        logger.error(f"Content analysis failed for company {company_id}: {e}")
        raise


@celery_app.task(
    bind=True,
    name='app.workers.tasks.generate_summary',
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(RetryableError,),
    retry_backoff=True,
)
def generate_summary(self, company_id: str):
    """
    Task to generate the final summary from analysis sections.

    Args:
        company_id: UUID of the company

    Returns:
        Dict with summary generation results
    """
    from app import db
    from app.models import Company
    from app.models.enums import ProcessingPhase, CompanyStatus

    logger.info(f"Starting summary generation for company {company_id}")

    try:
        company = db.session.get(Company, company_id)
        if not company:
            raise PermanentError(f"Company {company_id} not found")

        # Update phase
        company.processing_phase = ProcessingPhase.GENERATING
        db.session.commit()

        # Update Redis progress
        redis_service.set_progress(company_id, {
            'phase': 'generating',
            'current_activity': 'Generating final summary...'
        })

        # TODO: Actual summary generation logic will be implemented in Phase 6
        # Mark as completed
        company.processing_phase = ProcessingPhase.COMPLETED
        company.status = CompanyStatus.COMPLETED
        company.completed_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Summary generation completed for company {company_id}")
        return {
            'company_id': company_id,
            'status': 'completed'
        }

    except PermanentError:
        raise
    except Exception as e:
        logger.error(f"Summary generation failed for company {company_id}: {e}")
        raise


# ==================== Utility Tasks ====================

@celery_app.task(name='app.workers.tasks.health_check')
def health_check():
    """
    Simple health check task to verify Celery is working.

    Returns:
        Dict with worker health status
    """
    return {
        'status': 'healthy',
        'timestamp': datetime.now(tz=None).isoformat(),
        'worker': 'celery'
    }
