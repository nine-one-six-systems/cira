"""Checkpoint persistence service for pause/resume functionality."""

import logging
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from sqlalchemy.orm.attributes import flag_modified

if TYPE_CHECKING:
    from app.models import Company, CrawlSession

logger = logging.getLogger(__name__)


class CheckpointService:
    """
    Service for managing checkpoint persistence and recovery.

    Checkpoints are persisted to the CrawlSession.checkpoint_data JSON column
    and enable pause/resume functionality with minimal data loss.

    Features:
    - Atomic checkpoint saves
    - Checkpoint validation and recovery
    - Visited URL tracking for deduplication
    - Phase-aware checkpoint loading
    - Graceful handling of corrupted checkpoints
    """

    # Checkpoint structure version for future migrations
    CHECKPOINT_VERSION = 1

    # Default values for checkpoint fields
    DEFAULT_CHECKPOINT = {
        'version': CHECKPOINT_VERSION,
        'pagesVisited': [],
        'pagesQueued': [],
        'externalLinksFound': [],
        'currentDepth': 0,
        'crawlStartTime': None,
        'lastCheckpointTime': None,
        'entitiesExtractedCount': 0,
        'analysisSectionsCompleted': []
    }

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
        from app.models.enums import CrawlStatus
        return CrawlStatus

    def _now(self) -> datetime:
        """Get current UTC time as timezone-aware datetime."""
        return datetime.now(timezone.utc)

    # ==================== Save Operations ====================

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
        Save a checkpoint for a company's crawl session.

        This creates or updates the checkpoint data in the most recent
        CrawlSession for the company.

        Args:
            company_id: UUID of the company
            pages_visited: List of visited page URLs
            pages_queued: List of queued page URLs
            external_links: List of external links found
            current_depth: Current crawl depth
            entities_count: Number of entities extracted
            sections_completed: List of completed analysis sections

        Returns:
            True if checkpoint saved successfully
        """
        db = self._get_db()
        Company = self._get_company_model()
        CrawlSession = self._get_crawl_session_model()
        CrawlStatus = self._get_enums()

        try:
            company = db.session.get(Company, company_id)
            if not company:
                logger.error(f"Cannot save checkpoint: Company {company_id} not found")
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

            # Build checkpoint data with version
            checkpoint_data = {
                'version': self.CHECKPOINT_VERSION,
                'pagesVisited': pages_visited or [],
                'pagesQueued': pages_queued or [],
                'externalLinksFound': external_links or [],
                'currentDepth': current_depth,
                'crawlStartTime': (
                    company.started_at.isoformat()
                    if company.started_at else None
                ),
                'lastCheckpointTime': self._now().isoformat(),
                'entitiesExtractedCount': entities_count,
                'analysisSectionsCompleted': sections_completed or []
            }

            # Update crawl session
            crawl_session.checkpoint_data = checkpoint_data
            crawl_session.pages_crawled = len(pages_visited or [])
            crawl_session.pages_queued = len(pages_queued or [])
            crawl_session.crawl_depth_reached = current_depth
            crawl_session.external_links_followed = len(external_links or [])

            db.session.commit()

            logger.debug(
                f"Checkpoint saved for company {company_id}: "
                f"{len(pages_visited or [])} pages visited, "
                f"{len(pages_queued or [])} queued"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to save checkpoint for {company_id}: {e}")
            db.session.rollback()
            return False

    def update_checkpoint_field(
        self,
        company_id: str,
        field: str,
        value: Any
    ) -> bool:
        """
        Update a single field in the checkpoint.

        Useful for incremental updates without rebuilding the entire checkpoint.

        Args:
            company_id: UUID of the company
            field: Field name to update
            value: New value for the field

        Returns:
            True if update successful
        """
        db = self._get_db()
        CrawlSession = self._get_crawl_session_model()

        try:
            crawl_session = CrawlSession.query.filter_by(
                company_id=company_id
            ).order_by(CrawlSession.created_at.desc()).first()

            if not crawl_session:
                logger.warning(
                    f"Cannot update checkpoint field: No session for {company_id}"
                )
                return False

            # Get existing checkpoint or create new one
            checkpoint = dict(crawl_session.checkpoint_data or self.DEFAULT_CHECKPOINT)
            checkpoint[field] = value
            checkpoint['lastCheckpointTime'] = self._now().isoformat()

            crawl_session.checkpoint_data = checkpoint
            flag_modified(crawl_session, 'checkpoint_data')
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to update checkpoint field for {company_id}: {e}")
            db.session.rollback()
            return False

    def add_visited_url(self, company_id: str, url: str) -> bool:
        """
        Add a URL to the visited pages list.

        Args:
            company_id: UUID of the company
            url: URL that was visited

        Returns:
            True if successful
        """
        db = self._get_db()
        CrawlSession = self._get_crawl_session_model()

        try:
            crawl_session = CrawlSession.query.filter_by(
                company_id=company_id
            ).order_by(CrawlSession.created_at.desc()).first()

            if not crawl_session:
                return False

            checkpoint = dict(crawl_session.checkpoint_data or self.DEFAULT_CHECKPOINT)
            visited = list(checkpoint.get('pagesVisited', []))
            if url not in visited:
                visited.append(url)
                checkpoint['pagesVisited'] = visited

            crawl_session.checkpoint_data = checkpoint
            crawl_session.pages_crawled = len(visited)
            flag_modified(crawl_session, 'checkpoint_data')
            db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to add visited URL for {company_id}: {e}")
            db.session.rollback()
            return False

    # ==================== Load Operations ====================

    def load_checkpoint(self, company_id: str) -> dict[str, Any] | None:
        """
        Load the most recent checkpoint for a company.

        Args:
            company_id: UUID of the company

        Returns:
            Checkpoint data dictionary or None if not found
        """
        CrawlSession = self._get_crawl_session_model()

        try:
            crawl_session = CrawlSession.query.filter_by(
                company_id=company_id
            ).order_by(CrawlSession.created_at.desc()).first()

            if not crawl_session or not crawl_session.checkpoint_data:
                return None

            # Validate and migrate checkpoint if needed
            checkpoint = self._validate_checkpoint(crawl_session.checkpoint_data)
            return checkpoint

        except Exception as e:
            logger.error(f"Failed to load checkpoint for {company_id}: {e}")
            return None

    def _validate_checkpoint(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Validate and repair checkpoint data.

        Handles missing fields, type errors, and version migrations.

        Args:
            data: Raw checkpoint data

        Returns:
            Validated checkpoint data
        """
        if not isinstance(data, dict):
            logger.warning("Checkpoint data is not a dict, using defaults")
            return dict(self.DEFAULT_CHECKPOINT)

        # Merge with defaults to handle missing fields
        checkpoint = dict(self.DEFAULT_CHECKPOINT)
        for key, default_value in self.DEFAULT_CHECKPOINT.items():
            if key in data:
                value = data[key]
                # Type check common fields
                if key in ['pagesVisited', 'pagesQueued', 'externalLinksFound',
                           'analysisSectionsCompleted']:
                    if not isinstance(value, list):
                        logger.warning(f"Checkpoint field {key} not a list, using default")
                        value = default_value
                elif key in ['currentDepth', 'entitiesExtractedCount']:
                    if not isinstance(value, int):
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            logger.warning(
                                f"Checkpoint field {key} not an int, using default"
                            )
                            value = default_value
                checkpoint[key] = value

        return checkpoint

    def get_visited_urls(self, company_id: str) -> set[str]:
        """
        Get the set of visited URLs for deduplication during resume.

        Args:
            company_id: UUID of the company

        Returns:
            Set of visited URLs
        """
        checkpoint = self.load_checkpoint(company_id)
        if checkpoint:
            return set(checkpoint.get('pagesVisited', []))
        return set()

    def get_queued_urls(self, company_id: str) -> list[str]:
        """
        Get the list of queued URLs for resume.

        Args:
            company_id: UUID of the company

        Returns:
            List of queued URLs
        """
        checkpoint = self.load_checkpoint(company_id)
        if checkpoint:
            return checkpoint.get('pagesQueued', [])
        return []

    def get_sections_completed(self, company_id: str) -> list[str]:
        """
        Get the list of completed analysis sections.

        Args:
            company_id: UUID of the company

        Returns:
            List of completed section names
        """
        checkpoint = self.load_checkpoint(company_id)
        if checkpoint:
            return checkpoint.get('analysisSectionsCompleted', [])
        return []

    # ==================== Clear Operations ====================

    def clear_checkpoint(self, company_id: str) -> bool:
        """
        Clear checkpoint data for a company.

        Used when starting a fresh crawl or after successful completion.

        Args:
            company_id: UUID of the company

        Returns:
            True if successful
        """
        db = self._get_db()
        CrawlSession = self._get_crawl_session_model()

        try:
            crawl_session = CrawlSession.query.filter_by(
                company_id=company_id
            ).order_by(CrawlSession.created_at.desc()).first()

            if crawl_session:
                crawl_session.checkpoint_data = None
                db.session.commit()

            return True

        except Exception as e:
            logger.error(f"Failed to clear checkpoint for {company_id}: {e}")
            db.session.rollback()
            return False

    # ==================== Recovery Operations ====================

    def can_resume(self, company_id: str) -> bool:
        """
        Check if a company's job can be resumed from checkpoint.

        Args:
            company_id: UUID of the company

        Returns:
            True if checkpoint exists and is valid
        """
        checkpoint = self.load_checkpoint(company_id)
        if not checkpoint:
            return False

        # Must have at least some progress
        pages_visited = checkpoint.get('pagesVisited', [])
        pages_queued = checkpoint.get('pagesQueued', [])
        entities = checkpoint.get('entitiesExtractedCount', 0)
        sections = checkpoint.get('analysisSectionsCompleted', [])

        return bool(pages_visited or pages_queued or entities or sections)

    def get_resume_phase(self, company_id: str) -> str | None:
        """
        Determine which phase to resume at based on checkpoint.

        Args:
            company_id: UUID of the company

        Returns:
            Phase name to resume at, or None if no valid checkpoint
        """
        checkpoint = self.load_checkpoint(company_id)
        if not checkpoint:
            return None

        sections = checkpoint.get('analysisSectionsCompleted', [])
        entities = checkpoint.get('entitiesExtractedCount', 0)
        pages_visited = checkpoint.get('pagesVisited', [])
        pages_queued = checkpoint.get('pagesQueued', [])

        # Determine phase based on progress
        if sections:
            # Has analysis progress, resume at analyzing or generating
            return 'analyzing'
        elif entities > 0:
            # Has extracted entities, resume at analyzing
            return 'analyzing'
        elif pages_visited:
            # Has crawled pages, resume at extracting
            return 'extracting'
        elif pages_queued:
            # Has queued pages, resume at crawling
            return 'crawling'
        else:
            # No meaningful progress, start fresh
            return 'queued'

    def get_checkpoint_stats(self, company_id: str) -> dict[str, Any] | None:
        """
        Get summary statistics from checkpoint.

        Args:
            company_id: UUID of the company

        Returns:
            Dict with checkpoint statistics or None
        """
        checkpoint = self.load_checkpoint(company_id)
        if not checkpoint:
            return None

        return {
            'pagesVisited': len(checkpoint.get('pagesVisited', [])),
            'pagesQueued': len(checkpoint.get('pagesQueued', [])),
            'externalLinksFound': len(checkpoint.get('externalLinksFound', [])),
            'currentDepth': checkpoint.get('currentDepth', 0),
            'entitiesExtracted': checkpoint.get('entitiesExtractedCount', 0),
            'sectionsCompleted': len(checkpoint.get('analysisSectionsCompleted', [])),
            'lastCheckpointTime': checkpoint.get('lastCheckpointTime')
        }


# Global service instance
checkpoint_service = CheckpointService()
