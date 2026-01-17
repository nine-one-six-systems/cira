"""Tests for SQLAlchemy models."""

import pytest
from app import db
from app.models import (
    Company,
    CrawlSession,
    Page,
    Entity,
    Analysis,
    TokenUsage,
    CompanyStatus,
    CrawlStatus,
    AnalysisMode,
    PageType,
    EntityType,
    ApiCallType,
)


class TestCompanyModel:
    """Tests for Company model."""

    def test_create_company(self, app):
        """Test creating a company."""
        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://example.com',
                industry='Technology'
            )
            db.session.add(company)
            db.session.commit()

            assert company.id is not None
            assert company.company_name == 'Test Company'
            assert company.website_url == 'https://example.com'
            assert company.status == CompanyStatus.PENDING
            assert company.analysis_mode == AnalysisMode.THOROUGH

    def test_company_default_values(self, app):
        """Test company default values."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            assert company.status == CompanyStatus.PENDING
            assert company.total_tokens_used == 0
            assert company.estimated_cost == 0.0
            assert company.created_at is not None

    def test_company_to_dict(self, app):
        """Test company to_dict method."""
        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://example.com',
                industry='Technology'
            )
            db.session.add(company)
            db.session.commit()

            data = company.to_dict()
            assert data['companyName'] == 'Test Company'
            assert data['websiteUrl'] == 'https://example.com'
            assert data['industry'] == 'Technology'
            assert data['status'] == 'pending'

    def test_company_relationships(self, app):
        """Test company relationships work correctly."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            # Add related records
            page = Page(
                company_id=company.id,
                url='https://test.com/about'
            )
            entity = Entity(
                company_id=company.id,
                entity_type=EntityType.PERSON,
                entity_value='John Doe'
            )
            db.session.add_all([page, entity])
            db.session.commit()

            assert len(company.pages) == 1
            assert len(company.entities) == 1


class TestCrawlSessionModel:
    """Tests for CrawlSession model."""

    def test_create_crawl_session(self, app):
        """Test creating a crawl session."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                pages_crawled=10,
                pages_queued=5
            )
            db.session.add(session)
            db.session.commit()

            assert session.id is not None
            assert session.status == CrawlStatus.ACTIVE
            assert session.pages_crawled == 10

    def test_crawl_session_checkpoint_data(self, app):
        """Test crawl session with checkpoint data."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            checkpoint = {
                'pagesVisited': ['https://test.com'],
                'pagesQueued': ['https://test.com/about'],
                'currentDepth': 1
            }
            session = CrawlSession(
                company_id=company.id,
                checkpoint_data=checkpoint
            )
            db.session.add(session)
            db.session.commit()

            # Retrieve and verify
            retrieved = db.session.get(CrawlSession, session.id)
            assert retrieved.checkpoint_data['currentDepth'] == 1


class TestPageModel:
    """Tests for Page model."""

    def test_create_page(self, app):
        """Test creating a page."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            page = Page(
                company_id=company.id,
                url='https://test.com/about',
                page_type=PageType.ABOUT,
                extracted_text='About us page content'
            )
            db.session.add(page)
            db.session.commit()

            assert page.id is not None
            assert page.page_type == PageType.ABOUT
            assert page.is_external is False


class TestEntityModel:
    """Tests for Entity model."""

    def test_create_entity(self, app):
        """Test creating an entity."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            entity = Entity(
                company_id=company.id,
                entity_type=EntityType.PERSON,
                entity_value='John Smith',
                context_snippet='John Smith, CEO and founder...',
                confidence_score=0.95
            )
            db.session.add(entity)
            db.session.commit()

            assert entity.id is not None
            assert entity.entity_type == EntityType.PERSON
            assert entity.confidence_score == 0.95

    def test_entity_types(self, app):
        """Test all entity types are valid."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            for entity_type in EntityType:
                entity = Entity(
                    company_id=company.id,
                    entity_type=entity_type,
                    entity_value='Test Value'
                )
                db.session.add(entity)

            db.session.commit()
            assert len(company.entities) == len(EntityType)


class TestAnalysisModel:
    """Tests for Analysis model."""

    def test_create_analysis(self, app):
        """Test creating an analysis."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            full_analysis = {
                'companyOverview': {
                    'content': 'Overview content',
                    'sources': ['https://test.com/about'],
                    'confidence': 0.9
                }
            }
            analysis = Analysis(
                company_id=company.id,
                version_number=1,
                executive_summary='Test company is a technology company...',
                full_analysis=full_analysis
            )
            db.session.add(analysis)
            db.session.commit()

            assert analysis.id is not None
            assert analysis.version_number == 1
            assert analysis.full_analysis['companyOverview']['confidence'] == 0.9


class TestTokenUsageModel:
    """Tests for TokenUsage model."""

    def test_create_token_usage(self, app):
        """Test creating token usage record."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            usage = TokenUsage(
                company_id=company.id,
                api_call_type=ApiCallType.ANALYSIS,
                section='executive_summary',
                input_tokens=1000,
                output_tokens=500
            )
            db.session.add(usage)
            db.session.commit()

            assert usage.id is not None
            assert usage.input_tokens == 1000
            assert usage.output_tokens == 500


class TestCascadeDeletes:
    """Tests for cascade delete behavior."""

    def test_delete_company_cascades(self, app):
        """Test that deleting a company cascades to related records."""
        with app.app_context():
            company = Company(
                company_name='Test',
                website_url='https://test.com'
            )
            db.session.add(company)
            db.session.commit()

            # Add related records
            page = Page(company_id=company.id, url='https://test.com')
            entity = Entity(
                company_id=company.id,
                entity_type=EntityType.PERSON,
                entity_value='John'
            )
            analysis = Analysis(company_id=company.id, version_number=1)
            token_usage = TokenUsage(
                company_id=company.id,
                api_call_type=ApiCallType.ANALYSIS,
                input_tokens=100,
                output_tokens=50
            )
            db.session.add_all([page, entity, analysis, token_usage])
            db.session.commit()

            company_id = company.id

            # Delete company
            db.session.delete(company)
            db.session.commit()

            # Verify cascade
            assert db.session.get(Company, company_id) is None
            assert Page.query.filter_by(company_id=company_id).count() == 0
            assert Entity.query.filter_by(company_id=company_id).count() == 0
            assert Analysis.query.filter_by(company_id=company_id).count() == 0
            assert TokenUsage.query.filter_by(company_id=company_id).count() == 0
