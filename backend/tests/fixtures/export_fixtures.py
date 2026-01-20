"""Export integration test fixtures.

Provides shared fixtures for export integration testing, including:
- COMPLETE_ANALYSIS_DATA: Full analysis sections matching 2-page template
- EXECUTIVE_SUMMARY_TEXT: Sample executive summary
- KEY_EXECUTIVES: Executive data for table rendering
- TOKEN_USAGE_RECORDS: Token usage simulation data
- CRAWLED_PAGES: Page data for source URLs
- Factory functions for creating test companies

Requirements coverage:
- EXP-01: Markdown export format
- EXP-02: Word/DOCX export format
- EXP-03: PDF export format
- EXP-04: JSON export format
- EXP-05: 2-page template structure
"""

from datetime import datetime, timezone
from typing import Any

from app import db
from app.models.company import Company, Analysis, Entity, Page, TokenUsage
from app.models.enums import (
    CompanyStatus,
    AnalysisMode,
    EntityType,
    PageType,
    ApiCallType,
)


# Complete analysis data matching 2-page template structure (EXP-05)
COMPLETE_ANALYSIS_DATA: dict[str, Any] = {
    "companyOverview": {
        "content": (
            "Acme Technologies is a leading enterprise software company founded in 2018 "
            "and headquartered in Austin, Texas. The company specializes in AI-powered "
            "business intelligence solutions for Fortune 500 companies. With over 200 "
            "employees and presence in 15 countries, Acme has established itself as a "
            "key player in the enterprise analytics market. The company has raised $50M "
            "in Series B funding and reports ARR of $25M with 150% year-over-year growth."
        ),
        "sources": [
            "https://acme-tech.com/about",
            "https://acme-tech.com/company",
        ],
        "confidence": 0.92,
    },
    "businessModel": {
        "content": (
            "Acme operates on a B2B SaaS subscription model with three pricing tiers:\n"
            "- **Starter**: $500/month for small teams (up to 10 users)\n"
            "- **Professional**: $2,000/month for mid-market (up to 50 users)\n"
            "- **Enterprise**: Custom pricing for large organizations\n\n"
            "Key products include:\n"
            "1. AcmeInsight - Real-time analytics dashboard\n"
            "2. AcmePredict - ML-powered forecasting engine\n"
            "3. AcmeConnect - Data integration platform\n\n"
            "Revenue streams: 85% subscription, 10% professional services, 5% training."
        ),
        "sources": [
            "https://acme-tech.com/products",
            "https://acme-tech.com/pricing",
        ],
        "confidence": 0.88,
    },
    "teamLeadership": {
        "content": (
            "Acme's leadership team brings extensive experience from top tech companies. "
            "The executive team has a combined 75+ years of industry experience, with "
            "backgrounds spanning Google, Microsoft, Salesforce, and Oracle. The company "
            "has grown from 15 to 200+ employees in the past three years, with strong "
            "retention rates above industry average. Engineering team comprises 60% of "
            "total headcount, emphasizing the company's product-first approach."
        ),
        "sources": [
            "https://acme-tech.com/team",
            "https://acme-tech.com/about",
        ],
        "confidence": 0.85,
    },
    "marketPosition": {
        "content": (
            "Acme competes in the $15B business intelligence market, targeting the "
            "enterprise segment. Key competitors include Tableau, Looker (Google), "
            "and Power BI (Microsoft). Acme differentiates through AI-native architecture "
            "and superior data integration capabilities.\n\n"
            "Market share: Estimated 2% of enterprise BI market\n"
            "Growth trajectory: 150% YoY, outpacing market growth of 12%\n"
            "Target customers: Fortune 500, financial services, healthcare"
        ),
        "sources": [
            "https://acme-tech.com/about",
            "https://acme-tech.com/customers",
        ],
        "confidence": 0.78,
    },
    "technology": {
        "content": (
            "Acme's tech stack reflects modern cloud-native architecture:\n\n"
            "**Backend**: Python (FastAPI), Go microservices\n"
            "**Frontend**: React, TypeScript, TailwindCSS\n"
            "**Data**: PostgreSQL, ClickHouse, Apache Kafka\n"
            "**ML/AI**: PyTorch, Hugging Face Transformers, custom LLM integrations\n"
            "**Infrastructure**: AWS (primary), Kubernetes, Terraform\n\n"
            "The company invests heavily in R&D, with 30% of engineering focused on "
            "AI/ML capabilities. Recent technical achievements include sub-100ms query "
            "performance on billion-row datasets."
        ),
        "sources": [
            "https://acme-tech.com/careers",
            "https://acme-tech.com/blog/tech-stack",
        ],
        "confidence": 0.82,
    },
    "keyInsights": {
        "content": (
            "- **Strong product-market fit**: 95% customer retention rate indicates "
            "solving real enterprise pain points\n"
            "- **Rapid scaling**: 150% YoY growth with efficient capital deployment\n"
            "- **Technical moat**: AI-native architecture provides competitive advantage\n"
            "- **Enterprise credibility**: Fortune 500 customer base validates market position\n"
            "- **Experienced team**: Leadership from top tech companies reduces execution risk\n"
            "- **Expansion opportunity**: Only 15% international revenue, significant upside"
        ),
        "sources": [],
        "confidence": 0.85,
    },
    "redFlags": {
        "content": (
            "- **Competitive pressure**: Major players (Microsoft, Google) aggressively "
            "expanding in BI space with deep pockets\n"
            "- **Customer concentration**: Top 5 customers represent 40% of revenue\n"
            "- **Burn rate**: Currently unprofitable, 18-month runway at current spend\n"
            "- **Key person risk**: CTO departure could impact product roadmap\n"
            "- **Regulatory**: Healthcare customers require HIPAA compliance investment"
        ),
        "sources": [],
        "confidence": 0.80,
    },
}


