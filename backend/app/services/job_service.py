"""Job queue management service for analysis pipeline orchestration."""

import logging
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

from app.services.redis_service import redis_service

if TYPE_CHECKING:
    from app.models import Company
    from app.models.enums import CompanyStatus, ProcessingPhase

logger = logging.getLogger(__name__)


class JobService:
    """
    Service for managing the analysis pipeline job queue.

    Pipeline stages:
    1. QUEUED - Job created, waiting to start
    2. CRAWLING - Web crawler fetching pages
    3. EXTRACTING - Entity extraction with spaCy
    4. ANALYZING - AI analysis with Claude
    5. GENERATING - Summary generation
    6. COMPLETED - All processing done

    Features:
    - Pipeline orchestration with proper state transitions
    - Automatic job recovery on startup
    - Failure handling with proper status updates
    - Stage transition logging
    """

    # Stale job threshold (1 hour)
    STALE_JOB_THRESHOLD_SECONDS = 3600

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
        from app.models.enums import CompanyStatus, ProcessingPhase, CrawlStatus
        return CompanyStatus, ProcessingPhase, CrawlStatus

    def _get_phase_order(self):
        """Get processing phase order lazily."""
        _, ProcessingPhase, _ = self._get_enums()
        return [
            ProcessingPhase.QUEUED,
            ProcessingPhase.CRAWLING,
            ProcessingPhase.EXTRACTING,
            ProcessingPhase.ANALYZING,
            ProcessingPhase.GENERATING,
            ProcessingPhase.COMPLETED,
        ]

    def _get_valid_transitions(self):
        """Get valid transitions map lazily."""
        _, ProcessingPhase, _ = self._get_enums()
        return {
            ProcessingPhase.QUEUED: [ProcessingPhase.CRAWLING],
            ProcessingPhase.CRAWLING: [ProcessingPhase.EXTRACTING, ProcessingPhase.COMPLETED],
            ProcessingPhase.EXTRACTING: [ProcessingPhase.ANALYZING],
            ProcessingPhase.ANALYZING: [ProcessingPhase.GENERATING],
            ProcessingPhase.GENERATING: [ProcessingPhase.COMPLETED],
            ProcessingPhase.COMPLETED: [],
        }

    def start_job(self, company_id: str, config: dict | None = None) -> dict[str, Any]:
        """
        Start a new analysis job for a company.

        Args:
            company_id: UUID of the company
            config: Optional configuration overrides

        Returns:
            Dict with job start status
        """
        db = self._get_db()
        Company = self._get_company_model()
        CompanyStatus, ProcessingPhase, _ = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Check if already processing
        if company.status == CompanyStatus.IN_PROGRESS:
            logger.warning(f"Job already in progress for company {company_id}")
            return {
                'success': False,
                'error': 'Job already in progress',
                'company_id': company_id
            }

        # Reset status if needed
        company.status = CompanyStatus.IN_PROGRESS
        company.processing_phase = ProcessingPhase.QUEUED
        company.started_at = datetime.utcnow()
        company.completed_at = None
        db.session.commit()

        # Update Redis
        self._update_redis_status(company_id, company.status, company.processing_phase)

        # Queue the first task
        self._dispatch_next_phase(company_id, config)

        logger.info(f"Started job for company {company_id}")
        return {
            'success': True,
            'company_id': company_id,
            'status': company.status.value,
            'phase': company.processing_phase.value
        }

    def transition_phase(
        self,
        company_id: str,
        next_phase: "ProcessingPhase",
        config: dict | None = None
    ) -> bool:
        """
        Transition a job to the next processing phase.

        Args:
            company_id: UUID of the company
            next_phase: The phase to transition to
            config: Optional configuration overrides

        Returns:
            True if transition successful
        """
        db = self._get_db()
        Company = self._get_company_model()
        CompanyStatus, ProcessingPhase, _ = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company:
            logger.error(f"Company {company_id} not found for phase transition")
            return False

        current_phase = company.processing_phase
        valid_transitions = self._get_valid_transitions()

        # Validate transition
        if next_phase not in valid_transitions.get(current_phase, []):
            logger.warning(
                f"Invalid phase transition from {current_phase} to {next_phase} "
                f"for company {company_id}"
            )
            return False

        # Update phase
        company.processing_phase = next_phase
        db.session.commit()

        # Log transition
        logger.info(
            f"Company {company_id} transitioned from {current_phase.value} "
            f"to {next_phase.value}"
        )

        # Update Redis
        self._update_redis_status(company_id, company.status, next_phase)

        # Handle completion
        if next_phase == ProcessingPhase.COMPLETED:
            self._complete_job(company_id)
        else:
            # Dispatch next phase task
            self._dispatch_next_phase(company_id, config)

        return True

    def fail_job(
        self,
        company_id: str,
        error_message: str | None = None,
        preserve_progress: bool = True
    ) -> bool:
        """
        Mark a job as failed.

        Args:
            company_id: UUID of the company
            error_message: Optional error message
            preserve_progress: Whether to preserve partial progress

        Returns:
            True if successful
        """
        db = self._get_db()
        Company = self._get_company_model()
        CompanyStatus, _, _ = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company:
            logger.error(f"Company {company_id} not found for failure marking")
            return False

        # Update status
        company.status = CompanyStatus.FAILED
        db.session.commit()

        # Log failure
        logger.error(
            f"Job failed for company {company_id} at phase {company.processing_phase.value}: "
            f"{error_message or 'Unknown error'}"
        )

        # Update Redis
        self._update_redis_status(company_id, CompanyStatus.FAILED, company.processing_phase)
        redis_service.set_activity(company_id, f"Failed: {error_message or 'Unknown error'}")

        # Clean up Redis job data if not preserving
        if not preserve_progress:
            redis_service.cleanup_job(company_id)

        return True

    def _complete_job(self, company_id: str) -> None:
        """Complete a job and update all statuses."""
        db = self._get_db()
        Company = self._get_company_model()
        CompanyStatus, ProcessingPhase, _ = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company:
            return

        company.status = CompanyStatus.COMPLETED
        company.completed_at = datetime.utcnow()
        db.session.commit()

        # Update Redis
        self._update_redis_status(company_id, CompanyStatus.COMPLETED, ProcessingPhase.COMPLETED)
        redis_service.set_activity(company_id, "Analysis completed")

        logger.info(f"Job completed for company {company_id}")

    def _dispatch_next_phase(self, company_id: str, config: dict | None = None) -> None:
        """Dispatch the task for the current phase."""
        db = self._get_db()
        Company = self._get_company_model()
        _, ProcessingPhase, _ = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company:
            return

        phase = company.processing_phase

        # Import here to avoid circular imports
        from app.workers.tasks import (
            crawl_company,
            extract_entities,
            analyze_content,
            generate_summary,
        )

        # Dispatch task based on phase
        if phase == ProcessingPhase.QUEUED:
            crawl_company.delay(company_id, config)
            logger.debug(f"Dispatched crawl task for company {company_id}")
        elif phase == ProcessingPhase.CRAWLING:
            # Crawling is already in progress
            pass
        elif phase == ProcessingPhase.EXTRACTING:
            extract_entities.delay(company_id)
            logger.debug(f"Dispatched extraction task for company {company_id}")
        elif phase == ProcessingPhase.ANALYZING:
            analyze_content.delay(company_id)
            logger.debug(f"Dispatched analysis task for company {company_id}")
        elif phase == ProcessingPhase.GENERATING:
            generate_summary.delay(company_id)
            logger.debug(f"Dispatched summary task for company {company_id}")

    def _update_redis_status(
        self,
        company_id: str,
        status: "CompanyStatus",
        phase: "ProcessingPhase"
    ) -> None:
        """Update job status in Redis."""
        redis_service.set_job_status(company_id, {
            'status': status.value,
            'phase': phase.value,
            'updated_at': datetime.utcnow().isoformat()
        })

    # ==================== Recovery Operations ====================

    def recover_in_progress_jobs(self) -> list[str]:
        """
        Recover jobs that were in_progress when server shut down.

        This should be called on application startup.

        Returns:
            List of company IDs that were recovered
        """
        db = self._get_db()
        Company = self._get_company_model()
        CompanyStatus, ProcessingPhase, _ = self._get_enums()

        recovered = []

        # Find all in_progress jobs
        in_progress = Company.query.filter_by(status=CompanyStatus.IN_PROGRESS).all()

        for company in in_progress:
            company_id = str(company.id)

            # Check if job is stale (no progress for threshold duration)
            if self._is_stale_job(company):
                logger.warning(f"Marking stale job {company_id} as failed")
                self.fail_job(company_id, "Job stale - no progress for extended period")
                continue

            # Attempt to resume from checkpoint
            if self._resume_from_checkpoint(company):
                recovered.append(company_id)
                logger.info(f"Recovered job {company_id} from checkpoint")
            else:
                # No valid checkpoint, restart from beginning
                company.processing_phase = ProcessingPhase.QUEUED
                db.session.commit()
                self._dispatch_next_phase(company_id)
                recovered.append(company_id)
                logger.info(f"Restarted job {company_id} from beginning")

        return recovered

    def _is_stale_job(self, company: "Company") -> bool:
        """Check if a job is stale (no updates for extended period)."""
        # Check Redis for recent activity
        status = redis_service.get_job_status(str(company.id))
        if status:
            try:
                updated_at = datetime.fromisoformat(status.get('updated_at', ''))
                elapsed = datetime.utcnow() - updated_at
                if elapsed.total_seconds() < self.STALE_JOB_THRESHOLD_SECONDS:
                    return False
            except (ValueError, TypeError):
                pass

        # Fall back to database timestamps
        check_time = company.updated_at or company.started_at
        if check_time:
            elapsed = datetime.utcnow() - check_time
            return elapsed.total_seconds() > self.STALE_JOB_THRESHOLD_SECONDS

        return True  # No timestamp, consider stale

    def _resume_from_checkpoint(self, company: "Company") -> bool:
        """
        Resume a job from its checkpoint.

        Args:
            company: Company model instance

        Returns:
            True if successfully resumed from checkpoint
        """
        db = self._get_db()
        CrawlSession = self._get_crawl_session_model()
        _, ProcessingPhase, _ = self._get_enums()

        # Get the latest crawl session with checkpoint
        crawl_session = CrawlSession.query.filter_by(
            company_id=company.id
        ).order_by(CrawlSession.created_at.desc()).first()

        if not crawl_session or not crawl_session.checkpoint_data:
            return False

        # Validate checkpoint data
        checkpoint = crawl_session.checkpoint_data
        if not isinstance(checkpoint, dict):
            return False

        # Resume based on what phase the checkpoint indicates
        analysis_sections = checkpoint.get('analysisSectionsCompleted', [])
        entities_count = checkpoint.get('entitiesExtractedCount', 0)
        pages_visited = checkpoint.get('pagesVisited', [])

        # Determine which phase to resume at
        if analysis_sections:
            # Resume at analysis or generation
            company.processing_phase = ProcessingPhase.ANALYZING
        elif entities_count > 0:
            # Resume at analysis
            company.processing_phase = ProcessingPhase.ANALYZING
        elif pages_visited:
            # Resume at extraction
            company.processing_phase = ProcessingPhase.EXTRACTING
        else:
            # Start over
            company.processing_phase = ProcessingPhase.QUEUED

        db.session.commit()
        self._dispatch_next_phase(str(company.id))
        return True

    # ==================== Queue Management ====================

    def get_queue_status(self) -> dict[str, Any]:
        """
        Get current queue status.

        Returns:
            Dict with queue statistics
        """
        Company = self._get_company_model()
        CompanyStatus, ProcessingPhase, _ = self._get_enums()

        pending = Company.query.filter_by(status=CompanyStatus.PENDING).count()
        in_progress = Company.query.filter_by(status=CompanyStatus.IN_PROGRESS).count()
        completed = Company.query.filter_by(status=CompanyStatus.COMPLETED).count()
        failed = Company.query.filter_by(status=CompanyStatus.FAILED).count()
        paused = Company.query.filter_by(status=CompanyStatus.PAUSED).count()

        # Get phase breakdown for in_progress jobs
        phase_breakdown = {}
        for phase in ProcessingPhase:
            count = Company.query.filter_by(
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=phase
            ).count()
            if count > 0:
                phase_breakdown[phase.value] = count

        return {
            'pending': pending,
            'in_progress': in_progress,
            'completed': completed,
            'failed': failed,
            'paused': paused,
            'total': pending + in_progress + completed + failed + paused,
            'phase_breakdown': phase_breakdown
        }

    def get_jobs_by_status(
        self,
        status: "CompanyStatus",
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get jobs by status.

        Args:
            status: Status to filter by
            limit: Maximum number of results

        Returns:
            List of job summaries
        """
        Company = self._get_company_model()

        companies = Company.query.filter_by(status=status).limit(limit).all()
        return [
            {
                'id': str(c.id),
                'name': c.company_name,
                'status': c.status.value,
                'phase': c.processing_phase.value,
                'started_at': c.started_at.isoformat() if c.started_at else None,
                'completed_at': c.completed_at.isoformat() if c.completed_at else None,
            }
            for c in companies
        ]


# Global service instance
job_service = JobService()
