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

def _build_crawl_config(company, config_override: dict | None = None):
    """Convert company config to CrawlConfig."""
    from app.crawlers.crawl_worker import CrawlConfig
    
    config_dict = config_override or company.config or {}
    return CrawlConfig(
        max_pages=config_dict.get('maxPages', 100),
        max_time_seconds=config_dict.get('timeLimitMinutes', 30) * 60,
        max_depth=config_dict.get('maxDepth', 3),
        follow_linkedin=config_dict.get('followLinkedIn', False),
        follow_twitter=config_dict.get('followTwitter', False),
        follow_facebook=config_dict.get('followFacebook', False),
        requests_per_second=1.0,
    )


def _load_crawl_checkpoint(crawl_session):
    """Load CrawlCheckpoint from CrawlSession checkpoint_data."""
    from app.crawlers.crawl_worker import CrawlCheckpoint
    from datetime import datetime
    
    if not crawl_session or not crawl_session.checkpoint_data:
        return None
    
    checkpoint_data = crawl_session.checkpoint_data
    if not isinstance(checkpoint_data, dict):
        return None
    
    # Convert CheckpointService format to CrawlCheckpoint format
    # CheckpointService uses: pagesVisited, pagesQueued, externalLinksFound, etc.
    # CrawlCheckpoint needs: visited_urls, content_hashes, queue_state, progress
    
    # Reconstruct queue state from checkpoint data
    pages_visited = checkpoint_data.get('pagesVisited', [])
    pages_queued = checkpoint_data.get('pagesQueued', [])
    
    queue_state = {
        'visited_urls': pages_visited,
        'seen_urls': pages_visited.copy(),
        'content_hashes': [],
        'queued_urls': [
            {
                'url': url,
                'depth': 0,
                'page_type': 'other',
                'insertion_order': i
            }
            for i, url in enumerate(pages_queued)
        ],
        'insertion_counter': len(pages_queued)
    }
    
    # Parse started_at datetime
    started_at = None
    if checkpoint_data.get('crawlStartTime'):
        try:
            started_at = datetime.fromisoformat(
                checkpoint_data['crawlStartTime'].replace('Z', '+00:00')
            )
        except (ValueError, AttributeError):
            pass
    
    progress_data = {
        'pages_crawled': len(pages_visited),
        'pages_queued': len(pages_queued),
        'pages_skipped': 0,
        'duplicates_found': 0,
        'errors_count': 0,
        'external_links_found': len(checkpoint_data.get('externalLinksFound', [])),
        'current_url': '',
        'current_activity': 'Resuming crawl...',
        'started_at': started_at,
        'last_checkpoint_at': None,
        'elapsed_seconds': 0.0,
    }
    
    try:
        return CrawlCheckpoint(
            visited_urls=set(pages_visited),
            content_hashes=set(),  # Not stored in CheckpointService format, will be rebuilt
            queue_state=queue_state,
            progress=progress_data,
            timestamp=checkpoint_data.get('lastCheckpointTime', ''),
        )
    except Exception as e:
        logger.warning(f"Failed to load checkpoint: {e}")
        return None


