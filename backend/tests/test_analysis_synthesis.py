"""Tests for the Analysis Synthesis module (Task 6.5)."""

import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, patch, MagicMock


class TestSectionResultDataclass:
    """Test SectionResult dataclass."""

    def test_section_result_creation(self):
        """Test creating a SectionResult."""
        from app.analysis.synthesis import SectionResult

        result = SectionResult(
            section_id='company_overview',
            content='Analysis content here',
            sources=['https://example.com/about'],
            confidence=0.85,
            input_tokens=500,
            output_tokens=250,
        )

        assert result.section_id == 'company_overview'
        assert result.content == 'Analysis content here'
        assert result.success is True
        assert len(result.sources) == 1

    def test_section_result_success_property(self):
        """Test success property."""
        from app.analysis.synthesis import SectionResult

        # Successful result
        success_result = SectionResult(
            section_id='test',
            content='Some content',
        )
        assert success_result.success is True

        # Failed result (has error)
        failed_result = SectionResult(
            section_id='test',
            content='',
            error='API error',
        )
        assert failed_result.success is False

        # Empty content
        empty_result = SectionResult(
            section_id='test',
            content='',
        )
        assert empty_result.success is False

    def test_section_result_to_dict(self):
        """Test to_dict method."""
        from app.analysis.synthesis import SectionResult

        result = SectionResult(
            section_id='test',
            content='Content',
            sources=['url1', 'url2'],
            confidence=0.9,
        )

        d = result.to_dict()

        assert d['content'] == 'Content'
        assert d['sources'] == ['url1', 'url2']
        assert d['confidence'] == 0.9


class TestAnalysisResultDataclass:
    """Test AnalysisResult dataclass."""

    def test_analysis_result_creation(self):
        """Test creating an AnalysisResult."""
        from app.analysis.synthesis import AnalysisResult, SectionResult

        sections = {
            'company_overview': SectionResult(
                section_id='company_overview',
                content='Overview content',
                input_tokens=100,
                output_tokens=50,
            ),
            'executive_summary': SectionResult(
                section_id='executive_summary',
                content='Summary content',
                input_tokens=200,
                output_tokens=100,
            ),
        }

        result = AnalysisResult(
            company_id='test-id',
            version_number=1,
            executive_summary='Summary content',
            sections=sections,
            total_input_tokens=300,
            total_output_tokens=150,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        assert result.company_id == 'test-id'
        assert result.version_number == 1
        assert result.total_tokens == 450

    def test_analysis_result_success_property(self):
        """Test success property with required sections."""
        from app.analysis.synthesis import AnalysisResult, SectionResult

        # Create successful sections
        success_sections = {
            'company_overview': SectionResult(
                section_id='company_overview',
                content='Content',
            ),
            'business_model': SectionResult(
                section_id='business_model',
                content='Content',
            ),
            'executive_summary': SectionResult(
                section_id='executive_summary',
                content='Summary',
            ),
        }

        result = AnalysisResult(
            company_id='test-id',
            version_number=1,
            executive_summary='Summary',
            sections=success_sections,
            total_input_tokens=0,
            total_output_tokens=0,
            started_at=datetime.now(UTC),
        )

        assert result.success is True

    def test_analysis_result_to_dict(self):
        """Test to_dict method."""
        from app.analysis.synthesis import AnalysisResult, SectionResult

        result = AnalysisResult(
            company_id='test-id',
            version_number=1,
            executive_summary='Summary',
            sections={
                'test': SectionResult(
                    section_id='test',
                    content='Content',
                )
            },
            total_input_tokens=100,
            total_output_tokens=50,
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )

        d = result.to_dict()

        assert d['company_id'] == 'test-id'
        assert d['version_number'] == 1
        assert d['total_tokens'] == 150
        assert 'full_analysis' in d


class TestAnalysisSynthesizerInit:
    """Test AnalysisSynthesizer initialization."""

    def test_synthesizer_initializes(self):
        """Test that synthesizer initializes without error."""
        from app.analysis.synthesis import AnalysisSynthesizer

        synthesizer = AnalysisSynthesizer()
        assert synthesizer is not None

    def test_global_instance_exists(self):
        """Test that global instance is available."""
        from app.analysis.synthesis import analysis_synthesizer

        assert analysis_synthesizer is not None


class TestPrepareContentForAnalysis:
    """Test prepare_content_for_analysis method."""

    def test_prepare_content_with_company(self, app):
        """Test preparing content for a company."""
        from app.analysis.synthesis import AnalysisSynthesizer
        from app.models import Company
        from app import db

        with app.app_context():
            # Create test company
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
                industry='Technology',
            )
            db.session.add(company)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            assert context['company_name'] == 'Test Company'
            assert context['website_url'] == 'https://test.com'
            assert context['industry'] == 'Technology'

    def test_prepare_content_not_found(self, app):
        """Test prepare_content raises error for missing company."""
        from app.analysis.synthesis import AnalysisSynthesizer

        with app.app_context():
            synthesizer = AnalysisSynthesizer()

            with pytest.raises(ValueError) as exc_info:
                synthesizer.prepare_content_for_analysis('non-existent-id')

            assert 'not found' in str(exc_info.value)

    def test_prepare_content_with_pages_and_entities(self, app):
        """Test preparing content includes pages and entities."""
        from app.analysis.synthesis import AnalysisSynthesizer
        from app.models import Company, Page, Entity
        from app.models.enums import PageType, EntityType
        from app import db

        with app.app_context():
            # Create company with pages and entities
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.flush()

            # Add a page
            page = Page(
                company_id=company.id,
                url='https://test.com/about',
                page_type=PageType.ABOUT,
                extracted_text='About us content here',
            )
            db.session.add(page)

            # Add an entity
            entity = Entity(
                company_id=company.id,
                entity_type=EntityType.PERSON,
                entity_value='John Smith',
            )
            db.session.add(entity)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            context = synthesizer.prepare_content_for_analysis(company.id)

            assert 'About us content' in context['content']
            assert 'John Smith' in context['people_entities']


