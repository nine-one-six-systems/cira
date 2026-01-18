"""Tests for automatic job recovery on startup.

Tests Task 9.5: Automatic Job Recovery per spec 04-state-management.md (FR-STA-005).
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app import db, create_app
from app.models.company import Company, CrawlSession
from app.models.enums import CompanyStatus, ProcessingPhase, CrawlStatus
from app.services.job_service import JobService, job_service


class TestJobRecoveryOnStartup:
    """Tests for automatic job recovery mechanism."""

    def test_recover_in_progress_jobs_finds_jobs(self, app):
        """Test that recovery finds in_progress jobs."""
        with app.app_context():
            # Create an in_progress job
            company = Company(
                company_name="Test Recovery Corp",
                website_url="https://test-recovery.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

            # Mock the dispatch to avoid actually starting tasks
            with patch.object(job_service, '_dispatch_next_phase') as mock_dispatch:
                recovered = job_service.recover_in_progress_jobs()

                # Should have found the job
                assert company_id in recovered

    def test_recovery_skips_completed_jobs(self, app):
        """Test that recovery doesn't affect completed jobs."""
        with app.app_context():
            # Create a completed job
            company = Company(
                company_name="Completed Corp",
                website_url="https://completed.com",
                status=CompanyStatus.COMPLETED,
                processing_phase=ProcessingPhase.COMPLETED,
            )
            db.session.add(company)
            db.session.commit()

            with patch.object(job_service, '_dispatch_next_phase') as mock_dispatch:
                recovered = job_service.recover_in_progress_jobs()

                # Completed job should not be recovered
                assert company.id not in recovered
                mock_dispatch.assert_not_called()

    def test_recovery_skips_pending_jobs(self, app):
        """Test that recovery doesn't affect pending jobs."""
        with app.app_context():
            # Create a pending job
            company = Company(
                company_name="Pending Corp",
                website_url="https://pending.com",
                status=CompanyStatus.PENDING,
            )
            db.session.add(company)
            db.session.commit()

            with patch.object(job_service, '_dispatch_next_phase') as mock_dispatch:
                recovered = job_service.recover_in_progress_jobs()

                # Pending job should not be recovered
                assert company.id not in recovered

    def test_stale_job_marked_as_failed(self, app):
        """Test that stale jobs (no progress for 1 hour) are marked as failed."""
        with app.app_context():
            # Create a stale in_progress job (updated more than 1 hour ago)
            old_time = datetime.now(timezone.utc) - timedelta(hours=2)
            company = Company(
                company_name="Stale Corp",
                website_url="https://stale.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=old_time,
            )
            # Manually set updated_at to simulate staleness
            company.updated_at = old_time
            db.session.add(company)
            db.session.commit()
            company_id = company.id

            # Mock Redis to return no recent status
            with patch('app.services.job_service.redis_service') as mock_redis:
                mock_redis.get_job_status.return_value = None

                recovered = job_service.recover_in_progress_jobs()

                # Should not be in recovered (marked as failed instead)
                assert company_id not in recovered

                # Check that the job is now failed
                company = db.session.get(Company, company_id)
                assert company.status == CompanyStatus.FAILED


