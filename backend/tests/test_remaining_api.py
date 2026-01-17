"""Tests for remaining Phase 2 API endpoints (progress, entities, pages, tokens, config, versions)."""

import pytest
from datetime import datetime, timezone, timedelta
from app import db
from app.models.company import Company, CrawlSession, Entity, Page, Analysis, TokenUsage
from app.models.enums import (
    CompanyStatus, CrawlStatus, ProcessingPhase,
    EntityType, PageType, ApiCallType
)


class TestProgressEndpoint:
    """Tests for GET /api/v1/companies/:id/progress."""

    def test_get_progress_basic(self, client, app):
        """Test getting basic progress information."""
        with app.app_context():
            company = Company(
                company_name='Progress Corp',
                website_url='https://progress.com',
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                total_tokens_used=5000
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['companyId'] == company_id
        assert data['data']['status'] == 'in_progress'
        assert data['data']['phase'] == 'crawling'
        assert data['data']['tokensUsed'] == 5000

    def test_get_progress_with_crawl_session(self, client, app):
        """Test progress includes crawl session stats."""
        with app.app_context():
            company = Company(
                company_name='Crawling Corp',
                website_url='https://crawling.com',
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.flush()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.ACTIVE,
                pages_crawled=30,
                pages_queued=70
            )
            db.session.add(session)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        data = response.get_json()
        assert data['data']['pagesCrawled'] == 30
        assert data['data']['pagesTotal'] == 100

    def test_get_progress_with_entities(self, client, app):
        """Test progress includes entity count."""
        with app.app_context():
            company = Company(
                company_name='Entity Corp',
                website_url='https://entity.com',
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.flush()

            for i in range(15):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}'
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        data = response.get_json()
        assert data['data']['entitiesExtracted'] == 15

    def test_get_progress_not_found(self, client):
        """Test progress for non-existent company returns 404."""
        response = client.get('/api/v1/companies/nonexistent/progress')

        assert response.status_code == 404


class TestEntitiesEndpoint:
    """Tests for GET /api/v1/companies/:id/entities."""

    def test_list_entities_basic(self, client, app):
        """Test listing entities for a company."""
        with app.app_context():
            company = Company(
                company_name='Entity Corp',
                website_url='https://entity.com'
            )
            db.session.add(company)
            db.session.flush()

            for i in range(5):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}',
                    confidence_score=0.9 - (i * 0.1)
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 5
        assert data['meta']['total'] == 5
        # Should be ordered by confidence descending
        assert data['data'][0]['confidenceScore'] >= data['data'][1]['confidenceScore']

    def test_list_entities_filter_by_type(self, client, app):
        """Test filtering entities by type."""
        with app.app_context():
            company = Company(
                company_name='Mixed Corp',
                website_url='https://mixed.com'
            )
            db.session.add(company)
            db.session.flush()

            db.session.add(Entity(company_id=company.id, entity_type=EntityType.PERSON, entity_value='John'))
            db.session.add(Entity(company_id=company.id, entity_type=EntityType.ORGANIZATION, entity_value='Acme'))
            for i in range(3):
                db.session.add(Entity(company_id=company.id, entity_type=EntityType.PERSON, entity_value=f'P{i}'))
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities?type=person')

        data = response.get_json()
        assert data['meta']['total'] == 4  # Only PERSON entities

    def test_list_entities_filter_by_confidence(self, client, app):
        """Test filtering entities by minimum confidence."""
        with app.app_context():
            company = Company(
                company_name='Confidence Corp',
                website_url='https://confidence.com'
            )
            db.session.add(company)
            db.session.flush()

            db.session.add(Entity(company_id=company.id, entity_type=EntityType.PERSON, entity_value='High', confidence_score=0.9))
            db.session.add(Entity(company_id=company.id, entity_type=EntityType.PERSON, entity_value='Medium', confidence_score=0.6))
            db.session.add(Entity(company_id=company.id, entity_type=EntityType.PERSON, entity_value='Low', confidence_score=0.3))
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities?minConfidence=0.5')

        data = response.get_json()
        assert data['meta']['total'] == 2  # Only high and medium

    def test_list_entities_pagination(self, client, app):
        """Test entity pagination."""
        with app.app_context():
            company = Company(
                company_name='Paginated Corp',
                website_url='https://paginated.com'
            )
            db.session.add(company)
            db.session.flush()

            for i in range(25):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}'
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities?page=1&pageSize=10')

        data = response.get_json()
        assert len(data['data']) == 10
        assert data['meta']['total'] == 25
        assert data['meta']['totalPages'] == 3


class TestPagesEndpoint:
    """Tests for GET /api/v1/companies/:id/pages."""

    def test_list_pages_basic(self, client, app):
        """Test listing pages for a company."""
        with app.app_context():
            company = Company(
                company_name='Pages Corp',
                website_url='https://pages.com'
            )
            db.session.add(company)
            db.session.flush()

            for i in range(3):
                page = Page(
                    company_id=company.id,
                    url=f'https://pages.com/page{i}',
                    page_type=PageType.OTHER
                )
                db.session.add(page)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/pages')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 3
        assert data['meta']['total'] == 3

    def test_list_pages_filter_by_type(self, client, app):
        """Test filtering pages by type."""
        with app.app_context():
            company = Company(
                company_name='Types Corp',
                website_url='https://types.com'
            )
            db.session.add(company)
            db.session.flush()

            db.session.add(Page(company_id=company.id, url='https://types.com/about', page_type=PageType.ABOUT))
            db.session.add(Page(company_id=company.id, url='https://types.com/team', page_type=PageType.TEAM))
            db.session.add(Page(company_id=company.id, url='https://types.com/about2', page_type=PageType.ABOUT))
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/pages?pageType=about')

        data = response.get_json()
        assert data['meta']['total'] == 2