class TestAnalyzeSection:
    """Test analyze_section method."""

    @patch('app.services.token_tracker.token_tracker')
    @patch('app.services.anthropic_service.anthropic_service')
    def test_analyze_section_success(self, mock_anthropic, mock_tracker, app):
        """Test successful section analysis."""
        from app.analysis.synthesis import AnalysisSynthesizer, SectionResult
        from app.services.anthropic_service import ClaudeResponse

        # Mock the API response
        mock_anthropic.call.return_value = ClaudeResponse(
            content='Analysis result\n\nSOURCES:\nhttps://example.com',
            input_tokens=500,
            output_tokens=250,
            model='claude-sonnet-4-20250514',
        )

        with app.app_context():
            synthesizer = AnalysisSynthesizer()
            context = {
                'company_name': 'Test Co',
                'website_url': 'https://test.com',
                'industry': 'Tech',
                'content': 'Page content',
                'entities': 'Entity list',
            }

            result = synthesizer.analyze_section(
                company_id='test-id',
                section_id='company_overview',
                context=context,
            )

            assert result.success is True
            assert 'Analysis result' in result.content
            assert result.input_tokens == 500
            assert result.output_tokens == 250

    @patch('app.services.anthropic_service.anthropic_service')
    def test_analyze_section_api_error(self, mock_anthropic, app):
        """Test section analysis handles API errors."""
        from app.analysis.synthesis import AnalysisSynthesizer
        from app.services.anthropic_service import AnthropicServiceError

        mock_anthropic.call.side_effect = AnthropicServiceError("API failed")

        with app.app_context():
            synthesizer = AnalysisSynthesizer()
            context = {
                'company_name': 'Test Co',
                'website_url': 'https://test.com',
                'industry': 'Tech',
            }

            result = synthesizer.analyze_section(
                company_id='test-id',
                section_id='company_overview',
                context=context,
            )

            assert result.success is False
            assert result.error is not None

    def test_analyze_section_unknown_section(self, app):
        """Test analyze_section handles unknown section."""
        from app.analysis.synthesis import AnalysisSynthesizer

        with app.app_context():
            synthesizer = AnalysisSynthesizer()

            result = synthesizer.analyze_section(
                company_id='test-id',
                section_id='unknown_section',
                context={},
            )

            assert result.success is False
            assert 'Unknown section' in result.error


