"""Shared fixtures for state management integration testing.

Provides mock checkpoint data, mock Redis service, and factory functions
for creating companies with various state management configurations.

Requirements covered: STA-01 (checkpoint persistence), STA-02 (pause), STA-03 (resume)
"""

from datetime import datetime, timezone, timedelta
from typing import Any
from unittest.mock import MagicMock


# ==================== Checkpoint Configuration ====================

CHECKPOINT_INTERVALS = {
    'PAGE_INTERVAL': 10,           # Save checkpoint every 10 pages
    'TIME_INTERVAL_SECONDS': 120,  # Save checkpoint every 2 minutes
    'DEFAULT_TIMEOUT_SECONDS': 3600,  # 1 hour default job timeout
}


# ==================== Mock Checkpoint Data ====================

def _iso_timestamp(delta_minutes: int = 0) -> str:
    """Generate ISO timestamp with optional offset."""
    dt = datetime.now(timezone.utc) - timedelta(minutes=delta_minutes)
    return dt.isoformat()


MOCK_CHECKPOINT_DATA = {
    'version': 1,
    'pagesVisited': [
        'https://example.com/',
        'https://example.com/about',
        'https://example.com/team',
        'https://example.com/products',
        'https://example.com/services',
        'https://example.com/contact',
        'https://example.com/careers',
        'https://example.com/blog',
        'https://example.com/news',
        'https://example.com/pricing',
        'https://example.com/faq',
        'https://example.com/support',
        'https://example.com/about/mission',
        'https://example.com/about/history',
        'https://example.com/team/leadership',
    ],
    'pagesQueued': [
        'https://example.com/about/values',
        'https://example.com/team/engineering',
        'https://example.com/products/enterprise',
        'https://example.com/services/consulting',
        'https://example.com/careers/jobs',
    ],
    'externalLinksFound': [
        'https://linkedin.com/company/example',
        'https://twitter.com/example',
        'https://github.com/example',
    ],
    'currentDepth': 2,
    'entitiesExtractedCount': 42,
    'analysisSectionsCompleted': ['executive_summary', 'company_overview'],
    'crawlStartTime': _iso_timestamp(30),  # Started 30 minutes ago
    'lastCheckpointTime': _iso_timestamp(2),  # Last checkpoint 2 minutes ago
}


MOCK_PROGRESS_DATA = {
    'pagesCrawled': 15,
    'pagesTotal': 25,
    'entitiesExtracted': 42,
    'tokensUsed': 5000,
    'timeElapsed': 120,
    'currentActivity': 'Crawling page 16 of 25',
    'phase': 'crawling',
    'percentage': 60,
}


# ==================== Mock Redis Service ====================

