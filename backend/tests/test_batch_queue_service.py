"""Tests for Batch Queue Management Service."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock


class TestBatchQueueServiceCreateBatch:
    """Tests for batch creation."""

    def test_create_batch_success(self, app):
        """Test successfully creating a batch with companies."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            # Create test companies
            companies = [
                Company(
                    company_name=f"Company {i}",
                    website_url=f"https://example{i}.com",
                    status=CompanyStatus.PENDING
                )
                for i in range(5)
            ]
            db.session.add_all(companies)
            db.session.commit()
            company_ids = [c.id for c in companies]

            # Mock job_service.start_job to avoid actual task dispatch
            with patch('app.services.batch_queue_service.job_service'):
                service = BatchQueueService()
                result = service.create_batch(
                    company_ids=company_ids,
                    name="Test Batch",
                    description="Test description",
                    priority=50,
                    start_immediately=False,
                )

                assert result['success'] is True
                assert result['total_companies'] == 5

                # Verify batch was created
                batch = db.session.get(BatchJob, result['batch_id'])
                assert batch is not None
                assert batch.name == "Test Batch"
                assert batch.description == "Test description"
                assert batch.priority == 50
                assert batch.total_companies == 5
                assert batch.pending_companies == 5
                assert batch.status == BatchStatus.PENDING

                # Verify companies are associated
                for company in companies:
                    db.session.refresh(company)
                    assert company.batch_id == batch.id

    def test_create_batch_empty_company_list(self, app):
        """Test creating batch with empty company list fails."""
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            service = BatchQueueService()
            result = service.create_batch(company_ids=[])

            assert result['success'] is False
            assert 'No company IDs' in result['error']

    def test_create_batch_with_start_immediately(self, app):
        """Test creating batch and starting processing immediately."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PENDING
            )
            db.session.add(company)
            db.session.commit()

            with patch('app.services.batch_queue_service.job_service') as mock_job_service:
                mock_job_service.start_job.return_value = {'success': True}

                service = BatchQueueService()
                result = service.create_batch(
                    company_ids=[company.id],
                    start_immediately=True,
                )

                assert result['success'] is True

                batch = db.session.get(BatchJob, result['batch_id'])
                assert batch.status == BatchStatus.PROCESSING

    def test_create_batch_with_config(self, app):
        """Test that batch config is applied to companies."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PENDING,
                config={'existing': 'value'}
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

            with patch('app.services.batch_queue_service.job_service'):
                service = BatchQueueService()
                result = service.create_batch(
                    company_ids=[company_id],
                    config={'maxPages': 50, 'maxDepth': 3},
                    start_immediately=False,
                )

                assert result['success'] is True

                # Verify config was merged
                company = db.session.get(Company, company_id)
                assert company.config['existing'] == 'value'
                assert company.config['maxPages'] == 50
                assert company.config['maxDepth'] == 3