# Executive summary text (2-3 paragraphs)
EXECUTIVE_SUMMARY_TEXT: str = (
    "Acme Technologies represents a compelling opportunity in the enterprise business "
    "intelligence market. The company has demonstrated strong product-market fit with "
    "a 95% customer retention rate and 150% year-over-year revenue growth, reaching "
    "$25M ARR. Their AI-native platform differentiates from legacy BI tools by providing "
    "real-time insights with sub-100ms query performance on massive datasets.\n\n"
    "The leadership team brings credibility with backgrounds from Google, Microsoft, and "
    "Salesforce. With $50M in Series B funding and a clear path to profitability, Acme "
    "is well-positioned to capture share in the $15B BI market. Key risks include "
    "competitive pressure from well-funded incumbents and customer concentration.\n\n"
    "Overall assessment: Strong growth-stage company with validated technology and "
    "clear market opportunity. Recommend continued monitoring for expansion progress "
    "and competitive positioning."
)


# Key executives data for table rendering (EXP-05)
KEY_EXECUTIVES: list[dict[str, str]] = [
    {
        "name": "Sarah Chen",
        "role": "CEO & Co-founder",
        "source_url": "https://acme-tech.com/team",
    },
    {
        "name": "Michael Torres",
        "role": "CTO & Co-founder",
        "source_url": "https://acme-tech.com/team",
    },
    {
        "name": "Jennifer Williams",
        "role": "CFO",
        "source_url": "https://acme-tech.com/team",
    },
    {
        "name": "David Park",
        "role": "VP Engineering",
        "source_url": "https://acme-tech.com/team",
    },
    {
        "name": "Amanda Foster",
        "role": "Head of Product",
        "source_url": "https://acme-tech.com/team",
    },
]


# Token usage records for testing (realistic 10K-20K total)
TOKEN_USAGE_RECORDS: list[dict[str, Any]] = [
    {
        "api_call_type": ApiCallType.EXTRACTION,
        "section": "company_overview",
        "input_tokens": 4500,
        "output_tokens": 1200,
    },
    {
        "api_call_type": ApiCallType.EXTRACTION,
        "section": "business_model",
        "input_tokens": 3800,
        "output_tokens": 1100,
    },
    {
        "api_call_type": ApiCallType.ANALYSIS,
        "section": "market_analysis",
        "input_tokens": 5200,
        "output_tokens": 1800,
    },
    {
        "api_call_type": ApiCallType.SUMMARIZATION,
        "section": "executive_summary",
        "input_tokens": 2500,
        "output_tokens": 800,
    },
]


# Crawled pages data for source URLs
CRAWLED_PAGES: list[dict[str, Any]] = [
    {
        "url": "https://acme-tech.com/",
        "page_type": PageType.OTHER,
        "content_length": 15000,
    },
    {
        "url": "https://acme-tech.com/about",
        "page_type": PageType.ABOUT,
        "content_length": 8500,
    },
    {
        "url": "https://acme-tech.com/team",
        "page_type": PageType.TEAM,
        "content_length": 12000,
    },
    {
        "url": "https://acme-tech.com/products",
        "page_type": PageType.PRODUCT,
        "content_length": 18000,
    },
    {
        "url": "https://acme-tech.com/pricing",
        "page_type": PageType.PRICING,
        "content_length": 5500,
    },
    {
        "url": "https://acme-tech.com/careers",
        "page_type": PageType.CAREERS,
        "content_length": 22000,
    },
    {
        "url": "https://acme-tech.com/contact",
        "page_type": PageType.CONTACT,
        "content_length": 3500,
    },
    {
        "url": "https://acme-tech.com/blog",
        "page_type": PageType.BLOG,
        "content_length": 45000,
    },
]


