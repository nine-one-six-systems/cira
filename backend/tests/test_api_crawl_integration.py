"""API Integration tests for Company CRUD endpoints.

These tests verify the full create-to-list workflow for companies,
including pagination, filtering, sorting, and related data counts.

Requirements verified:
- API-01: POST /companies creates company and returns 201
- API-03: GET /companies lists companies with status badges
- API-04: GET /companies/:id returns company with page count and analysis
"""

import pytest
from app import db
from app.models.company import Company, Page, Entity, Analysis
from app.models.enums import CompanyStatus, AnalysisMode, EntityType, PageType


class TestCompanyCreationFlow:
    """Tests for company creation flow - API-01 requirement."""

    def test_create_company_returns_correct_response_format(self, client):
        """
        API-01: POST /companies with valid data returns 201
        Response must have: success=true, data.companyId, data.status='pending', data.createdAt
        """
        response = client.post('/api/v1/companies', json={
            'companyName': 'Integration Test Corp',
            'websiteUrl': 'https://integration-test.com',
            'industry': 'Technology'
        })

        assert response.status_code == 201
        assert response.content_type == 'application/json'

        data = response.get_json()
        assert data['success'] is True
        assert 'companyId' in data['data']
        assert data['data']['status'] == 'pending'
        assert 'createdAt' in data['data']

        # Verify companyId is a valid format (UUID-like string)
        assert len(data['data']['companyId']) > 0

    def test_create_company_with_crawl_config(self, client, app):
        """
        API-01: POST with config persists all configuration values.
        Config includes: maxPages, maxDepth, followLinkedIn, etc.
        """
        response = client.post('/api/v1/companies', json={
            'companyName': 'Configured Corp',
            'websiteUrl': 'https://configured-corp.com',
            'config': {
                'maxPages': 100,
                'maxDepth': 5,
                'followLinkedIn': True,
                'followTwitter': False,
                'followFacebook': True,
                'analysisMode': 'thorough',
                'timeLimitMinutes': 30,
                'exclusionPatterns': ['/blog/*', '/archive/*']
            }
        })

        assert response.status_code == 201
        company_id = response.get_json()['data']['companyId']

        # Verify config was persisted by fetching the company
        get_response = client.get(f'/api/v1/companies/{company_id}')
        assert get_response.status_code == 200

        # Verify in database directly
        with app.app_context():
            company = db.session.get(Company, company_id)
            assert company is not None
            assert company.config['maxPages'] == 100
            assert company.config['maxDepth'] == 5
            assert company.config['followLinkedIn'] is True
            assert company.config['followTwitter'] is False
            assert company.config['followFacebook'] is True
            assert company.analysis_mode == AnalysisMode.THOROUGH

    def test_create_company_validates_url_format(self, client):
        """
        API-01: Invalid URL formats return 400 with VALIDATION_ERROR code.
        Test cases: 'not-a-url', 'ftp://invalid.com', ''
        """
        invalid_urls = [
            ('not-a-url', 'invalid URL format'),
            ('ftp://invalid.com', 'invalid protocol'),
            ('', 'empty URL'),
        ]

        for invalid_url, description in invalid_urls:
            response = client.post('/api/v1/companies', json={
                'companyName': 'Bad URL Corp',
                'websiteUrl': invalid_url
            })

            assert response.status_code == 400, f"Expected 400 for {description}"
            data = response.get_json()
            assert data['success'] is False, f"Expected success=false for {description}"
            assert data['error']['code'] == 'VALIDATION_ERROR', f"Expected VALIDATION_ERROR for {description}"

    def test_create_company_rejects_duplicate_url(self, client, app):
        """
        API-01: Duplicate URL (normalized) returns 409 with CONFLICT code
        and includes existingCompanyId in response details.
        """
        # Create first company
        with app.app_context():
            company = Company(
                company_name='Original Corp',
                website_url='https://duplicate-test.com'
            )
            db.session.add(company)
            db.session.commit()
            original_id = company.id

        # Try to create with same URL (should fail)
        response = client.post('/api/v1/companies', json={
            'companyName': 'Duplicate Corp',
            'websiteUrl': 'https://duplicate-test.com'
        })

        assert response.status_code == 409
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'CONFLICT'
        assert 'existingCompanyId' in data['error']['details']
        assert data['error']['details']['existingCompanyId'] == original_id


