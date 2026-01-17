"""Tests for Job Queue Management Service."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


class TestJobServiceStartJob:
    """Tests for starting jobs."""

    def test_start_job_success(self, app):
        """Test successfully starting a job."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus, ProcessingPhase
        from app.services.job_service import JobService

        with app.app_context():
            # Create test company
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PENDING
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            # Mock the task dispatch
            with patch('app.workers.tasks.crawl_company'):
                service = JobService()
                result = service.start_job(company_id)

                assert result['success'] is True
                assert result['company_id'] == company_id

                # Verify company was updated
                company = db.session.get(Company, company_id)
                assert company.status == CompanyStatus.IN_PROGRESS
                assert company.processing_phase == ProcessingPhase.QUEUED
                assert company.started_at is not None

    def test_start_job_not_found(self, app):
        """Test starting a job for non-existent company."""
        from app.services.job_service import JobService

        with app.app_context():
            service = JobService()
            with pytest.raises(ValueError) as exc_info:
                service.start_job("nonexistent-id")
            assert "not found" in str(exc_info.value).lower()

    def test_start_job_already_in_progress(self, app):
        """Test starting a job that's already in progress."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = JobService()
            result = service.start_job(company_id)

            assert result['success'] is False
            assert 'already in progress' in result['error'].lower()


class TestJobServicePhaseTransition:
    """Tests for phase transitions."""

    def test_valid_transition_queued_to_crawling(self, app):
        """Test valid transition from QUEUED to CRAWLING."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus, ProcessingPhase
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.QUEUED
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            with patch('app.workers.tasks.crawl_company'):
                service = JobService()
                result = service.transition_phase(company_id, ProcessingPhase.CRAWLING)

                assert result is True
                company = db.session.get(Company, company_id)
                assert company.processing_phase == ProcessingPhase.CRAWLING

    def test_valid_transition_crawling_to_extracting(self, app):
        """Test valid transition from CRAWLING to EXTRACTING."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus, ProcessingPhase
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            with patch('app.workers.tasks.extract_entities'):
                service = JobService()
                result = service.transition_phase(company_id, ProcessingPhase.EXTRACTING)

                assert result is True
                company = db.session.get(Company, company_id)
                assert company.processing_phase == ProcessingPhase.EXTRACTING

    def test_valid_transition_to_completed(self, app):
        """Test transition to COMPLETED marks job complete."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus, ProcessingPhase
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.GENERATING
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = JobService()
            result = service.transition_phase(company_id, ProcessingPhase.COMPLETED)

            assert result is True
            company = db.session.get(Company, company_id)
            assert company.processing_phase == ProcessingPhase.COMPLETED
            assert company.status == CompanyStatus.COMPLETED
            assert company.completed_at is not None

    def test_invalid_transition_skipping_phase(self, app):
        """Test invalid transition that skips a phase."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus, ProcessingPhase
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.QUEUED
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = JobService()
            # Try to skip directly to ANALYZING
            result = service.transition_phase(company_id, ProcessingPhase.ANALYZING)

            assert result is False
            company = db.session.get(Company, company_id)
            assert company.processing_phase == ProcessingPhase.QUEUED  # Unchanged

    def test_transition_company_not_found(self, app):
        """Test transition for non-existent company."""
        from app.models.enums import ProcessingPhase
        from app.services.job_service import JobService

        with app.app_context():
            service = JobService()
            result = service.transition_phase("nonexistent-id", ProcessingPhase.CRAWLING)
            assert result is False


class TestJobServiceFailJob:
    """Tests for job failure handling."""

    def test_fail_job_success(self, app):
        """Test marking a job as failed."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus, ProcessingPhase
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = JobService()
            result = service.fail_job(company_id, "Network error")

            assert result is True
            company = db.session.get(Company, company_id)
            assert company.status == CompanyStatus.FAILED
            # Phase should remain where it was
            assert company.processing_phase == ProcessingPhase.CRAWLING

    def test_fail_job_not_found(self, app):
        """Test failing a non-existent company."""
        from app.services.job_service import JobService

        with app.app_context():
            service = JobService()
            result = service.fail_job("nonexistent-id", "Error")
            assert result is False


class TestJobServiceValidTransitions:
    """Tests for valid transition mapping."""

    def test_phase_order_complete(self, app):
        """Test all phases are in PHASE_ORDER."""
        from app.models.enums import ProcessingPhase
        from app.services.job_service import JobService

        with app.app_context():
            service = JobService()
            phase_order = service._get_phase_order()
            for phase in ProcessingPhase:
                assert phase in phase_order

    def test_valid_transitions_defined(self, app):
        """Test all phases have defined transitions."""
        from app.models.enums import ProcessingPhase
        from app.services.job_service import JobService

        with app.app_context():
            service = JobService()
            valid_transitions = service._get_valid_transitions()
            for phase in ProcessingPhase:
                assert phase in valid_transitions


