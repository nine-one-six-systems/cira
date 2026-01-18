"""Tests for the Content Analysis Prompts (Task 6.3)."""

import pytest


class TestAnalysisSectionDataclass:
    """Test AnalysisSection dataclass."""

    def test_analysis_section_creation(self):
        """Test creating an AnalysisSection."""
        from app.analysis.prompts import AnalysisSection

        section = AnalysisSection(
            id='test_section',
            name='Test Section',
            description='A test section',
            prompt_template='Analyze {content}',
            system_prompt='Be helpful',
            priority=5,
            required=True,
        )

        assert section.id == 'test_section'
        assert section.name == 'Test Section'
        assert section.priority == 5
        assert section.required is True


class TestAnalysisSectionsDefinitions:
    """Test ANALYSIS_SECTIONS definitions."""

    def test_all_sections_defined(self):
        """Test that all expected sections are defined."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        expected_sections = [
            'company_overview',
            'business_model',
            'team_leadership',
            'market_position',
            'technology',
            'key_insights',
            'red_flags',
            'executive_summary',
        ]

        for section_id in expected_sections:
            assert section_id in ANALYSIS_SECTIONS, f"Missing section: {section_id}"

    def test_sections_have_required_fields(self):
        """Test that all sections have required fields."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        for section_id, section in ANALYSIS_SECTIONS.items():
            assert section.id == section_id
            assert section.name, f"Section {section_id} missing name"
            assert section.description, f"Section {section_id} missing description"
            assert section.prompt_template, f"Section {section_id} missing prompt_template"
            assert section.system_prompt, f"Section {section_id} missing system_prompt"

    def test_executive_summary_is_required(self):
        """Test that executive_summary section is required."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        assert ANALYSIS_SECTIONS['executive_summary'].required is True

    def test_section_priorities_unique(self):
        """Test that section priorities are distinct."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        priorities = [s.priority for s in ANALYSIS_SECTIONS.values()]
        # Priorities should be unique (no duplicates)
        assert len(priorities) == len(set(priorities))


class TestGetAnalysisPrompt:
    """Test get_analysis_prompt function."""

    def test_get_analysis_prompt_valid_section(self):
        """Test getting prompt for valid section."""
        from app.analysis.prompts import get_analysis_prompt

        prompt, system = get_analysis_prompt(
            section_id='company_overview',
            text='Company content here',
            context={
                'company_name': 'Test Company',
                'website_url': 'https://test.com',
                'industry': 'Technology',
            }
        )

        assert 'Test Company' in prompt
        assert 'https://test.com' in prompt
        assert system is not None

    def test_get_analysis_prompt_invalid_section(self):
        """Test that invalid section raises error."""
        from app.analysis.prompts import get_analysis_prompt

        with pytest.raises(ValueError) as exc_info:
            get_analysis_prompt(
                section_id='invalid_section',
                text='Some text',
            )

        assert 'Unknown analysis section' in str(exc_info.value)

    def test_get_analysis_prompt_includes_entities(self):
        """Test that prompt includes entities when provided."""
        from app.analysis.prompts import get_analysis_prompt

        prompt, _ = get_analysis_prompt(
            section_id='company_overview',
            context={
                'company_name': 'Test Co',
                'website_url': 'https://test.com',
                'industry': 'Tech',
                'entities': 'John Smith (CEO)\nJane Doe (CTO)',
            }
        )

        assert 'John Smith' in prompt
        assert 'Jane Doe' in prompt

    def test_get_analysis_prompt_executive_summary(self):
        """Test executive summary prompt includes full analysis."""
        from app.analysis.prompts import get_analysis_prompt

        prompt, system = get_analysis_prompt(
            section_id='executive_summary',
            context={
                'company_name': 'Test Company',
                'website_url': 'https://test.com',
                'industry': 'Technology',
                'full_analysis': 'Previous analysis content here',
            }
        )

        assert 'Test Company' in prompt
        assert 'executive summary' in prompt.lower()