def create_complete_export_company(db_session) -> Company:
    """
    Create a complete company with all related data for export testing.

    Creates a Company with:
    - status=COMPLETED
    - Full Analysis with all sections from COMPLETE_ANALYSIS_DATA
    - Entity records for executives from KEY_EXECUTIVES
    - Page records from CRAWLED_PAGES
    - TokenUsage records from TOKEN_USAGE_RECORDS

    Args:
        db_session: SQLAlchemy database session

    Returns:
        Company instance with all relationships loaded

    Requirements: EXP-01 through EXP-05 (complete data for all format tests)
    """
    # Create company with realistic metadata
    company = Company(
        company_name="Acme Technologies",
        website_url="https://acme-tech.com",
        industry="Enterprise Software",
        analysis_mode=AnalysisMode.THOROUGH,
        status=CompanyStatus.COMPLETED,
        total_tokens_used=20900,  # Sum of token records
        estimated_cost=0.1156,  # Calculated from token usage
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(company)
    db_session.flush()

    # Create analysis with complete data
    analysis = Analysis(
        company_id=company.id,
        version_number=1,
        executive_summary=EXECUTIVE_SUMMARY_TEXT,
        full_analysis=COMPLETE_ANALYSIS_DATA,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(analysis)

    # Create entity records for executives
    for exec_data in KEY_EXECUTIVES:
        entity = Entity(
            company_id=company.id,
            entity_type=EntityType.PERSON,
            entity_value=exec_data["name"],
            context_snippet=f"{exec_data['name']} serves as {exec_data['role']}",
            source_url=exec_data["source_url"],
            confidence_score=0.92,
            extra_data={"role": exec_data["role"]},
        )
        db_session.add(entity)

    # Add additional entities (products, locations)
    additional_entities = [
        Entity(
            company_id=company.id,
            entity_type=EntityType.PRODUCT,
            entity_value="AcmeInsight",
            context_snippet="AcmeInsight provides real-time analytics dashboard",
            source_url="https://acme-tech.com/products",
            confidence_score=0.95,
        ),
        Entity(
            company_id=company.id,
            entity_type=EntityType.PRODUCT,
            entity_value="AcmePredict",
            context_snippet="AcmePredict is our ML-powered forecasting engine",
            source_url="https://acme-tech.com/products",
            confidence_score=0.94,
        ),
        Entity(
            company_id=company.id,
            entity_type=EntityType.LOCATION,
            entity_value="Austin, Texas",
            context_snippet="Headquartered in Austin, Texas",
            source_url="https://acme-tech.com/about",
            confidence_score=0.98,
        ),
        Entity(
            company_id=company.id,
            entity_type=EntityType.MONEY,
            entity_value="$50M",
            context_snippet="The company has raised $50M in Series B funding",
            source_url="https://acme-tech.com/about",
            confidence_score=0.96,
        ),
    ]
    for entity in additional_entities:
        db_session.add(entity)

    # Create page records
    for page_data in CRAWLED_PAGES:
        page = Page(
            company_id=company.id,
            url=page_data["url"],
            page_type=page_data["page_type"],
            is_external=False,
            crawled_at=datetime.now(timezone.utc),
        )
        db_session.add(page)

    # Create token usage records
    for usage_data in TOKEN_USAGE_RECORDS:
        token_usage = TokenUsage(
            company_id=company.id,
            api_call_type=usage_data["api_call_type"],
            section=usage_data["section"],
            input_tokens=usage_data["input_tokens"],
            output_tokens=usage_data["output_tokens"],
            timestamp=datetime.now(timezone.utc),
        )
        db_session.add(token_usage)

    db_session.commit()

    # Refresh to load relationships
    db_session.refresh(company)
    return company


def create_minimal_export_company(db_session) -> Company:
    """
    Create a minimal company with sparse data for export testing.

    Creates a Company with:
    - status=COMPLETED
    - Analysis with executive_summary only (no full_analysis sections)
    - No entities
    - No pages
    - Minimal token usage (single record)

    Tests graceful handling of sparse/missing data in exports.

    Args:
        db_session: SQLAlchemy database session

    Returns:
        Company instance with minimal data

    Requirements: EXP-01 through EXP-04 (graceful degradation tests)
    """
    # Create company with minimal data
    company = Company(
        company_name="Minimal Corp",
        website_url="https://minimal-corp.com",
        industry=None,  # No industry
        analysis_mode=AnalysisMode.QUICK,
        status=CompanyStatus.COMPLETED,
        total_tokens_used=500,
        estimated_cost=0.003,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(company)
    db_session.flush()

    # Create analysis with only executive summary
    analysis = Analysis(
        company_id=company.id,
        version_number=1,
        executive_summary="Minimal Corp is a small startup with limited public information.",
        full_analysis={},  # Empty sections - tests placeholder text
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(analysis)

    # Single minimal token usage record
    token_usage = TokenUsage(
        company_id=company.id,
        api_call_type=ApiCallType.SUMMARIZATION,
        section="summary",
        input_tokens=400,
        output_tokens=100,
        timestamp=datetime.now(timezone.utc),
    )
    db_session.add(token_usage)

    db_session.commit()

    # Refresh to load relationships
    db_session.refresh(company)
    return company


def calculate_total_tokens() -> dict[str, int]:
    """
    Calculate total tokens from TOKEN_USAGE_RECORDS.

    Returns:
        Dictionary with total, input, and output token counts
    """
    total_input = sum(r["input_tokens"] for r in TOKEN_USAGE_RECORDS)
    total_output = sum(r["output_tokens"] for r in TOKEN_USAGE_RECORDS)
    return {
        "total": total_input + total_output,
        "input": total_input,
        "output": total_output,
    }
