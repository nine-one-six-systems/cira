"""Tests for Batch Queue Management API endpoints."""

import pytest
import json
from unittest.mock import patch


class TestCreateBatchEndpoint:
    """Tests for POST /api/v1/batches."""

    def test_create_batch_success(self, client, app):
        """Test successfully creating a batch via API."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus

        with app.app_context():
            # Create test companies
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
            company_ids = [c.id for c in companies]

        with patch('app.services.batch_queue_service.job_service'):
            response = client.post(
                '/api/v1/batches',
                json={
                    'companyIds': company_ids,
                    'name': 'Test Batch',
                    'description': 'Test description',
                    'priority': 50,
                    'maxConcurrent': 5,
                    'startImmediately': False,
                },
                content_type='application/json'
            )

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['success'] is True
            assert 'batch_id' in data['data']

    def test_create_batch_missing_company_ids(self, client):
        """Test creating batch without company IDs."""
        response = client.post(
            '/api/v1/batches',
            json={'name': 'Test Batch'},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        # Check message contains companyIds (case insensitive)
        assert 'companyids' in data['error']['message'].lower()

    def test_create_batch_empty_company_list(self, client):
        """Test creating batch with empty company list."""
        response = client.post(
            '/api/v1/batches',
            json={'companyIds': []},
            content_type='application/json'
        )

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


class TestListBatchesEndpoint:
    """Tests for GET /api/v1/batches."""

    def test_list_batches_empty(self, client):
        """Test listing batches when none exist."""
        response = client.get('/api/v1/batches')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['total'] == 0
        assert data['data']['batches'] == []

    def test_list_batches_with_data(self, client, app):
        """Test listing batches with data."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            batches = [
                BatchJob(name=f"Batch {i}", status=BatchStatus.PENDING)
                for i in range(5)
            ]
            db.session.add_all(batches)
            db.session.commit()

        response = client.get('/api/v1/batches')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['total'] == 5
        assert len(data['data']['batches']) == 5

    def test_list_batches_with_status_filter(self, client, app):
        """Test listing batches with status filter."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            batches = [
                BatchJob(name="Pending", status=BatchStatus.PENDING),
                BatchJob(name="Processing", status=BatchStatus.PROCESSING),
                BatchJob(name="Completed", status=BatchStatus.COMPLETED),
            ]
            db.session.add_all(batches)
            db.session.commit()

        response = client.get('/api/v1/batches?status=pending')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['total'] == 1
        assert data['data']['batches'][0]['status'] == 'pending'

    def test_list_batches_invalid_status(self, client):
        """Test listing batches with invalid status."""
        response = client.get('/api/v1/batches?status=invalid')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False

    def test_list_batches_pagination(self, client, app):
        """Test batch listing pagination."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            batches = [
                BatchJob(name=f"Batch {i}", status=BatchStatus.PENDING)
                for i in range(10)
            ]
            db.session.add_all(batches)
            db.session.commit()

        response = client.get('/api/v1/batches?limit=3&offset=2')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['total'] == 10
        assert len(data['data']['batches']) == 3
        assert data['data']['limit'] == 3
        assert data['data']['offset'] == 2


