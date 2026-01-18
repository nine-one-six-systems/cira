"""Batch queue management service for orchestrating batch processing with fair scheduling."""

import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from app.services.redis_service import redis_service
from app.services.job_service import job_service

if TYPE_CHECKING:
    from app.models import BatchJob, Company
    from app.models.enums import BatchStatus, CompanyStatus

logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class BatchQueueService:
    """
    Service for managing batch processing with fair scheduling.

    Features:
    - Batch-level job orchestration
    - Fair scheduling between multiple concurrent batches
    - Batch-level progress tracking
    - Batch cancellation and pause/resume
    - Automatic batch status updates based on company completions
    """

    # Redis keys for batch tracking
    BATCH_PROGRESS_KEY = "batch:{batch_id}:progress"
    BATCH_QUEUE_KEY = "batch_queue"
    PROCESSING_COMPANIES_KEY = "batch:{batch_id}:processing"

    # Default concurrency limits
    DEFAULT_MAX_CONCURRENT_PER_BATCH = 3
    GLOBAL_MAX_CONCURRENT = 10  # Maximum companies processing across all batches

    def _get_db(self):
        """Get db instance lazily to avoid circular import."""
        from app import db
        return db

    def _get_models(self):
        """Get models lazily to avoid circular import."""
        from app.models import BatchJob, Company
        return BatchJob, Company

    def _get_enums(self):
        """Get enums lazily to avoid circular import."""
        from app.models.enums import BatchStatus, CompanyStatus
        return BatchStatus, CompanyStatus

    # ==================== Batch Creation ====================

    def create_batch(
        self,
        company_ids: list[str],
        name: str | None = None,
        description: str | None = None,
        config: dict | None = None,
        priority: int = 100,
        max_concurrent: int | None = None,
        start_immediately: bool = True,
    ) -> dict[str, Any]:
        """
        Create a new batch job and associate companies with it.

        Args:
            company_ids: List of company UUIDs to include in batch
            name: Optional batch name
            description: Optional batch description
            config: Optional shared configuration for all companies
            priority: Priority level (lower = higher priority)
            max_concurrent: Max concurrent companies from this batch
            start_immediately: Whether to start processing immediately

        Returns:
            Dict with batch creation result
        """
        db = self._get_db()
        BatchJob, Company = self._get_models()
        BatchStatus, CompanyStatus = self._get_enums()

        if not company_ids:
            return {
                'success': False,
                'error': 'No company IDs provided'
            }

        # Create batch job
        batch = BatchJob(
            name=name,
            description=description,
            config=config,
            priority=priority,
            max_concurrent=max_concurrent or self.DEFAULT_MAX_CONCURRENT_PER_BATCH,
            total_companies=len(company_ids),
            pending_companies=0,
            processing_companies=0,
            completed_companies=0,
            failed_companies=0,
        )
        db.session.add(batch)
        db.session.flush()  # Get the batch ID

        # Associate companies with batch
        associated_count = 0
        for company_id in company_ids:
            company = db.session.get(Company, company_id)
            if company:
                company.batch_id = batch.id
                # Apply batch config if provided
                if config:
                    company.config = {**(company.config or {}), **config}
                associated_count += 1

        batch.total_companies = associated_count
        batch.pending_companies = associated_count
        db.session.commit()

        logger.info(f"Created batch {batch.id} with {associated_count} companies")

        # Start processing if requested
        if start_immediately and associated_count > 0:
            self.start_batch(batch.id)

        return {
            'success': True,
            'batch_id': batch.id,
            'total_companies': associated_count,
            'status': batch.status.value,
        }

    # ==================== Batch Control Operations ====================

    def start_batch(self, batch_id: str) -> dict[str, Any]:
        """
        Start processing a batch.

        Args:
            batch_id: UUID of the batch

        Returns:
            Dict with start result
        """
        db = self._get_db()
        BatchJob, Company = self._get_models()
        BatchStatus, CompanyStatus = self._get_enums()

        batch = db.session.get(BatchJob, batch_id)
        if not batch:
            return {'success': False, 'error': f'Batch {batch_id} not found'}

        if batch.status == BatchStatus.PROCESSING:
            return {'success': False, 'error': 'Batch already processing'}

        if batch.status == BatchStatus.COMPLETED:
            return {'success': False, 'error': 'Batch already completed'}

        if batch.status == BatchStatus.CANCELLED:
            return {'success': False, 'error': 'Batch was cancelled'}

        # Update batch status
        batch.status = BatchStatus.PROCESSING
        batch.started_at = utcnow()
        db.session.commit()

        # Initialize progress in Redis
        self._update_batch_progress(batch_id)

        # Schedule companies for processing using fair scheduling
        scheduled = self._schedule_batch_companies(batch_id)

        logger.info(f"Started batch {batch_id}, scheduled {scheduled} companies")
        return {
            'success': True,
            'batch_id': batch_id,
            'companies_scheduled': scheduled,
        }

    def pause_batch(self, batch_id: str) -> dict[str, Any]:
        """
        Pause a batch and all its in-progress companies.

        Args:
            batch_id: UUID of the batch

        Returns:
            Dict with pause result
        """
        db = self._get_db()
        BatchJob, Company = self._get_models()
        BatchStatus, CompanyStatus = self._get_enums()

        batch = db.session.get(BatchJob, batch_id)
        if not batch:
            return {'success': False, 'error': f'Batch {batch_id} not found'}

        if batch.status not in (BatchStatus.PROCESSING, BatchStatus.PENDING):
            return {'success': False, 'error': f'Cannot pause batch in {batch.status.value} status'}

        # Pause all in-progress companies in the batch
        in_progress_companies = Company.query.filter_by(
            batch_id=batch_id,
            status=CompanyStatus.IN_PROGRESS
        ).all()

        paused_count = 0
        for company in in_progress_companies:
            try:
                # Use the control endpoint logic to pause each company
                from app.api.routes.control import _pause_company_internal
                result = _pause_company_internal(company.id)
                if result.get('success'):
                    paused_count += 1
            except Exception as e:
                logger.warning(f"Failed to pause company {company.id}: {e}")

        # Update batch status
        batch.status = BatchStatus.PAUSED
        batch.update_counts()
        db.session.commit()

        logger.info(f"Paused batch {batch_id}, paused {paused_count} companies")
        return {
            'success': True,
            'batch_id': batch_id,
            'companies_paused': paused_count,
        }

    def resume_batch(self, batch_id: str) -> dict[str, Any]:
        """
        Resume a paused batch.

        Args:
            batch_id: UUID of the batch

        Returns:
            Dict with resume result
        """
        db = self._get_db()
        BatchJob, Company = self._get_models()
        BatchStatus, CompanyStatus = self._get_enums()

        batch = db.session.get(BatchJob, batch_id)
        if not batch:
            return {'success': False, 'error': f'Batch {batch_id} not found'}

        if batch.status != BatchStatus.PAUSED:
            return {'success': False, 'error': f'Batch is not paused (status: {batch.status.value})'}

        # Resume all paused companies in the batch
        paused_companies = Company.query.filter_by(
            batch_id=batch_id,
            status=CompanyStatus.PAUSED
        ).all()

        resumed_count = 0
        for company in paused_companies:
            try:
                from app.api.routes.control import _resume_company_internal
                result = _resume_company_internal(company.id)
                if result.get('success'):
                    resumed_count += 1
            except Exception as e:
                logger.warning(f"Failed to resume company {company.id}: {e}")

        # Update batch status
        batch.status = BatchStatus.PROCESSING
        batch.update_counts()
        db.session.commit()

        # Schedule any pending companies
        scheduled = self._schedule_batch_companies(batch_id)

        logger.info(f"Resumed batch {batch_id}, resumed {resumed_count} companies, scheduled {scheduled} new")
        return {
            'success': True,
            'batch_id': batch_id,
            'companies_resumed': resumed_count,
            'companies_scheduled': scheduled,
        }

    def cancel_batch(self, batch_id: str) -> dict[str, Any]:
        """
        Cancel a batch and all its pending/in-progress companies.

        Args:
            batch_id: UUID of the batch

        Returns:
            Dict with cancel result
        """
        db = self._get_db()
        BatchJob, Company = self._get_models()
        BatchStatus, CompanyStatus = self._get_enums()

        batch = db.session.get(BatchJob, batch_id)
        if not batch:
            return {'success': False, 'error': f'Batch {batch_id} not found'}

        if batch.status in (BatchStatus.COMPLETED, BatchStatus.CANCELLED):
            return {'success': False, 'error': f'Batch is already {batch.status.value}'}

        # Cancel all pending and in-progress companies
        companies = Company.query.filter(
            Company.batch_id == batch_id,
            Company.status.in_([CompanyStatus.PENDING, CompanyStatus.IN_PROGRESS, CompanyStatus.PAUSED])
        ).all()

        cancelled_count = 0
        for company in companies:
            company.status = CompanyStatus.FAILED
            cancelled_count += 1
            # Clean up Redis data
            redis_service.cleanup_job(company.id)

        # Update batch status
        batch.status = BatchStatus.CANCELLED
        batch.completed_at = utcnow()
        batch.update_counts()
        db.session.commit()

        logger.info(f"Cancelled batch {batch_id}, cancelled {cancelled_count} companies")
        return {
            'success': True,
            'batch_id': batch_id,
            'companies_cancelled': cancelled_count,
        }

    # ==================== Fair Scheduling ====================

    def _schedule_batch_companies(self, batch_id: str) -> int:
        """
        Schedule companies from a batch for processing using fair scheduling.

        Returns:
            Number of companies scheduled
        """
        db = self._get_db()
        BatchJob, Company = self._get_models()
        BatchStatus, CompanyStatus = self._get_enums()

        batch = db.session.get(BatchJob, batch_id)
        if not batch or batch.status != BatchStatus.PROCESSING:
            return 0

        # Count currently processing companies for this batch
        current_processing = Company.query.filter_by(
            batch_id=batch_id,
            status=CompanyStatus.IN_PROGRESS
        ).count()

        # Calculate available slots
        available_slots = min(
            batch.max_concurrent - current_processing,
            self._get_global_available_slots()
        )

        if available_slots <= 0:
            return 0

        # Get pending companies from this batch
        pending_companies = Company.query.filter_by(
            batch_id=batch_id,
            status=CompanyStatus.PENDING
        ).order_by(Company.created_at.asc()).limit(available_slots).all()

        scheduled_count = 0
        for company in pending_companies:
            try:
                result = job_service.start_job(company.id, batch.config)
                if result.get('success'):
                    scheduled_count += 1
            except Exception as e:
                logger.error(f"Failed to start job for company {company.id}: {e}")

        # Update batch counts
        if scheduled_count > 0:
            batch.update_counts()
            db.session.commit()

        return scheduled_count

    def _get_global_available_slots(self) -> int:
        """
        Get number of available processing slots globally.

        Returns:
            Number of available slots
        """
        _, Company = self._get_models()
        _, CompanyStatus = self._get_enums()

        current_processing = Company.query.filter_by(
            status=CompanyStatus.IN_PROGRESS
        ).count()

        return max(0, self.GLOBAL_MAX_CONCURRENT - current_processing)

    def schedule_next_from_all_batches(self) -> int:
        """
        Schedule the next companies from all active batches using fair round-robin.

        This method implements fair scheduling across batches by:
        1. Sorting batches by priority (lower = higher priority)
        2. Round-robin scheduling within same priority
        3. Respecting per-batch and global concurrency limits

        Returns:
            Total number of companies scheduled
        """
        db = self._get_db()
        BatchJob, Company = self._get_models()
        BatchStatus, CompanyStatus = self._get_enums()

        total_scheduled = 0
        global_available = self._get_global_available_slots()

        if global_available <= 0:
            return 0

        # Get all processing batches sorted by priority
        active_batches = BatchJob.query.filter_by(
            status=BatchStatus.PROCESSING
        ).order_by(BatchJob.priority.asc(), BatchJob.created_at.asc()).all()

        if not active_batches:
            return 0

        # Round-robin across batches
        batches_with_pending = list(active_batches)
        while batches_with_pending and global_available > 0:
            scheduled_in_round = 0

            for batch in list(batches_with_pending):
                if global_available <= 0:
                    break

                # Count currently processing for this batch
                current_processing = Company.query.filter_by(
                    batch_id=batch.id,
                    status=CompanyStatus.IN_PROGRESS
                ).count()

                # Check if batch has available slots
                if current_processing >= batch.max_concurrent:
                    continue

                # Get next pending company from this batch
                next_company = Company.query.filter_by(
                    batch_id=batch.id,
                    status=CompanyStatus.PENDING
                ).order_by(Company.created_at.asc()).first()

                if not next_company:
                    batches_with_pending.remove(batch)
                    continue

                # Start the job
                try:
                    result = job_service.start_job(next_company.id, batch.config)
                    if result.get('success'):
                        total_scheduled += 1
                        scheduled_in_round += 1
                        global_available -= 1
                except Exception as e:
                    logger.error(f"Failed to start job for company {next_company.id}: {e}")

            # If no companies were scheduled in this round, break
            if scheduled_in_round == 0:
                break

        # Update batch counts for all active batches
        for batch in active_batches:
            batch.update_counts()
        db.session.commit()

        return total_scheduled

    # ==================== Progress Tracking ====================

    def _update_batch_progress(self, batch_id: str) -> None:
        """Update batch progress in Redis for fast polling."""
        db = self._get_db()
        BatchJob, _ = self._get_models()

        batch = db.session.get(BatchJob, batch_id)
        if not batch:
            return

        progress = {
            'batch_id': batch_id,
            'status': batch.status.value,
            'total': batch.total_companies,
            'pending': batch.pending_companies,
            'processing': batch.processing_companies,
            'completed': batch.completed_companies,
            'failed': batch.failed_companies,
            'progress_percentage': batch.progress_percentage,
            'tokens_used': batch.total_tokens_used,
            'estimated_cost': batch.estimated_cost,
            'updated_at': utcnow().isoformat(),
        }

        redis_service.cache_set(
            f"batch:{batch_id}:progress",
            progress,
            expiry=86400  # 24 hours
        )

    def get_batch_progress(self, batch_id: str) -> dict[str, Any] | None:
        """
        Get batch progress from Redis (with DB fallback).

        Args:
            batch_id: UUID of the batch

        Returns:
            Progress dictionary or None
        """
        # Try Redis first
        progress = redis_service.cache_get(f"batch:{batch_id}:progress")
        if progress:
            return progress

        # Fall back to database - return current stored values
        db = self._get_db()
        BatchJob, _ = self._get_models()

        batch = db.session.get(BatchJob, batch_id)
        if not batch:
            return None

        # Return progress directly from DB values (don't recalculate)
        return {
            'batch_id': batch_id,
            'status': batch.status.value,
            'total': batch.total_companies,
            'pending': batch.pending_companies,
            'processing': batch.processing_companies,
            'completed': batch.completed_companies,
            'failed': batch.failed_companies,
            'progress_percentage': batch.progress_percentage,
            'tokens_used': batch.total_tokens_used,
            'estimated_cost': batch.estimated_cost,
            'updated_at': utcnow().isoformat(),
        }

    # ==================== Batch Status Updates ====================

    def on_company_status_change(
        self,
        company_id: str,
        old_status: "CompanyStatus",
        new_status: "CompanyStatus"
    ) -> None:
        """
        Called when a company's status changes to update batch state.

        Args:
            company_id: UUID of the company
            old_status: Previous status
            new_status: New status
        """
        db = self._get_db()
        BatchJob, Company = self._get_models()
        BatchStatus, CompanyStatus = self._get_enums()

        company = db.session.get(Company, company_id)
        if not company or not company.batch_id:
            return

        batch = db.session.get(BatchJob, company.batch_id)
        if not batch:
            return

        # Update batch counts
        batch.update_counts()
        batch.aggregate_tokens()
        db.session.commit()

        # Update progress in Redis
        self._update_batch_progress(batch.id)

        # Check if we should schedule more companies
        if new_status in (CompanyStatus.COMPLETED, CompanyStatus.FAILED):
            if batch.status == BatchStatus.PROCESSING:
                self._schedule_batch_companies(batch.id)

        logger.debug(
            f"Company {company_id} status changed from {old_status.value} to {new_status.value}, "
            f"batch {batch.id} progress: {batch.progress_percentage}%"
        )

    # ==================== Query Operations ====================

    def get_batch(self, batch_id: str) -> dict[str, Any] | None:
        """
        Get batch details.

        Args:
            batch_id: UUID of the batch

        Returns:
            Batch dictionary or None
        """
        db = self._get_db()
        BatchJob, _ = self._get_models()

        batch = db.session.get(BatchJob, batch_id)
        if not batch:
            return None

        return batch.to_dict()

    def list_batches(
        self,
        status: "BatchStatus | None" = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        List batches with optional filtering.

        Args:
            status: Optional status filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dict with batches and pagination info
        """
        BatchJob, _ = self._get_models()
        BatchStatus, _ = self._get_enums()

        query = BatchJob.query

        if status:
            query = query.filter_by(status=status)

        total = query.count()
        batches = query.order_by(
            BatchJob.created_at.desc()
        ).offset(offset).limit(limit).all()

        return {
            'batches': [b.to_dict() for b in batches],
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    def get_batch_companies(
        self,
        batch_id: str,
        status: "CompanyStatus | None" = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """
        Get companies in a batch.

        Args:
            batch_id: UUID of the batch
            status: Optional status filter
            limit: Maximum results
            offset: Pagination offset

        Returns:
            Dict with companies and pagination info
        """
        _, Company = self._get_models()
        _, CompanyStatus = self._get_enums()

        query = Company.query.filter_by(batch_id=batch_id)

        if status:
            query = query.filter_by(status=status)

        total = query.count()
        companies = query.order_by(
            Company.created_at.asc()
        ).offset(offset).limit(limit).all()

        return {
            'companies': [c.to_dict() for c in companies],
            'total': total,
            'limit': limit,
            'offset': offset,
        }

    # ==================== Cleanup ====================

    def cleanup_completed_batches(self, days_old: int = 7) -> int:
        """
        Clean up completed batches older than specified days.

        Args:
            days_old: Number of days after which to clean up

        Returns:
            Number of batches cleaned up
        """
        from datetime import timedelta

        db = self._get_db()
        BatchJob, Company = self._get_models()
        BatchStatus, _ = self._get_enums()

        cutoff = utcnow() - timedelta(days=days_old)

        # Find old completed/cancelled batches
        old_batches = BatchJob.query.filter(
            BatchJob.status.in_([BatchStatus.COMPLETED, BatchStatus.CANCELLED]),
            BatchJob.completed_at < cutoff
        ).all()

        cleaned_count = 0
        for batch in old_batches:
            # Disassociate companies from batch (don't delete them)
            Company.query.filter_by(batch_id=batch.id).update({'batch_id': None})

            # Delete batch
            db.session.delete(batch)
            cleaned_count += 1

            # Clean up Redis
            redis_service.cache_delete(f"batch:{batch.id}:progress")

        db.session.commit()
        logger.info(f"Cleaned up {cleaned_count} old batches")
        return cleaned_count


# Global service instance
batch_queue_service = BatchQueueService()
