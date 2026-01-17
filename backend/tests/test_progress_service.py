"""Tests for Progress State Management Service."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock


class TestProgressServicePause:
    """Tests for pause functionality."""

    def test_pause_job_success(self, app):
        """Test successfully pausing an in-progress job."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus, ProcessingPhase
        from app.services.progress_service import ProgressService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            result = service.pause_job(company_id)

            assert result['success'] is True
            assert result['status'] == 'paused'
            assert 'paused_at' in result

            company = db.session.get(Company, company_id)
            assert company.status == CompanyStatus.PAUSED
            assert company.paused_at is not None

    def test_pause_job_not_found(self, app):
        """Test pausing a non-existent company."""
        from app.services.progress_service import ProgressService

        with app.app_context():
            service = ProgressService()
            result = service.pause_job("nonexistent-id")

            assert result['success'] is False
            assert 'not found' in result['error'].lower()

    def test_pause_job_invalid_status(self, app):
        """Test pausing a job that's not in progress."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.COMPLETED
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            result = service.pause_job(company_id)

            assert result['success'] is False
            assert 'cannot pause' in result['error'].lower()

    def test_pause_job_already_paused(self, app):
        """Test pausing a job that's already paused."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED,
                paused_at=datetime.now(timezone.utc)
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            result = service.pause_job(company_id)

            assert result['success'] is False


class TestProgressServiceResume:
    """Tests for resume functionality."""

    def test_resume_job_success(self, app):
        """Test successfully resuming a paused job."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus, ProcessingPhase
        from app.services.progress_service import ProgressService

        with app.app_context():
            paused_at = datetime.now(timezone.utc) - timedelta(minutes=5)
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=datetime.now(timezone.utc) - timedelta(hours=1),
                paused_at=paused_at
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            with patch('app.services.progress_service.redis_service') as mock_redis:
                mock_redis.acquire_lock.return_value = True
                mock_redis.release_lock.return_value = True
                mock_redis.set_job_status.return_value = True
                mock_redis.set_activity.return_value = True

                with patch('app.services.progress_service.ProgressService._dispatch_resume_task'):
                    service = ProgressService()
                    result = service.resume_job(company_id)

                    assert result['success'] is True
                    assert result['status'] == 'in_progress'

                    company = db.session.get(Company, company_id)
                    assert company.status == CompanyStatus.IN_PROGRESS
                    assert company.paused_at is None
                    assert company.total_paused_duration_ms > 0

    def test_resume_job_not_found(self, app):
        """Test resuming a non-existent company."""
        from app.services.progress_service import ProgressService

        with app.app_context():
            service = ProgressService()
            result = service.resume_job("nonexistent-id")

            assert result['success'] is False
            assert 'not found' in result['error'].lower()

    def test_resume_job_invalid_status(self, app):
        """Test resuming a job that's not paused."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PENDING
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            result = service.resume_job(company_id)

            assert result['success'] is False
            assert 'cannot resume' in result['error'].lower()


class TestProgressServiceProgressTracking:
    """Tests for progress tracking functionality."""

    def test_update_progress(self, app):
        """Test updating progress."""
        from app.services.progress_service import ProgressService

        with app.app_context():
            service = ProgressService()

            with patch('app.services.progress_service.redis_service') as mock_redis:
                mock_redis.set_progress.return_value = True
                mock_redis.set_activity.return_value = True

                result = service.update_progress(
                    'company-123',
                    phase='crawling',
                    pages_crawled=10,
                    pages_queued=50,
                    current_activity='Crawling page 10...',
                    percentage=20
                )

                assert result is True
                mock_redis.set_progress.assert_called_once()
                mock_redis.set_activity.assert_called_once_with(
                    'company-123', 'Crawling page 10...'
                )

    def test_get_progress(self, app):
        """Test getting progress."""
        from app.services.progress_service import ProgressService

        with app.app_context():
            service = ProgressService()

            with patch('app.services.progress_service.redis_service') as mock_redis:
                mock_redis.get_progress.return_value = {
                    'phase': 'crawling',
                    'pages_crawled': 10
                }
                mock_redis.get_activity.return_value = 'Crawling...'

                result = service.get_progress('company-123')

                assert result['phase'] == 'crawling'
                assert result['pages_crawled'] == 10
                assert result['current_activity'] == 'Crawling...'

    def test_update_progress_clamps_percentage(self, app):
        """Test that percentage is clamped between 0 and 100."""
        from app.services.progress_service import ProgressService

        with app.app_context():
            service = ProgressService()

            with patch('app.services.progress_service.redis_service') as mock_redis:
                mock_redis.set_progress.return_value = True

                service.update_progress('company-123', phase='crawling', percentage=150)

                call_args = mock_redis.set_progress.call_args[0]
                progress_data = call_args[1]
                assert progress_data['percentage'] == 100

                mock_redis.reset_mock()
                service.update_progress('company-123', phase='crawling', percentage=-10)

                call_args = mock_redis.set_progress.call_args[0]
                progress_data = call_args[1]
                assert progress_data['percentage'] == 0