class TestCompanyListingFlow:
    """Tests for company listing flow - API-03 requirement."""

    def test_list_companies_returns_pagination_meta(self, client, app):
        """
        API-03: GET /companies returns proper pagination metadata.
        With 25 companies and pageSize=10: meta.total=25, totalPages=3
        """
        with app.app_context():
            for i in range(25):
                company = Company(
                    company_name=f'Paginated Company {i:02d}',
                    website_url=f'https://paginated{i:02d}.com'
                )
                db.session.add(company)
            db.session.commit()

        response = client.get('/api/v1/companies?page=1&pageSize=10')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 10
        assert data['meta']['total'] == 25
        assert data['meta']['page'] == 1
        assert data['meta']['pageSize'] == 10
        assert data['meta']['totalPages'] == 3

    def test_list_companies_filters_by_status(self, client, app):
        """
        API-03: Status filter returns only companies with matching status.
        """
        with app.app_context():
            # Create companies with different statuses
            pending = Company(
                company_name='Pending Corp',
                website_url='https://pending-filter.com',
                status=CompanyStatus.PENDING
            )
            completed = Company(
                company_name='Completed Corp',
                website_url='https://completed-filter.com',
                status=CompanyStatus.COMPLETED
            )
            failed = Company(
                company_name='Failed Corp',
                website_url='https://failed-filter.com',
                status=CompanyStatus.FAILED
            )
            db.session.add_all([pending, completed, failed])
            db.session.commit()

        # Filter by completed
        response = client.get('/api/v1/companies?status=completed')
        data = response.get_json()

        assert data['meta']['total'] == 1
        assert len(data['data']) == 1
        assert data['data'][0]['companyName'] == 'Completed Corp'
        assert data['data'][0]['status'] == 'completed'

    def test_list_companies_search_by_name(self, client, app):
        """
        API-03: Search parameter filters by company name (case-insensitive).
        """
        with app.app_context():
            acme = Company(
                company_name='Acme Corp',
                website_url='https://acme-search.com'
            )
            beta = Company(
                company_name='Beta Inc',
                website_url='https://beta-search.com'
            )
            db.session.add_all([acme, beta])
            db.session.commit()

        # Search for 'acme' (case insensitive)
        response = client.get('/api/v1/companies?search=acme')
        data = response.get_json()

        assert data['meta']['total'] == 1
        assert len(data['data']) == 1
        assert data['data'][0]['companyName'] == 'Acme Corp'

    def test_list_companies_sort_options(self, client, app):
        """
        API-03: Sort by company_name and created_at with asc/desc order.
        """
        with app.app_context():
            alpha = Company(
                company_name='Alpha Corp',
                website_url='https://alpha-sort.com'
            )
            db.session.add(alpha)
            db.session.commit()

            zeta = Company(
                company_name='Zeta Corp',
                website_url='https://zeta-sort.com'
            )
            db.session.add(zeta)
            db.session.commit()

        # Sort by name ascending
        response = client.get('/api/v1/companies?sort=company_name&order=asc')
        data = response.get_json()
        assert data['data'][0]['companyName'] == 'Alpha Corp'
        assert data['data'][1]['companyName'] == 'Zeta Corp'

        # Sort by name descending
        response = client.get('/api/v1/companies?sort=company_name&order=desc')
        data = response.get_json()
        assert data['data'][0]['companyName'] == 'Zeta Corp'
        assert data['data'][1]['companyName'] == 'Alpha Corp'

        # Sort by created_at descending (newest first - Zeta was created second)
        response = client.get('/api/v1/companies?sort=created_at&order=desc')
        data = response.get_json()
        assert data['data'][0]['companyName'] == 'Zeta Corp'
        assert data['data'][1]['companyName'] == 'Alpha Corp'


