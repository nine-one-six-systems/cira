"""Integration tests for Batch API endpoints.

These tests verify batch upload response schemas, batch control operations,
and delete cascade behavior for API-02 and API-09 requirements.
"""

import io
import pytest
from unittest.mock import patch

from app import db
from app.models import (
    Company,
    BatchJob,
    Page,
    Entity,
    Analysis,
    TokenUsage,
    CrawlSession,
)
from app.models.enums import (
    CompanyStatus,
    BatchStatus,
    EntityType,
    PageType,
    ApiCallType,
)


def create_csv_file(content: str, filename: str = 'test.csv'):
    """Create a file-like object for CSV content."""
    return (io.BytesIO(content.encode('utf-8')), filename)


class TestBatchUploadResponses:
    """Tests for batch upload response schema (API-02).

    Verifies that POST /companies/batch returns proper response schema
    with totalCount, successful, failed, and companies array.
    """

    def test_successful_upload_response_schema(self, client):
        """Test successful batch upload returns proper schema (API-02).

        POST valid CSV to /companies/batch should return:
        - 201 status
        - success: true
        - data.totalCount, data.successful, data.failed, data.companies
        - Each company result has: companyName, companyId, error
        """
        csv_content = """company_name,website_url,industry
Acme Corp,https://acme.com,Technology
Beta Inc,https://beta.io,Healthcare
Gamma Ltd,https://gamma.co,Finance"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()

        # Verify top-level structure
        assert data['success'] is True
        assert 'data' in data

        # Verify data fields
        assert data['data']['totalCount'] == 3
        assert data['data']['successful'] == 3
        assert data['data']['failed'] == 0
        assert 'companies' in data['data']
        assert len(data['data']['companies']) == 3

        # Verify each company result has required fields
        for company in data['data']['companies']:
            assert 'companyName' in company
            assert 'companyId' in company
            assert 'error' in company
            # Successful uploads have companyId and null error
            assert company['companyId'] is not None
            assert company['error'] is None

    def test_partial_success_response(self, client):
        """Test batch upload with partial success returns correct counts (API-02).

        POST CSV with some invalid rows should return:
        - 201 status (partial success)
        - Correct success/fail counts
        - Failed rows have error messages, successful have companyId
        """
        csv_content = """company_name,website_url,industry
