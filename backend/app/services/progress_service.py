"""Progress state management service for pause/resume and progress tracking."""

import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from app.services.redis_service import redis_service

if TYPE_CHECKING:
    from app.models import Company, CrawlSession
    from app.models.enums import CompanyStatus

logger = logging.getLogger(__name__)


class ProgressService:
    """
    Service for managing progress state, pause/resume functionality, and checkpoints.

    Features:
    - Pause/resume operations with proper state management
    - Progress tracking for UI polling
    - Checkpoint triggering based on page count or time interval
    - Timeout handling with remaining time calculation
    - Concurrent access protection via distributed locking
    """

    # Checkpoint intervals
    CHECKPOINT_PAGE_INTERVAL = 10  # Save checkpoint every N pages
    CHECKPOINT_TIME_INTERVAL_SECONDS = 120  # Save checkpoint every N seconds
    DEFAULT_TIMEOUT_SECONDS = 3600  # 1 hour default job timeout

    def _get_db(self):
        """Get db instance lazily to avoid circular import."""
        from app import db
        return db

    def _get_company_model(self):
        """Get Company model lazily to avoid circular import."""
        from app.models import Company
        return Company

    def _get_crawl_session_model(self):
        """Get CrawlSession model lazily to avoid circular import."""
        from app.models import CrawlSession
        return CrawlSession

    def _get_enums(self):
        """Get enum classes lazily to avoid circular import."""
        from app.models.enums import CompanyStatus, CrawlStatus
        return CompanyStatus, CrawlStatus

    def _now(self) -> datetime:
        """Get current UTC time as timezone-aware datetime."""
        return datetime.now(timezone.utc)

    # ==================== Pause/Resume Operations ====================

    def pause_job(self, company_id: str, worker_id: str | None = None) -> dict[str, Any]:
        """
        Pause an in-progress job.

        Args:
            company_id: UUID of the company
            worker_id: Optional worker ID for lock verification

        Returns:
            Dict with pause status and any errors
        """
        db = self._get_db()
        Company = self._get_company_model()
        CompanyStatus, CrawlStatus = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company:
            return {'success': False, 'error': 'Company not found'}

        # Verify status allows pause
        if company.status != CompanyStatus.IN_PROGRESS:
            return {
                'success': False,
                'error': f'Cannot pause job with status {company.status.value}'
            }

        # Acquire lock to ensure exclusive access
        if worker_id and not redis_service.acquire_lock(company_id, worker_id):
            return {
                'success': False,
                'error': 'Job is locked by another worker'
            }

        try:
            # Save checkpoint immediately
            self._save_checkpoint(company_id)

            # Update company status
            company.status = CompanyStatus.PAUSED
            company.paused_at = self._now()
            db.session.commit()

            # Update Redis status
            redis_service.set_job_status(company_id, {
                'status': CompanyStatus.PAUSED.value,
                'phase': company.processing_phase.value,
                'paused_at': company.paused_at.isoformat()
            })
            redis_service.set_activity(company_id, 'Paused')

            logger.info(f"Job paused for company {company_id}")
            return {
                'success': True,
                'company_id': company_id,
                'status': CompanyStatus.PAUSED.value,
                'paused_at': company.paused_at.isoformat()
            }

        finally:
            if worker_id:
                redis_service.release_lock(company_id, worker_id)

    def resume_job(
        self,
        company_id: str,
        worker_id: str | None = None,
        config: dict | None = None
    ) -> dict[str, Any]:
        """
        Resume a paused job.

        Args:
            company_id: UUID of the company
            worker_id: Optional worker ID for lock acquisition
            config: Optional configuration overrides

        Returns:
            Dict with resume status and any errors
        """
        db = self._get_db()
        Company = self._get_company_model()
        CompanyStatus, _ = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company:
            return {'success': False, 'error': 'Company not found'}

        # Verify status allows resume
        valid_resume_statuses = [CompanyStatus.PAUSED]
        if company.status not in valid_resume_statuses:
            return {
                'success': False,
                'error': f'Cannot resume job with status {company.status.value}'
            }

        # Acquire lock to ensure exclusive access
        lock_id = worker_id or f"resume-{company_id}"
        if not redis_service.acquire_lock(company_id, lock_id):
            return {
                'success': False,
                'error': 'Job is locked by another worker'
            }

        try:
            # Calculate pause duration
            if company.paused_at:
                paused_at = company.paused_at
                if paused_at.tzinfo is None:
                    paused_at = paused_at.replace(tzinfo=timezone.utc)
                pause_duration_ms = int(
                    (self._now() - paused_at).total_seconds() * 1000
                )
                company.total_paused_duration_ms += pause_duration_ms

            # Update company status
            company.status = CompanyStatus.IN_PROGRESS
            company.paused_at = None
            db.session.commit()

            # Update Redis status
            redis_service.set_job_status(company_id, {
                'status': CompanyStatus.IN_PROGRESS.value,
                'phase': company.processing_phase.value,
                'resumed_at': self._now().isoformat()
            })
            redis_service.set_activity(company_id, 'Resuming from checkpoint...')

            # Dispatch the appropriate task based on current phase
            self._dispatch_resume_task(company_id, config)

            logger.info(f"Job resumed for company {company_id}")
            return {
                'success': True,
                'company_id': company_id,
                'status': CompanyStatus.IN_PROGRESS.value,
                'phase': company.processing_phase.value
            }

        except Exception as e:
            logger.error(f"Failed to resume job {company_id}: {e}")
            return {'success': False, 'error': str(e)}

        finally:
            redis_service.release_lock(company_id, lock_id)

    def _dispatch_resume_task(self, company_id: str, config: dict | None = None) -> None:
        """Dispatch the appropriate task to resume processing."""
        from app.services.job_service import job_service
        job_service._dispatch_next_phase(company_id, config)

    # ==================== Progress Tracking ====================

    def update_progress(
        self,
        company_id: str,
        phase: str,
        pages_crawled: int = 0,
        pages_queued: int = 0,
        entities_extracted: int = 0,
        sections_completed: list[str] | None = None,
        current_activity: str | None = None,
        percentage: int | None = None
    ) -> bool:
        """
        Update progress for a job.

        Args:
            company_id: UUID of the company
            phase: Current processing phase
            pages_crawled: Number of pages crawled
            pages_queued: Number of pages in queue
            entities_extracted: Number of entities extracted
            sections_completed: List of completed analysis sections
            current_activity: Description of current activity
            percentage: Overall completion percentage (0-100)

        Returns:
            True if successful
        """
        progress = {
            'phase': phase,
            'pages_crawled': pages_crawled,
            'pages_queued': pages_queued,
            'entities_extracted': entities_extracted,
            'sections_completed': sections_completed or [],
            'updated_at': self._now().isoformat()
        }

        if percentage is not None:
            progress['percentage'] = min(100, max(0, percentage))

        success = redis_service.set_progress(company_id, progress)

        if current_activity:
            redis_service.set_activity(company_id, current_activity)

        return success

    def get_progress(self, company_id: str) -> dict[str, Any] | None:
        """
        Get progress for a job.

        Args:
            company_id: UUID of the company

        Returns:
            Progress dictionary or None
        """
        progress = redis_service.get_progress(company_id)
        if progress:
            # Add activity if available
            activity = redis_service.get_activity(company_id)
            if activity:
                progress['current_activity'] = activity
        return progress

    # ==================== Checkpoint Management ====================

    def should_checkpoint(
        self,
        company_id: str,
        pages_since_checkpoint: int,
        seconds_since_checkpoint: float
    ) -> bool:
        """
        Determine if a checkpoint should be saved.

        Args:
            company_id: UUID of the company
            pages_since_checkpoint: Pages crawled since last checkpoint
            seconds_since_checkpoint: Seconds elapsed since last checkpoint

        Returns:
            True if checkpoint should be saved
        """
        return (
            pages_since_checkpoint >= self.CHECKPOINT_PAGE_INTERVAL or
            seconds_since_checkpoint >= self.CHECKPOINT_TIME_INTERVAL_SECONDS
        )

    def _save_checkpoint(self, company_id: str) -> bool:
        """
        Save current progress as checkpoint.

        Args:
            company_id: UUID of the company

        Returns:
            True if successful
        """
        db = self._get_db()
        Company = self._get_company_model()
        CrawlSession = self._get_crawl_session_model()

        company = db.session.get(Company, company_id)
        if not company:
            return False

        # Get current progress from Redis
        progress = redis_service.get_progress(company_id)
        if not progress:
            progress = {}

        # Get or create crawl session
        crawl_session = CrawlSession.query.filter_by(
            company_id=company_id
        ).order_by(CrawlSession.created_at.desc()).first()

        if not crawl_session:
            _, CrawlStatus = self._get_enums()
            crawl_session = CrawlSession(
                company_id=company_id,
                status=CrawlStatus.ACTIVE
            )
            db.session.add(crawl_session)

        # Build checkpoint data
        checkpoint_data = {
            'pagesVisited': progress.get('pages_visited', []),
            'pagesQueued': progress.get('pages_queued_urls', []),
            'externalLinksFound': progress.get('external_links', []),
            'currentDepth': progress.get('current_depth', 0),
            'crawlStartTime': company.started_at.isoformat() if company.started_at else None,
            'lastCheckpointTime': self._now().isoformat(),
            'entitiesExtractedCount': progress.get('entities_extracted', 0),
            'analysisSectionsCompleted': progress.get('sections_completed', [])
        }

        # Save to crawl session
        crawl_session.checkpoint_data = checkpoint_data
        crawl_session.pages_crawled = progress.get('pages_crawled', 0)
        crawl_session.pages_queued = progress.get('pages_queued', 0)
        db.session.commit()

        logger.debug(f"Checkpoint saved for company {company_id}")
        return True

    def save_checkpoint(
        self,
        company_id: str,
        pages_visited: list[str] | None = None,
        pages_queued: list[str] | None = None,
        external_links: list[str] | None = None,
        current_depth: int = 0,
        entities_count: int = 0,
        sections_completed: list[str] | None = None
    ) -> bool:
        """
        Save checkpoint with provided data.

        Args:
            company_id: UUID of the company
            pages_visited: List of visited page URLs
            pages_queued: List of queued page URLs
            external_links: List of external links found
            current_depth: Current crawl depth
            entities_count: Number of entities extracted
            sections_completed: List of completed analysis sections

        Returns:
            True if successful
        """
        db = self._get_db()
        Company = self._get_company_model()
        CrawlSession = self._get_crawl_session_model()
        _, CrawlStatus = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company:
            return False

        # Get or create crawl session
        crawl_session = CrawlSession.query.filter_by(
            company_id=company_id
        ).order_by(CrawlSession.created_at.desc()).first()

        if not crawl_session:
            crawl_session = CrawlSession(
                company_id=company_id,
                status=CrawlStatus.ACTIVE
            )
            db.session.add(crawl_session)

        # Build checkpoint data
        checkpoint_data = {
            'pagesVisited': pages_visited or [],
            'pagesQueued': pages_queued or [],
            'externalLinksFound': external_links or [],
            'currentDepth': current_depth,
            'crawlStartTime': company.started_at.isoformat() if company.started_at else None,
            'lastCheckpointTime': self._now().isoformat(),
            'entitiesExtractedCount': entities_count,
            'analysisSectionsCompleted': sections_completed or []
        }

        # Save to crawl session
        crawl_session.checkpoint_data = checkpoint_data
        crawl_session.pages_crawled = len(pages_visited or [])
        crawl_session.pages_queued = len(pages_queued or [])
        crawl_session.crawl_depth_reached = current_depth
        db.session.commit()

        logger.debug(f"Checkpoint saved for company {company_id}")
        return True

    def load_checkpoint(self, company_id: str) -> dict[str, Any] | None:
        """
        Load the last checkpoint for a job.

        Args:
            company_id: UUID of the company

        Returns:
            Checkpoint data or None
        """
        CrawlSession = self._get_crawl_session_model()

        crawl_session = CrawlSession.query.filter_by(
            company_id=company_id
        ).order_by(CrawlSession.created_at.desc()).first()

        if not crawl_session or not crawl_session.checkpoint_data:
            return None

        return crawl_session.checkpoint_data

    def get_visited_urls(self, company_id: str) -> set[str]:
        """
        Get set of visited URLs for deduplication on resume.

        Args:
            company_id: UUID of the company

        Returns:
            Set of visited URLs
        """
        checkpoint = self.load_checkpoint(company_id)
        if checkpoint:
            return set(checkpoint.get('pagesVisited', []))
        return set()

    # ==================== Timeout Handling ====================

    def get_remaining_time(
        self,
        company_id: str,
        timeout_seconds: int | None = None
    ) -> int:
        """
        Get remaining time for a job, accounting for pauses.

        Args:
            company_id: UUID of the company
            timeout_seconds: Custom timeout in seconds

        Returns:
            Remaining seconds, or -1 if no timeout
        """
        db = self._get_db()
        Company = self._get_company_model()

        company = db.session.get(Company, company_id)
        if not company or not company.started_at:
            return -1

        timeout = timeout_seconds or self.DEFAULT_TIMEOUT_SECONDS

        # Calculate elapsed time
        # Handle both timezone-aware and naive datetimes
        started_at = company.started_at
        if started_at.tzinfo is None:
            # Make naive datetime timezone-aware (assume UTC)
            started_at = started_at.replace(tzinfo=timezone.utc)

        now = self._now()
        elapsed = (now - started_at).total_seconds()

        # Subtract paused duration
        paused_seconds = company.total_paused_duration_ms / 1000

        effective_elapsed = elapsed - paused_seconds
        remaining = timeout - effective_elapsed

        return max(0, int(remaining))

    def is_timeout(
        self,
        company_id: str,
        timeout_seconds: int | None = None
    ) -> bool:
        """
        Check if a job has timed out.

        Args:
            company_id: UUID of the company
            timeout_seconds: Custom timeout in seconds

        Returns:
            True if timed out
        """
        remaining = self.get_remaining_time(company_id, timeout_seconds)
        return remaining == 0

    def handle_timeout(self, company_id: str) -> dict[str, Any]:
        """
        Handle job timeout by saving checkpoint and updating status.

        Args:
            company_id: UUID of the company

        Returns:
            Dict with timeout handling status
        """
        db = self._get_db()
        Company = self._get_company_model()
        CompanyStatus, _ = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company:
            return {'success': False, 'error': 'Company not found'}

        # Save checkpoint before timeout
        self._save_checkpoint(company_id)

        # Note: TIMEOUT is not in the current enum, using FAILED with a marker
        # In production, you'd add a TIMEOUT status to the enum
        company.status = CompanyStatus.FAILED  # Would be TIMEOUT
        db.session.commit()

        # Update Redis
        redis_service.set_job_status(company_id, {
            'status': 'timeout',
            'phase': company.processing_phase.value,
            'timed_out_at': self._now().isoformat()
        })
        redis_service.set_activity(company_id, 'Job timed out - partial results available')

        logger.info(f"Job timed out for company {company_id}")
        return {
            'success': True,
            'company_id': company_id,
            'status': 'timeout',
            'phase': company.processing_phase.value
        }

    # ==================== Job State Queries ====================

    def get_job_state(self, company_id: str) -> dict[str, Any] | None:
        """
        Get complete job state including checkpoint.

        Args:
            company_id: UUID of the company

        Returns:
            Complete job state or None
        """
        db = self._get_db()
        Company = self._get_company_model()

        company = db.session.get(Company, company_id)
        if not company:
            return None

        checkpoint = self.load_checkpoint(company_id)

        return {
            'companyId': company_id,
            'status': company.status.value,
            'phase': company.processing_phase.value,
            'startedAt': company.started_at.isoformat() if company.started_at else None,
            'pausedAt': company.paused_at.isoformat() if company.paused_at else None,
            'totalPausedDuration': company.total_paused_duration_ms,
            'checkpoint': checkpoint
        }


# Global service instance
progress_service = ProgressService()