class TestProgressServiceCheckpoint:
    """Tests for checkpoint functionality."""

    def test_should_checkpoint_page_threshold(self, app):
        """Test checkpoint triggers at page threshold."""
        from app.services.progress_service import ProgressService

        with app.app_context():
            service = ProgressService()

            assert service.should_checkpoint('company-123', 10, 60) is True
            assert service.should_checkpoint('company-123', 5, 60) is False

    def test_should_checkpoint_time_threshold(self, app):
        """Test checkpoint triggers at time threshold."""
        from app.services.progress_service import ProgressService

        with app.app_context():
            service = ProgressService()

            assert service.should_checkpoint('company-123', 5, 120) is True
            assert service.should_checkpoint('company-123', 5, 60) is False

    def test_save_checkpoint_success(self, app):
        """Test saving checkpoint."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            result = service.save_checkpoint(
                company_id,
                pages_visited=['https://example.com', 'https://example.com/about'],
                pages_queued=['https://example.com/contact'],
                external_links=['https://external.com'],
                current_depth=2,
                entities_count=5,
                sections_completed=['overview']
            )

            assert result is True

            crawl_session = CrawlSession.query.filter_by(company_id=company_id).first()
            assert crawl_session is not None
            assert crawl_session.checkpoint_data is not None
            assert len(crawl_session.checkpoint_data['pagesVisited']) == 2
            assert crawl_session.pages_crawled == 2

    def test_load_checkpoint_success(self, app):
        """Test loading checkpoint."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': ['https://example.com'],
                    'entitiesExtractedCount': 10
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            checkpoint = service.load_checkpoint(company_id)

            assert checkpoint is not None
            assert checkpoint['pagesVisited'] == ['https://example.com']
            assert checkpoint['entitiesExtractedCount'] == 10

    def test_load_checkpoint_no_session(self, app):
        """Test loading checkpoint when no session exists."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PENDING
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            checkpoint = service.load_checkpoint(company_id)

            assert checkpoint is None

    def test_get_visited_urls(self, app):
        """Test getting visited URLs from checkpoint."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': ['https://a.com', 'https://b.com', 'https://c.com']
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            visited = service.get_visited_urls(company_id)

            assert isinstance(visited, set)
            assert len(visited) == 3
            assert 'https://a.com' in visited


class TestProgressServiceTimeout:
    """Tests for timeout handling."""

    def test_get_remaining_time(self, app):
        """Test getting remaining time."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            started = datetime.now(timezone.utc) - timedelta(minutes=30)
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=started,
                total_paused_duration_ms=0
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            remaining = service.get_remaining_time(company_id, timeout_seconds=3600)

            # Should have ~30 minutes remaining
            assert remaining > 1700  # At least 28 minutes
            assert remaining < 1900  # At most 31 minutes

    def test_get_remaining_time_with_pauses(self, app):
        """Test remaining time accounts for pauses."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            started = datetime.now(timezone.utc) - timedelta(minutes=30)
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=started,
                total_paused_duration_ms=600000  # 10 minutes paused
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            remaining = service.get_remaining_time(company_id, timeout_seconds=3600)

            # 60 minutes timeout - 30 minutes elapsed + 10 minutes pause = 40 minutes
            assert remaining > 2300  # At least 38 minutes
            assert remaining < 2500  # At most 41 minutes

    def test_is_timeout_true(self, app):
        """Test timeout detection when time expired."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            started = datetime.now(timezone.utc) - timedelta(hours=2)
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=started,
                total_paused_duration_ms=0
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            is_timeout = service.is_timeout(company_id, timeout_seconds=3600)

            assert is_timeout is True

    def test_is_timeout_false(self, app):
        """Test timeout detection when time not expired."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            started = datetime.now(timezone.utc) - timedelta(minutes=10)
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=started,
                total_paused_duration_ms=0
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            is_timeout = service.is_timeout(company_id, timeout_seconds=3600)

            assert is_timeout is False

    def test_handle_timeout(self, app):
        """Test timeout handling."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus, ProcessingPhase
        from app.services.progress_service import ProgressService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=datetime.now(timezone.utc) - timedelta(hours=2)
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            result = service.handle_timeout(company_id)

            assert result['success'] is True
            assert result['status'] == 'timeout'

            company = db.session.get(Company, company_id)
            assert company.status == CompanyStatus.FAILED


class TestProgressServiceJobState:
    """Tests for job state queries."""

    def test_get_job_state_complete(self, app):
        """Test getting complete job state."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, ProcessingPhase, CrawlStatus
        from app.services.progress_service import ProgressService

        with app.app_context():
            started = datetime.now(timezone.utc) - timedelta(hours=1)
            paused = datetime.now(timezone.utc) - timedelta(minutes=10)
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=started,
                paused_at=paused,
                total_paused_duration_ms=5000
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={'pagesVisited': ['https://example.com']}
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = ProgressService()
            state = service.get_job_state(company_id)

            assert state is not None
            assert state['companyId'] == company_id
            assert state['status'] == 'paused'
            assert state['phase'] == 'crawling'
            assert state['startedAt'] is not None
            assert state['pausedAt'] is not None
            assert state['totalPausedDuration'] == 5000
            assert state['checkpoint'] is not None
            assert state['checkpoint']['pagesVisited'] == ['https://example.com']

    def test_get_job_state_not_found(self, app):
        """Test getting job state for non-existent company."""
        from app.services.progress_service import ProgressService

        with app.app_context():
            service = ProgressService()
            state = service.get_job_state("nonexistent-id")

            assert state is None


class TestProgressServiceGlobal:
    """Tests for global progress_service instance."""

    def test_global_service_exists(self, app):
        """Test that global service instance exists."""
        from app.services.progress_service import progress_service, ProgressService

        with app.app_context():
            assert progress_service is not None
            assert isinstance(progress_service, ProgressService)
