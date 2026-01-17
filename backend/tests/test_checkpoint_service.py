"""Tests for Checkpoint Persistence Service."""

import pytest
from datetime import datetime, timezone


class TestCheckpointServiceSave:
    """Tests for checkpoint save operations."""

    def test_save_checkpoint_success(self, app):
        """Test saving a checkpoint."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS,
                started_at=datetime.now(timezone.utc)
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            result = service.save_checkpoint(
                company_id,
                pages_visited=['https://example.com', 'https://example.com/about'],
                pages_queued=['https://example.com/contact'],
                external_links=['https://linkedin.com/company/test'],
                current_depth=2,
                entities_count=15,
                sections_completed=['overview', 'team']
            )

            assert result is True

            # Verify checkpoint was saved
            session = CrawlSession.query.filter_by(company_id=company_id).first()
            assert session is not None
            assert session.checkpoint_data is not None
            assert session.pages_crawled == 2
            assert session.pages_queued == 1
            assert session.crawl_depth_reached == 2
            assert session.external_links_followed == 1

            checkpoint = session.checkpoint_data
            assert checkpoint['version'] == 1
            assert len(checkpoint['pagesVisited']) == 2
            assert checkpoint['entitiesExtractedCount'] == 15
            assert len(checkpoint['analysisSectionsCompleted']) == 2

    def test_save_checkpoint_company_not_found(self, app):
        """Test saving checkpoint for non-existent company."""
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            service = CheckpointService()
            result = service.save_checkpoint("nonexistent-id", pages_visited=[])

            assert result is False

    def test_save_checkpoint_creates_session_if_needed(self, app):
        """Test that save_checkpoint creates CrawlSession if none exists."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            # Verify no session exists
            assert CrawlSession.query.filter_by(company_id=company_id).count() == 0

            service = CheckpointService()
            result = service.save_checkpoint(company_id, pages_visited=['https://example.com'])

            assert result is True
            assert CrawlSession.query.filter_by(company_id=company_id).count() == 1

    def test_update_checkpoint_field(self, app):
        """Test updating a single checkpoint field."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.ACTIVE,
                checkpoint_data={'pagesVisited': [], 'entitiesExtractedCount': 0}
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            result = service.update_checkpoint_field(
                company_id, 'entitiesExtractedCount', 25
            )

            assert result is True

            # Expire cache to get fresh data from DB
            db.session.expire_all()
            session = CrawlSession.query.filter_by(company_id=company_id).first()
            assert session.checkpoint_data['entitiesExtractedCount'] == 25

    def test_add_visited_url(self, app):
        """Test adding a visited URL to checkpoint."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.ACTIVE,
                checkpoint_data={'pagesVisited': ['https://example.com']}
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            result = service.add_visited_url(company_id, 'https://example.com/about')

            assert result is True

            # Expire cache to get fresh data from DB
            db.session.expire_all()
            session = CrawlSession.query.filter_by(company_id=company_id).first()
            assert 'https://example.com/about' in session.checkpoint_data['pagesVisited']
            assert session.pages_crawled == 2

    def test_add_visited_url_no_duplicates(self, app):
        """Test that adding duplicate URL doesn't create duplicate."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.ACTIVE,
                checkpoint_data={'pagesVisited': ['https://example.com']}
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            # Add same URL
            service.add_visited_url(company_id, 'https://example.com')

            session = CrawlSession.query.filter_by(company_id=company_id).first()
            assert len(session.checkpoint_data['pagesVisited']) == 1


class TestCheckpointServiceLoad:
    """Tests for checkpoint load operations."""

    def test_load_checkpoint_success(self, app):
        """Test loading a checkpoint."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'version': 1,
                    'pagesVisited': ['https://a.com', 'https://b.com'],
                    'entitiesExtractedCount': 10
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            checkpoint = service.load_checkpoint(company_id)

            assert checkpoint is not None
            assert len(checkpoint['pagesVisited']) == 2
            assert checkpoint['entitiesExtractedCount'] == 10

    def test_load_checkpoint_not_found(self, app):
        """Test loading checkpoint when none exists."""
        from app import db
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PENDING
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            checkpoint = service.load_checkpoint(company_id)

            assert checkpoint is None

    def test_load_checkpoint_validates_data(self, app):
        """Test that load validates and repairs checkpoint data."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            # Save corrupted checkpoint data
            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': 'not-a-list',  # Invalid type
                    'currentDepth': 'five',  # Invalid type
                    # Missing required fields
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            checkpoint = service.load_checkpoint(company_id)

            # Should have defaults for invalid/missing fields
            assert checkpoint is not None
            assert checkpoint['pagesVisited'] == []  # Replaced invalid
            assert checkpoint['currentDepth'] == 0  # Replaced invalid
            assert 'entitiesExtractedCount' in checkpoint  # Added missing

    def test_get_visited_urls(self, app):
        """Test getting visited URLs set."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': ['https://a.com', 'https://b.com', 'https://c.com']
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            visited = service.get_visited_urls(company_id)

            assert isinstance(visited, set)
            assert len(visited) == 3
            assert 'https://a.com' in visited
            assert 'https://b.com' in visited

    def test_get_queued_urls(self, app):
        """Test getting queued URLs."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesQueued': ['https://a.com/page1', 'https://a.com/page2']
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            queued = service.get_queued_urls(company_id)

            assert isinstance(queued, list)
            assert len(queued) == 2

    def test_get_sections_completed(self, app):
        """Test getting completed sections."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'analysisSectionsCompleted': ['overview', 'team', 'products']
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            sections = service.get_sections_completed(company_id)

            assert len(sections) == 3
            assert 'overview' in sections


