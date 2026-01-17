"""Tests for Company Control API endpoints (pause, resume, rescan)."""

import pytest
from app import db
from app.models.company import Company, CrawlSession, Analysis
from app.models.enums import CompanyStatus, CrawlStatus, ProcessingPhase


class TestPauseCompany:
    """Tests for POST /api/v1/companies/:id/pause."""

    def test_pause_in_progress_company(self, client, app):
        """Test pausing an in-progress company succeeds."""
        with app.app_context():
            company = Company(
                company_name='In Progress Corp',
                website_url='https://inprogress.com',
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/pause')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['status'] == 'paused'
        assert 'pausedAt' in data['data']

        # Verify company status changed
        with app.app_context():
            company = db.session.get(Company, company_id)
            assert company.status == CompanyStatus.PAUSED
            assert company.paused_at is not None

    def test_pause_with_active_crawl_session(self, client, app):
        """Test pausing saves checkpoint from active crawl session."""
        with app.app_context():
            company = Company(
                company_name='Active Crawl Corp',
                website_url='https://activecrawl.com',
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.flush()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.ACTIVE,
                pages_crawled=25,
                pages_queued=50
            )
            db.session.add(session)
            db.session.commit()
            company_id = company.id
            session_id = session.id

        response = client.post(f'/api/v1/companies/{company_id}/pause')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['checkpointSaved'] is True

        # Verify session status and checkpoint
        with app.app_context():
            session = db.session.get(CrawlSession, session_id)
            assert session.status == CrawlStatus.PAUSED
            assert session.checkpoint_data is not None
            assert session.checkpoint_data['pagesCrawled'] == 25

    def test_pause_pending_company_fails(self, client, app):
        """Test pausing a pending company returns 422."""
        with app.app_context():
            company = Company(
                company_name='Pending Corp',
                website_url='https://pending.com',
                status=CompanyStatus.PENDING
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/pause')

        assert response.status_code == 422
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_STATE'

    def test_pause_completed_company_fails(self, client, app):
        """Test pausing a completed company returns 422."""
        with app.app_context():
            company = Company(
                company_name='Completed Corp',
                website_url='https://completed.com',
                status=CompanyStatus.COMPLETED
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/pause')

        assert response.status_code == 422
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_STATE'

    def test_pause_nonexistent_company(self, client):
        """Test pausing a non-existent company returns 404."""
        response = client.post('/api/v1/companies/nonexistent/pause')

        assert response.status_code == 404
        data = response.get_json()
        assert data['error']['code'] == 'NOT_FOUND'


class TestResumeCompany:
    """Tests for POST /api/v1/companies/:id/resume."""

    def test_resume_paused_company(self, client, app):
        """Test resuming a paused company succeeds."""
        with app.app_context():
            company = Company(
                company_name='Paused Corp',
                website_url='https://paused.com',
                status=CompanyStatus.PAUSED,
                processing_phase=ProcessingPhase.CRAWLING
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['status'] == 'in_progress'
        assert 'resumedFrom' in data['data']

        # Verify company status changed
        with app.app_context():
            company = db.session.get(Company, company_id)
            assert company.status == CompanyStatus.IN_PROGRESS
            assert company.paused_at is None

    def test_resume_with_checkpoint(self, client, app):
        """Test resuming returns checkpoint data."""
        with app.app_context():
            company = Company(
                company_name='Checkpoint Corp',
                website_url='https://checkpoint.com',
                status=CompanyStatus.PAUSED,
                processing_phase=ProcessingPhase.EXTRACTING
            )
            db.session.add(company)
            db.session.flush()

            session = CrawlSession(
                company_id=company.id,
                status=CrawlStatus.PAUSED,
                pages_crawled=42,
                checkpoint_data={'pagesCrawled': 42}
            )
            db.session.add(session)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        data = response.get_json()
        assert data['data']['resumedFrom']['pagesCrawled'] == 42
        assert data['data']['resumedFrom']['phase'] == 'extracting'

    def test_resume_pending_company_fails(self, client, app):
        """Test resuming a pending company returns 422."""
        with app.app_context():
            company = Company(
                company_name='Pending Corp',
                website_url='https://pending.com',
                status=CompanyStatus.PENDING
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        assert response.status_code == 422
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_STATE'

    def test_resume_in_progress_company_fails(self, client, app):
        """Test resuming an in-progress company returns 422."""
        with app.app_context():
            company = Company(
                company_name='In Progress Corp',
                website_url='https://inprogress.com',
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        assert response.status_code == 422
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_STATE'

    def test_resume_nonexistent_company(self, client):
        """Test resuming a non-existent company returns 404."""
        response = client.post('/api/v1/companies/nonexistent/resume')

        assert response.status_code == 404


class TestRescanCompany:
    """Tests for POST /api/v1/companies/:id/rescan."""

    def test_rescan_completed_company(self, client, app):
        """Test rescanning a completed company creates new version."""
        with app.app_context():
            company = Company(
                company_name='Completed Corp',
                website_url='https://completed.com',
                status=CompanyStatus.COMPLETED
            )
            db.session.add(company)
            db.session.flush()

            analysis = Analysis(
                company_id=company.id,
                version_number=1,
                executive_summary='Original analysis'
            )
            db.session.add(analysis)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/rescan')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['versionNumber'] == 2
        assert data['data']['status'] == 'pending'
        assert 'newAnalysisId' in data['data']

        # Verify company status reset
        with app.app_context():
            company = db.session.get(Company, company_id)
            assert company.status == CompanyStatus.PENDING
            assert company.processing_phase == ProcessingPhase.QUEUED

    def test_rescan_creates_new_analysis(self, client, app):
        """Test rescan creates new analysis record."""
        with app.app_context():
            company = Company(
                company_name='Rescan Corp',
                website_url='https://rescan.com',
                status=CompanyStatus.COMPLETED
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id
            initial_count = Analysis.query.filter_by(company_id=company_id).count()

        response = client.post(f'/api/v1/companies/{company_id}/rescan')

        with app.app_context():
            final_count = Analysis.query.filter_by(company_id=company_id).count()
            assert final_count == initial_count + 1

    def test_rescan_limits_to_3_versions(self, client, app):
        """Test rescan maintains maximum 3 versions."""
        with app.app_context():
            company = Company(
                company_name='Version Limit Corp',
                website_url='https://versionlimit.com',
                status=CompanyStatus.COMPLETED
            )
            db.session.add(company)
            db.session.flush()

            # Create 3 existing versions
            for i in range(1, 4):
                analysis = Analysis(
                    company_id=company.id,
                    version_number=i
                )
                db.session.add(analysis)

            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/rescan')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['versionNumber'] == 3

        # Verify still only 3 versions (oldest deleted)
        with app.app_context():
            count = Analysis.query.filter_by(company_id=company_id).count()
            assert count == 3

    def test_rescan_pending_company_fails(self, client, app):
        """Test rescanning a pending company returns 422."""
        with app.app_context():
            company = Company(
                company_name='Pending Corp',
                website_url='https://pending.com',
                status=CompanyStatus.PENDING
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/rescan')

        assert response.status_code == 422
        data = response.get_json()
        assert data['error']['code'] == 'INVALID_STATE'

    def test_rescan_in_progress_company_fails(self, client, app):
        """Test rescanning an in-progress company returns 422."""
        with app.app_context():
            company = Company(
                company_name='In Progress Corp',
                website_url='https://inprogress.com',
                status=CompanyStatus.IN_PROGRESS
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/rescan')

        assert response.status_code == 422

    def test_rescan_nonexistent_company(self, client):
        """Test rescanning a non-existent company returns 404."""
        response = client.post('/api/v1/companies/nonexistent/rescan')

        assert response.status_code == 404