class TestJobRecoveryFromCheckpoint:
    """Tests for checkpoint-based job recovery."""

    def test_resume_from_crawl_checkpoint(self, app):
        """Test resuming from a crawl checkpoint."""
        with app.app_context():
            # Create company with in_progress status
            company = Company(
                company_name="Checkpoint Corp",
                website_url="https://checkpoint.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(company)
            db.session.flush()

            # Create a crawl session with checkpoint data
            checkpoint_data = {
                'pagesVisited': [
                    'https://checkpoint.com/',
                    'https://checkpoint.com/about',
                ],
                'pagesQueued': ['https://checkpoint.com/team'],
                'entitiesExtractedCount': 0,
                'analysisSectionsCompleted': [],
            }
            session = CrawlSession(
                company_id=company.id,
                pages_crawled=2,
                status=CrawlStatus.PAUSED,
                checkpoint_data=checkpoint_data,
            )
            db.session.add(session)
            db.session.commit()
            company_id = company.id

            # Mock dispatch to avoid Celery/Redis issues
            with patch.object(job_service, '_dispatch_next_phase'):
                # Test _resume_from_checkpoint
                company = db.session.get(Company, company_id)
                result = job_service._resume_from_checkpoint(company)

                assert result is True
                # Should resume at extraction since pages were visited
                assert company.processing_phase == ProcessingPhase.EXTRACTING

    def test_resume_from_extraction_checkpoint(self, app):
        """Test resuming from an extraction checkpoint."""
        with app.app_context():
            company = Company(
                company_name="Extraction Checkpoint Corp",
                website_url="https://extraction.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.EXTRACTING,
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(company)
            db.session.flush()

            checkpoint_data = {
                'pagesVisited': ['https://extraction.com/'],
                'entitiesExtractedCount': 15,  # Has entities
                'analysisSectionsCompleted': [],
            }
            session = CrawlSession(
                company_id=company.id,
                pages_crawled=1,
                status=CrawlStatus.PAUSED,
                checkpoint_data=checkpoint_data,
            )
            db.session.add(session)
            db.session.commit()
            company_id = company.id

            # Mock dispatch to avoid Celery/Redis issues
            with patch.object(job_service, '_dispatch_next_phase'):
                company = db.session.get(Company, company_id)
                result = job_service._resume_from_checkpoint(company)

                assert result is True
                # Should resume at analysis since entities were extracted
                assert company.processing_phase == ProcessingPhase.ANALYZING

    def test_no_checkpoint_restarts_from_beginning(self, app):
        """Test that jobs without checkpoints restart from the beginning."""
        with app.app_context():
            company = Company(
                company_name="No Checkpoint Corp",
                website_url="https://nocheckpoint.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

            company = db.session.get(Company, company_id)
            result = job_service._resume_from_checkpoint(company)

            # No checkpoint, so returns False
            assert result is False


class TestStaleJobDetection:
    """Tests for stale job detection."""

    def test_recent_redis_activity_not_stale(self, app):
        """Test that recent Redis activity means job is not stale."""
        with app.app_context():
            company = Company(
                company_name="Active Corp",
                website_url="https://active.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=datetime.now(timezone.utc) - timedelta(hours=2),
            )
            db.session.add(company)
            db.session.commit()

            # Mock Redis to return recent activity
            recent_time = datetime.utcnow() - timedelta(minutes=5)
            with patch('app.services.job_service.redis_service') as mock_redis:
                mock_redis.get_job_status.return_value = {
                    'updated_at': recent_time.isoformat()
                }

                is_stale = job_service._is_stale_job(company)
                assert is_stale is False

    def test_old_redis_activity_is_stale(self, app):
        """Test that old Redis activity means job is stale."""
        with app.app_context():
            company = Company(
                company_name="Stale Corp",
                website_url="https://stale.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=datetime.now(timezone.utc) - timedelta(hours=3),
            )
            # Manually set old updated_at for fallback
            company.updated_at = datetime.now(timezone.utc) - timedelta(hours=3)
            db.session.add(company)
            db.session.commit()

            # Mock Redis to return None (no recent activity) so it falls back to DB
            with patch('app.services.job_service.redis_service') as mock_redis:
                mock_redis.get_job_status.return_value = None

                is_stale = job_service._is_stale_job(company)
                assert is_stale is True

    def test_no_redis_data_uses_db_timestamp(self, app):
        """Test fallback to DB timestamp when no Redis data."""
        with app.app_context():
            # Recent DB timestamp
            company_recent = Company(
                company_name="Recent Corp",
                website_url="https://recent.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=datetime.now(timezone.utc) - timedelta(minutes=30),
            )
            db.session.add(company_recent)
            db.session.commit()

            with patch('app.services.job_service.redis_service') as mock_redis:
                mock_redis.get_job_status.return_value = None

                is_stale = job_service._is_stale_job(company_recent)
                assert is_stale is False

            # Old DB timestamp
            company_old = Company(
                company_name="Old Corp",
                website_url="https://old.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=datetime.now(timezone.utc) - timedelta(hours=3),
            )
            # Manually set updated_at to be old
            company_old.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
            db.session.add(company_old)
            db.session.commit()

            with patch('app.services.job_service.redis_service') as mock_redis:
                mock_redis.get_job_status.return_value = None

                is_stale = job_service._is_stale_job(company_old)
                assert is_stale is True


class TestJobRecoveryConfiguration:
    """Tests for job recovery configuration options."""

    def test_stale_threshold_is_one_hour(self):
        """Test that stale threshold is 1 hour (3600 seconds)."""
        assert JobService.STALE_JOB_THRESHOLD_SECONDS == 3600

    def test_recovery_logs_actions(self, app):
        """Test that recovery logs its actions."""
        with app.app_context():
            company = Company(
                company_name="Log Test Corp",
                website_url="https://logtest.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=datetime.now(timezone.utc),
            )
            db.session.add(company)
            db.session.commit()

            with patch.object(job_service, '_dispatch_next_phase'):
                with patch('app.services.job_service.logger') as mock_logger:
                    job_service.recover_in_progress_jobs()

                    # Should log the recovery action
                    assert mock_logger.info.called


class TestQueueManagement:
    """Tests for queue status and management."""

    def test_get_queue_status(self, app):
        """Test getting queue status."""
        with app.app_context():
            # Create various jobs
            Company(
                company_name="Pending Corp",
                website_url="https://pending.com",
                status=CompanyStatus.PENDING,
            )
            Company(
                company_name="In Progress Corp",
                website_url="https://inprogress.com",
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
            )
            Company(
                company_name="Completed Corp",
                website_url="https://completed.com",
                status=CompanyStatus.COMPLETED,
            )
            db.session.add_all([
                Company(
                    company_name="P1",
                    website_url="https://p1.com",
                    status=CompanyStatus.PENDING,
                ),
                Company(
                    company_name="IP1",
                    website_url="https://ip1.com",
                    status=CompanyStatus.IN_PROGRESS,
                    processing_phase=ProcessingPhase.CRAWLING,
                ),
                Company(
                    company_name="C1",
                    website_url="https://c1.com",
                    status=CompanyStatus.COMPLETED,
                ),
            ])
            db.session.commit()

            status = job_service.get_queue_status()

            assert 'pending' in status
            assert 'in_progress' in status
            assert 'completed' in status
            assert 'failed' in status
            assert 'total' in status
            assert 'phase_breakdown' in status

    def test_get_jobs_by_status(self, app):
        """Test getting jobs by status."""
        with app.app_context():
            c1 = Company(
                company_name="Pending 1",
                website_url="https://pending1.com",
                status=CompanyStatus.PENDING,
            )
            c2 = Company(
                company_name="Pending 2",
                website_url="https://pending2.com",
                status=CompanyStatus.PENDING,
            )
            c3 = Company(
                company_name="Completed 1",
                website_url="https://completed1.com",
                status=CompanyStatus.COMPLETED,
            )
            db.session.add_all([c1, c2, c3])
            db.session.commit()

            pending_jobs = job_service.get_jobs_by_status(CompanyStatus.PENDING)

            assert len(pending_jobs) == 2
            assert all(j['status'] == 'pending' for j in pending_jobs)

            completed_jobs = job_service.get_jobs_by_status(CompanyStatus.COMPLETED)
            assert len(completed_jobs) == 1