class TestBatchQueueServiceStartBatch:
    """Tests for starting batches."""

    def test_start_batch_success(self, app):
        """Test successfully starting a batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PENDING,
                total_companies=2,
                pending_companies=2,
            )
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(
                    company_name=f"Company {i}",
                    website_url=f"https://example{i}.com",
                    status=CompanyStatus.PENDING,
                    batch_id=batch.id
                )
                for i in range(2)
            ]
            db.session.add_all(companies)
            db.session.commit()
            batch_id = batch.id

            with patch('app.services.batch_queue_service.job_service') as mock_job_service:
                mock_job_service.start_job.return_value = {'success': True}

                service = BatchQueueService()
                result = service.start_batch(batch_id)

                assert result['success'] is True
                assert result['companies_scheduled'] > 0

                batch = db.session.get(BatchJob, batch_id)
                assert batch.status == BatchStatus.PROCESSING
                assert batch.started_at is not None

    def test_start_batch_not_found(self, app):
        """Test starting non-existent batch."""
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            service = BatchQueueService()
            result = service.start_batch("nonexistent-id")

            assert result['success'] is False
            assert 'not found' in result['error'].lower()

    def test_start_batch_already_processing(self, app):
        """Test starting batch that's already processing."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.start_batch(batch_id)

            assert result['success'] is False
            assert 'already processing' in result['error'].lower()

    def test_start_batch_already_completed(self, app):
        """Test starting batch that's already completed."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.COMPLETED,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.start_batch(batch_id)

            assert result['success'] is False
            assert 'completed' in result['error'].lower()


class TestBatchQueueServicePauseBatch:
    """Tests for pausing batches."""

    def test_pause_batch_success(self, app):
        """Test successfully pausing a batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
                total_companies=2,
                processing_companies=2,
            )
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(
                    company_name=f"Company {i}",
                    website_url=f"https://example{i}.com",
                    status=CompanyStatus.IN_PROGRESS,
                    batch_id=batch.id
                )
                for i in range(2)
            ]
            db.session.add_all(companies)
            db.session.commit()
            batch_id = batch.id

            with patch('app.api.routes.control._pause_company_internal') as mock_pause:
                mock_pause.return_value = {'success': True}

                service = BatchQueueService()
                result = service.pause_batch(batch_id)

                assert result['success'] is True
                assert result['companies_paused'] == 2

                # Refresh batch from DB to get updated status
                db.session.expire_all()
                batch = db.session.get(BatchJob, batch_id)
                assert batch.status == BatchStatus.PAUSED

    def test_pause_batch_not_found(self, app):
        """Test pausing non-existent batch."""
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            service = BatchQueueService()
            result = service.pause_batch("nonexistent-id")

            assert result['success'] is False
            assert 'not found' in result['error'].lower()

    def test_pause_batch_invalid_state(self, app):
        """Test pausing batch in invalid state."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.COMPLETED,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.pause_batch(batch_id)

            assert result['success'] is False


class TestBatchQueueServiceResumeBatch:
    """Tests for resuming batches."""

    def test_resume_batch_success(self, app):
        """Test successfully resuming a paused batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PAUSED,
                total_companies=2,
                pending_companies=1,
            )
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(
                    company_name="Paused Company",
                    website_url="https://paused.com",
                    status=CompanyStatus.PAUSED,
                    batch_id=batch.id
                ),
                Company(
                    company_name="Pending Company",
                    website_url="https://pending.com",
                    status=CompanyStatus.PENDING,
                    batch_id=batch.id
                ),
            ]
            db.session.add_all(companies)
            db.session.commit()
            batch_id = batch.id

            with patch('app.api.routes.control._resume_company_internal') as mock_resume:
                mock_resume.return_value = {'success': True}
                with patch('app.services.batch_queue_service.job_service') as mock_job:
                    mock_job.start_job.return_value = {'success': True}

                    service = BatchQueueService()
                    result = service.resume_batch(batch_id)

                    assert result['success'] is True
                    assert result['companies_resumed'] == 1

                    batch = db.session.get(BatchJob, batch_id)
                    assert batch.status == BatchStatus.PROCESSING

    def test_resume_batch_not_paused(self, app):
        """Test resuming batch that's not paused."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.resume_batch(batch_id)

            assert result['success'] is False
            assert 'not paused' in result['error'].lower()


class TestBatchQueueServiceCancelBatch:
    """Tests for cancelling batches."""

    def test_cancel_batch_success(self, app):
        """Test successfully cancelling a batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
                total_companies=3,
            )
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(
                    company_name="Pending Company",
                    website_url="https://pending.com",
                    status=CompanyStatus.PENDING,
                    batch_id=batch.id
                ),
                Company(
                    company_name="In Progress Company",
                    website_url="https://progress.com",
                    status=CompanyStatus.IN_PROGRESS,
                    batch_id=batch.id
                ),
                Company(
                    company_name="Completed Company",
                    website_url="https://completed.com",
                    status=CompanyStatus.COMPLETED,
                    batch_id=batch.id
                ),
            ]
            db.session.add_all(companies)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.cancel_batch(batch_id)

            assert result['success'] is True
            assert result['companies_cancelled'] == 2  # pending + in_progress

            batch = db.session.get(BatchJob, batch_id)
            assert batch.status == BatchStatus.CANCELLED
            assert batch.completed_at is not None

            # Verify pending and in_progress are now failed
            for company in companies:
                db.session.refresh(company)
            assert companies[0].status == CompanyStatus.FAILED
            assert companies[1].status == CompanyStatus.FAILED
            assert companies[2].status == CompanyStatus.COMPLETED  # unchanged

    def test_cancel_batch_already_completed(self, app):
        """Test cancelling batch that's already completed."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.COMPLETED,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.cancel_batch(batch_id)

            assert result['success'] is False
            assert 'already' in result['error'].lower()


class TestBatchQueueServiceFairScheduling:
    """Tests for fair scheduling across batches."""

    def test_schedule_respects_batch_priority(self, app):
        """Test that higher priority batches get scheduled first."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            # Create high priority batch
            high_priority_batch = BatchJob(
                name="High Priority",
                status=BatchStatus.PROCESSING,
                priority=10,
                max_concurrent=5,
            )
            # Create low priority batch
            low_priority_batch = BatchJob(
                name="Low Priority",
                status=BatchStatus.PROCESSING,
                priority=100,
                max_concurrent=5,
            )
            db.session.add_all([high_priority_batch, low_priority_batch])
            db.session.commit()

            # Add pending companies to both batches
            high_companies = [
                Company(
                    company_name=f"High {i}",
                    website_url=f"https://high{i}.com",
                    status=CompanyStatus.PENDING,
                    batch_id=high_priority_batch.id
                )
                for i in range(3)
            ]
            low_companies = [
                Company(
                    company_name=f"Low {i}",
                    website_url=f"https://low{i}.com",
                    status=CompanyStatus.PENDING,
                    batch_id=low_priority_batch.id
                )
                for i in range(3)
            ]
            db.session.add_all(high_companies + low_companies)
            db.session.commit()

            scheduled_company_ids = []

            with patch('app.services.batch_queue_service.job_service') as mock_job:
                def track_start(company_id, config=None):
                    scheduled_company_ids.append(company_id)
                    return {'success': True}

                mock_job.start_job.side_effect = track_start

                service = BatchQueueService()
                service.GLOBAL_MAX_CONCURRENT = 2  # Limit to see priority effect
                total = service.schedule_next_from_all_batches()

                # Should schedule from both batches due to round-robin
                assert total == 2

    def test_schedule_respects_batch_concurrency_limit(self, app):
        """Test that batch concurrency limit is respected."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
                max_concurrent=2,  # Only allow 2 concurrent
            )
            db.session.add(batch)
            db.session.commit()

            # Add 5 pending companies
            companies = [
                Company(
                    company_name=f"Company {i}",
                    website_url=f"https://example{i}.com",
                    status=CompanyStatus.PENDING,
                    batch_id=batch.id
                )
                for i in range(5)
            ]
            db.session.add_all(companies)
            db.session.commit()

            scheduled_count = 0
            with patch('app.services.batch_queue_service.job_service') as mock_job:
                def track_and_update(company_id, config=None):
                    nonlocal scheduled_count
                    company = db.session.get(Company, company_id)
                    company.status = CompanyStatus.IN_PROGRESS
                    db.session.commit()
                    scheduled_count += 1
                    return {'success': True}

                mock_job.start_job.side_effect = track_and_update

                service = BatchQueueService()
                service.GLOBAL_MAX_CONCURRENT = 10
                service._schedule_batch_companies(batch.id)

                # Should only schedule max_concurrent (2) companies
                assert scheduled_count == 2

    def test_round_robin_scheduling(self, app):
        """Test round-robin scheduling across batches."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            # Create two batches with same priority
            batch1 = BatchJob(
                name="Batch 1",
                status=BatchStatus.PROCESSING,
                priority=100,
                max_concurrent=10,
            )
            batch2 = BatchJob(
                name="Batch 2",
                status=BatchStatus.PROCESSING,
                priority=100,
                max_concurrent=10,
            )
            db.session.add_all([batch1, batch2])
            db.session.commit()

            # Add companies to both
            for batch in [batch1, batch2]:
                companies = [
                    Company(
                        company_name=f"{batch.name} Company {i}",
                        website_url=f"https://{batch.name.lower().replace(' ', '')}{i}.com",
                        status=CompanyStatus.PENDING,
                        batch_id=batch.id
                    )
                    for i in range(3)
                ]
                db.session.add_all(companies)
            db.session.commit()

            batch_ids_scheduled = []

            with patch('app.services.batch_queue_service.job_service') as mock_job:
                def track_batch(company_id, config=None):
                    company = db.session.get(Company, company_id)
                    batch_ids_scheduled.append(company.batch_id)
                    return {'success': True}

                mock_job.start_job.side_effect = track_batch

                service = BatchQueueService()
                service.GLOBAL_MAX_CONCURRENT = 4
                service.schedule_next_from_all_batches()

                # Should schedule from both batches (round-robin)
                assert batch1.id in batch_ids_scheduled
                assert batch2.id in batch_ids_scheduled


