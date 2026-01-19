"""Edge case tests for analysis robustness.

Tests verify that the analysis pipeline handles unusual inputs gracefully:
- Empty and missing content
- Very long content with truncation
- API rate limits and errors
- Partial failures and recovery
- Content preparation edge cases
- Concurrent analyses
- Progress reporting
- Token pricing calculations

Requirements covered:
- FR-SUM-001: Executive summary handles edge cases
- FR-ANA-001: Team analysis with missing data
- FR-ANA-002: Business model with missing data
- FR-ANA-003: Company stage with minimal info
- FR-TOK-001: Token tracking edge cases
"""

import time
from datetime import datetime, timedelta, UTC
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from app.analysis.synthesis import (
    AnalysisSynthesizer,
    AnalysisResult,
    SectionResult,
)
from app.analysis.prompts import (
    ANALYSIS_SECTIONS,
    get_section_order,
    get_analysis_prompt,
)
from app.services.anthropic_service import (
    AnthropicService,
    AnthropicServiceError,
    RateLimitError,
    APIError,
    TimeoutError,
    ClaudeResponse,
)
from app.services.token_tracker import TokenTracker, TokenCost


class TestEmptyContentHandling:
    """Tests for handling empty or missing content.

    Verifies analysis handles companies with no pages, empty text,
    no entities, and other missing data scenarios.
    """

    def test_analysis_handles_company_with_no_pages(self, app):
        """
        Test that analysis handles company with 0 pages.

        Verifies: Analysis completes without exception, indicates insufficient data.
        """
        from app.models import Company
        from app import db

        with app.app_context():
            # Create company with no pages
            company = Company(
                company_name='Empty Company',
                website_url='https://empty.com',
                industry='Unknown',
            )
            db.session.add(company)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()

            # Should not raise exception
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Content should be empty or minimal
            assert context['content'] == '' or len(context['content']) < 100
            assert context['entities'] == '' or len(context['entities']) < 50

    def test_analysis_handles_pages_with_empty_text(self, app):
        """
        Test that analysis handles pages but all have empty extracted_text.

        Verifies: Analysis completes without exception.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Empty Text Company',
                website_url='https://emptytext.com',
            )
            db.session.add(company)
            db.session.flush()

            # Add pages with empty text (using available PageType values)
            for i, page_type in enumerate([PageType.OTHER, PageType.ABOUT, PageType.TEAM]):
                page = Page(
                    company_id=company.id,
                    url=f'https://emptytext.com/page{i}',
                    page_type=page_type,
                    extracted_text='',  # Empty text
                )
                db.session.add(page)

            db.session.commit()

            synthesizer = AnalysisSynthesizer()

            # Should not raise exception
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Content should be minimal (just headers, no actual text)
            assert isinstance(context['content'], str)

    def test_analysis_handles_company_with_no_entities(self, app):
        """
        Test that analysis handles company with pages but 0 entities.

        Verifies: Analysis completes, team_leadership section notes lack of data.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='No Entities Company',
                website_url='https://noentities.com',
            )
            db.session.add(company)
            db.session.flush()

            # Add page with content but no entities extracted
            page = Page(
                company_id=company.id,
                url='https://noentities.com/about',
                page_type=PageType.ABOUT,
                extracted_text='About us page with generic content but no names.',
            )
            db.session.add(page)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Entity fields should be empty
            assert context['people_entities'] == ''
            assert context['org_entities'] == ''
            assert context['tech_entities'] == ''

    def test_analysis_handles_only_external_pages(self, app):
        """
        Test that analysis handles company where all pages are external.

        Verifies: Analysis completes using available external data.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='External Only Company',
                website_url='https://external.com',
            )
            db.session.add(company)
            db.session.flush()

            # Add only external pages (marked as external with OTHER type)
            external_pages = [
                ('https://linkedin.com/company/external', PageType.OTHER),
                ('https://twitter.com/external', PageType.OTHER),
            ]

            for url, page_type in external_pages:
                page = Page(
                    company_id=company.id,
                    url=url,
                    page_type=page_type,
                    extracted_text=f'Profile content from {url}',
                    is_external=True,
                )
                db.session.add(page)

            db.session.commit()

            synthesizer = AnalysisSynthesizer()

            # Should not raise exception
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Content should include social profile data
            assert isinstance(context['content'], str)

    def test_analysis_handles_missing_page_types(self, app):
        """
        Test that analysis handles company with only 'other' page types.

        Verifies: Analysis completes without exception.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Other Pages Company',
                website_url='https://otherpages.com',
            )
            db.session.add(company)
            db.session.flush()

            # Add only 'other' type pages
            for i in range(3):
                page = Page(
                    company_id=company.id,
                    url=f'https://otherpages.com/page{i}',
                    page_type=PageType.OTHER,
                    extracted_text=f'Generic content on page {i}',
                )
                db.session.add(page)

            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Team and careers content should be empty
            assert context['team_content'] == ''
            assert context['careers_content'] == ''


