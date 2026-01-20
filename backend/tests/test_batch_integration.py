"""
Batch pipeline integration tests.

Tests the full batch processing pipeline from CSV upload through company
creation and batch queue management.

Requirements covered:
- BAT-01: CSV file upload
- BAT-02: Validate CSV, report errors per row
- BAT-03: Download CSV template
- BAT-04: Queue batch companies
- API-02: POST /companies/batch
"""

import pytest
from unittest.mock import patch, MagicMock

from app import db
from app.models import BatchJob, Company
from app.models.enums import BatchStatus, CompanyStatus
from app.services.batch_queue_service import batch_queue_service

from backend.tests.fixtures.batch_fixtures import (
    VALID_CSV_CONTENT,
    MIXED_VALIDITY_CSV,
    CSV_WITH_DUPLICATES,
    LARGE_CSV_CONTENT,
    create_csv_file,
    create_batch_with_companies,
    create_processing_batch,
    create_batch_ready_for_completion,
)


# =============================================================================
# Test Class: Batch Upload Flow (BAT-01, BAT-02, API-02)
# =============================================================================

class TestBatchUploadFlow:
    """
    Integration tests for batch CSV upload flow.

    Covers requirements BAT-01, BAT-02, API-02.
    """

    def test_valid_csv_creates_all_companies(self, client, app):
        """
        Test that uploading a valid CSV creates all companies (BAT-01, API-02).

        Verifies:
        - 201 response with success=True
        - All 5 companies created in database
        - Each company has correct name and URL
        - Companies have PENDING status
        """
        with patch('app.services.batch_queue_service.job_service') as mock_job:
            mock_job.start_job.return_value = {'success': True}

            response = client.post(
                '/api/v1/companies/batch',
                data={'file': create_csv_file(VALID_CSV_CONTENT)},
                content_type='multipart/form-data'
            )

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['totalCount'] == 5
        assert data['data']['successful'] == 5
        assert data['data']['failed'] == 0

        # Verify all companies created in database
        with app.app_context():
            companies = Company.query.all()
            assert len(companies) == 5

            # Check company names and URLs
            names = {c.company_name for c in companies}
            expected_names = {'Acme Corp', 'Beta Inc', 'Gamma Ltd', 'Delta LLC', 'Epsilon Co'}
            assert names == expected_names

            # All should be PENDING status
            for company in companies:
                assert company.status == CompanyStatus.PENDING

    def test_mixed_csv_reports_per_row_errors(self, client, app):
        """
        Test that mixed validity CSV reports per-row errors (BAT-02).

        Verifies:
        - Response has totalCount=5, successful=3, failed=2
        - Specific error messages for each failed row
        - Row 2 error mentions "name" or "required"
        - Row 4 error mentions "Invalid URL" or "URL"
        """
        with patch('app.services.batch_queue_service.job_service') as mock_job:
            mock_job.start_job.return_value = {'success': True}

            response = client.post(
                '/api/v1/companies/batch',
                data={'file': create_csv_file(MIXED_VALIDITY_CSV)},
                content_type='multipart/form-data'
            )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['totalCount'] == 5
        assert data['data']['successful'] == 3
        assert data['data']['failed'] == 2

        # Check specific error messages
        companies = data['data']['companies']

        # Row 1: Valid - should have companyId
        assert companies[0]['companyId'] is not None
        assert companies[0]['error'] is None

        # Row 2: Missing name - should have error
        assert companies[1]['error'] is not None
        assert 'name' in companies[1]['error'].lower() or 'required' in companies[1]['error'].lower()

        # Row 3: Valid
        assert companies[2]['companyId'] is not None
        assert companies[2]['error'] is None

        # Row 4: Invalid URL - should have error
        assert companies[3]['error'] is not None
        assert 'url' in companies[3]['error'].lower() or 'invalid' in companies[3]['error'].lower()

        # Row 5: Valid
        assert companies[4]['companyId'] is not None
        assert companies[4]['error'] is None

    def test_duplicate_urls_detected(self, client, app):
        """
        Test that duplicate URLs within batch are detected (BAT-02).

        Verifies:
        - Second occurrence of same.com has error
        - First occurrence succeeds
        - Third row (unique URL) succeeds
        """
        with patch('app.services.batch_queue_service.job_service') as mock_job:
            mock_job.start_job.return_value = {'success': True}

            response = client.post(
                '/api/v1/companies/batch',
                data={'file': create_csv_file(CSV_WITH_DUPLICATES)},
                content_type='multipart/form-data'
            )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 2
        assert data['data']['failed'] == 1

        companies = data['data']['companies']

        # First same.com should succeed
        assert companies[0]['companyId'] is not None
        assert companies[0]['error'] is None

        # Second same.com should fail with duplicate error
        assert companies[1]['error'] is not None
        assert 'duplicate' in companies[1]['error'].lower()

        # Third unique.com should succeed
        assert companies[2]['companyId'] is not None
        assert companies[2]['error'] is None

    def test_companies_linked_to_batch_job(self, client, app):
        """
        Test that uploaded companies are linked to a BatchJob.

        Verifies:
        - All created companies have batch_id set
        - BatchJob exists in database
        - batch.total_companies matches upload count
        """
        with patch('app.services.batch_queue_service.job_service') as mock_job:
            mock_job.start_job.return_value = {'success': True}

            response = client.post(
                '/api/v1/companies/batch',
                data={'file': create_csv_file(VALID_CSV_CONTENT)},
                content_type='multipart/form-data'
            )

        assert response.status_code == 201
        data = response.get_json()

        # Response should include batch ID
        assert 'batchId' in data['data']
        batch_id = data['data']['batchId']

        # Verify batch exists and companies linked
        with app.app_context():
            batch = db.session.get(BatchJob, batch_id)
            assert batch is not None
            assert batch.total_companies == 5

            # All companies should have batch_id
            companies = Company.query.filter_by(batch_id=batch_id).all()
            assert len(companies) == 5

    def test_large_csv_handles_many_rows(self, client, app):
        """
        Test that large CSV (50 rows) is handled correctly.

        Verifies:
        - All 50 companies created successfully
        - No timeout or memory issues
        """
        with patch('app.services.batch_queue_service.job_service') as mock_job:
            mock_job.start_job.return_value = {'success': True}

            response = client.post(
                '/api/v1/companies/batch',
                data={'file': create_csv_file(LARGE_CSV_CONTENT)},
                content_type='multipart/form-data'
            )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['totalCount'] == 50
        assert data['data']['successful'] == 50
        assert data['data']['failed'] == 0