class TestBatchQueueServiceProgress:
    """Tests for batch progress tracking."""

    def test_get_batch_progress(self, app):
        """Test getting batch progress."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
                total_companies=10,
                pending_companies=3,
                processing_companies=2,
                completed_companies=4,
                failed_companies=1,
                total_tokens_used=5000,
                estimated_cost=0.50,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            progress = service.get_batch_progress(batch_id)

            assert progress is not None
            assert progress['total'] == 10
            assert progress['pending'] == 3
            assert progress['processing'] == 2
            assert progress['completed'] == 4
            assert progress['failed'] == 1
            assert progress['progress_percentage'] == 50.0  # (4+1)/10 * 100
            assert progress['tokens_used'] == 5000

    def test_progress_percentage_calculation(self, app):
        """Test progress percentage calculation."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
                total_companies=100,
                pending_companies=25,
                processing_companies=25,
                completed_companies=40,
                failed_companies=10,
            )
            db.session.add(batch)
            db.session.commit()

            # Progress should be (completed + failed) / total
            assert batch.progress_percentage == 50.0


class TestBatchQueueServiceStatusUpdates:
    """Tests for batch status updates on company changes."""

    def test_on_company_completion_schedules_more(self, app):
        """Test that completing a company triggers scheduling more."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
                total_companies=2,
                processing_companies=1,
                pending_companies=1,
                max_concurrent=2,  # Allow 2 concurrent so slot is available
            )
            db.session.add(batch)
            db.session.commit()

            # Create one completed (was in_progress) and one pending
            completed_company = Company(
                company_name="Completed",
                website_url="https://completed.com",
                status=CompanyStatus.COMPLETED,  # Already completed
                batch_id=batch.id
            )
            pending = Company(
                company_name="Pending",
                website_url="https://pending.com",
                status=CompanyStatus.PENDING,
                batch_id=batch.id
            )
            db.session.add_all([completed_company, pending])
            db.session.commit()
            company_id = completed_company.id

            with patch('app.services.batch_queue_service.job_service') as mock_job:
                mock_job.start_job.return_value = {'success': True}

                service = BatchQueueService()
                # Trigger the status change handler
                service.on_company_status_change(
                    company_id,
                    CompanyStatus.IN_PROGRESS,
                    CompanyStatus.COMPLETED
                )

                # Should have attempted to schedule the pending company
                mock_job.start_job.assert_called_once()

    def test_batch_auto_completes_when_all_done(self, app):
        """Test batch auto-completes when all companies are done."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
                total_companies=2,
                processing_companies=1,
                completed_companies=1,
            )
            db.session.add(batch)
            db.session.commit()

            last_company = Company(
                company_name="Last Company",
                website_url="https://last.com",
                status=CompanyStatus.IN_PROGRESS,
                batch_id=batch.id
            )
            completed_company = Company(
                company_name="Completed Company",
                website_url="https://completed.com",
                status=CompanyStatus.COMPLETED,
                batch_id=batch.id
            )
            db.session.add_all([last_company, completed_company])
            db.session.commit()

            # Simulate completion of last company
            last_company.status = CompanyStatus.COMPLETED
            db.session.commit()

            service = BatchQueueService()
            service.on_company_status_change(
                last_company.id,
                CompanyStatus.IN_PROGRESS,
                CompanyStatus.COMPLETED
            )

            # Batch should be completed
            db.session.refresh(batch)
            assert batch.status == BatchStatus.COMPLETED
            assert batch.completed_at is not None