class TestJobServiceQueueStatus:
    """Tests for queue status queries."""

    def test_get_queue_status_empty(self, app):
        """Test queue status with no jobs."""
        from app.services.job_service import JobService

        with app.app_context():
            service = JobService()
            status = service.get_queue_status()

            assert status['pending'] == 0
            assert status['in_progress'] == 0
            assert status['completed'] == 0
            assert status['failed'] == 0
            assert status['paused'] == 0
            assert status['total'] == 0

    def test_get_queue_status_with_jobs(self, app):
        """Test queue status with various jobs."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.job_service import JobService

        with app.app_context():
            # Create jobs with various statuses
            companies = [
                Company(
                    company_name=f"Company {i}",
                    website_url=f"https://example{i}.com",
                    status=status
                )
                for i, status in enumerate([
                    CompanyStatus.PENDING,
                    CompanyStatus.PENDING,
                    CompanyStatus.IN_PROGRESS,
                    CompanyStatus.COMPLETED,
                    CompanyStatus.FAILED,
                ])
            ]
            db.session.add_all(companies)
            db.session.commit()

            service = JobService()
            status = service.get_queue_status()

            assert status['pending'] == 2
            assert status['in_progress'] == 1
            assert status['completed'] == 1
            assert status['failed'] == 1
            assert status['total'] == 5

    def test_get_jobs_by_status(self, app):
        """Test getting jobs filtered by status."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.job_service import JobService

        with app.app_context():
            companies = [
                Company(
                    company_name=f"Company {i}",
                    website_url=f"https://example{i}.com",
                    status=CompanyStatus.PENDING
                )
                for i in range(3)
            ]
            db.session.add_all(companies)
            db.session.commit()

            service = JobService()
            jobs = service.get_jobs_by_status(CompanyStatus.PENDING)

            assert len(jobs) == 3
            for job in jobs:
                assert job['status'] == 'pending'


class TestJobServiceRecovery:
    """Tests for job recovery functionality."""

    def test_recover_in_progress_jobs_none(self, app):
        """Test recovery when no jobs need recovery."""
        from app.services.job_service import JobService

        with app.app_context():
            service = JobService()
            recovered = service.recover_in_progress_jobs()
            assert recovered == []

    def test_recover_stale_job(self, app):
        """Test that stale jobs are marked as failed."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.job_service import JobService

        with app.app_context():
            # Create a stale job (old timestamp)
            old_time = datetime.utcnow() - timedelta(hours=2)
            company = Company(
                company_name="Stale Company",
                website_url="https://stale.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=old_time,
                updated_at=old_time
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = JobService()
            recovered = service.recover_in_progress_jobs()

            # Stale job should be marked as failed, not recovered
            assert company_id not in recovered
            company = db.session.get(Company, company_id)
            assert company.status == CompanyStatus.FAILED

    def test_recover_with_checkpoint(self, app):
        """Test recovery from checkpoint."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, ProcessingPhase, CrawlStatus
        from app.services.job_service import JobService

        with app.app_context():
            # Create a company with recent timestamp
            company = Company(
                company_name="Recoverable Company",
                website_url="https://recoverable.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(company)
            db.session.commit()

            # Create crawl session with checkpoint
            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': ['https://example.com', 'https://example.com/about'],
                    'entitiesExtractedCount': 5
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            with patch('app.workers.tasks.analyze_content'):
                service = JobService()
                recovered = service.recover_in_progress_jobs()

                # Job should be recovered
                assert company_id in recovered


class TestJobServiceIsStaleJob:
    """Tests for stale job detection."""

    def test_stale_job_with_old_updated_at(self, app):
        """Test job with old updated_at timestamp is considered stale."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.job_service import JobService

        with app.app_context():
            # Create company with old timestamp (beyond stale threshold)
            old_time = datetime.utcnow() - timedelta(hours=2)
            company = Company(
                company_name="Old Timestamp",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                updated_at=old_time
            )
            db.session.add(company)
            db.session.commit()

            service = JobService()
            assert service._is_stale_job(company) is True

    def test_recent_job_not_stale(self, app):
        """Test job with recent timestamp is not stale."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="Recent Job",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.session.add(company)
            db.session.commit()

            service = JobService()
            assert service._is_stale_job(company) is False

    def test_old_job_is_stale(self, app):
        """Test job with old timestamp is stale."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.job_service import JobService

        with app.app_context():
            old_time = datetime.utcnow() - timedelta(hours=2)
            company = Company(
                company_name="Old Job",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=old_time,
                updated_at=old_time
            )
            db.session.add(company)
            db.session.commit()

            service = JobService()
            assert service._is_stale_job(company) is True


class TestJobServiceResumeFromCheckpoint:
    """Tests for resuming from checkpoint."""

    def test_resume_no_checkpoint(self, app):
        """Test resume returns False with no checkpoint."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="No Checkpoint",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()

            service = JobService()
            result = service._resume_from_checkpoint(company)
            assert result is False

    def test_resume_with_pages_visited(self, app):
        """Test resume with pages visited goes to extraction."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, ProcessingPhase, CrawlStatus
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="With Pages",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': ['https://example.com']
                }
            )
            db.session.add(session)
            db.session.commit()

            with patch('app.workers.tasks.extract_entities'):
                service = JobService()
                result = service._resume_from_checkpoint(company)

                assert result is True
                assert company.processing_phase == ProcessingPhase.EXTRACTING

    def test_resume_with_entities(self, app):
        """Test resume with entities goes to analysis."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, ProcessingPhase, CrawlStatus
        from app.services.job_service import JobService

        with app.app_context():
            company = Company(
                company_name="With Entities",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.EXTRACTING
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

            with patch('app.workers.tasks.analyze_content'):
                service = JobService()
                result = service._resume_from_checkpoint(company)

                assert result is True
                assert company.processing_phase == ProcessingPhase.ANALYZING


class TestGlobalJobService:
    """Tests for global job_service instance."""

    def test_global_service_exists(self, app):
        """Test that global service instance exists."""
        from app.services.job_service import job_service, JobService

        with app.app_context():
            assert job_service is not None
            assert isinstance(job_service, JobService)