class TestGetSectionOrder:
    """Test get_section_order function."""

    def test_get_section_order_returns_list(self):
        """Test that get_section_order returns a list."""
        from app.analysis.prompts import get_section_order

        order = get_section_order()

        assert isinstance(order, list)
        assert len(order) > 0

    def test_executive_summary_is_last(self):
        """Test that executive_summary is last in order."""
        from app.analysis.prompts import get_section_order

        order = get_section_order()

        assert order[-1] == 'executive_summary'

    def test_section_order_contains_all_sections(self):
        """Test that order contains all sections."""
        from app.analysis.prompts import get_section_order, ANALYSIS_SECTIONS

        order = get_section_order()

        assert len(order) == len(ANALYSIS_SECTIONS)
        for section_id in ANALYSIS_SECTIONS:
            assert section_id in order


class TestGetRequiredSections:
    """Test get_required_sections function."""

    def test_get_required_sections_returns_list(self):
        """Test that get_required_sections returns a list."""
        from app.analysis.prompts import get_required_sections

        required = get_required_sections()

        assert isinstance(required, list)
        assert len(required) > 0

    def test_executive_summary_is_required(self):
        """Test that executive_summary is in required list."""
        from app.analysis.prompts import get_required_sections

        required = get_required_sections()

        assert 'executive_summary' in required


class TestPromptTemplates:
    """Test prompt template content."""

    def test_company_overview_prompt_structure(self):
        """Test company overview prompt has expected structure."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        template = ANALYSIS_SECTIONS['company_overview'].prompt_template

        assert '{company_name}' in template
        assert '{website_url}' in template
        assert '{content}' in template
        assert 'Founded' in template or 'founded' in template.lower()
        assert 'Headquarters' in template or 'headquarters' in template.lower()

    def test_business_model_prompt_structure(self):
        """Test business model prompt has expected structure."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        template = ANALYSIS_SECTIONS['business_model'].prompt_template

        assert '{company_name}' in template
        assert 'Business Model' in template or 'business model' in template.lower()
        assert 'Revenue' in template or 'revenue' in template.lower()

    def test_team_leadership_prompt_structure(self):
        """Test team leadership prompt has expected structure."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        template = ANALYSIS_SECTIONS['team_leadership'].prompt_template

        assert '{company_name}' in template
        assert '{people_entities}' in template
        assert 'Founders' in template or 'founders' in template.lower()
        assert 'Leadership' in template or 'leadership' in template.lower()

    def test_red_flags_prompt_structure(self):
        """Test red flags prompt has expected structure."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        template = ANALYSIS_SECTIONS['red_flags'].prompt_template

        assert '{company_name}' in template
        assert 'Inconsistencies' in template or 'inconsistencies' in template.lower()
        assert 'Missing' in template or 'missing' in template.lower()
        assert 'Concerns' in template or 'concerns' in template.lower()

    def test_executive_summary_prompt_structure(self):
        """Test executive summary prompt has expected structure."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        template = ANALYSIS_SECTIONS['executive_summary'].prompt_template

        assert '{company_name}' in template
        assert '{full_analysis}' in template
        assert 'paragraph' in template.lower()


class TestSystemPrompt:
    """Test system prompt content."""

    def test_base_system_prompt_content(self):
        """Test base system prompt has expected content."""
        from app.analysis.prompts import BASE_SYSTEM_PROMPT

        assert 'business analyst' in BASE_SYSTEM_PROMPT.lower()
        assert 'factual' in BASE_SYSTEM_PROMPT.lower() or 'accurate' in BASE_SYSTEM_PROMPT.lower()
        assert 'sources' in BASE_SYSTEM_PROMPT.lower() or 'cite' in BASE_SYSTEM_PROMPT.lower()

    def test_all_sections_have_system_prompt(self):
        """Test all sections have a system prompt."""
        from app.analysis.prompts import ANALYSIS_SECTIONS

        for section_id, section in ANALYSIS_SECTIONS.items():
            assert section.system_prompt, f"Section {section_id} missing system prompt"
            assert len(section.system_prompt) > 50, f"Section {section_id} system prompt too short"