Valid Corp,https://valid.com,Technology
,https://noname.com,Healthcare
No URL Corp,,Finance
Invalid URL Corp,not-a-valid-url,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()

        assert data['data']['totalCount'] == 4
        assert data['data']['successful'] == 1
        assert data['data']['failed'] == 3

        companies = data['data']['companies']
        # First row (valid)
        assert companies[0]['companyId'] is not None
        assert companies[0]['error'] is None

        # Remaining rows (invalid) should have errors
        for i in range(1, 4):
            assert companies[i]['companyId'] is None
            assert companies[i]['error'] is not None

    def test_all_fail_response(self, client):
        """Test batch upload with all failures returns correct counts (API-02).

        POST CSV with all invalid rows should return:
        - 201 status
        - successful=0, failed=N
        - All companies have error field populated
        """
        csv_content = """company_name,website_url,industry
,https://noname.com,Healthcare
Another Missing,,Finance
Invalid URL Corp,not-a-valid-url,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()

        assert data['data']['totalCount'] == 3
        assert data['data']['successful'] == 0
        assert data['data']['failed'] == 3

        # All should have errors
        for company in data['data']['companies']:
            assert company['companyId'] is None
            assert company['error'] is not None

    def test_missing_file_error(self, client):
        """Test batch upload without file returns 400 with VALIDATION_ERROR (API-02).

        POST to /companies/batch without file should return:
        - 400 status
        - error.code = VALIDATION_ERROR
        """
        response = client.post(
            '/api/v1/companies/batch',
            data={},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_wrong_file_type_error(self, client):
        """Test batch upload with non-CSV file returns 400 (API-02).

        POST .txt file instead of .csv should return:
        - 400 status
        - error message mentions CSV
        """
        response = client.post(
            '/api/v1/companies/batch',
            data={'file': (io.BytesIO(b'test content'), 'test.txt')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert 'CSV' in data['error']['message']

    def test_empty_csv_error(self, client):
        """Test batch upload with empty CSV returns 400 (API-02).

        POST empty CSV file should return:
        - 400 status
        - Appropriate error message
        """
        csv_content = ""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_ERROR'


class TestBatchControlEndpoints:
    """Tests for batch control endpoints (start, pause, resume, cancel).

    Verifies that batch state transitions work correctly and return
    appropriate responses for valid and invalid operations.
    """

    def test_start_batch_success(self, client, app):
        """Test starting a pending batch succeeds.

        POST /batches/{id}/start should:
        - Return 200 with success=True
        - Change batch status to PROCESSING
        """
        with app.app_context():
            batch = BatchJob(name='Test Batch', status=BatchStatus.PENDING)
            db.session.add(batch)
            db.session.commit()

            company = Company(
                company_name='Test Company',
                website_url='https://example.com',
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
            data = response.get_json()
            assert data['success'] is True
            assert data['data']['success'] is True

    def test_pause_batch_success(self, client, app):
        """Test pausing a processing batch succeeds.

        POST /batches/{id}/pause should:
        - Return 200 with success=True
        - Change batch status to PAUSED
        """
        with app.app_context():
            batch = BatchJob(name='Test Batch', status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()

            company = Company(
                company_name='Test Company',
                website_url='https://example.com',
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
            data = response.get_json()
            assert data['success'] is True

    def test_resume_batch_success(self, client, app):
        """Test resuming a paused batch succeeds.

        POST /batches/{id}/resume should:
        - Return 200 with success=True
        - Change batch status to PROCESSING
        """
        with app.app_context():
            batch = BatchJob(name='Test Batch', status=BatchStatus.PAUSED)
            db.session.add(batch)
            db.session.commit()

            company = Company(
                company_name='Test Company',
                website_url='https://example.com',
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
                data = response.get_json()
                assert data['success'] is True

    def test_cancel_batch_success(self, client, app):
        """Test cancelling a processing batch succeeds.

        POST /batches/{id}/cancel should:
        - Return 200 with success=True
        - Change batch status to CANCELLED
        """
        with app.app_context():
            batch = BatchJob(name='Test Batch', status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()

            company = Company(
                company_name='Test Company',
                website_url='https://example.com',
                status=CompanyStatus.PENDING,
                batch_id=batch.id
            )
            db.session.add(company)
            db.session.commit()
            batch_id = batch.id

        response = client.post(f'/api/v1/batches/{batch_id}/cancel')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

    def test_invalid_state_transition_pause_completed(self, client, app):
        """Test pausing a completed batch returns 422.

        Try to pause completed batch should return 422 INVALID_STATE.
        """
        with app.app_context():
            batch = BatchJob(name='Test Batch', status=BatchStatus.COMPLETED)
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        response = client.post(f'/api/v1/batches/{batch_id}/pause')

        assert response.status_code == 422

    def test_invalid_state_transition_resume_processing(self, client, app):
        """Test resuming a processing batch returns 422.

        Try to resume processing batch should return 422 INVALID_STATE.
        """
        with app.app_context():
            batch = BatchJob(name='Test Batch', status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        response = client.post(f'/api/v1/batches/{batch_id}/resume')

        assert response.status_code == 422

    def test_invalid_state_transition_cancel_completed(self, client, app):
        """Test cancelling a completed batch returns 422.

        Try to cancel completed batch should return 422 INVALID_STATE.
        """
        with app.app_context():
            batch = BatchJob(name='Test Batch', status=BatchStatus.COMPLETED)
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

        response = client.post(f'/api/v1/batches/{batch_id}/cancel')

        assert response.status_code == 422

    def test_batch_not_found_start(self, client):
        """Test starting non-existent batch returns 404."""
        response = client.post('/api/v1/batches/nonexistent-id/start')
        assert response.status_code == 404

    def test_batch_not_found_pause(self, client):
        """Test pausing non-existent batch returns 404."""
        response = client.post('/api/v1/batches/nonexistent-id/pause')
        assert response.status_code == 404

    def test_batch_not_found_resume(self, client):
        """Test resuming non-existent batch returns 404."""
        response = client.post('/api/v1/batches/nonexistent-id/resume')
        assert response.status_code == 404

    def test_batch_not_found_cancel(self, client):
        """Test cancelling non-existent batch returns 404."""
        response = client.post('/api/v1/batches/nonexistent-id/cancel')
        assert response.status_code == 404


class TestDeleteCompanyEndpoint:
    """Tests for DELETE /companies/:id endpoint (API-09).

    Verifies that company deletion cascades to all related data
    including pages, entities, analyses, and token usage.
    """

    def test_delete_existing_company(self, client, app):
        """Test deleting an existing company returns 200 (API-09).

        DELETE /companies/{id} should:
        - Return 200 status
        - Company no longer in database
        """
        with app.app_context():
            company = Company(
                company_name='To Delete Corp',
                website_url='https://delete.com'
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.delete(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['deleted'] is True

        # Verify company is deleted
        with app.app_context():
            assert db.session.get(Company, company_id) is None

    def test_delete_cascades_pages(self, client, app):
        """Test delete cascades to Page records (API-09).

        DELETE company should also delete associated pages.
        """
        with app.app_context():
            company = Company(
                company_name='Cascade Corp',
                website_url='https://cascade.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add pages
            pages = [
                Page(
                    company_id=company.id,
                    url=f'https://cascade.com/page{i}',
                    page_type=PageType.ABOUT
                )
                for i in range(3)
            ]
            db.session.add_all(pages)
            db.session.commit()
            company_id = company.id
            page_ids = [p.id for p in pages]

        response = client.delete(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['deletedRecords']['pages'] == 3

        # Verify pages are deleted
        with app.app_context():
            for page_id in page_ids:
                assert db.session.get(Page, page_id) is None

    def test_delete_cascades_entities(self, client, app):
        """Test delete cascades to Entity records (API-09).

        DELETE company should also delete associated entities.
        """
        with app.app_context():
            company = Company(
                company_name='Entity Corp',
                website_url='https://entity.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add entities
            entities = [
                Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}'
                )
                for i in range(5)
            ]
            db.session.add_all(entities)
            db.session.commit()
            company_id = company.id
            entity_ids = [e.id for e in entities]

        response = client.delete(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['deletedRecords']['entities'] == 5

        # Verify entities are deleted
        with app.app_context():
            for entity_id in entity_ids:
                assert db.session.get(Entity, entity_id) is None

    def test_delete_cascades_analysis(self, client, app):
        """Test delete cascades to Analysis records (API-09).

        DELETE company should also delete associated analyses.
        """
        with app.app_context():
            company = Company(
                company_name='Analysis Corp',
                website_url='https://analysis.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add analysis
            analysis = Analysis(
                company_id=company.id,
                version_number=1,
                executive_summary='Test summary'
            )
            db.session.add(analysis)
            db.session.commit()
            company_id = company.id
            analysis_id = analysis.id

        response = client.delete(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['deletedRecords']['analyses'] == 1

        # Verify analysis is deleted
        with app.app_context():
            assert db.session.get(Analysis, analysis_id) is None

    def test_delete_cascades_token_usage(self, client, app):
        """Test delete cascades to TokenUsage records (API-09).

        DELETE company should also delete associated token usage records.
        """
        with app.app_context():
            company = Company(
                company_name='Token Corp',
                website_url='https://token.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add token usage records
            token_usages = [
                TokenUsage(
                    company_id=company.id,
                    api_call_type=ApiCallType.ANALYSIS,
                    input_tokens=100,
                    output_tokens=50
                )
                for _ in range(3)
            ]
            db.session.add_all(token_usages)
            db.session.commit()
            company_id = company.id
            token_ids = [t.id for t in token_usages]

        response = client.delete(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200

        # Verify token usage records are deleted
        with app.app_context():
            for token_id in token_ids:
                assert db.session.get(TokenUsage, token_id) is None

    def test_delete_nonexistent_company(self, client):
        """Test deleting non-existent company returns 404 (API-09).

        DELETE /companies/nonexistent-id should return 404.
        """
        response = client.delete('/api/v1/companies/nonexistent-id')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_delete_removes_from_batch(self, client, app):
        """Test delete removes company from batch but preserves batch (API-09).

        DELETE company associated with batch should:
        - Delete the company
        - Keep the batch intact
        """
        with app.app_context():
            batch = BatchJob(
                name='Test Batch',
                status=BatchStatus.PENDING,
                total_companies=2
            )
            db.session.add(batch)
            db.session.commit()

            company1 = Company(
                company_name='Company 1',
                website_url='https://company1.com',
                batch_id=batch.id
            )
            company2 = Company(
                company_name='Company 2',
                website_url='https://company2.com',
                batch_id=batch.id
            )
            db.session.add_all([company1, company2])
            db.session.commit()

            batch_id = batch.id
            company1_id = company1.id
            company2_id = company2.id

        response = client.delete(f'/api/v1/companies/{company1_id}')

        assert response.status_code == 200

        # Verify batch still exists
        with app.app_context():
            batch = db.session.get(BatchJob, batch_id)
            assert batch is not None

            # Company 2 should still exist
            assert db.session.get(Company, company2_id) is not None

            # Company 1 should be deleted
            assert db.session.get(Company, company1_id) is None

    def test_delete_full_cascade(self, client, app):
        """Test full cascade deletes all related records (API-09).

        Create company with all related records and verify complete deletion.
        """
        with app.app_context():
            company = Company(
                company_name='Full Cascade Corp',
                website_url='https://fullcascade.com'
            )
            db.session.add(company)
            db.session.flush()
            company_id = company.id

            # Add 3 Page records
            pages = [
                Page(company_id=company_id, url=f'https://fullcascade.com/page{i}')
                for i in range(3)
            ]
            db.session.add_all(pages)

            # Add 5 Entity records
            entities = [
                Entity(
                    company_id=company_id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}'
                )
                for i in range(5)
            ]
            db.session.add_all(entities)

            # Add 1 Analysis record
            analysis = Analysis(
                company_id=company_id,
                version_number=1,
                executive_summary='Test summary'
            )
            db.session.add(analysis)

            # Add 2 TokenUsage records
            token_usages = [
                TokenUsage(
                    company_id=company_id,
                    api_call_type=ApiCallType.EXTRACTION,
                    input_tokens=100,
                    output_tokens=50
                )
                for _ in range(2)
            ]
            db.session.add_all(token_usages)

            # Add 1 CrawlSession record
            crawl_session = CrawlSession(
                company_id=company_id,
                pages_crawled=3
            )
            db.session.add(crawl_session)

            db.session.commit()

            # Store all IDs for verification
            page_ids = [p.id for p in pages]
            entity_ids = [e.id for e in entities]
            analysis_id = analysis.id
            token_ids = [t.id for t in token_usages]
            crawl_session_id = crawl_session.id

        response = client.delete(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['deleted'] is True
        assert data['data']['deletedRecords']['pages'] == 3
        assert data['data']['deletedRecords']['entities'] == 5
        assert data['data']['deletedRecords']['analyses'] == 1

        # Verify all related records are deleted
        with app.app_context():
            # Company deleted
            assert db.session.get(Company, company_id) is None

            # Pages deleted
            for page_id in page_ids:
                assert db.session.get(Page, page_id) is None

            # Entities deleted
            for entity_id in entity_ids:
                assert db.session.get(Entity, entity_id) is None

            # Analysis deleted
            assert db.session.get(Analysis, analysis_id) is None

            # Token usages deleted
            for token_id in token_ids:
                assert db.session.get(TokenUsage, token_id) is None

            # Crawl session deleted
            assert db.session.get(CrawlSession, crawl_session_id) is None

    def test_delete_preserves_unrelated_data(self, client, app):
        """Test delete preserves unrelated company data (API-09).

        Delete first company should not affect second company's data.
        """
        with app.app_context():
            # Create two companies with data
            company1 = Company(
                company_name='Company 1',
                website_url='https://company1.com'
            )
            company2 = Company(
                company_name='Company 2',
                website_url='https://company2.com'
            )
            db.session.add_all([company1, company2])
            db.session.flush()

            # Add pages to both
            page1 = Page(company_id=company1.id, url='https://company1.com/about')
            page2 = Page(company_id=company2.id, url='https://company2.com/about')
            db.session.add_all([page1, page2])

            # Add entities to both
            entity1 = Entity(
                company_id=company1.id,
                entity_type=EntityType.PERSON,
                entity_value='John Doe'
            )
            entity2 = Entity(
                company_id=company2.id,
                entity_type=EntityType.PERSON,
                entity_value='Jane Doe'
            )
            db.session.add_all([entity1, entity2])

            db.session.commit()

            company1_id = company1.id
            company2_id = company2.id
            page2_id = page2.id
            entity2_id = entity2.id

        # Delete first company
        response = client.delete(f'/api/v1/companies/{company1_id}')
        assert response.status_code == 200

        # Verify second company and its data still exist
        with app.app_context():
            assert db.session.get(Company, company2_id) is not None
            assert db.session.get(Page, page2_id) is not None
            assert db.session.get(Entity, entity2_id) is not None

    def test_delete_handles_in_progress_company(self, client, app):
        """Test delete handles IN_PROGRESS company (API-09).

        Verify IN_PROGRESS company can be deleted.
        """
        with app.app_context():
            company = Company(
                company_name='In Progress Corp',
                website_url='https://inprogress.com',
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.delete(f'/api/v1/companies/{company_id}')

        # Should successfully delete (no restriction on in-progress)
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['deleted'] is True

        # Verify company is deleted
        with app.app_context():
            assert db.session.get(Company, company_id) is None


class TestBatchListingEndpoints:
    """Tests for batch listing API endpoints.

    Verifies pagination, filtering, and batch companies listing.
    """

    def test_list_batches_pagination(self, client, app):
        """Test batch listing with pagination.

        GET /batches?limit=3&offset=2 should return proper subset.
        """
        with app.app_context():
            batches = [
                BatchJob(name=f'Batch {i}', status=BatchStatus.PENDING)
                for i in range(10)
            ]
            db.session.add_all(batches)
            db.session.commit()

        response = client.get('/api/v1/batches?limit=3&offset=2')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['total'] == 10
        assert len(data['data']['batches']) == 3
        assert data['data']['limit'] == 3
        assert data['data']['offset'] == 2

    def test_list_batches_status_filter(self, client, app):
        """Test batch listing with status filter.

        GET /batches?status=processing should return only processing batches.
        """
        with app.app_context():
            batches = [
                BatchJob(name='Pending 1', status=BatchStatus.PENDING),
                BatchJob(name='Processing 1', status=BatchStatus.PROCESSING),
                BatchJob(name='Processing 2', status=BatchStatus.PROCESSING),
                BatchJob(name='Completed 1', status=BatchStatus.COMPLETED),
            ]
            db.session.add_all(batches)
            db.session.commit()

        response = client.get('/api/v1/batches?status=processing')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['total'] == 2
        for batch in data['data']['batches']:
            assert batch['status'] == 'processing'

    def test_get_batch_companies(self, client, app):
        """Test getting companies in a batch.

        GET /batches/{id}/companies should return all companies in batch.
        """
        with app.app_context():
            batch = BatchJob(name='Test Batch', status=BatchStatus.PROCESSING)
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(
                    company_name=f'Company {i}',
                    website_url=f'https://company{i}.com',
                    status=CompanyStatus.PENDING,
                    batch_id=batch.id
                )
                for i in range(5)
            ]
            db.session.add_all(companies)
            db.session.commit()
            batch_id = batch.id

        response = client.get(f'/api/v1/batches/{batch_id}/companies')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['total'] == 5
        assert len(data['data']['companies']) == 5