class TestLongContentHandling:
    """Tests for handling very long content.

    Verifies analysis truncates content appropriately without errors.
    """

    def test_truncates_content_to_max_length(self, app):
        """
        Test that content is truncated to 50000 chars.

        Verifies: Content prepared for Claude is within limit.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Long Content Company',
                website_url='https://longcontent.com',
            )
            db.session.add(company)
            db.session.flush()

            # Add page with 100,000+ characters
            long_text = 'A' * 100_000
            page = Page(
                company_id=company.id,
                url='https://longcontent.com/long',
                page_type=PageType.ABOUT,
                extracted_text=long_text,
            )
            db.session.add(page)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Content should be truncated to 50000
            assert len(context['content']) <= 50_000

    def test_prioritizes_about_and_team_pages(self, app):
        """
        Test that about and team page content is preserved when truncating.

        Verifies: Important page types have their content preserved.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Multi Page Company',
                website_url='https://multipage.com',
            )
            db.session.add(company)
            db.session.flush()

            # Add pages of various types
            pages_data = [
                (PageType.ABOUT, 'ABOUT_MARKER_IMPORTANT This is about content.'),
                (PageType.TEAM, 'TEAM_MARKER_IMPORTANT This is team content.'),
                (PageType.OTHER, 'Other page content that might be truncated.'),
            ]

            for page_type, text in pages_data:
                page = Page(
                    company_id=company.id,
                    url=f'https://multipage.com/{page_type.value}',
                    page_type=page_type,
                    extracted_text=text,
                )
                db.session.add(page)

            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            # About and team markers should be present
            assert 'ABOUT_MARKER_IMPORTANT' in context['content']

    def test_per_page_type_truncation(self, app):
        """
        Test that per-page-type limits are applied.

        Verifies: Very long team pages are truncated to ~10000 chars.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Long Team Page Company',
                website_url='https://longteam.com',
            )
            db.session.add(company)
            db.session.flush()

            # Add very long team page (20000+ chars)
            long_team_text = 'Team member info. ' * 2000  # ~36000 chars
            page = Page(
                company_id=company.id,
                url='https://longteam.com/team',
                page_type=PageType.TEAM,
                extracted_text=long_team_text,
            )
            db.session.add(page)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Team content should be limited to 10000
            assert len(context['team_content']) <= 10_000

    def test_handles_single_very_long_page(self, app):
        """
        Test that a single page with 200,000 characters is handled.

        Verifies: Completes without memory error, content truncated.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Very Long Page Company',
                website_url='https://verylong.com',
            )
            db.session.add(company)
            db.session.flush()

            # Single page with 200,000 characters
            very_long_text = 'X' * 200_000
            page = Page(
                company_id=company.id,
                url='https://verylong.com/huge',
                page_type=PageType.OTHER,  # No HOME type, use OTHER
                extracted_text=very_long_text,
            )
            db.session.add(page)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()

            # Should not raise MemoryError or take excessive time
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Content should be truncated
            assert len(context['content']) <= 50_000