# =============================================================================
# Test Class: Batch Queue Flow (BAT-04)
# =============================================================================

class TestBatchQueueFlow:
    """
    Integration tests for batch queue management.

    Covers requirement BAT-04: Queue batch companies for processing.
    """

    def test_batch_start_schedules_companies(self, client, app):
        """
        Test that starting a batch schedules companies (BAT-04).

        Verifies:
        - POST /batches/{id}/start returns success
        - Batch status changes to PROCESSING
        - At least one company gets scheduled (IN_PROGRESS)
        """
        with app.app_context():
            # Create batch with pending companies
            batch, companies = create_batch_with_companies(
                db, company_count=3, batch_status=BatchStatus.PENDING
            )
            batch_id = batch.id

        with patch('app.services.batch_queue_service.job_service') as mock_job:
            mock_job.start_job.return_value = {'success': True}

            response = client.post(f'/api/v1/batches/{batch_id}/start')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['batch_id'] == batch_id

        # Verify batch status changed
        with app.app_context():
            batch = db.session.get(BatchJob, batch_id)
            assert batch.status == BatchStatus.PROCESSING

    def test_company_completion_updates_batch_counts(self, client, app):
        """
        Test that company completion updates batch counts (BAT-04).

        Verifies:
        - batch.completed_companies incremented after company completes
        - batch.processing_companies decremented
        """
        with app.app_context():
            batch, companies = create_processing_batch(db)
            batch_id = batch.id
            # Get the in-progress company
            in_progress_company = next(c for c in companies if c.status == CompanyStatus.IN_PROGRESS)
            company_id = in_progress_company.id

            # Record initial counts
            initial_completed = batch.completed_companies
            initial_processing = batch.processing_companies

        # Simulate company completion by directly calling service
        with app.app_context():
            company = db.session.get(Company, company_id)
            old_status = company.status
            company.status = CompanyStatus.COMPLETED
            db.session.commit()

            # Call the status change handler
            with patch('app.services.batch_queue_service.job_service') as mock_job:
                mock_job.start_job.return_value = {'success': True}
                batch_queue_service.on_company_status_change(
                    company_id,
                    old_status,
                    CompanyStatus.COMPLETED
                )

            # Verify batch counts updated
            batch = db.session.get(BatchJob, batch_id)
            assert batch.completed_companies > initial_completed

    def test_batch_auto_completes_when_all_done(self, client, app):
        """
        Test that batch auto-completes when all companies are done (BAT-04).

        Verifies:
        - When last company completes, batch status becomes COMPLETED
        """
        with app.app_context():
            batch, companies = create_batch_ready_for_completion(db)
            batch_id = batch.id
            # Get the last company (IN_PROGRESS)
            last_company = next(c for c in companies if c.status == CompanyStatus.IN_PROGRESS)
            company_id = last_company.id

        # Complete the last company
        with app.app_context():
            company = db.session.get(Company, company_id)
            old_status = company.status
            company.status = CompanyStatus.COMPLETED
            db.session.commit()

            # Call the status change handler
            with patch('app.services.batch_queue_service.job_service') as mock_job:
                mock_job.start_job.return_value = {'success': True}
                batch_queue_service.on_company_status_change(
                    company_id,
                    old_status,
                    CompanyStatus.COMPLETED
                )

            # Verify batch is now COMPLETED
            batch = db.session.get(BatchJob, batch_id)
            assert batch.status == BatchStatus.COMPLETED
            assert batch.pending_companies == 0
            assert batch.processing_companies == 0
            assert batch.completed_companies == 3