class MockRedisService:
    """
    Mock Redis service for state management testing.

    Stores data in memory dict and tracks all method calls
    for verification in tests.
    """

    def __init__(self):
        """Initialize mock Redis with empty storage."""
        self._progress: dict[str, dict] = {}
        self._job_status: dict[str, dict] = {}
        self._activity: dict[str, str] = {}
        self._locks: dict[str, str] = {}
        self.call_log: list[dict[str, Any]] = []

    def _log_call(self, method: str, **kwargs):
        """Log a method call for verification."""
        self.call_log.append({
            'method': method,
            'args': kwargs,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

    def reset(self):
        """Reset all stored data and call log."""
        self._progress.clear()
        self._job_status.clear()
        self._activity.clear()
        self._locks.clear()
        self.call_log.clear()

    # Progress operations
    def get_progress(self, company_id: str) -> dict[str, Any] | None:
        """Get progress data for a company."""
        self._log_call('get_progress', company_id=company_id)
        return self._progress.get(company_id)

    def set_progress(self, company_id: str, progress: dict[str, Any]) -> bool:
        """Set progress data for a company."""
        self._log_call('set_progress', company_id=company_id, progress=progress)
        self._progress[company_id] = progress
        return True

    # Job status operations
    def get_job_status(self, company_id: str) -> dict[str, Any] | None:
        """Get job status for a company."""
        self._log_call('get_job_status', company_id=company_id)
        return self._job_status.get(company_id)

    def set_job_status(self, company_id: str, status: dict[str, Any], expiry: int | None = None) -> bool:
        """Set job status for a company."""
        self._log_call('set_job_status', company_id=company_id, status=status, expiry=expiry)
        self._job_status[company_id] = status
        return True

    # Activity operations
    def get_activity(self, company_id: str) -> str | None:
        """Get current activity for a company."""
        self._log_call('get_activity', company_id=company_id)
        return self._activity.get(company_id)

    def set_activity(self, company_id: str, activity: str) -> bool:
        """Set current activity for a company."""
        self._log_call('set_activity', company_id=company_id, activity=activity)
        self._activity[company_id] = activity
        return True

    # Lock operations
    def acquire_lock(self, company_id: str, worker_id: str, expiry: int | None = None) -> bool:
        """Acquire distributed lock for a company."""
        self._log_call('acquire_lock', company_id=company_id, worker_id=worker_id, expiry=expiry)
        if company_id in self._locks:
            return False  # Lock already held
        self._locks[company_id] = worker_id
        return True

    def release_lock(self, company_id: str, worker_id: str) -> bool:
        """Release distributed lock for a company."""
        self._log_call('release_lock', company_id=company_id, worker_id=worker_id)
        if self._locks.get(company_id) == worker_id:
            del self._locks[company_id]
            return True
        return False

    def extend_lock(self, company_id: str, worker_id: str, expiry: int | None = None) -> bool:
        """Extend lock expiry time."""
        self._log_call('extend_lock', company_id=company_id, worker_id=worker_id, expiry=expiry)
        return self._locks.get(company_id) == worker_id

    def get_lock_holder(self, company_id: str) -> str | None:
        """Get the worker ID holding the lock."""
        self._log_call('get_lock_holder', company_id=company_id)
        return self._locks.get(company_id)

    # Cleanup operations
    def cleanup_job(self, company_id: str) -> bool:
        """Clean up all data for a job."""
        self._log_call('cleanup_job', company_id=company_id)
        self._progress.pop(company_id, None)
        self._job_status.pop(company_id, None)
        self._activity.pop(company_id, None)
        self._locks.pop(company_id, None)
        return True

    # Test helper methods
    def get_calls_for(self, method: str) -> list[dict]:
        """Get all calls for a specific method."""
        return [c for c in self.call_log if c['method'] == method]

    def was_called(self, method: str) -> bool:
        """Check if a method was called."""
        return any(c['method'] == method for c in self.call_log)

    @property
    def is_available(self) -> bool:
        """Always available in mock."""
        return True


# ==================== Factory Functions ====================

def create_company_with_crawl_session(db, status: str = 'in_progress'):
    """
    Create a Company with an associated CrawlSession.

    Args:
        db: SQLAlchemy database instance
        status: Company status string ('pending', 'in_progress', 'paused', etc.)

    Returns:
        Tuple of (Company, CrawlSession)
    """
    from app.models import Company, CrawlSession
    from app.models.enums import CompanyStatus, CrawlStatus, ProcessingPhase

    # Map string status to enum
    status_map = {
        'pending': CompanyStatus.PENDING,
        'in_progress': CompanyStatus.IN_PROGRESS,
        'completed': CompanyStatus.COMPLETED,
        'failed': CompanyStatus.FAILED,
        'paused': CompanyStatus.PAUSED,
    }
    company_status = status_map.get(status, CompanyStatus.IN_PROGRESS)

    # Create company
    company = Company(
        company_name='Test Company',
        website_url='https://example.com',
        status=company_status,
        processing_phase=ProcessingPhase.CRAWLING,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
    )
    db.session.add(company)
    db.session.flush()  # Get company ID

    # Create crawl session
    crawl_session = CrawlSession(
        company_id=company.id,
        status=CrawlStatus.ACTIVE if company_status == CompanyStatus.IN_PROGRESS else CrawlStatus.PAUSED,
        pages_crawled=5,
        pages_queued=10,
        crawl_depth_reached=1,
    )
    db.session.add(crawl_session)
    db.session.commit()

    return company, crawl_session


def create_paused_company_with_checkpoint(db):
    """
    Create a paused Company with checkpoint data.

    Args:
        db: SQLAlchemy database instance

    Returns:
        Tuple of (Company, CrawlSession)
    """
    from app.models import Company, CrawlSession, Page
    from app.models.enums import CompanyStatus, CrawlStatus, ProcessingPhase

    # Create paused company
    company = Company(
        company_name='Paused Test Company',
        website_url='https://paused-example.com',
        status=CompanyStatus.PAUSED,
        processing_phase=ProcessingPhase.CRAWLING,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        paused_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        total_paused_duration_ms=0,
    )
    db.session.add(company)
    db.session.flush()

    # Create crawl session with checkpoint
    crawl_session = CrawlSession(
        company_id=company.id,
        status=CrawlStatus.PAUSED,
        pages_crawled=15,
        pages_queued=5,
        crawl_depth_reached=2,
        checkpoint_data=MOCK_CHECKPOINT_DATA.copy(),
    )
    db.session.add(crawl_session)

    # Create some Page records for completeness
    for i, url in enumerate(MOCK_CHECKPOINT_DATA['pagesVisited'][:5]):
        page = Page(
            company_id=company.id,
            url=url,
            extracted_text=f'Sample content for page {i}',
        )
        db.session.add(page)

    db.session.commit()

    return company, crawl_session


def create_company_at_analysis_phase(db, sections_completed: list[str] | None = None):
    """
    Create a Company at the analysis phase with partial progress.

    Args:
        db: SQLAlchemy database instance
        sections_completed: List of completed analysis section names

    Returns:
        Tuple of (Company, CrawlSession)
    """
    from app.models import Company, CrawlSession
    from app.models.enums import CompanyStatus, CrawlStatus, ProcessingPhase

    company = Company(
        company_name='Analysis Phase Company',
        website_url='https://analysis-example.com',
        status=CompanyStatus.IN_PROGRESS,
        processing_phase=ProcessingPhase.ANALYZING,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=20),
    )
    db.session.add(company)
    db.session.flush()

    # Create checkpoint with analysis progress
    checkpoint = {
        'version': 1,
        'pagesVisited': ['https://analysis-example.com/' + str(i) for i in range(20)],
        'pagesQueued': [],
        'externalLinksFound': [],
        'currentDepth': 3,
        'entitiesExtractedCount': 85,
        'analysisSectionsCompleted': sections_completed or ['executive_summary', 'company_overview', 'market_analysis'],
        'crawlStartTime': (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat(),
        'lastCheckpointTime': datetime.now(timezone.utc).isoformat(),
    }

    crawl_session = CrawlSession(
        company_id=company.id,
        status=CrawlStatus.ACTIVE,
        pages_crawled=20,
        pages_queued=0,
        crawl_depth_reached=3,
        checkpoint_data=checkpoint,
    )
    db.session.add(crawl_session)
    db.session.commit()

    return company, crawl_session


# ==================== Test Helper Functions ====================

def make_checkpoint_data(
    pages_visited: int = 10,
    pages_queued: int = 5,
    entities_count: int = 25,
    sections_completed: list[str] | None = None,
    depth: int = 2
) -> dict[str, Any]:
    """
    Create custom checkpoint data for testing.

    Args:
        pages_visited: Number of visited page URLs to generate
        pages_queued: Number of queued page URLs to generate
        entities_count: Number of entities extracted
        sections_completed: List of completed analysis sections
        depth: Current crawl depth

    Returns:
        Checkpoint data dictionary
    """
    base_url = 'https://test.example.com'

    return {
        'version': 1,
        'pagesVisited': [f'{base_url}/page{i}' for i in range(pages_visited)],
        'pagesQueued': [f'{base_url}/queued{i}' for i in range(pages_queued)],
        'externalLinksFound': ['https://external.com/link1', 'https://external.com/link2'],
        'currentDepth': depth,
        'entitiesExtractedCount': entities_count,
        'analysisSectionsCompleted': sections_completed or [],
        'crawlStartTime': _iso_timestamp(30),
        'lastCheckpointTime': _iso_timestamp(0),
    }


def make_corrupted_checkpoint() -> str:
    """Create intentionally corrupted checkpoint data (not valid JSON when stored as string)."""
    return '{"version": 1, "pagesVisited": ["incomplete'


def make_incomplete_checkpoint() -> dict[str, Any]:
    """Create checkpoint missing required fields for testing validation."""
    return {
        'version': 1,
        # Missing pagesVisited, pagesQueued, etc.
        'currentDepth': 2,
    }


def make_old_version_checkpoint() -> dict[str, Any]:
    """Create checkpoint with old version for migration testing."""
    return {
        'version': 0,  # Old version
        'visited_pages': ['https://old-format.com/page1'],  # Old field name
        'queued_pages': ['https://old-format.com/queued1'],
        'depth': 1,
    }