class TestCheckpointServiceClear:
    """Tests for checkpoint clear operations."""

    def test_clear_checkpoint_success(self, app):
        """Test clearing a checkpoint."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.COMPLETED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.COMPLETED,
                checkpoint_data={'pagesVisited': ['https://example.com']}
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            result = service.clear_checkpoint(company_id)

            assert result is True

            session = CrawlSession.query.filter_by(company_id=company_id).first()
            assert session.checkpoint_data is None


class TestCheckpointServiceRecovery:
    """Tests for checkpoint recovery operations."""

    def test_can_resume_with_visited_pages(self, app):
        """Test can_resume returns True when pages visited."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={'pagesVisited': ['https://example.com']}
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            assert service.can_resume(company_id) is True

    def test_can_resume_with_entities(self, app):
        """Test can_resume returns True when entities extracted."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': [],
                    'entitiesExtractedCount': 10
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            assert service.can_resume(company_id) is True

    def test_can_resume_empty_checkpoint(self, app):
        """Test can_resume returns False for empty checkpoint."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': [],
                    'pagesQueued': [],
                    'entitiesExtractedCount': 0,
                    'analysisSectionsCompleted': []
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            assert service.can_resume(company_id) is False

    def test_get_resume_phase_extracting(self, app):
        """Test get_resume_phase returns extracting when pages visited."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': ['https://example.com'],
                    'entitiesExtractedCount': 0,
                    'analysisSectionsCompleted': []
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            phase = service.get_resume_phase(company_id)

            assert phase == 'extracting'

    def test_get_resume_phase_analyzing(self, app):
        """Test get_resume_phase returns analyzing when entities extracted."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': ['https://example.com'],
                    'entitiesExtractedCount': 10,
                    'analysisSectionsCompleted': []
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            phase = service.get_resume_phase(company_id)

            assert phase == 'analyzing'

    def test_get_resume_phase_crawling(self, app):
        """Test get_resume_phase returns crawling when only queued pages."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': [],
                    'pagesQueued': ['https://example.com/about'],
                    'entitiesExtractedCount': 0,
                    'analysisSectionsCompleted': []
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            phase = service.get_resume_phase(company_id)

            assert phase == 'crawling'

    def test_get_checkpoint_stats(self, app):
        """Test getting checkpoint statistics."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus, CrawlStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.PAUSED
            )
            db.session.add(company)
            db.session.commit()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                checkpoint_data={
                    'pagesVisited': ['https://a.com', 'https://b.com'],
                    'pagesQueued': ['https://c.com'],
                    'externalLinksFound': ['https://ext.com'],
                    'currentDepth': 2,
                    'entitiesExtractedCount': 15,
                    'analysisSectionsCompleted': ['overview', 'team'],
                    'lastCheckpointTime': '2024-01-15T10:30:00+00:00'
                }
            )
            db.session.add(session)
            db.session.commit()
            company_id = str(company.id)

            service = CheckpointService()
            stats = service.get_checkpoint_stats(company_id)

            assert stats is not None
            assert stats['pagesVisited'] == 2
            assert stats['pagesQueued'] == 1
            assert stats['externalLinksFound'] == 1
            assert stats['currentDepth'] == 2
            assert stats['entitiesExtracted'] == 15
            assert stats['sectionsCompleted'] == 2


class TestCheckpointServicePersistence:
    """Tests for checkpoint persistence across operations."""

    def test_checkpoint_survives_reload(self, app):
        """Test that checkpoint data survives session reload."""
        from app import db
        from app.models import Company, CrawlSession
        from app.models.enums import CompanyStatus
        from app.services.checkpoint_service import CheckpointService

        with app.app_context():
            company = Company(
                company_name="Test Company",
                website_url="https://example.com",
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()
            company_id = str(company.id)

            # Save checkpoint
            service = CheckpointService()
            service.save_checkpoint(
                company_id,
                pages_visited=['https://example.com', 'https://example.com/about'],
                entities_count=10
            )

            # Clear SQLAlchemy session cache
            db.session.expire_all()

            # Reload and verify
            checkpoint = service.load_checkpoint(company_id)
            assert checkpoint is not None
            assert len(checkpoint['pagesVisited']) == 2
            assert checkpoint['entitiesExtractedCount'] == 10


class TestGlobalCheckpointService:
    """Tests for global checkpoint_service instance."""

    def test_global_service_exists(self, app):
        """Test that global service instance exists."""
        from app.services.checkpoint_service import checkpoint_service, CheckpointService

        with app.app_context():
            assert checkpoint_service is not None
            assert isinstance(checkpoint_service, CheckpointService)
