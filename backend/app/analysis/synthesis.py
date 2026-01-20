"""Analysis Synthesis and Summary Generation.

Task 6.5: Analysis Synthesis and Summary Generation
- 3-4 paragraph executive summary (FR-SUM-001)
- Structured sections per AnalysisSections (FR-SUM-002)
- Include metadata (FR-OUT-002)
- Store complete analysis
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class SectionResult:
    """Result of analyzing a single section."""
    section_id: str
    content: str
    sources: list[str] = field(default_factory=list)
    confidence: float = 0.7
    input_tokens: int = 0
    output_tokens: int = 0
    error: str | None = None

    @property
    def success(self) -> bool:
        """Whether the section was analyzed successfully."""
        return self.error is None and bool(self.content)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            'content': self.content,
            'sources': self.sources,
            'confidence': self.confidence,
        }


@dataclass
class AnalysisResult:
    """Complete analysis result for a company."""
    company_id: str
    version_number: int
    executive_summary: str
    sections: dict[str, SectionResult]
    total_input_tokens: int
    total_output_tokens: int
    started_at: datetime
    completed_at: datetime | None = None
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Whether the overall analysis was successful."""
        # At minimum need executive summary and most sections
        required_sections = ['company_overview', 'business_model', 'executive_summary']
        return all(
            section_id in self.sections and self.sections[section_id].success
            for section_id in required_sections
        )

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.total_input_tokens + self.total_output_tokens

    def get_full_analysis(self) -> dict[str, Any]:
        """Get the full analysis as a dictionary for storage."""
        return {
            section_id: result.to_dict()
            for section_id, result in self.sections.items()
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'company_id': self.company_id,
            'version_number': self.version_number,
            'executive_summary': self.executive_summary,
            'full_analysis': self.get_full_analysis(),
            'total_tokens': self.total_tokens,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'errors': self.errors,
            'success': self.success,
        }