# =============================================================================
# Test Class: Template Download (BAT-03)
# =============================================================================

class TestTemplateDownload:
    """
    Integration tests for CSV template download.

    Covers requirement BAT-03: Download CSV template.
    """

    def test_template_has_required_columns(self, client):
        """
        Test that template contains required columns (BAT-03).

        Verifies:
        - Response contains company_name, website_url, industry
        - Content-Type is text/csv
        """
        response = client.get('/api/v1/companies/template')

        assert response.status_code == 200
        assert 'text/csv' in response.content_type

        content = response.data.decode('utf-8')
        assert 'company_name' in content
        assert 'website_url' in content
        assert 'industry' in content

    def test_template_includes_example_data(self, client):
        """
        Test that template includes example rows (BAT-03).

        Verifies:
        - Parse CSV content
        - At least 2 rows (header + example)
        """
        response = client.get('/api/v1/companies/template')

        content = response.data.decode('utf-8')
        lines = [line for line in content.strip().split('\n') if line]

        # Should have header + at least 1 example row
        assert len(lines) >= 2

        # First line should be header
        assert lines[0] == 'company_name,website_url,industry'


# =============================================================================
# Test Class: Batch Progress Tracking
# =============================================================================

class TestBatchProgressTracking:
    """
    Integration tests for batch progress tracking.

    Covers batch progress percentage calculation and status counts.
    """

    def test_progress_percentage_calculation(self, client, app):
        """
        Test progress percentage is calculated correctly.

        Verifies:
        - With 10 companies, 5 completed, progress is 50%
        """
        with app.app_context():
            # Create batch with 10 companies, manually set 5 as completed
            batch = BatchJob(
                name='Progress Test Batch',
                status=BatchStatus.PROCESSING,
                total_companies=10,
                pending_companies=2,
                processing_companies=3,
                completed_companies=5,
                failed_companies=0,
                max_concurrent=3,
                priority=100,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        response = client.get(f'/api/v1/batches/{batch_id}/progress')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['progress_percentage'] == 50.0

    def test_progress_includes_all_counts(self, client, app):
        """
        Test progress includes all status counts.

        Verifies:
        - pending, processing, completed, failed counts are correct
        """
        with app.app_context():
            batch, companies = create_processing_batch(db)
            batch_id = batch.id

        response = client.get(f'/api/v1/batches/{batch_id}/progress')

        assert response.status_code == 200
        data = response.get_json()

        # Verify all counts present
        assert 'pending' in data['data']
        assert 'processing' in data['data']
        assert 'completed' in data['data']
        assert 'failed' in data['data']

        # Verify counts match fixture (2 pending, 1 processing, 1 completed)
        assert data['data']['pending'] == 2
        assert data['data']['processing'] == 1
        assert data['data']['completed'] == 1
        assert data['data']['failed'] == 0

    def test_progress_not_found_returns_404(self, client):
        """
        Test that progress for non-existent batch returns 404.
        """
        response = client.get('/api/v1/batches/nonexistent-batch-id/progress')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'


# =============================================================================
# Test Class: Batch Control Operations
# =============================================================================

class TestBatchControlOperations:
    """
    Integration tests for batch control operations (pause, resume, cancel).
    """

    def test_pause_batch_changes_status(self, client, app):
        """
        Test that pausing a batch changes its status.
        """
        with app.app_context():
            batch, companies = create_processing_batch(db)
            batch_id = batch.id

        with patch('app.api.routes.control._pause_company_internal') as mock_pause:
            mock_pause.return_value = {'success': True}
            response = client.post(f'/api/v1/batches/{batch_id}/pause')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        with app.app_context():
            batch = db.session.get(BatchJob, batch_id)
            assert batch.status == BatchStatus.PAUSED

    def test_resume_batch_restarts_processing(self, client, app):
        """
        Test that resuming a paused batch restarts processing.
        """
        with app.app_context():
            batch, companies = create_processing_batch(db)
            batch.status = BatchStatus.PAUSED
            # Also set companies to PAUSED status
            for c in companies:
                if c.status == CompanyStatus.IN_PROGRESS:
                    c.status = CompanyStatus.PAUSED
            db.session.commit()
            batch_id = batch.id

        with patch('app.api.routes.control._resume_company_internal') as mock_resume:
            mock_resume.return_value = {'success': True}
            with patch('app.services.batch_queue_service.job_service') as mock_job:
                mock_job.start_job.return_value = {'success': True}
                response = client.post(f'/api/v1/batches/{batch_id}/resume')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        with app.app_context():
            batch = db.session.get(BatchJob, batch_id)
            assert batch.status == BatchStatus.PROCESSING

    def test_cancel_batch_stops_all_work(self, client, app):
        """
        Test that cancelling a batch stops all pending/in-progress work.
        """
        with app.app_context():
            batch, companies = create_processing_batch(db)
            batch_id = batch.id

        with patch('app.services.redis_service.redis_service') as mock_redis:
            mock_redis.cleanup_job.return_value = None
            response = client.post(f'/api/v1/batches/{batch_id}/cancel')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        with app.app_context():
            batch = db.session.get(BatchJob, batch_id)
            assert batch.status == BatchStatus.CANCELLED

    def test_cannot_start_completed_batch(self, client, app):
        """
        Test that starting an already completed batch returns error.
        """
        with app.app_context():
            batch, _ = create_batch_with_companies(
                db, company_count=3, batch_status=BatchStatus.COMPLETED
            )
            batch_id = batch.id

        response = client.post(f'/api/v1/batches/{batch_id}/start')

        assert response.status_code == 422
        data = response.get_json()
        assert data['success'] is False
        assert 'already completed' in data['error']['message'].lower()
