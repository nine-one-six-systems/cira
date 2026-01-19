"""API Integration tests for Control and Progress endpoints.

These tests verify the pause, resume, and progress endpoints work correctly,
including state validation, checkpoint handling, and response formats.

Requirements verified:
- API-05: GET /companies/:id/progress returns real-time progress
- API-06: POST /companies/:id/pause pauses in-progress analysis
- API-07: POST /companies/:id/resume resumes paused analysis
"""

from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime

import pytest
from app import db
from app.models.company import Company, CrawlSession, Entity
from app.models.enums import CompanyStatus, CrawlStatus, ProcessingPhase, EntityType


def naive_utcnow() -> datetime:
    """Return current UTC time as naive datetime (for SQLite compatibility)."""
    return datetime.utcnow()


# ==================== Helper Functions ====================


def create_in_progress_company(
    db_session,
    pages_crawled: int = 5,
    pages_queued: int = 10,
    with_session: bool = True,
    processing_phase: ProcessingPhase = ProcessingPhase.CRAWLING
) -> Company:
    """Create a company in in_progress state ready to pause.

    Args:
        db_session: Database session
        pages_crawled: Number of pages already crawled
        pages_queued: Number of pages queued for crawling
        with_session: Whether to create an active crawl session
        processing_phase: Current processing phase

    Returns:
        Company object with in_progress status
    """
    company = Company(
        company_name='In Progress Corp',
        website_url='https://in-progress.com',
        status=CompanyStatus.IN_PROGRESS,
        processing_phase=processing_phase,
        started_at=naive_utcnow() - timedelta(minutes=5)
    )
    db_session.add(company)
    db_session.flush()

    if with_session:
        session = CrawlSession(
            company_id=company.id,
            pages_crawled=pages_crawled,
            pages_queued=pages_queued,
            crawl_depth_reached=2,
            external_links_followed=1,
            status=CrawlStatus.ACTIVE
        )
        db_session.add(session)

    db_session.commit()
    return company


def create_paused_company(
    db_session,
    pages_crawled: int = 10,
    pages_queued: int = 5,
    entities_count: int = 25,
    paused_minutes_ago: int = 5
) -> Company:
    """Create a company in paused state ready to resume.

    Args:
        db_session: Database session
        pages_crawled: Number of pages crawled before pause
        pages_queued: Number of pages queued when paused
        entities_count: Number of entities extracted
        paused_minutes_ago: How many minutes ago the company was paused

    Returns:
        Company object with paused status
    """
    now = naive_utcnow()
    company = Company(
        company_name='Paused Corp',
        website_url='https://paused.com',
        status=CompanyStatus.PAUSED,
        processing_phase=ProcessingPhase.CRAWLING,
        started_at=now - timedelta(minutes=10),
        paused_at=now - timedelta(minutes=paused_minutes_ago)
    )
    db_session.add(company)
    db_session.flush()

    # Create paused crawl session with checkpoint data
    session = CrawlSession(
        company_id=company.id,
        pages_crawled=pages_crawled,
        pages_queued=pages_queued,
        crawl_depth_reached=3,
        external_links_followed=2,
        status=CrawlStatus.PAUSED,
        checkpoint_data={
            'pagesCrawled': pages_crawled,
            'pagesQueued': pages_queued,
            'crawlDepthReached': 3,
            'externalLinksFollowed': 2,
            'pausedAt': (now - timedelta(minutes=paused_minutes_ago)).isoformat()
        }
    )
    db_session.add(session)

    # Create entities
    for i in range(entities_count):
        entity = Entity(
            company_id=company.id,
            entity_type=EntityType.PERSON,
            entity_value=f'Person {i}'
        )
        db_session.add(entity)

    db_session.commit()
    return company


# ==================== Test Classes ====================