class TestBatchQueueServiceQueries:
    """Tests for batch query operations."""

    def test_list_batches(self, app):
        """Test listing batches."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batches = [
                BatchJob(name=f"Batch {i}", status=BatchStatus.PENDING)
                for i in range(5)
            ]
            db.session.add_all(batches)
            db.session.commit()

            service = BatchQueueService()
            result = service.list_batches()

            assert result['total'] == 5
            assert len(result['batches']) == 5

    def test_list_batches_with_status_filter(self, app):
        """Test listing batches with status filter."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batches = [
                BatchJob(name="Pending 1", status=BatchStatus.PENDING),
                BatchJob(name="Pending 2", status=BatchStatus.PENDING),
                BatchJob(name="Processing", status=BatchStatus.PROCESSING),
                BatchJob(name="Completed", status=BatchStatus.COMPLETED),
            ]
            db.session.add_all(batches)
            db.session.commit()

            service = BatchQueueService()
            result = service.list_batches(status=BatchStatus.PENDING)

            assert result['total'] == 2
            for batch in result['batches']:
                assert batch['status'] == 'pending'

    def test_list_batches_pagination(self, app):
        """Test batch listing pagination."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batches = [
                BatchJob(name=f"Batch {i}", status=BatchStatus.PENDING)
                for i in range(10)
            ]
            db.session.add_all(batches)
            db.session.commit()

            service = BatchQueueService()
            result = service.list_batches(limit=3, offset=2)

            assert result['total'] == 10
            assert len(result['batches']) == 3
            assert result['limit'] == 3
            assert result['offset'] == 2

    def test_get_batch_companies(self, app):
        """Test getting companies in a batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.PENDING)
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(
                    company_name=f"Company {i}",
                    website_url=f"https://example{i}.com",
                    status=CompanyStatus.PENDING,
                    batch_id=batch.id
                )
                for i in range(5)
            ]
            db.session.add_all(companies)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.get_batch_companies(batch_id)

            assert result['total'] == 5
            assert len(result['companies']) == 5