class TestTokensEndpoint:
    """Tests for GET /api/v1/companies/:id/tokens."""

    def test_get_token_usage(self, client, app):
        """Test getting token usage breakdown."""
        with app.app_context():
            company = Company(
                company_name='Tokens Corp',
                website_url='https://tokens.com',
                estimated_cost=1.50
            )
            db.session.add(company)
            db.session.flush()

            db.session.add(TokenUsage(
                company_id=company.id,
                api_call_type=ApiCallType.EXTRACTION,
                input_tokens=5000,
                output_tokens=1000
            ))
            db.session.add(TokenUsage(
                company_id=company.id,
                api_call_type=ApiCallType.ANALYSIS,
                input_tokens=3000,
                output_tokens=2000
            ))
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['totalTokens'] == 11000
        assert data['data']['totalInputTokens'] == 8000
        assert data['data']['totalOutputTokens'] == 3000
        assert data['data']['estimatedCost'] == 1.50
        assert len(data['data']['byApiCall']) == 2

    def test_get_token_usage_empty(self, client, app):
        """Test token usage when no usage records exist."""
        with app.app_context():
            company = Company(
                company_name='Empty Corp',
                website_url='https://empty.com'
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        data = response.get_json()
        assert data['data']['totalTokens'] == 0
        assert len(data['data']['byApiCall']) == 0


class TestConfigEndpoint:
    """Tests for GET /api/v1/config."""

    def test_get_config(self, client):
        """Test getting application configuration."""
        response = client.get('/api/v1/config')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'defaults' in data['data']
        assert 'quickMode' in data['data']
        assert 'thoroughMode' in data['data']

    def test_config_defaults(self, client):
        """Test default configuration values."""
        response = client.get('/api/v1/config')

        data = response.get_json()
        defaults = data['data']['defaults']
        assert defaults['analysisMode'] == 'thorough'
        assert defaults['timeLimitMinutes'] == 30
        assert defaults['maxPages'] == 100
        assert defaults['maxDepth'] == 3

    def test_config_mode_settings(self, client):
        """Test mode-specific configuration."""
        response = client.get('/api/v1/config')

        data = response.get_json()
        quick = data['data']['quickMode']
        thorough = data['data']['thoroughMode']

        assert quick['maxPages'] < thorough['maxPages']
        assert quick['maxDepth'] < thorough['maxDepth']


class TestVersionsEndpoint:
    """Tests for version history and comparison endpoints."""

    def test_list_versions(self, client, app):
        """Test listing analysis versions."""
        with app.app_context():
            company = Company(
                company_name='Versions Corp',
                website_url='https://versions.com',
                status=CompanyStatus.COMPLETED
            )
            db.session.add(company)
            db.session.flush()

            for i in range(1, 4):
                analysis = Analysis(
                    company_id=company.id,
                    version_number=i,
                    executive_summary=f'Summary version {i}'
                )
                db.session.add(analysis)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/versions')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 3
        # Should be ordered by version number descending
        assert data['data'][0]['versionNumber'] == 3
        assert data['data'][2]['versionNumber'] == 1

    def test_compare_versions(self, client, app):
        """Test comparing two analysis versions."""
        with app.app_context():
            company = Company(
                company_name='Compare Corp',
                website_url='https://compare.com',
                status=CompanyStatus.COMPLETED
            )
            db.session.add(company)
            db.session.flush()

            analysis1 = Analysis(
                company_id=company.id,
                version_number=1,
                executive_summary='Original summary',
                full_analysis={'team': {'CEO': 'John'}, 'products': ['Product A']}
            )
            analysis2 = Analysis(
                company_id=company.id,
                version_number=2,
                executive_summary='Updated summary',
                full_analysis={'team': {'CEO': 'Jane', 'CTO': 'Bob'}, 'products': ['Product A', 'Product B']}
            )
            db.session.add_all([analysis1, analysis2])
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/compare?version1=1&version2=2')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['previousVersion'] == 1
        assert data['data']['currentVersion'] == 2
        assert data['data']['significantChanges'] is True

    def test_compare_versions_missing_params(self, client, app):
        """Test compare without required parameters returns 400."""
        with app.app_context():
            company = Company(
                company_name='Missing Corp',
                website_url='https://missing.com'
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/compare?version1=1')

        assert response.status_code == 400

    def test_compare_versions_not_found(self, client, app):
        """Test compare with non-existent version returns 404."""
        with app.app_context():
            company = Company(
                company_name='Not Found Corp',
                website_url='https://notfound.com'
            )
            db.session.add(company)
            db.session.flush()

            analysis = Analysis(company_id=company.id, version_number=1)
            db.session.add(analysis)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/compare?version1=1&version2=99')

        assert response.status_code == 404