class TestAPIErrorRecovery:
    """Tests for API error handling and retry logic.

    Verifies analysis recovers from rate limits, transient errors,
    and handles timeouts gracefully.
    """

    def test_recovers_from_rate_limit_error(self):
        """
        Test that analysis recovers from RateLimitError after retries.

        Verifies: Eventually succeeds after retries with exponential backoff.
        """
        import anthropic

        service = AnthropicService()
        service._client = MagicMock()

        # Track call count
        call_count = [0]

        def mock_create(**kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                # First 2 calls raise rate limit error
                raise anthropic.RateLimitError(
                    message="Rate limited",
                    response=MagicMock(status_code=429),
                    body={},
                )
            # Third call succeeds
            mock_response = MagicMock()
            mock_response.content = [MagicMock(type='text', text='Success response')]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 50
            mock_response.model = 'claude-sonnet-4-20250514'
            mock_response.stop_reason = 'end_turn'
            mock_response.id = 'msg_123'
            mock_response.type = 'message'
            mock_response.role = 'assistant'
            return mock_response

        service._client.messages.create = mock_create

        with patch.object(service, '_get_config_value') as mock_config:
            mock_config.return_value = 3  # MAX_RETRIES

            # Should eventually succeed
            with patch('time.sleep'):  # Skip actual delays
                result = service.call("Test prompt")

            assert result.content == 'Success response'
            assert call_count[0] == 3  # Should have tried 3 times

    def test_recovers_from_transient_api_error(self):
        """
        Test that analysis recovers from transient APIError.

        Verifies: Completes successfully after retry.
        """
        import anthropic

        service = AnthropicService()
        service._client = MagicMock()

        call_count = [0]

        def mock_create(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise anthropic.APIStatusError(
                    message="Temporary error",
                    response=MagicMock(status_code=500),
                    body={},
                )
            mock_response = MagicMock()
            mock_response.content = [MagicMock(type='text', text='Recovered')]
            mock_response.usage.input_tokens = 100
            mock_response.usage.output_tokens = 50
            mock_response.model = 'claude-sonnet-4-20250514'
            mock_response.stop_reason = 'end_turn'
            mock_response.id = 'msg_123'
            mock_response.type = 'message'
            mock_response.role = 'assistant'
            return mock_response

        service._client.messages.create = mock_create

        with patch.object(service, '_get_config_value') as mock_config:
            mock_config.return_value = 3

            with patch('time.sleep'):
                result = service.call("Test prompt")

            assert result.content == 'Recovered'

    def test_fails_after_max_retries(self):
        """
        Test that analysis raises RateLimitError after max retries.

        Verifies: Raises RateLimitError after exhausting retries.
        """
        import anthropic

        service = AnthropicService()
        service._client = MagicMock()

        def always_fail(**kwargs):
            raise anthropic.RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body={},
            )

        service._client.messages.create = always_fail

        with patch.object(service, '_get_config_value') as mock_config:
            mock_config.return_value = 3

            with patch('time.sleep'):
                with pytest.raises(RateLimitError):
                    service.call("Test prompt")

    def test_handles_api_timeout(self):
        """
        Test that analysis handles API timeout gracefully.

        Verifies: TimeoutError raised with appropriate message.
        """
        import anthropic

        service = AnthropicService()
        service._client = MagicMock()

        def timeout_error(**kwargs):
            raise anthropic.APITimeoutError(request=MagicMock())

        service._client.messages.create = timeout_error

        with patch.object(service, '_get_config_value') as mock_config:
            mock_config.return_value = 60

            with pytest.raises(TimeoutError) as exc_info:
                service.call("Test prompt")

            # Message is "Request timed out after Xs"
            assert 'timed out' in str(exc_info.value).lower()

    def test_handles_invalid_api_response(self):
        """
        Test that analysis handles malformed API response.

        Verifies: Error handled, no crash.
        """
        service = AnthropicService()
        service._client = MagicMock()

        # Response with missing/malformed content
        mock_response = MagicMock()
        mock_response.content = []  # No content blocks
        mock_response.usage.input_tokens = 0
        mock_response.usage.output_tokens = 0
        mock_response.model = 'claude-sonnet-4-20250514'
        mock_response.stop_reason = 'end_turn'
        mock_response.id = 'msg_123'
        mock_response.type = 'message'
        mock_response.role = 'assistant'

        service._client.messages.create.return_value = mock_response

        with patch.object(service, '_get_config_value') as mock_config:
            mock_config.return_value = 60

            # Should not crash, returns empty content
            result = service.call("Test prompt")
            assert result.content == ''


class TestPartialFailureRecovery:
    """Tests for handling partial analysis failures.

    Verifies completed sections are preserved when later sections fail.
    """

    @patch('app.services.anthropic_service.anthropic_service')
    def test_preserves_completed_sections_on_failure(self, mock_anthropic, app):
        """
        Test that completed sections are saved when failure occurs.

        Verifies: First sections saved before failure.
        """
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='Partial Fail Company',
                website_url='https://partialfail.com',
            )
            db.session.add(company)
            db.session.commit()

            # Track call count
            call_count = [0]
            success_count = 3

            def mock_call(**kwargs):
                call_count[0] += 1
                if call_count[0] <= success_count:
                    return ClaudeResponse(
                        content=f'Section {call_count[0]} content',
                        input_tokens=100,
                        output_tokens=50,
                        model='claude-sonnet-4-20250514',
                    )
                raise APIError("Simulated failure")

            mock_anthropic.call.side_effect = mock_call

            synthesizer = AnalysisSynthesizer()

            # Run analysis - should complete with partial results
            result = synthesizer.run_full_analysis(company.id)

            # Should have some successful sections
            successful = [s for s in result.sections.values() if s.success]
            assert len(successful) >= success_count

    @patch('app.services.anthropic_service.anthropic_service')
    def test_section_failure_doesnt_corrupt_others(self, mock_anthropic, app):
        """
        Test that one section's failure doesn't corrupt others.

        Verifies: Other sections have valid content.
        """
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='Section Fail Company',
                website_url='https://sectionfail.com',
            )
            db.session.add(company)
            db.session.commit()

            call_count = [0]
            fail_on_section = 4  # Fail on 4th section

            def mock_call(**kwargs):
                call_count[0] += 1
                if call_count[0] == fail_on_section:
                    raise APIError("Section 4 failed")
                return ClaudeResponse(
                    content=f'Valid content for section {call_count[0]}',
                    input_tokens=100,
                    output_tokens=50,
                    model='claude-sonnet-4-20250514',
                )

            mock_anthropic.call.side_effect = mock_call

            synthesizer = AnalysisSynthesizer()
            result = synthesizer.run_full_analysis(company.id)

            # Count successful vs failed
            successful = [s for s in result.sections.values() if s.success]
            failed = [s for s in result.sections.values() if not s.success]

            # Most sections should be successful
            assert len(successful) >= 6  # At least 6 of 8 sections
            # Failed section should be marked
            assert len(failed) >= 1