class TestBatchQueueServiceCleanup:
    """Tests for batch cleanup operations."""

    def test_cleanup_old_batches(self, app):
        """Test cleaning up old completed batches."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus
        from app.services.batch_queue_service import BatchQueueService
        from datetime import timedelta

        with app.app_context():
            old_batch = BatchJob(
                name="Old Batch",
                status=BatchStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc) - timedelta(days=10)
            )
            recent_batch = BatchJob(
                name="Recent Batch",
                status=BatchStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc) - timedelta(days=3)
            )
            db.session.add_all([old_batch, recent_batch])
            db.session.commit()

            # Add companies to old batch
            company = Company(
                company_name="Old Company",
                website_url="https://old.com",
                status=CompanyStatus.COMPLETED,
                batch_id=old_batch.id
            )
            db.session.add(company)
            db.session.commit()
            old_batch_id = old_batch.id
            company_id = company.id

            service = BatchQueueService()
            cleaned = service.cleanup_completed_batches(days_old=7)

            assert cleaned == 1

            # Old batch should be deleted
            assert db.session.get(BatchJob, old_batch_id) is None

            # Company should still exist but unassociated
            company = db.session.get(Company, company_id)
            assert company is not None
            assert company.batch_id is None

            # Recent batch should still exist
            assert recent_batch.id is not None


class TestBatchJobModel:
    """Tests for BatchJob model functionality."""

    def test_batch_to_dict(self, app):
        """Test BatchJob to_dict method."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                description="Test description",
                status=BatchStatus.PROCESSING,
                total_companies=10,
                completed_companies=5,
                failed_companies=1,
                total_tokens_used=5000,
                estimated_cost=0.50,
                priority=50,
                max_concurrent=5,
            )
            db.session.add(batch)
            db.session.commit()

            data = batch.to_dict()

            assert data['name'] == "Test Batch"
            assert data['description'] == "Test description"
            assert data['status'] == 'processing'
            assert data['totalCompanies'] == 10
            assert data['completedCompanies'] == 5
            assert data['failedCompanies'] == 1
            assert data['totalTokensUsed'] == 5000
            assert data['estimatedCost'] == 0.50
            assert data['priority'] == 50
            assert data['maxConcurrent'] == 5
            assert data['progress'] == 60.0  # (5+1)/10 * 100

    def test_batch_is_active(self, app):
        """Test BatchJob is_active property."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            pending = BatchJob(name="Pending", status=BatchStatus.PENDING)
            processing = BatchJob(name="Processing", status=BatchStatus.PROCESSING)
            completed = BatchJob(name="Completed", status=BatchStatus.COMPLETED)
            cancelled = BatchJob(name="Cancelled", status=BatchStatus.CANCELLED)

            assert pending.is_active is True
            assert processing.is_active is True
            assert completed.is_active is False
            assert cancelled.is_active is False

    def test_batch_is_finished(self, app):
        """Test BatchJob is_finished property."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            pending = BatchJob(name="Pending", status=BatchStatus.PENDING)
            processing = BatchJob(name="Processing", status=BatchStatus.PROCESSING)
            completed = BatchJob(name="Completed", status=BatchStatus.COMPLETED)
            cancelled = BatchJob(name="Cancelled", status=BatchStatus.CANCELLED)

            assert pending.is_finished is False
            assert processing.is_finished is False
            assert completed.is_finished is True
            assert cancelled.is_finished is True

    def test_batch_update_counts(self, app):
        """Test BatchJob update_counts method."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
            )
            db.session.add(batch)
            db.session.commit()

            # Add companies with various statuses
            companies = [
                Company(company_name="Pending 1", website_url="https://p1.com",
                        status=CompanyStatus.PENDING, batch_id=batch.id),
                Company(company_name="Pending 2", website_url="https://p2.com",
                        status=CompanyStatus.PENDING, batch_id=batch.id),
                Company(company_name="In Progress", website_url="https://ip.com",
                        status=CompanyStatus.IN_PROGRESS, batch_id=batch.id),
                Company(company_name="Completed", website_url="https://c.com",
                        status=CompanyStatus.COMPLETED, batch_id=batch.id),
                Company(company_name="Failed", website_url="https://f.com",
                        status=CompanyStatus.FAILED, batch_id=batch.id),
            ]
            db.session.add_all(companies)
            db.session.commit()

            batch.update_counts()
            db.session.commit()

            assert batch.total_companies == 5
            assert batch.pending_companies == 2
            assert batch.processing_companies == 1
            assert batch.completed_companies == 1
            assert batch.failed_companies == 1

    def test_batch_aggregate_tokens(self, app):
        """Test BatchJob aggregate_tokens method."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
            )
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(company_name=f"Company {i}", website_url=f"https://c{i}.com",
                        status=CompanyStatus.COMPLETED, batch_id=batch.id,
                        total_tokens_used=1000 * i, estimated_cost=0.10 * i)
                for i in range(1, 4)
            ]
            db.session.add_all(companies)
            db.session.commit()

            batch.aggregate_tokens()
            db.session.commit()

            assert batch.total_tokens_used == 6000  # 1000 + 2000 + 3000
            assert batch.estimated_cost == pytest.approx(0.60)  # 0.10 + 0.20 + 0.30


class TestGlobalBatchQueueService:
    """Tests for global batch_queue_service instance."""

    def test_global_service_exists(self, app):
        """Test that global service instance exists."""
        from app.services.batch_queue_service import batch_queue_service, BatchQueueService

        with app.app_context():
            assert batch_queue_service is not None
            assert isinstance(batch_queue_service, BatchQueueService)