def _save_crawled_page(db, company_id: str, crawled_page, crawl_session_id: str):
    """Save a CrawledPage to database as Page model."""
    from app.models.company import Page
    from app.models.enums import PageType
    
    # Map page_type string to PageType enum
    page_type_str = crawled_page.page_type or 'other'
    try:
        page_type = PageType(page_type_str)
    except ValueError:
        page_type = PageType.OTHER
    
    # Check if page already exists (by URL)
    existing_page = Page.query.filter_by(
        company_id=company_id,
        url=crawled_page.url
    ).first()
    
    if existing_page:
        # Update existing page
        existing_page.raw_html = crawled_page.html
        existing_page.extracted_text = crawled_page.text
        existing_page.content_hash = crawled_page.content_hash
        existing_page.page_type = page_type
        existing_page.is_external = crawled_page.is_external
        return existing_page
    
    # Create new page
    page = Page(
        company_id=company_id,
        url=crawled_page.url,
        page_type=page_type,
        content_hash=crawled_page.content_hash if crawled_page.content_hash else None,
        raw_html=crawled_page.html if crawled_page.html else None,
        extracted_text=crawled_page.text if crawled_page.text else None,
        is_external=crawled_page.is_external,
    )
    db.session.add(page)
    return page


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

    # Ensure Flask app context is available
    # The ContextTask class should provide app context, but we need to ensure
    # the Flask app instance is available and properly configured
    from app.workers.celery_app import celery_app
    from app import create_app
    
    # Get Flask app from celery_app (set during init_celery)
    # If not available, create a new instance
    if not hasattr(celery_app, 'flask_app') or celery_app.flask_app is None:
        flask_app = create_app()
        celery_app.flask_app = flask_app
    else:
        flask_app = celery_app.flask_app
    
    with flask_app.app_context():
        try:
            # Log database info for debugging
            logger.debug(f"Database URI: {flask_app.config.get('SQLALCHEMY_DATABASE_URI')}")
            
            # Refresh the database session to ensure we have a clean connection
            db.session.expire_all()
            
            # Get the company from database - try multiple methods
            company = None
            try:
                company = db.session.get(Company, company_id)
            except Exception as e:
                logger.warning(f"Error getting company with db.session.get: {e}")
            
            if not company:
                try:
                    company = Company.query.filter_by(id=company_id).first()
                except Exception as e:
                    logger.warning(f"Error querying company: {e}")
            
            if not company:
                # Log all companies for debugging
                try:
                    all_companies = Company.query.limit(10).all()
                    logger.error(
                        f"Company {company_id} not found. "
                        f"Database has {len(all_companies)} companies. "
                        f"Sample IDs: {[str(c.id) for c in all_companies[:3]]}"
                    )
                except Exception as e:
                    logger.error(f"Could not query companies: {e}")
                raise PermanentError(f"Company {company_id} not found")

            # Check if already being crawled by another worker (prevent duplicates)
            if company.processing_phase == ProcessingPhase.CRAWLING:
                logger.info(f"Company {company_id} already being crawled, skipping duplicate task")
                return {'status': 'already_crawling', 'company_id': company_id}

            # Update status and phase - always set to CRAWLING when task starts
            company.status = CompanyStatus.IN_PROGRESS
            company.processing_phase = ProcessingPhase.CRAWLING
            if not company.started_at:
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

            # Build crawl configuration
            crawl_config = _build_crawl_config(company, config)
            
            # Load checkpoint if resuming
            checkpoint = _load_crawl_checkpoint(crawl_session)
            
            # Import crawler components
            from app.crawlers.crawl_worker import CrawlWorker, CrawlCheckpoint
            from app.services.checkpoint_service import checkpoint_service
            
            # Create crawl worker
            worker = CrawlWorker(config=crawl_config)
            
            # Track saved page URLs to avoid duplicates
            saved_page_urls = set()
            
            # Set up progress callback
            def on_progress(progress):
                """Update Redis progress from CrawlProgress."""
                redis_service.set_progress(company_id, {
                    'phase': 'crawling',
                    'pages_crawled': progress.pages_crawled,
                    'pages_queued': progress.pages_queued,
                    'pages_skipped': progress.pages_skipped,
                    'duplicates_found': progress.duplicates_found,
                    'errors_count': progress.errors_count,
                    'external_links_found': progress.external_links_found,
                    'current_url': progress.current_url,
                    'current_activity': progress.current_activity or 'Crawling...',
                })
            
            # Set up checkpoint callback
            def on_checkpoint(checkpoint_data):
                """Save checkpoint to database."""
                # Convert CrawlCheckpoint to CheckpointService format
                visited_urls = list(checkpoint_data.visited_urls)
                queue_state = checkpoint_data.queue_state
                queued_urls = []
                if isinstance(queue_state, dict):
                    queued_urls = [q.get('url', '') for q in queue_state.get('queued_urls', [])]
                
                checkpoint_service.save_checkpoint(
                    company_id=company_id,
                    pages_visited=visited_urls,
                    pages_queued=queued_urls,
                    external_links=[],
                    current_depth=crawl_config.max_depth,
                    entities_count=0,
                    sections_completed=[]
                )
            
            # Set up page callback
            def on_page(crawled_page):
                """Save each crawled page to database immediately."""
                if crawled_page.is_success and crawled_page.url not in saved_page_urls:
                    try:
                        _save_crawled_page(db, company_id, crawled_page, str(crawl_session.id))
                        saved_page_urls.add(crawled_page.url)
                        # Commit periodically to avoid large transactions
                        if len(saved_page_urls) % 10 == 0:
                            db.session.commit()
                    except Exception as e:
                        logger.warning(f"Failed to save page {crawled_page.url} in callback: {e}")
                        # Rollback to recover from failed insert (e.g., SQLite locking)
                        try:
                            db.session.rollback()
                        except Exception:
                            pass
            
            # Set callbacks
            worker.set_callbacks(
                on_progress=on_progress,
                on_checkpoint=on_checkpoint,
                on_page=on_page
            )
            
            # Update initial Redis progress
            redis_service.set_progress(company_id, {
                'phase': 'crawling',
                'pages_crawled': 0,
                'pages_queued': 0,
                'current_activity': 'Starting crawl...'
            })
            
            # Start crawling
            logger.info(f"Starting crawl for company {company_id} at {company.website_url}")
            result = worker.crawl(company.website_url, checkpoint)
            
            # Save any remaining pages that weren't saved in callback
            saved_pages = len(saved_page_urls)
            for crawled_page in result.pages:
                if crawled_page.is_success and crawled_page.url not in saved_page_urls:
                    try:
                        _save_crawled_page(db, company_id, crawled_page, str(crawl_session.id))
                        saved_page_urls.add(crawled_page.url)
                        saved_pages += 1
                    except Exception as e:
                        logger.warning(f"Failed to save page {crawled_page.url}: {e}")
                        try:
                            db.session.rollback()
                        except Exception:
                            pass
            
            # Commit all remaining pages
            try:
                db.session.commit()
            except Exception as e:
                logger.warning(f"Failed to commit pages: {e}")
                db.session.rollback()
            
            # Update crawl session stats
            crawl_session.pages_crawled = result.progress.pages_crawled
            crawl_session.pages_queued = result.progress.pages_queued
            crawl_session.crawl_depth_reached = crawl_config.max_depth
            
            # Update final checkpoint
            if result.checkpoint:
                on_checkpoint(result.checkpoint)
            
            # Determine if crawl completed successfully
            if result.stopped_reason == 'completed' or result.stopped_reason == 'max_pages' or result.stopped_reason == 'max_time':
                crawl_session.status = CrawlStatus.COMPLETED
                company.processing_phase = ProcessingPhase.EXTRACTING
                
                # Dispatch next phase - import here since extract_entities is defined later in this file
                # This avoids circular import issues
                from app.workers.tasks import extract_entities
                extract_entities.delay(company_id)
                
                logger.info(
                    f"Crawl completed for company {company_id}: "
                    f"{saved_pages} pages saved, stopped: {result.stopped_reason}"
                )
            elif result.stopped_reason == 'paused':
                crawl_session.status = CrawlStatus.PAUSED
                company.status = CompanyStatus.PAUSED
                logger.info(f"Crawl paused for company {company_id}")
            else:
                crawl_session.status = CrawlStatus.FAILED
                company.status = CompanyStatus.FAILED
                logger.error(f"Crawl failed for company {company_id}: {result.stopped_reason}")
            
            db.session.commit()
            
            # Update final progress
            redis_service.set_progress(company_id, {
                'phase': company.processing_phase.value,
                'pages_crawled': result.progress.pages_crawled,
                'pages_queued': result.progress.pages_queued,
                'current_activity': f'Crawl {result.stopped_reason}'
            })
            
            return {
                'company_id': company_id,
                'status': 'completed' if result.stopped_reason in ('completed', 'max_pages', 'max_time') else result.stopped_reason,
                'pages_crawled': saved_pages,
                'stopped_reason': result.stopped_reason
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
                try:
                    company = db.session.get(Company, company_id)
                    if company:
                        company.status = CompanyStatus.FAILED
                        db.session.commit()
                except Exception as db_error:
                    logger.error(f"Failed to update company status: {db_error}")
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
    from app import db, create_app
    from app.models import Company, Page, Entity
    from app.models.enums import ProcessingPhase, EntityType
    from app.workers.celery_app import celery_app

    logger.info(f"Starting entity extraction for company {company_id}")

    # Ensure Flask app context is available
    if not hasattr(celery_app, 'flask_app') or celery_app.flask_app is None:
        celery_app.flask_app = create_app()
    flask_app = celery_app.flask_app

    with flask_app.app_context():
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

            # Update phase to ANALYZING and dispatch AI analysis task
            company.processing_phase = ProcessingPhase.ANALYZING
            db.session.commit()

            # Update Redis to reflect new phase
            redis_service.set_progress(company_id, {
                'phase': 'analyzing',
                'entities_extracted': saved_count,
                'current_activity': 'Starting AI analysis...'
            })

            # Dispatch AI analysis task
            from app.workers.tasks import analyze_content
            analyze_content.delay(company_id)
            logger.info(f"Dispatched analyze_content task for company {company_id}")

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
    from app import db, create_app
    from app.models import Company
    from app.models.enums import ProcessingPhase
    from app.analysis.synthesis import analysis_synthesizer
    from app.analysis.prompts import get_section_order, ANALYSIS_SECTIONS
    from app.workers.celery_app import celery_app

    logger.info(f"Starting content analysis for company {company_id}")

    # Ensure Flask app context is available
    if not hasattr(celery_app, 'flask_app') or celery_app.flask_app is None:
        celery_app.flask_app = create_app()
    flask_app = celery_app.flask_app

    with flask_app.app_context():
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

            # Dispatch generate_summary task to finalize
            from app.workers.tasks import generate_summary
            generate_summary.delay(company_id)
            logger.info(f"Dispatched generate_summary task for company {company_id}")

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
    queue='analyze',
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
    from app import db, create_app
    from app.models import Company, Analysis
    from app.models.enums import ProcessingPhase, CompanyStatus
    from app.workers.celery_app import celery_app

    logger.info(f"Starting summary generation for company {company_id}")

    # Ensure Flask app context is available
    if not hasattr(celery_app, 'flask_app') or celery_app.flask_app is None:
        celery_app.flask_app = create_app()
    flask_app = celery_app.flask_app

    with flask_app.app_context():
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