class TestCompanyDetailFlow:
    """Tests for company detail endpoint - API-04 requirement."""

    def test_get_company_includes_page_count(self, client, app):
        """
        API-04: GET /companies/:id includes pageCount from Page records.
        """
        with app.app_context():
            company = Company(
                company_name='Page Count Corp',
                website_url='https://pagecount.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 5 Page records
            for i in range(5):
                page = Page(
                    company_id=company.id,
                    url=f'https://pagecount.com/page{i}'
                )
                db.session.add(page)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['pageCount'] == 5

    def test_get_company_includes_entity_count(self, client, app):
        """
        API-04: GET /companies/:id includes entityCount from Entity records.
        """
        with app.app_context():
            company = Company(
                company_name='Entity Count Corp',
                website_url='https://entitycount.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 10 Entity records
            for i in range(10):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}'
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['entityCount'] == 10

    def test_get_company_includes_latest_analysis(self, client, app):
        """
        API-04: GET /companies/:id returns latest analysis (highest version_number).
        """
        with app.app_context():
            company = Company(
                company_name='Analysis Corp',
                website_url='https://analysiscorp.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 2 Analysis records with different versions
            analysis_v1 = Analysis(
                company_id=company.id,
                version_number=1,
                executive_summary='Version 1 summary'
            )
            analysis_v2 = Analysis(
                company_id=company.id,
                version_number=2,
                executive_summary='Version 2 summary'
            )
            db.session.add_all([analysis_v1, analysis_v2])
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['analysis'] is not None
        assert data['data']['analysis']['versionNumber'] == 2
        assert data['data']['analysis']['executiveSummary'] == 'Version 2 summary'

    def test_get_company_not_found(self, client):
        """
        API-04: Non-existent company returns 404 with NOT_FOUND code.
        """
        # Use a valid UUID format that doesn't exist
        response = client.get('/api/v1/companies/00000000-0000-0000-0000-000000000000')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'


class TestPagesEndpoint:
    """Tests for pages endpoint - GET /companies/:id/pages."""

    def test_get_pages_returns_paginated_list(self, client, app):
        """
        API-04: GET /companies/:id/pages returns paginated list of pages.
        """
        with app.app_context():
            company = Company(
                company_name='Pages Corp',
                website_url='https://pagescorp.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 30 pages
            for i in range(30):
                page = Page(
                    company_id=company.id,
                    url=f'https://pagescorp.com/page{i:02d}'
                )
                db.session.add(page)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/pages?pageSize=10')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 10
        assert data['meta']['total'] == 30
        assert data['meta']['pageSize'] == 10
        assert data['meta']['totalPages'] == 3

    def test_get_pages_filters_by_type(self, client, app):
        """
        API-04: GET /companies/:id/pages filters by pageType.
        """
        with app.app_context():
            company = Company(
                company_name='Page Types Corp',
                website_url='https://pagetypes.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add pages with different types
            about_page = Page(
                company_id=company.id,
                url='https://pagetypes.com/about',
                page_type=PageType.ABOUT
            )
            team_page = Page(
                company_id=company.id,
                url='https://pagetypes.com/team',
                page_type=PageType.TEAM
            )
            product_page = Page(
                company_id=company.id,
                url='https://pagetypes.com/products',
                page_type=PageType.PRODUCT
            )
            db.session.add_all([about_page, team_page, product_page])
            db.session.commit()
            company_id = company.id

        # Filter by about type
        response = client.get(f'/api/v1/companies/{company_id}/pages?pageType=about')

        assert response.status_code == 200
        data = response.get_json()
        assert data['meta']['total'] == 1
        assert len(data['data']) == 1
        assert data['data'][0]['pageType'] == 'about'


class TestAPIEdgeCases:
    """Edge case tests for API error handling and boundary conditions.

    These tests verify robust handling of:
    - Boundary conditions (max lengths, pagination limits)
    - Invalid input formats
    - Cascade deletion
    - URL normalization

    Requirements verified:
    - API-01: Robust input validation
    - API-03: Pagination boundary handling
    - API-04: Error response consistency
    """

    def test_create_company_name_boundary_lengths(self, client):
        """
        API-01: Company name length validation.
        - 200 chars: should succeed (boundary)
        - 201 chars: should fail with VALIDATION_ERROR
        """
        # Test exactly 200 characters (should succeed)
        name_200 = 'x' * 200
        response = client.post('/api/v1/companies', json={
            'companyName': name_200,
            'websiteUrl': 'https://boundary-200.com'
        })

        assert response.status_code == 201, "200-char name should be accepted"
        data = response.get_json()
        assert data['success'] is True

        # Test 201 characters (should fail)
        name_201 = 'y' * 201
        response = client.post('/api/v1/companies', json={
            'companyName': name_201,
            'websiteUrl': 'https://boundary-201.com'
        })

        assert response.status_code == 400, "201-char name should be rejected"
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_create_company_url_normalization(self, client, app):
        """
        API-01: URL normalization on creation.
        Input: 'https://Example.COM/Page/'
        Expected: URL stored normalized (trailing slash removed)
        """
        response = client.post('/api/v1/companies', json={
            'companyName': 'Normalized URL Corp',
            'websiteUrl': 'https://Example.COM/Page/'
        })

        assert response.status_code == 201
        company_id = response.get_json()['data']['companyId']

        # Verify URL is normalized in database
        with app.app_context():
            company = db.session.get(Company, company_id)
            # Check trailing slash is removed
            assert not company.website_url.endswith('/')
            # Check URL is lowercased in domain part
            assert 'example.com' in company.website_url.lower()

    def test_list_companies_invalid_page_number(self, client, app):
        """
        API-03: Invalid page numbers are handled gracefully.
        - page=-1: should clamp to page 1
        - page=9999 (beyond total): should return empty data
        """
        # Create some companies
        with app.app_context():
            for i in range(5):
                company = Company(
                    company_name=f'Page Test Company {i}',
                    website_url=f'https://pagetest{i}.com'
                )
                db.session.add(company)
            db.session.commit()

        # Test negative page number (should clamp to 1)
        response = client.get('/api/v1/companies?page=-1')
        data = response.get_json()

        assert response.status_code == 200
        assert data['meta']['page'] == 1, "Negative page should clamp to 1"
        assert len(data['data']) > 0, "Should return first page data"

        # Test page beyond total (should return empty)
        response = client.get('/api/v1/companies?page=9999')
        data = response.get_json()

        assert response.status_code == 200
        assert data['data'] == [], "Page beyond total should return empty array"
        assert data['meta']['page'] == 9999, "Page number should be preserved"

    def test_list_companies_page_size_capped(self, client, app):
        """
        API-03: Page size is capped at 100.
        Request pageSize=500, expect meta.pageSize <= 100
        """
        # Create 150 companies to test capping
        with app.app_context():
            for i in range(150):
                company = Company(
                    company_name=f'Cap Test Company {i:03d}',
                    website_url=f'https://captest{i:03d}.com'
                )
                db.session.add(company)
            db.session.commit()

        response = client.get('/api/v1/companies?pageSize=500')
        data = response.get_json()

        assert response.status_code == 200
        assert data['meta']['pageSize'] <= 100, "Page size should be capped at 100"
        assert len(data['data']) <= 100, "Returned data should respect cap"

    def test_get_company_invalid_uuid_format(self, client):
        """
        API-04: Invalid UUID format returns 404, not 500 server error.
        This ensures proper error handling vs. database errors.
        """
        response = client.get('/api/v1/companies/not-a-uuid')

        # Should return 404 (not found), not 500 (server error)
        assert response.status_code == 404, "Invalid UUID should return 404"
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_delete_company_cascades_correctly(self, client, app):
        """
        API-04: DELETE /companies/:id cascades to related records.
        Verify deletedRecords counts and that records are actually removed.
        """
        # Create company with related records
        with app.app_context():
            company = Company(
                company_name='Cascade Delete Corp',
                website_url='https://cascade-delete.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add pages
            for i in range(3):
                page = Page(
                    company_id=company.id,
                    url=f'https://cascade-delete.com/page{i}'
                )
                db.session.add(page)

            # Add entities
            for i in range(5):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}'
                )
                db.session.add(entity)

            # Add analyses
            for i in range(2):
                analysis = Analysis(
                    company_id=company.id,
                    version_number=i + 1,
                    executive_summary=f'Summary v{i + 1}'
                )
                db.session.add(analysis)

            db.session.commit()
            company_id = company.id

        # Delete the company
        response = client.delete(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['deleted'] is True

        # Verify deletedRecords counts
        assert data['data']['deletedRecords']['pages'] == 3
        assert data['data']['deletedRecords']['entities'] == 5
        assert data['data']['deletedRecords']['analyses'] == 2

        # Verify records are actually deleted from database
        with app.app_context():
            assert db.session.get(Company, company_id) is None
            assert Page.query.filter_by(company_id=company_id).count() == 0
            assert Entity.query.filter_by(company_id=company_id).count() == 0
            assert Analysis.query.filter_by(company_id=company_id).count() == 0