class TestPauseEndpoint:
    """Tests for POST /companies/:id/pause endpoint - API-06 requirement."""

    def test_pause_returns_success_for_in_progress_company(self, client, app):
        """
        API-06: POST /companies/:id/pause with in_progress company returns 200.
        Response must have: status='paused', checkpointSaved (boolean), pausedAt (timestamp string).
        """
        with app.app_context():
            company = create_in_progress_company(db.session)
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/pause')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['status'] == 'paused'
        assert isinstance(data['data']['checkpointSaved'], bool)
        assert 'pausedAt' in data['data']
        # Verify pausedAt is a timestamp string (HTTP date format or ISO)
        assert isinstance(data['data']['pausedAt'], str)
        assert len(data['data']['pausedAt']) > 0

    def test_pause_updates_company_status_to_paused(self, client, app):
        """
        API-06: After pause, GET /companies/:id shows status='paused'.
        """
        with app.app_context():
            company = create_in_progress_company(db.session)
            company_id = company.id

        # Pause the company
        client.post(f'/api/v1/companies/{company_id}/pause')

        # Verify status via GET
        get_response = client.get(f'/api/v1/companies/{company_id}')
        assert get_response.status_code == 200
        company_data = get_response.get_json()['data']['company']
        assert company_data['status'] == 'paused'

    def test_pause_saves_checkpoint_data(self, client, app):
        """
        API-06: Pause with active crawl session saves checkpoint data.
        checkpointSaved=True when session exists, checkpoint contains page counts.
        """
        with app.app_context():
            company = create_in_progress_company(
                db.session,
                pages_crawled=5,
                pages_queued=3
            )
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/pause')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['checkpointSaved'] is True

        # Verify checkpoint in database
        with app.app_context():
            session = CrawlSession.query.filter_by(
                company_id=company_id,
                status=CrawlStatus.PAUSED
            ).first()
            assert session is not None
            assert session.checkpoint_data is not None
            assert session.checkpoint_data['pagesCrawled'] == 5
            assert session.checkpoint_data['pagesQueued'] == 3

    def test_pause_returns_422_for_paused_company(self, client, app):
        """
        API-06: Cannot pause already paused company. Returns 422 with INVALID_STATE.
        Error includes currentStatus in details.
        """
        with app.app_context():
            company = create_paused_company(db.session)
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/pause')

        assert response.status_code == 422
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_STATE'
        assert 'currentStatus' in data['error']['details']
        assert data['error']['details']['currentStatus'] == 'paused'

    def test_pause_returns_422_for_completed_company(self, client, app):
        """
        API-06: Cannot pause completed company. Returns 422 with INVALID_STATE.
        """
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
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_STATE'
        assert data['error']['details']['currentStatus'] == 'completed'

    def test_pause_returns_422_for_pending_company(self, client, app):
        """
        API-06: Cannot pause pending company. Returns 422 with INVALID_STATE.
        """
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
        assert data['error']['details']['currentStatus'] == 'pending'

    def test_pause_returns_404_for_nonexistent_company(self, client):
        """
        API-06: Pause of non-existent company returns 404 with NOT_FOUND.
        """
        response = client.post('/api/v1/companies/00000000-0000-0000-0000-000000000000/pause')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_pause_sets_paused_at_timestamp(self, client, app):
        """
        API-06: Pause sets pausedAt to recent timestamp (within 5 seconds of now).
        """
        with app.app_context():
            company = create_in_progress_company(db.session)
            company_id = company.id

        before_pause = naive_utcnow()
        response = client.post(f'/api/v1/companies/{company_id}/pause')
        after_pause = naive_utcnow()

        assert response.status_code == 200
        data = response.get_json()

        # Parse pausedAt timestamp (HTTP date format like "Mon, 19 Jan 2026 23:19:48 GMT")
        paused_at_str = data['data']['pausedAt']
        paused_at = parsedate_to_datetime(paused_at_str).replace(tzinfo=None)

        # Verify it's within a reasonable time window
        assert paused_at >= before_pause - timedelta(seconds=1)
        assert paused_at <= after_pause + timedelta(seconds=1)


