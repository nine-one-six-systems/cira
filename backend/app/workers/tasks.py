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

    This task:
    1. Loads crawled pages for the company
    2. Uses spaCy NLP to extract named entities (PERSON, ORG, GPE, DATE, MONEY)
    3. Uses regex patterns to extract structured data (emails, phones, addresses, social handles)
    4. Deduplicates entities across pages
    5. Stores results in the database

    Args:
        company_id: UUID of the company
        page_ids: Optional list of specific page IDs to process

    Returns:
        Dict with extraction results
    """
    from app import db
    from app.models import Company, Page, Entity
    from app.models.enums import ProcessingPhase, EntityType

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
            'current_activity': 'Initializing extraction pipeline...'
        })

        # Import extractors
        from app.extractors.nlp_pipeline import nlp_pipeline
        from app.extractors.structured_extractor import structured_extractor
        from app.extractors.deduplicator import deduplicator

        # Get pages to process
        if page_ids:
            pages = Page.query.filter(
                Page.company_id == company_id,
                Page.id.in_(page_ids)
            ).all()
        else:
            pages = Page.query.filter_by(company_id=company_id).filter(
                Page.extracted_text.isnot(None),
                Page.extracted_text != ''
            ).all()

        if not pages:
            logger.info(f"No pages with content found for company {company_id}")
            return {
                'company_id': company_id,
                'status': 'completed',
                'entities_extracted': 0,
                'message': 'No pages with content to process'
            }

        # Collect all entities
        all_entities: list[dict] = []
        total_pages = len(pages)

        for i, page in enumerate(pages):
            # Update progress
            redis_service.set_progress(company_id, {
                'phase': 'extracting',
                'pages_processed': i + 1,
                'total_pages': total_pages,
                'entities_extracted': len(all_entities),
                'current_activity': f'Extracting from page {i + 1}/{total_pages}...'
            })

            text = page.extracted_text or ''
            if not text.strip():
                continue

            # Extract named entities using NLP
            nlp_entities = nlp_pipeline.process_text(text)
            for ent in nlp_entities:
                entity_type = nlp_pipeline.LABEL_MAPPING.get(ent.label)
                if entity_type and entity_type != 'other':
                    all_entities.append({
                        'type': entity_type,
                        'value': ent.text,
                        'confidence': ent.confidence,
                        'context': ent.context_snippet,
                        'source_url': page.url,
                        'extra_data': ent.extra_data,
                    })

            # Extract structured data
            structured_entities = structured_extractor.extract_all(text, page.url)
            for sent in structured_entities:
                all_entities.append({
                    'type': sent.entity_type,
                    'value': sent.value,
                    'confidence': sent.confidence,
                    'context': sent.context,
                    'source_url': page.url,
                    'extra_data': sent.extra_data,
                })

        # Deduplicate entities
        redis_service.set_progress(company_id, {
            'phase': 'extracting',
            'pages_processed': total_pages,
            'total_pages': total_pages,
            'entities_extracted': len(all_entities),
            'current_activity': 'Deduplicating entities...'
        })

        merged_entities = deduplicator.deduplicate_entities(all_entities)

        # Save to database
        saved_count = 0
        for merged in merged_entities:
            try:
                # Map type string to enum
                try:
                    entity_type = EntityType(merged.entity_type)
                except ValueError:
                    logger.warning(f"Unknown entity type: {merged.entity_type}")
                    continue

                entity = Entity(
                    company_id=company_id,
                    entity_type=entity_type,
                    entity_value=merged.entity_value,
                    context_snippet=merged.contexts[0] if merged.contexts else None,
                    source_url=merged.source_urls[0] if merged.source_urls else None,
                    confidence_score=merged.confidence_score,
                    extra_data={
                        'canonical': merged.canonical_value,
                        'mentions': merged.mention_count,
                        'all_sources': merged.source_urls,
                        **merged.extra_data
                    },
                )
                db.session.add(entity)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Failed to save entity: {e}")

        db.session.commit()

        # Update final progress
        redis_service.set_progress(company_id, {
            'phase': 'extracting',
            'pages_processed': total_pages,
            'total_pages': total_pages,
            'entities_extracted': saved_count,
            'current_activity': 'Entity extraction completed'
        })

        logger.info(
            f"Entity extraction completed for company {company_id}: "
            f"{saved_count} entities from {total_pages} pages"
        )
        return {
            'company_id': company_id,
            'status': 'completed',
            'pages_processed': total_pages,
            'entities_extracted': saved_count,
            'entities_before_dedup': len(all_entities),
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

    This task:
    1. Loads crawled pages and extracted entities
    2. Passes content to Claude API for analysis
    3. Generates structured analysis sections
    4. Tracks token usage and costs
    5. Stores results in the database

    Args:
        company_id: UUID of the company
        sections: Optional list of specific sections to analyze

    Returns:
        Dict with analysis results
    """
    from app import db
    from app.models import Company
    from app.models.enums import ProcessingPhase
    from app.analysis.synthesis import analysis_synthesizer
    from app.analysis.prompts import get_section_order, ANALYSIS_SECTIONS

    logger.info(f"Starting content analysis for company {company_id}")

    try:
        company = db.session.get(Company, company_id)
        if not company:
            raise PermanentError(f"Company {company_id} not found")

        # Update phase
        company.processing_phase = ProcessingPhase.ANALYZING
        db.session.commit()

        # Progress callback to update Redis
        def progress_callback(section_id: str, completed: int, total: int):
            section_name = 'Complete' if section_id == 'complete' else \
                ANALYSIS_SECTIONS.get(section_id, {}).name if hasattr(ANALYSIS_SECTIONS.get(section_id, {}), 'name') else section_id
            redis_service.set_progress(company_id, {
                'phase': 'analyzing',
                'sections_completed': completed,
                'sections_total': total,
                'current_section': section_id,
                'current_activity': f'Analyzing: {section_name}...' if section_id != 'complete' else 'Analysis complete'
            })

        # Run the full analysis
        result = analysis_synthesizer.run_full_analysis(
            company_id=company_id,
            progress_callback=progress_callback,
        )

        logger.info(
            f"Content analysis completed for company {company_id}: "
            f"{len([s for s in result.sections.values() if s.success])}/{len(result.sections)} sections, "
            f"{result.total_tokens} tokens"
        )

        return {
            'company_id': company_id,
            'status': 'completed' if result.success else 'partial',
            'sections_analyzed': list(result.sections.keys()),
            'total_tokens': result.total_tokens,
            'errors': result.errors,
        }

    except PermanentError:
        raise
    except Exception as e:
        logger.error(f"Content analysis failed for company {company_id}: {e}")
        # Update status to failed
        try:
            company = db.session.get(Company, company_id)
            if company:
                from app.models.enums import CompanyStatus
                company.status = CompanyStatus.FAILED
                db.session.commit()
        except Exception:
            pass
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

    This task:
    1. Checks that analysis is complete
    2. Marks the company as COMPLETED
    3. Updates final timestamps

    Note: The executive summary is now generated as part of analyze_content.
    This task serves as the final step to mark completion.

    Args:
        company_id: UUID of the company

    Returns:
        Dict with summary generation results
    """
    from app import db
    from app.models import Company, Analysis
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
            'current_activity': 'Finalizing analysis...'
        })

        # Check that analysis exists
        analysis = Analysis.query.filter_by(
            company_id=company_id
        ).order_by(Analysis.version_number.desc()).first()

        if not analysis:
            logger.warning(f"No analysis found for company {company_id}")
            # Run analysis if missing
            analyze_content.delay(company_id)
            return {
                'company_id': company_id,
                'status': 'pending_analysis',
                'message': 'Analysis not found, triggering analysis task'
            }

        # Mark as completed
        company.processing_phase = ProcessingPhase.COMPLETED
        company.status = CompanyStatus.COMPLETED
        company.completed_at = datetime.now(tz=None)
        db.session.commit()

        # Update Redis with final progress
        redis_service.set_progress(company_id, {
            'phase': 'completed',
            'current_activity': 'Analysis complete',
            'sections_completed': 8,
            'sections_total': 8,
        })

        logger.info(f"Summary generation completed for company {company_id}")
        return {
            'company_id': company_id,
            'status': 'completed',
            'analysis_version': analysis.version_number,
            'has_executive_summary': bool(analysis.executive_summary),
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