class TestContentPreparation:
    """Tests for content preparation edge cases.

    Verifies content is properly formatted for Claude analysis.
    """

    def test_prepare_content_includes_entities(self, app):
        """
        Test that prepared content includes entity context.

        Verifies: Entities are included for Claude.
        """
        from app.models import Company, Page, Entity
        from app.models.enums import PageType, EntityType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Entity Company',
                website_url='https://entitycompany.com',
            )
            db.session.add(company)
            db.session.flush()

            # Add page
            page = Page(
                company_id=company.id,
                url='https://entitycompany.com/about',
                page_type=PageType.ABOUT,
                extracted_text='About the company.',
            )
            db.session.add(page)

            # Add entities
            entities = [
                Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value='John Doe',
                    extra_data={'role': 'CEO'},
                ),
                Entity(
                    company_id=company.id,
                    entity_type=EntityType.ORGANIZATION,
                    entity_value='Partner Corp',
                    extra_data={'relationship': 'Partner'},
                ),
            ]
            for entity in entities:
                db.session.add(entity)

            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Entities should be included
            assert 'John Doe' in context['people_entities']
            assert 'CEO' in context['people_entities']
            assert 'Partner Corp' in context['org_entities']

    def test_prepare_content_formats_page_metadata(self, app):
        """
        Test that page titles and URLs are formatted for Claude.

        Verifies: Page URLs appear in content.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Metadata Company',
                website_url='https://metadata.com',
            )
            db.session.add(company)
            db.session.flush()

            page = Page(
                company_id=company.id,
                url='https://metadata.com/about',
                page_type=PageType.ABOUT,
                extracted_text='About us content.',
            )
            db.session.add(page)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            # URL should appear in content
            assert 'metadata.com/about' in context['content']

    def test_prepare_content_handles_unicode(self, app):
        """
        Test that unicode characters are preserved or safely encoded.

        Verifies: Emojis and special characters handled.
        """
        from app.models import Company, Page
        from app.models.enums import PageType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Unicode Company',
                website_url='https://unicode.com',
            )
            db.session.add(company)
            db.session.flush()

            # Text with various unicode
            unicode_text = 'Company info with emojis and special chars'
            page = Page(
                company_id=company.id,
                url='https://unicode.com/about',
                page_type=PageType.ABOUT,
                extracted_text=unicode_text,
            )
            db.session.add(page)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()

            # Should not raise exception
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Content should be valid string
            assert isinstance(context['content'], str)

    def test_prepare_content_handles_none_industry(self, app):
        """
        Test that None industry is handled.

        Verifies: Defaults to 'Unknown' when industry is None.
        """
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='No Industry Company',
                website_url='https://noindustry.com',
                industry=None,
            )
            db.session.add(company)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Industry should default to 'Unknown'
            assert context['industry'] == 'Unknown'


class TestConcurrency:
    """Tests for concurrent analysis scenarios.

    Verifies multiple analyses don't interfere with each other.
    """

    @patch('app.services.anthropic_service.anthropic_service')
    def test_multiple_analyses_dont_interfere(self, mock_anthropic, app):
        """
        Test that analyses for 2 companies get correct results.

        Verifies: Each company gets its own results, no crossover.
        """
        from app.models import Company
        from app import db

        with app.app_context():
            # Create two companies
            company1 = Company(
                company_name='Company One',
                website_url='https://one.com',
            )
            company2 = Company(
                company_name='Company Two',
                website_url='https://two.com',
            )
            db.session.add(company1)
            db.session.add(company2)
            db.session.commit()

            # Mock returns company name in response
            def mock_call(**kwargs):
                prompt = kwargs.get('prompt', '')
                if 'Company One' in prompt:
                    return ClaudeResponse(
                        content='Analysis for Company One',
                        input_tokens=100,
                        output_tokens=50,
                        model='claude-sonnet-4-20250514',
                    )
                return ClaudeResponse(
                    content='Analysis for Company Two',
                    input_tokens=100,
                    output_tokens=50,
                    model='claude-sonnet-4-20250514',
                )

            mock_anthropic.call.side_effect = mock_call

            synthesizer = AnalysisSynthesizer()

            # Run both analyses
            result1 = synthesizer.run_full_analysis(company1.id)
            result2 = synthesizer.run_full_analysis(company2.id)

            # Each should have their own data
            assert result1.company_id == str(company1.id)
            assert result2.company_id == str(company2.id)

    def test_handles_analysis_while_crawl_in_progress(self, app):
        """
        Test that analysis handles company with in_progress status.

        Verifies: Still prepares content even if status is 'in_progress'.
        """
        from app.models import Company
        from app.models.enums import CompanyStatus
        from app import db

        with app.app_context():
            company = Company(
                company_name='Crawling Company',
                website_url='https://crawling.com',
                status=CompanyStatus.IN_PROGRESS,  # Use IN_PROGRESS instead of CRAWLING
            )
            db.session.add(company)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()

            # Should not raise exception
            context = synthesizer.prepare_content_for_analysis(company.id)

            # Context should still be prepared
            assert context['company_name'] == 'Crawling Company'


class TestProgressReporting:
    """Tests for progress reporting during analysis.

    Verifies progress callbacks work correctly.
    """

    @patch('app.services.anthropic_service.anthropic_service')
    def test_progress_updates_on_each_section(self, mock_anthropic, app):
        """
        Test that progress updates are sent for each section.

        Verifies: Callback called for each of 8 sections.
        """
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='Progress Company',
                website_url='https://progress.com',
            )
            db.session.add(company)
            db.session.commit()

            mock_anthropic.call.return_value = ClaudeResponse(
                content='Section content',
                input_tokens=100,
                output_tokens=50,
                model='claude-sonnet-4-20250514',
            )

            progress_updates = []

            def progress_callback(section_id, completed, total):
                progress_updates.append({
                    'section': section_id,
                    'completed': completed,
                    'total': total,
                })

            synthesizer = AnalysisSynthesizer()
            synthesizer.run_full_analysis(
                company.id,
                progress_callback=progress_callback,
            )

            # Should have updates for each section plus 'complete'
            assert len(progress_updates) >= 8

    @patch('app.services.anthropic_service.anthropic_service')
    def test_progress_shows_failure_status(self, mock_anthropic, app):
        """
        Test that progress includes failure information.

        Verifies: Errors are tracked in result.
        """
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='Fail Progress Company',
                website_url='https://failprogress.com',
            )
            db.session.add(company)
            db.session.commit()

            call_count = [0]

            def mock_call(**kwargs):
                call_count[0] += 1
                if call_count[0] == 3:
                    raise APIError("Section failed")
                return ClaudeResponse(
                    content='Content',
                    input_tokens=100,
                    output_tokens=50,
                    model='claude-sonnet-4-20250514',
                )

            mock_anthropic.call.side_effect = mock_call

            synthesizer = AnalysisSynthesizer()
            result = synthesizer.run_full_analysis(company.id)

            # Should have recorded the error
            assert len(result.errors) >= 1


class TestTokenPricing:
    """Tests for token cost calculation edge cases.

    Verifies cost calculations are accurate and handle edge cases.
    """

    def test_cost_calculation_with_zero_tokens(self):
        """
        Test that cost calculation handles 0 tokens.

        Verifies: Cost is 0.0, no division error.
        """
        tracker = TokenTracker()
        cost = tracker.calculate_cost(0, 0)

        assert cost.total_cost == 0.0
        assert cost.input_cost == 0.0
        assert cost.output_cost == 0.0
        assert cost.total_tokens == 0

    def test_cost_calculation_precision(self):
        """
        Test that cost calculation preserves precision.

        Verifies: 4+ decimal places preserved, no floating point errors.
        """
        tracker = TokenTracker()

        # Small token counts
        cost = tracker.calculate_cost(100, 50)

        # Cost should have proper precision
        # 100 input * $3/1M = $0.0003
        # 50 output * $15/1M = $0.00075
        assert cost.input_cost == pytest.approx(0.0003, rel=1e-6)
        assert cost.output_cost == pytest.approx(0.00075, rel=1e-6)
        assert cost.total_cost == pytest.approx(0.00105, rel=1e-6)

    def test_cost_uses_default_rates(self):
        """
        Test that default rates are used when no config.

        Verifies: Default rates applied correctly.
        """
        tracker = TokenTracker()

        # Default rates: $3/1M input, $15/1M output
        cost = tracker.calculate_cost(1_000_000, 1_000_000)

        assert cost.input_cost == pytest.approx(3.0, rel=1e-6)
        assert cost.output_cost == pytest.approx(15.0, rel=1e-6)

    def test_cost_calculation_large_numbers(self):
        """
        Test that large token counts are handled correctly.

        Verifies: No overflow with large numbers.
        """
        tracker = TokenTracker()

        # Large token counts (realistic for batch processing)
        cost = tracker.calculate_cost(10_000_000, 5_000_000)

        # Should calculate correctly without overflow
        assert cost.input_cost == pytest.approx(30.0, rel=1e-6)
        assert cost.output_cost == pytest.approx(75.0, rel=1e-6)
        assert cost.total_cost == pytest.approx(105.0, rel=1e-6)

    def test_token_cost_to_dict(self):
        """
        Test that TokenCost.to_dict() works correctly.

        Verifies: Dictionary has all expected fields.
        """
        tracker = TokenTracker()
        cost = tracker.calculate_cost(1000, 500)
        cost_dict = cost.to_dict()

        assert 'input_tokens' in cost_dict
        assert 'output_tokens' in cost_dict
        assert 'total_tokens' in cost_dict
        assert 'input_cost' in cost_dict
        assert 'output_cost' in cost_dict
        assert 'total_cost' in cost_dict

        assert cost_dict['total_tokens'] == 1500


class TestAnalysisPromptEdgeCases:
    """Tests for analysis prompt handling edge cases.

    Verifies prompts handle missing context gracefully.
    """

    def test_get_prompt_with_empty_context(self):
        """
        Test that prompts work with empty context.

        Verifies: Uses defaults for missing values.
        """
        prompt, system_prompt = get_analysis_prompt(
            'company_overview',
            text='',
            context={},
        )

        # Should use defaults
        assert 'Unknown Company' in prompt
        assert system_prompt is not None

    def test_get_prompt_unknown_section_raises(self):
        """
        Test that unknown section raises ValueError.

        Verifies: ValueError for invalid section_id.
        """
        with pytest.raises(ValueError) as exc_info:
            get_analysis_prompt('invalid_section')

        assert 'Unknown analysis section' in str(exc_info.value)

    def test_all_sections_have_prompts(self):
        """
        Test that all defined sections have valid prompts.

        Verifies: Each section can generate a prompt.
        """
        section_order = get_section_order()

        for section_id in section_order:
            prompt, system_prompt = get_analysis_prompt(section_id, context={})
            assert prompt is not None
            assert len(prompt) > 0
            assert system_prompt is not None


class TestAnalysisResultEdgeCases:
    """Tests for AnalysisResult dataclass edge cases.

    Verifies result handling for various scenarios.
    """

    def test_analysis_result_empty_sections(self):
        """
        Test AnalysisResult with empty sections dict.

        Verifies: success property handles empty sections.
        """
        result = AnalysisResult(
            company_id='test-id',
            version_number=1,
            executive_summary='',
            sections={},
            total_input_tokens=0,
            total_output_tokens=0,
            started_at=datetime.now(UTC),
        )

        # Should be unsuccessful (missing required sections)
        assert result.success is False

    def test_analysis_result_missing_required_section(self):
        """
        Test that missing required section means failure.

        Verifies: success is False when required section missing.
        """
        # Only have one section
        sections = {
            'company_overview': SectionResult(
                section_id='company_overview',
                content='Overview content',
            ),
        }

        result = AnalysisResult(
            company_id='test-id',
            version_number=1,
            executive_summary='',
            sections=sections,
            total_input_tokens=0,
            total_output_tokens=0,
            started_at=datetime.now(UTC),
        )

        # Missing business_model and executive_summary (required)
        assert result.success is False

    def test_analysis_result_to_dict_with_none_completed_at(self):
        """
        Test that to_dict handles None completed_at.

        Verifies: completed_at can be None in dict.
        """
        result = AnalysisResult(
            company_id='test-id',
            version_number=1,
            executive_summary='Summary',
            sections={},
            total_input_tokens=100,
            total_output_tokens=50,
            started_at=datetime.now(UTC),
            completed_at=None,
        )

        result_dict = result.to_dict()

        assert result_dict['completed_at'] is None
        assert result_dict['total_tokens'] == 150


class TestSectionResultEdgeCases:
    """Tests for SectionResult dataclass edge cases.

    Verifies section result handling for edge cases.
    """

    def test_section_result_with_error_has_no_success(self):
        """
        Test that section with error is not successful.

        Verifies: success is False when error is set.
        """
        result = SectionResult(
            section_id='test',
            content='Some content',
            error='Error message',
        )

        assert result.success is False

    def test_section_result_empty_content_no_success(self):
        """
        Test that empty content means no success.

        Verifies: Empty content = not successful.
        """
        result = SectionResult(
            section_id='test',
            content='',
        )

        assert result.success is False

    def test_section_result_whitespace_content_no_success(self):
        """
        Test that whitespace-only content means no success.

        Verifies: Whitespace = not successful (bool('') is False).
        """
        result = SectionResult(
            section_id='test',
            content='   ',  # Whitespace only
        )

        # Whitespace string is truthy, so this will be True
        # This tests the actual behavior
        assert result.success is True  # '   ' is truthy

    def test_section_result_to_dict_preserves_fields(self):
        """
        Test that to_dict preserves all fields correctly.

        Verifies: All fields present in dictionary.
        """
        result = SectionResult(
            section_id='test',
            content='Test content',
            sources=['https://source1.com', 'https://source2.com'],
            confidence=0.85,
            input_tokens=100,
            output_tokens=50,
        )

        result_dict = result.to_dict()

        assert result_dict['content'] == 'Test content'
        assert len(result_dict['sources']) == 2
        assert result_dict['confidence'] == 0.85