class TestResumeEndpoint:
    """Tests for POST /companies/:id/resume endpoint - API-07 requirement."""

    def test_resume_returns_success_for_paused_company(self, client, app):
        """
        API-07: POST /companies/:id/resume with paused company returns 200.
        Response must have: status='in_progress', resumedFrom with pagesCrawled, entitiesExtracted, phase.
        """
        with app.app_context():
            company = create_paused_company(
                db.session,
                pages_crawled=10,
                entities_count=25
            )
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['status'] == 'in_progress'
        assert 'resumedFrom' in data['data']
        assert 'pagesCrawled' in data['data']['resumedFrom']
        assert 'entitiesExtracted' in data['data']['resumedFrom']
        assert 'phase' in data['data']['resumedFrom']

    def test_resume_updates_company_status_to_in_progress(self, client, app):
        """
        API-07: After resume, GET /companies/:id shows status='in_progress'.
        """
        with app.app_context():
            company = create_paused_company(db.session)
            company_id = company.id

        # Resume the company
        client.post(f'/api/v1/companies/{company_id}/resume')

        # Verify status via GET
        get_response = client.get(f'/api/v1/companies/{company_id}')
        assert get_response.status_code == 200
        company_data = get_response.get_json()['data']['company']
        assert company_data['status'] == 'in_progress'

    def test_resume_returns_resumedFrom_with_progress(self, client, app):
        """
        API-07: Resume returns resumedFrom with correct pagesCrawled and entitiesExtracted.
        """
        with app.app_context():
            company = create_paused_company(
                db.session,
                pages_crawled=10,
                entities_count=25
            )
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        assert response.status_code == 200
        data = response.get_json()
        resumed_from = data['data']['resumedFrom']
        assert resumed_from['pagesCrawled'] == 10
        assert resumed_from['entitiesExtracted'] == 25
        # Phase should be a valid ProcessingPhase value
        valid_phases = [p.value for p in ProcessingPhase]
        assert resumed_from['phase'] in valid_phases

    def test_resume_returns_422_for_in_progress_company(self, client, app):
        """
        API-07: Cannot resume in_progress company. Returns 422 with INVALID_STATE.
        """
        with app.app_context():
            company = create_in_progress_company(db.session)
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        assert response.status_code == 422
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_STATE'
        assert data['error']['details']['currentStatus'] == 'in_progress'

    def test_resume_returns_422_for_completed_company(self, client, app):
        """
        API-07: Cannot resume completed company. Returns 422 with INVALID_STATE.
        """
        with app.app_context():
            company = Company(
                company_name='Completed Corp',
                website_url='https://completed-resume.com',
                status=CompanyStatus.COMPLETED
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        assert response.status_code == 422
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_STATE'

    def test_resume_returns_422_for_pending_company(self, client, app):
        """
        API-07: Cannot resume pending company. Returns 422 with INVALID_STATE.
        """
        with app.app_context():
            company = Company(
                company_name='Pending Corp',
                website_url='https://pending-resume.com',
                status=CompanyStatus.PENDING
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        assert response.status_code == 422
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'INVALID_STATE'

    def test_resume_returns_404_for_nonexistent_company(self, client):
        """
        API-07: Resume of non-existent company returns 404 with NOT_FOUND.
        """
        response = client.post('/api/v1/companies/00000000-0000-0000-0000-000000000000/resume')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_resume_clears_paused_at(self, client, app):
        """
        API-07: After resume, company.pausedAt is null.
        """
        with app.app_context():
            company = create_paused_company(db.session)
            company_id = company.id
            # Verify paused_at is set before resume
            assert company.paused_at is not None

        # Resume the company
        client.post(f'/api/v1/companies/{company_id}/resume')

        # Verify paused_at is cleared
        with app.app_context():
            company = db.session.get(Company, company_id)
            assert company.paused_at is None

    def test_resume_accumulates_paused_duration(self, client, app):
        """
        API-07: Resume accumulates paused duration in total_paused_duration_ms.
        """
        with app.app_context():
            company = create_paused_company(db.session, paused_minutes_ago=5)
            company_id = company.id
            initial_paused_ms = company.total_paused_duration_ms

        # Resume the company
        client.post(f'/api/v1/companies/{company_id}/resume')

        # Verify paused duration increased
        with app.app_context():
            company = db.session.get(Company, company_id)
            # Should have added approximately 5 minutes (300000ms) of paused time
            # Allow some tolerance for test execution time
            added_duration = company.total_paused_duration_ms - initial_paused_ms
            assert added_duration >= 280000  # At least 4.67 minutes
            assert added_duration <= 320000  # At most 5.33 minutes


class TestProgressEndpoint:
    """Tests for GET /companies/:id/progress endpoint - API-05 requirement."""

    def test_progress_returns_all_required_fields(self, client, app):
        """
        API-05: GET /companies/:id/progress returns all required fields.
        Required: companyId, status, phase, pagesCrawled, pagesTotal,
                  entitiesExtracted, tokensUsed, timeElapsed.
        """
        with app.app_context():
            company = create_in_progress_company(db.session)
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        progress = data['data']
        required_fields = [
            'companyId', 'status', 'phase', 'pagesCrawled',
            'pagesTotal', 'entitiesExtracted', 'tokensUsed', 'timeElapsed'
        ]
        for field in required_fields:
            assert field in progress, f"Missing required field: {field}"

    def test_progress_returns_current_activity(self, client, app):
        """
        API-05: Progress for in_progress company includes currentActivity.
        """
        with app.app_context():
            company = create_in_progress_company(
                db.session,
                processing_phase=ProcessingPhase.CRAWLING
            )
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        assert response.status_code == 200
        data = response.get_json()
        progress = data['data']
        # currentActivity should contain phase-related message
        assert progress.get('currentActivity') is not None
        assert 'crawling' in progress['currentActivity'].lower()

    def test_progress_returns_estimated_time_remaining(self, client, app):
        """
        API-05: Progress with partial completion returns estimatedTimeRemaining > 0.
        """
        with app.app_context():
            company = Company(
                company_name='Estimated Time Corp',
                website_url='https://estimated.com',
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=naive_utcnow() - timedelta(minutes=2)
            )
            db.session.add(company)
            db.session.flush()

            # Create session with 10 pages crawled, 10 queued
            session = CrawlSession(
                company_id=company.id,
                pages_crawled=10,
                pages_queued=10,
                status=CrawlStatus.ACTIVE
            )
            db.session.add(session)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        assert response.status_code == 200
        data = response.get_json()
        progress = data['data']
        # Should have estimated time since we have partial progress
        assert progress.get('estimatedTimeRemaining') is not None
        assert progress['estimatedTimeRemaining'] > 0

    def test_progress_handles_company_with_no_session(self, client, app):
        """
        API-05: Progress for company without crawl session returns zeros.
        """
        with app.app_context():
            company = Company(
                company_name='No Session Corp',
                website_url='https://nosession.com',
                status=CompanyStatus.PENDING,
                processing_phase=ProcessingPhase.QUEUED
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        assert response.status_code == 200
        data = response.get_json()
        progress = data['data']
        assert progress['pagesCrawled'] == 0
        assert progress['pagesTotal'] == 0

    def test_progress_returns_404_for_nonexistent_company(self, client):
        """
        API-05: Progress for non-existent company returns 404.
        """
        response = client.get('/api/v1/companies/00000000-0000-0000-0000-000000000000/progress')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_progress_returns_paused_status_when_paused(self, client, app):
        """
        API-05: Progress for paused company shows status='paused'.
        """
        with app.app_context():
            company = create_paused_company(db.session)
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['status'] == 'paused'

    def test_progress_excludes_paused_time_from_elapsed(self, client, app):
        """
        API-05: timeElapsed excludes paused duration.
        Company started 10min ago, paused for 5min => timeElapsed ~= 5min (300s).
        """
        with app.app_context():
            company = Company(
                company_name='Paused Duration Corp',
                website_url='https://paused-duration.com',
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=naive_utcnow() - timedelta(minutes=10),
                total_paused_duration_ms=300000  # 5 minutes paused
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        assert response.status_code == 200
        data = response.get_json()
        progress = data['data']

        # Should be approximately 5 minutes (300 seconds)
        # Not 10 minutes (600 seconds)
        time_elapsed = progress['timeElapsed']
        assert time_elapsed >= 290  # At least ~4.8 minutes
        assert time_elapsed <= 310  # At most ~5.2 minutes

    def test_progress_returns_null_estimated_when_no_progress(self, client, app):
        """
        API-05: estimatedTimeRemaining is null when pagesCrawled=0.
        """
        with app.app_context():
            company = Company(
                company_name='No Progress Corp',
                website_url='https://noprogress.com',
                status=CompanyStatus.IN_PROGRESS,
                processing_phase=ProcessingPhase.CRAWLING,
                started_at=naive_utcnow()
            )
            db.session.add(company)
            db.session.flush()

            # Create session with no progress
            session = CrawlSession(
                company_id=company.id,
                pages_crawled=0,
                pages_queued=10,
                status=CrawlStatus.ACTIVE
            )
            db.session.add(session)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        assert response.status_code == 200
        data = response.get_json()
        progress = data['data']
        # Should be null since we can't estimate with no progress
        assert progress.get('estimatedTimeRemaining') is None


class TestResponseFormats:
    """Tests for response format compliance."""

    def test_pause_response_matches_schema(self, client, app):
        """
        Response format: PauseResponse has status, checkpointSaved, pausedAt.
        """
        with app.app_context():
            company = create_in_progress_company(db.session)
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/pause')

        assert response.status_code == 200
        data = response.get_json()['data']

        # Verify schema fields
        assert 'status' in data
        assert 'checkpointSaved' in data
        assert 'pausedAt' in data

        # Type checks
        assert isinstance(data['status'], str)
        assert isinstance(data['checkpointSaved'], bool)
        assert isinstance(data['pausedAt'], str)

    def test_resume_response_matches_schema(self, client, app):
        """
        Response format: ResumeResponse has status, resumedFrom.
        resumedFrom has pagesCrawled, entitiesExtracted, phase.
        """
        with app.app_context():
            company = create_paused_company(db.session)
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/resume')

        assert response.status_code == 200
        data = response.get_json()['data']

        # Verify schema fields
        assert 'status' in data
        assert 'resumedFrom' in data

        resumed_from = data['resumedFrom']
        assert 'pagesCrawled' in resumed_from
        assert 'entitiesExtracted' in resumed_from
        assert 'phase' in resumed_from

        # Type checks
        assert isinstance(data['status'], str)
        assert isinstance(resumed_from['pagesCrawled'], int)
        assert isinstance(resumed_from['entitiesExtracted'], int)
        assert isinstance(resumed_from['phase'], str)

    def test_progress_response_matches_schema(self, client, app):
        """
        Response format: ProgressResponse has all required fields with correct types.
        """
        with app.app_context():
            company = create_in_progress_company(db.session)
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/progress')

        assert response.status_code == 200
        data = response.get_json()['data']

        # Verify required fields and types
        assert isinstance(data['companyId'], str)
        assert isinstance(data['status'], str)
        assert isinstance(data['phase'], str)
        assert isinstance(data['pagesCrawled'], int)
        assert isinstance(data['pagesTotal'], int)
        assert isinstance(data['entitiesExtracted'], int)
        assert isinstance(data['tokensUsed'], int)
        assert isinstance(data['timeElapsed'], int)

        # Optional fields can be null
        if data.get('estimatedTimeRemaining') is not None:
            assert isinstance(data['estimatedTimeRemaining'], int)
        if data.get('currentActivity') is not None:
            assert isinstance(data['currentActivity'], str)

    def test_timestamps_are_parseable(self, client, app):
        """
        All timestamps should be parseable datetime strings (HTTP date format).
        """
        with app.app_context():
            company = create_in_progress_company(db.session)
            company_id = company.id

        response = client.post(f'/api/v1/companies/{company_id}/pause')

        assert response.status_code == 200
        data = response.get_json()['data']

        paused_at = data['pausedAt']
        # Flask serializes datetime in HTTP date format (RFC 2822)
        # e.g., "Mon, 19 Jan 2026 23:19:48 GMT"
        assert isinstance(paused_at, str)
        # Should be parseable using email.utils
        parsed = parsedate_to_datetime(paused_at)
        assert parsed is not None