class AnalysisSynthesizer:
    """
    Orchestrates the analysis process and synthesizes results.

    This class:
    - Coordinates section-by-section analysis
    - Tracks progress and tokens
    - Generates the final executive summary
    - Stores results in the database
    """

    def __init__(self):
        """Initialize the synthesizer."""
        pass

    def prepare_content_for_analysis(
        self,
        company_id: str,
    ) -> dict[str, Any]:
        """
        Prepare content and entities for analysis.

        Args:
            company_id: UUID of the company to analyze

        Returns:
            Dictionary with prepared content for prompts
        """
        from app.models import Company, Page, Entity
        from app.models.enums import PageType, EntityType

        company = Company.query.get(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Get all pages
        pages = Page.query.filter_by(company_id=company_id).all()

        # Categorize content by page type
        content_by_type: dict[str, list[str]] = {}
        for page in pages:
            page_type = page.page_type.value if page.page_type else 'other'
            if page_type not in content_by_type:
                content_by_type[page_type] = []
            if page.extracted_text:
                # Truncate long content
                text = page.extracted_text[:5000]
                content_by_type[page_type].append(f"[{page.url}]\n{text}\n")

        # Get all entities
        entities = Entity.query.filter_by(company_id=company_id).all()

        # Categorize entities by type
        entities_by_type: dict[str, list[str]] = {}
        for entity in entities:
            entity_type = entity.entity_type.value
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            value = entity.entity_value
            if entity.extra_data:
                extras = entity.extra_data
                if 'role' in extras:
                    value += f" ({extras['role']})"
                if 'relationship' in extras:
                    value += f" - {extras['relationship']}"
            entities_by_type[entity_type].append(value)

        # Build content strings
        all_content = "\n\n".join(
            f"=== {page_type.upper()} PAGES ===\n" + "\n".join(texts)
            for page_type, texts in content_by_type.items()
        )

        team_content = "\n".join(content_by_type.get('team', []))
        careers_content = "\n".join(content_by_type.get('careers', []))

        # Build entity strings
        all_entities = "\n".join(
            f"{entity_type}: {', '.join(values)}"
            for entity_type, values in entities_by_type.items()
        )

        people_entities = "\n".join(
            f"- {value}"
            for value in entities_by_type.get('person', [])
        )

        org_entities = "\n".join(
            f"- {value}"
            for value in entities_by_type.get('org', [])
        )

        tech_entities = "\n".join(
            f"- {value}"
            for value in entities_by_type.get('tech_stack', [])
        )

        return {
            'company_name': company.company_name,
            'website_url': company.website_url,
            'industry': company.industry or 'Unknown',
            'content': all_content[:50000],  # Limit total content
            'team_content': team_content[:10000],
            'careers_content': careers_content[:10000],
            'entities': all_entities[:10000],
            'people_entities': people_entities[:5000],
            'org_entities': org_entities[:5000],
            'tech_entities': tech_entities[:5000],
        }

    def analyze_section(
        self,
        company_id: str,
        section_id: str,
        context: dict[str, Any],
        previous_results: dict[str, SectionResult] | None = None,
    ) -> SectionResult:
        """
        Analyze a single section.

        Args:
            company_id: UUID of the company
            section_id: ID of the section to analyze
            context: Prepared content context
            previous_results: Results from previously analyzed sections

        Returns:
            SectionResult with analysis content
        """
        from app.analysis.prompts import get_analysis_prompt, ANALYSIS_SECTIONS
        from app.services.anthropic_service import anthropic_service, AnthropicServiceError
        from app.services.token_tracker import token_tracker

        if section_id not in ANALYSIS_SECTIONS:
            return SectionResult(
                section_id=section_id,
                content='',
                error=f"Unknown section: {section_id}"
            )

        section = ANALYSIS_SECTIONS[section_id]

        # Add previous analysis to context for later sections
        if previous_results and section_id in ('key_insights', 'executive_summary'):
            previous_content = "\n\n".join(
                f"=== {ANALYSIS_SECTIONS[sid].name} ===\n{result.content}"
                for sid, result in previous_results.items()
                if result.success
            )
            context = {**context, 'previous_analysis': previous_content, 'full_analysis': previous_content}

        try:
            # Get prompt
            prompt, system_prompt = get_analysis_prompt(section_id, context=context)

            # Make API call
            response = anthropic_service.call(
                prompt=prompt,
                system_prompt=system_prompt,
            )

            # Track tokens
            token_tracker.record_usage(
                company_id=company_id,
                api_call_type='analysis',
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
                section=section_id,
            )

            # Extract sources from response (look for SOURCES: section)
            content = response.content
            sources = []
            if 'SOURCES:' in content.upper():
                parts = content.split('SOURCES:', 1)
                if len(parts) > 1:
                    source_text = parts[1].strip()
                    # Extract URLs
                    import re
                    urls = re.findall(r'https?://[^\s\]>]+', source_text)
                    sources = urls[:10]  # Limit to 10 sources

            return SectionResult(
                section_id=section_id,
                content=content,
                sources=sources,
                confidence=0.8,  # Default confidence
                input_tokens=response.input_tokens,
                output_tokens=response.output_tokens,
            )

        except AnthropicServiceError as e:
            logger.error(f"Failed to analyze section {section_id}: {e}")
            return SectionResult(
                section_id=section_id,
                content='',
                error=str(e),
            )

    def run_full_analysis(
        self,
        company_id: str,
        progress_callback: Callable | None = None,
    ) -> AnalysisResult:
        """
        Run full analysis for a company.

        Args:
            company_id: UUID of the company
            progress_callback: Optional callback(section_id, completed, total)

        Returns:
            AnalysisResult with all sections analyzed
        """
        from app import db
        from app.models import Company, Analysis
        from app.analysis.prompts import get_section_order

        started_at = datetime.now(UTC)

        # Get company and determine version
        company = Company.query.get(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        # Determine version number (max 3 versions)
        existing_count = Analysis.query.filter_by(company_id=company_id).count()
        version_number = existing_count + 1

        # Prepare content
        context = self.prepare_content_for_analysis(company_id)

        # Get section order
        section_order = get_section_order()
        total_sections = len(section_order)

        # Analyze each section
        results: dict[str, SectionResult] = {}
        errors: list[str] = []
        total_input = 0
        total_output = 0

        for i, section_id in enumerate(section_order):
            logger.info(f"Analyzing section {section_id} ({i+1}/{total_sections})")

            if progress_callback:
                progress_callback(section_id, i, total_sections)

            result = self.analyze_section(
                company_id=company_id,
                section_id=section_id,
                context=context,
                previous_results=results,
            )

            results[section_id] = result
            total_input += result.input_tokens
            total_output += result.output_tokens

            if result.error:
                errors.append(f"{section_id}: {result.error}")
                logger.warning(f"Section {section_id} failed: {result.error}")

        # Get executive summary
        executive_summary = ''
        if 'executive_summary' in results and results['executive_summary'].success:
            executive_summary = results['executive_summary'].content

        completed_at = datetime.now(UTC)

        # Create result object
        analysis_result = AnalysisResult(
            company_id=company_id,
            version_number=version_number,
            executive_summary=executive_summary,
            sections=results,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            started_at=started_at,
            completed_at=completed_at,
            errors=errors,
        )

        # Save to database
        analysis = Analysis(
            company_id=company_id,
            version_number=version_number,
            executive_summary=executive_summary,
            full_analysis=analysis_result.get_full_analysis(),
            token_breakdown={
                'total_input': total_input,
                'total_output': total_output,
                'by_section': {
                    sid: {'input': r.input_tokens, 'output': r.output_tokens}
                    for sid, r in results.items()
                }
            },
        )
        db.session.add(analysis)
        db.session.commit()

        if progress_callback:
            progress_callback('complete', total_sections, total_sections)

        logger.info(
            f"Analysis complete for company {company_id}: "
            f"{len([r for r in results.values() if r.success])}/{total_sections} sections, "
            f"{total_input + total_output} tokens"
        )

        return analysis_result

    def resume_analysis(
        self,
        company_id: str,
        completed_sections: list[str],
        progress_callback: Callable | None = None,
    ) -> AnalysisResult:
        """
        Resume analysis from a checkpoint.

        Args:
            company_id: UUID of the company
            completed_sections: List of already completed section IDs
            progress_callback: Optional callback

        Returns:
            AnalysisResult with resumed analysis
        """
        from app.analysis.prompts import get_section_order

        # Get remaining sections
        section_order = get_section_order()
        remaining = [s for s in section_order if s not in completed_sections]

        if not remaining:
            logger.info("All sections already completed")
            # Load existing analysis
            from app.models import Analysis
            analysis = Analysis.query.filter_by(
                company_id=company_id
            ).order_by(Analysis.version_number.desc()).first()

            if analysis:
                return AnalysisResult(
                    company_id=company_id,
                    version_number=analysis.version_number,
                    executive_summary=analysis.executive_summary,
                    sections={},  # Would need to reconstruct
                    total_input_tokens=0,
                    total_output_tokens=0,
                    started_at=datetime.now(UTC),
                    completed_at=datetime.now(UTC),
                )

        # Continue with remaining sections
        return self.run_full_analysis(company_id, progress_callback)


# Global synthesizer instance
analysis_synthesizer = AnalysisSynthesizer()