class TestRunFullAnalysis:
    """Test run_full_analysis method."""

    @patch('app.analysis.synthesis.AnalysisSynthesizer.analyze_section')
    def test_run_full_analysis_success(self, mock_analyze, app):
        """Test running full analysis."""
        from app.analysis.synthesis import AnalysisSynthesizer, SectionResult
        from app.models import Company
        from app import db

        # Mock successful section analysis
        mock_analyze.return_value = SectionResult(
            section_id='test',
            content='Analysis content',
            input_tokens=100,
            output_tokens=50,
        )

        with app.app_context():
            # Create test company
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            result = synthesizer.run_full_analysis(company.id)

            # Should have called analyze_section for each section
            assert mock_analyze.call_count >= 8  # At least 8 sections

            # Result should have sections
            assert len(result.sections) > 0

    @patch('app.analysis.synthesis.AnalysisSynthesizer.analyze_section')
    def test_run_full_analysis_with_progress_callback(self, mock_analyze, app):
        """Test that progress callback is called."""
        from app.analysis.synthesis import AnalysisSynthesizer, SectionResult
        from app.models import Company
        from app import db

        mock_analyze.return_value = SectionResult(
            section_id='test',
            content='Content',
            input_tokens=50,
            output_tokens=25,
        )

        callback_calls = []

        def progress_callback(section_id, completed, total):
            callback_calls.append((section_id, completed, total))

        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            synthesizer.run_full_analysis(
                company.id,
                progress_callback=progress_callback,
            )

            # Callback should have been called
            assert len(callback_calls) > 0

    @patch('app.analysis.synthesis.AnalysisSynthesizer.analyze_section')
    def test_run_full_analysis_stores_to_database(self, mock_analyze, app):
        """Test that analysis is stored in database."""
        from app.analysis.synthesis import AnalysisSynthesizer, SectionResult
        from app.models import Company, Analysis
        from app import db

        mock_analyze.return_value = SectionResult(
            section_id='test',
            content='Analysis content for test',
            input_tokens=100,
            output_tokens=50,
        )

        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.commit()

            synthesizer = AnalysisSynthesizer()
            synthesizer.run_full_analysis(company.id)

            # Should have created an Analysis record
            analysis = Analysis.query.filter_by(company_id=company.id).first()
            assert analysis is not None
            assert analysis.version_number == 1


class TestResumeAnalysis:
    """Test resume_analysis method."""

    @patch('app.analysis.synthesis.AnalysisSynthesizer.run_full_analysis')
    def test_resume_analysis_with_remaining_sections(self, mock_run, app):
        """Test resuming analysis with remaining sections."""
        from app.analysis.synthesis import AnalysisSynthesizer, AnalysisResult
        from datetime import datetime, UTC

        mock_run.return_value = AnalysisResult(
            company_id='test-id',
            version_number=1,
            executive_summary='Summary',
            sections={},
            total_input_tokens=0,
            total_output_tokens=0,
            started_at=datetime.now(UTC),
        )

        with app.app_context():
            synthesizer = AnalysisSynthesizer()
            result = synthesizer.resume_analysis(
                company_id='test-id',
                completed_sections=['company_overview', 'business_model'],
            )

            # Should have called run_full_analysis
            mock_run.assert_called_once()


class TestSourceExtraction:
    """Test source URL extraction from responses."""

    @patch('app.services.token_tracker.token_tracker')
    @patch('app.services.anthropic_service.anthropic_service')
    def test_extracts_sources_from_response(self, mock_anthropic, mock_tracker, app):
        """Test that sources are extracted from response."""
        from app.analysis.synthesis import AnalysisSynthesizer
        from app.services.anthropic_service import ClaudeResponse

        mock_anthropic.call.return_value = ClaudeResponse(
            content="""Analysis content here.

SOURCES:
- https://example.com/page1
- https://example.com/page2
""",
            input_tokens=100,
            output_tokens=50,
            model='claude-sonnet-4-20250514',
        )

        with app.app_context():
            synthesizer = AnalysisSynthesizer()
            context = {
                'company_name': 'Test',
                'website_url': 'https://test.com',
                'industry': 'Tech',
            }

            result = synthesizer.analyze_section(
                company_id='test-id',
                section_id='company_overview',
                context=context,
            )

            assert len(result.sources) >= 1
            assert 'https://example.com/page1' in result.sources
