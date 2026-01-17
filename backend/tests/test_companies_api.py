"""Tests for Company CRUD API endpoints."""

import pytest
from app import db
from app.models.company import Company, Page, Entity, Analysis
from app.models.enums import CompanyStatus, AnalysisMode, EntityType, PageType


class TestCreateCompany:
    """Tests for POST /api/v1/companies."""

    def test_create_company_with_valid_data(self, client):
        """Test creating a company with valid data returns 201."""
        response = client.post('/api/v1/companies', json={
            'companyName': 'Acme Corp',
            'websiteUrl': 'https://acme.com',
            'industry': 'Technology'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'companyId' in data['data']
        assert data['data']['status'] == 'pending'

    def test_create_company_minimal_data(self, client):
        """Test creating a company with only required fields."""
        response = client.post('/api/v1/companies', json={
            'companyName': 'Minimal Corp',
            'websiteUrl': 'https://minimal.com'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'companyId' in data['data']

    def test_create_company_with_config(self, client, app):
        """Test creating a company with custom config."""
        response = client.post('/api/v1/companies', json={
            'companyName': 'Configured Corp',
            'websiteUrl': 'https://configured.com',
            'config': {
                'analysisMode': 'quick',
                'timeLimitMinutes': 15,
                'maxPages': 50,
                'maxDepth': 2,
                'followLinkedIn': True,
                'followTwitter': False
            }
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True

        # Verify config was saved
        with app.app_context():
            company = db.session.get(Company, data['data']['companyId'])
            assert company.analysis_mode == AnalysisMode.QUICK
            assert company.config['maxPages'] == 50

    def test_create_company_invalid_url(self, client):
        """Test creating a company with invalid URL returns 400."""
        response = client.post('/api/v1/companies', json={
            'companyName': 'Bad URL Corp',
            'websiteUrl': 'not-a-url'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_create_company_missing_required_fields(self, client):
        """Test creating a company with missing fields returns 400."""
        response = client.post('/api/v1/companies', json={
            'companyName': 'No URL Corp'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_create_company_name_too_long(self, client):
        """Test company name over 200 characters returns 400."""
        response = client.post('/api/v1/companies', json={
            'companyName': 'x' * 201,
            'websiteUrl': 'https://toolong.com'
        })

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_create_company_duplicate_url_returns_409(self, client, app):
        """Test creating company with existing URL returns 409."""
        # Create first company
        with app.app_context():
            company = Company(
                company_name='First Corp',
                website_url='https://duplicate.com'
            )
            db.session.add(company)
            db.session.commit()

        # Try to create duplicate
        response = client.post('/api/v1/companies', json={
            'companyName': 'Second Corp',
            'websiteUrl': 'https://duplicate.com'
        })

        assert response.status_code == 409
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'CONFLICT'


class TestListCompanies:
    """Tests for GET /api/v1/companies."""

    def test_list_companies_empty(self, client):
        """Test listing when no companies exist."""
        response = client.get('/api/v1/companies')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == []
        assert data['meta']['total'] == 0

    def test_list_companies_with_data(self, client, app):
        """Test listing companies returns all companies."""
        with app.app_context():
            for i in range(3):
                company = Company(
                    company_name=f'Company {i}',
                    website_url=f'https://company{i}.com'
                )
                db.session.add(company)
            db.session.commit()

        response = client.get('/api/v1/companies')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 3
        assert data['meta']['total'] == 3

    def test_list_companies_pagination(self, client, app):
        """Test pagination works correctly."""
        with app.app_context():
            for i in range(25):
                company = Company(
                    company_name=f'Company {i}',
                    website_url=f'https://company{i}.com'
                )
                db.session.add(company)
            db.session.commit()

        # First page
        response = client.get('/api/v1/companies?page=1&pageSize=10')
        data = response.get_json()
        assert len(data['data']) == 10
        assert data['meta']['total'] == 25
        assert data['meta']['page'] == 1
        assert data['meta']['pageSize'] == 10
        assert data['meta']['totalPages'] == 3

        # Second page
        response = client.get('/api/v1/companies?page=2&pageSize=10')
        data = response.get_json()
        assert len(data['data']) == 10
        assert data['meta']['page'] == 2

        # Last page
        response = client.get('/api/v1/companies?page=3&pageSize=10')
        data = response.get_json()
        assert len(data['data']) == 5

    def test_list_companies_status_filter(self, client, app):
        """Test filtering by status."""
        with app.app_context():
            company1 = Company(
                company_name='Pending Corp',
                website_url='https://pending.com',
                status=CompanyStatus.PENDING
            )
            company2 = Company(
                company_name='Completed Corp',
                website_url='https://completed.com',
                status=CompanyStatus.COMPLETED
            )
            db.session.add_all([company1, company2])
            db.session.commit()

        response = client.get('/api/v1/companies?status=completed')
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['status'] == 'completed'

    def test_list_companies_search(self, client, app):
        """Test search by company name."""
        with app.app_context():
            company1 = Company(
                company_name='Alpha Corp',
                website_url='https://alpha.com'
            )
            company2 = Company(
                company_name='Beta Inc',
                website_url='https://beta.com'
            )
            db.session.add_all([company1, company2])
            db.session.commit()

        response = client.get('/api/v1/companies?search=alpha')
        data = response.get_json()
        assert len(data['data']) == 1
        assert data['data'][0]['companyName'] == 'Alpha Corp'

    def test_list_companies_sort_order(self, client, app):
        """Test sorting by different fields and orders."""
        with app.app_context():
            company1 = Company(
                company_name='A Corp',
                website_url='https://acorp.com'
            )
            company2 = Company(
                company_name='Z Corp',
                website_url='https://zcorp.com'
            )
            db.session.add_all([company1, company2])
            db.session.commit()

        # Sort by name ascending
        response = client.get('/api/v1/companies?sort=company_name&order=asc')
        data = response.get_json()
        assert data['data'][0]['companyName'] == 'A Corp'
        assert data['data'][1]['companyName'] == 'Z Corp'

        # Sort by name descending
        response = client.get('/api/v1/companies?sort=company_name&order=desc')
        data = response.get_json()
        assert data['data'][0]['companyName'] == 'Z Corp'
        assert data['data'][1]['companyName'] == 'A Corp'

    def test_list_companies_page_size_limit(self, client, app):
        """Test page size is capped at 100."""
        with app.app_context():
            for i in range(150):
                company = Company(
                    company_name=f'Company {i}',
                    website_url=f'https://company{i}.com'
                )
                db.session.add(company)
            db.session.commit()

        response = client.get('/api/v1/companies?pageSize=200')
        data = response.get_json()
        assert len(data['data']) == 100
        assert data['meta']['pageSize'] == 100


class TestGetCompany:
    """Tests for GET /api/v1/companies/:id."""

    def test_get_company_exists(self, client, app):
        """Test getting an existing company."""
        with app.app_context():
            company = Company(
                company_name='Test Corp',
                website_url='https://test.com',
                industry='Technology'
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['company']['companyName'] == 'Test Corp'
        assert data['data']['company']['industry'] == 'Technology'
        assert data['data']['entityCount'] == 0
        assert data['data']['pageCount'] == 0

    def test_get_company_not_found(self, client):
        """Test getting a non-existent company returns 404."""
        response = client.get('/api/v1/companies/nonexistent-id')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_get_company_with_analysis(self, client, app):
        """Test getting company includes latest analysis."""
        with app.app_context():
            company = Company(
                company_name='Analyzed Corp',
                website_url='https://analyzed.com'
            )
            db.session.add(company)
            db.session.flush()

            analysis = Analysis(
                company_id=company.id,
                version_number=1,
                executive_summary='Test summary'
            )
            db.session.add(analysis)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}')

        data = response.get_json()
        assert data['data']['analysis'] is not None
        assert data['data']['analysis']['executiveSummary'] == 'Test summary'
        assert data['data']['analysis']['versionNumber'] == 1

    def test_get_company_with_entities_and_pages(self, client, app):
        """Test getting company includes entity and page counts."""
        with app.app_context():
            company = Company(
                company_name='Rich Corp',
                website_url='https://rich.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add pages
            for i in range(5):
                page = Page(
                    company_id=company.id,
                    url=f'https://rich.com/page{i}'
                )
                db.session.add(page)

            # Add entities
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

        data = response.get_json()
        assert data['data']['pageCount'] == 5
        assert data['data']['entityCount'] == 10


class TestDeleteCompany:
    """Tests for DELETE /api/v1/companies/:id."""

    def test_delete_company_exists(self, client, app):
        """Test deleting an existing company."""
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

    def test_delete_company_not_found(self, client):
        """Test deleting a non-existent company returns 404."""
        response = client.delete('/api/v1/companies/nonexistent-id')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_delete_company_cascades_related_records(self, client, app):
        """Test deleting company removes all related records."""
        with app.app_context():
            company = Company(
                company_name='Cascade Corp',
                website_url='https://cascade.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add related records
            page = Page(
                company_id=company.id,
                url='https://cascade.com/about'
            )
            entity = Entity(
                company_id=company.id,
                entity_type=EntityType.ORGANIZATION,
                entity_value='Cascade Corp'
            )
            analysis = Analysis(
                company_id=company.id,
                version_number=1
            )
            db.session.add_all([page, entity, analysis])
            db.session.commit()
            company_id = company.id

        response = client.delete(f'/api/v1/companies/{company_id}')

        data = response.get_json()
        assert data['data']['deletedRecords']['pages'] == 1
        assert data['data']['deletedRecords']['entities'] == 1
        assert data['data']['deletedRecords']['analyses'] == 1

        # Verify all related records are deleted
        with app.app_context():
            assert Page.query.filter_by(company_id=company_id).count() == 0
            assert Entity.query.filter_by(company_id=company_id).count() == 0
            assert Analysis.query.filter_by(company_id=company_id).count() == 0