class TestGetBatchEndpoint:
    """Tests for GET /api/v1/batches/<batch_id>."""

    def test_get_batch_success(self, client, app):
        """Test getting a specific batch."""
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
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        response = client.get(f'/api/v1/batches/{batch_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['name'] == 'Test Batch'
        assert data['data']['status'] == 'processing'

    def test_get_batch_not_found(self, client):
        """Test getting non-existent batch."""
        response = client.get('/api/v1/batches/nonexistent-id')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['success'] is False


class TestBatchProgressEndpoint:
    """Tests for GET /api/v1/batches/<batch_id>/progress."""

    def test_get_batch_progress(self, client, app):
        """Test getting batch progress."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            batch = BatchJob(
                name="Test Batch",
                status=BatchStatus.PROCESSING,
                total_companies=10,
                completed_companies=5,
                failed_companies=1,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        response = client.get(f'/api/v1/batches/{batch_id}/progress')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['total'] == 10
        assert data['data']['completed'] == 5
        assert data['data']['progress_percentage'] == 60.0

    def test_get_batch_progress_not_found(self, client):
        """Test getting progress for non-existent batch."""
        response = client.get('/api/v1/batches/nonexistent-id/progress')

        assert response.status_code == 404


class TestBatchCompaniesEndpoint:
    """Tests for GET /api/v1/batches/<batch_id>/companies."""

    def test_get_batch_companies(self, client, app):
        """Test getting companies in a batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(
                    company_name=f"Company {i}",
                    website_url=f"https://example{i}.com",
                    status=CompanyStatus.PENDING,
                    batch_id=batch.id
                )
                for i in range(3)
            ]
            db.session.add_all(companies)
            db.session.commit()
            batch_id = batch.id

        response = client.get(f'/api/v1/batches/{batch_id}/companies')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['data']['total'] == 3
        assert len(data['data']['companies']) == 3

    def test_get_batch_companies_not_found(self, client):
        """Test getting companies for non-existent batch."""
        response = client.get('/api/v1/batches/nonexistent-id/companies')

        assert response.status_code == 404

    def test_get_batch_companies_with_status_filter(self, client, app):
        """Test filtering batch companies by status."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(company_name="Pending", website_url="https://p.com",
                        status=CompanyStatus.PENDING, batch_id=batch.id),
                Company(company_name="Completed", website_url="https://c.com",
                        status=CompanyStatus.COMPLETED, batch_id=batch.id),
            ]
            db.session.add_all(companies)
            db.session.commit()
            batch_id = batch.id

        response = client.get(f'/api/v1/batches/{batch_id}/companies?status=pending')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['data']['total'] == 1
        assert data['data']['companies'][0]['status'] == 'pending'


class TestStartBatchEndpoint:
    """Tests for POST /api/v1/batches/<batch_id>/start."""

    def test_start_batch_success(self, client, app):
        """Test starting a batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.PENDING)
            db.session.add(batch)
            db.session.commit()

            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PENDING,
                batch_id=batch.id
            )
            db.session.add(company)
            db.session.commit()
            batch_id = batch.id

        with patch('app.services.batch_queue_service.job_service') as mock_job:
            mock_job.start_job.return_value = {'success': True}

            response = client.post(f'/api/v1/batches/{batch_id}/start')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['data']['success'] is True

    def test_start_batch_not_found(self, client):
        """Test starting non-existent batch."""
        response = client.post('/api/v1/batches/nonexistent-id/start')

        assert response.status_code == 404


class TestPauseBatchEndpoint:
    """Tests for POST /api/v1/batches/<batch_id>/pause."""

    def test_pause_batch_success(self, client, app):
        """Test pausing a batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()

            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                batch_id=batch.id
            )
            db.session.add(company)
            db.session.commit()
            batch_id = batch.id

        with patch('app.api.routes.control._pause_company_internal') as mock_pause:
            mock_pause.return_value = {'success': True}

            response = client.post(f'/api/v1/batches/{batch_id}/pause')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True

    def test_pause_batch_invalid_state(self, client, app):
        """Test pausing batch in invalid state."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.COMPLETED)
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        response = client.post(f'/api/v1/batches/{batch_id}/pause')

        assert response.status_code == 422


class TestResumeBatchEndpoint:
    """Tests for POST /api/v1/batches/<batch_id>/resume."""

    def test_resume_batch_success(self, client, app):
        """Test resuming a paused batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.PAUSED)
            db.session.add(batch)
            db.session.commit()

            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED,
                batch_id=batch.id
            )
            db.session.add(company)
            db.session.commit()
            batch_id = batch.id

        with patch('app.api.routes.control._resume_company_internal') as mock_resume:
            mock_resume.return_value = {'success': True}
            with patch('app.services.batch_queue_service.job_service'):
                response = client.post(f'/api/v1/batches/{batch_id}/resume')

                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True

    def test_resume_batch_not_paused(self, client, app):
        """Test resuming batch that's not paused."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        response = client.post(f'/api/v1/batches/{batch_id}/resume')

        assert response.status_code == 422


class TestCancelBatchEndpoint:
    """Tests for POST /api/v1/batches/<batch_id>/cancel."""

    def test_cancel_batch_success(self, client, app):
        """Test cancelling a batch."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()

            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PENDING,
                batch_id=batch.id
            )
            db.session.add(company)
            db.session.commit()
            batch_id = batch.id

        response = client.post(f'/api/v1/batches/{batch_id}/cancel')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

    def test_cancel_batch_already_completed(self, client, app):
        """Test cancelling already completed batch."""
        from app import db
        from app.models import BatchJob
        from app.models.enums import BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.COMPLETED)
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        response = client.post(f'/api/v1/batches/{batch_id}/cancel')

        assert response.status_code == 422


class TestScheduleBatchesEndpoint:
    """Tests for POST /api/v1/batches/schedule."""

    def test_schedule_batches(self, client, app):
        """Test triggering fair scheduling."""
        from app import db
        from app.models import Company, BatchJob
        from app.models.enums import CompanyStatus, BatchStatus

        with app.app_context():
            batch = BatchJob(name="Test Batch", status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()

            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PENDING,
                batch_id=batch.id
            )
            db.session.add(company)
            db.session.commit()

        with patch('app.services.batch_queue_service.job_service') as mock_job:
            mock_job.start_job.return_value = {'success': True}

            response = client.post('/api/v1/batches/schedule')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'companies_scheduled' in data['data']
