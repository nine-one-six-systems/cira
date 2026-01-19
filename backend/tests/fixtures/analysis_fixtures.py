"""Analysis integration test fixtures.

This module provides mock Claude responses and shared fixtures for testing
the AI analysis pipeline.

Requirements covered: ANA-01 to ANA-10
"""

import pytest
from dataclasses import dataclass, field
from typing import Any, Callable


# ============================================================================
# SECTION ORDER - Expected order of analysis sections
# ============================================================================

SECTION_ORDER = [
    'company_overview',
    'business_model',
    'team_leadership',
    'market_position',
    'technology',
    'key_insights',
    'red_flags',
    'executive_summary',
]


# ============================================================================
# MOCK CRAWLED CONTENT - Simulates content prepared for analysis
# ============================================================================

MOCK_CRAWLED_CONTENT = {
    'about': """
About NovaTech Industries

NovaTech Industries is a pioneering AI-powered manufacturing optimization company
founded in 2019 by Dr. Marcus Chen, CEO, and Dr. Priya Patel, CTO. Headquartered
in Austin, Texas, we have grown to over 150 employees across offices in Austin,
Chicago, and London.

Our mission is to revolutionize manufacturing through intelligent automation,
reducing waste and improving efficiency by 40% on average for our clients. We
serve mid-market and enterprise manufacturers in automotive, aerospace, and
consumer electronics sectors.

Since launching, NovaTech has raised $45 million in Series A funding from
Benchmark Capital and Kleiner Perkins. We are trusted by over 200 manufacturing
facilities worldwide, processing over 1 billion data points daily.

NovaTech was named one of Fast Company's Most Innovative Companies in 2023 and
has been recognized by Gartner as an emerging leader in the industrial AI space.
Our technology has helped clients save over $500 million in operational costs
collectively.

For more information, contact us at info@novatech.io or call (512) 555-3456.
Visit our headquarters at 500 Congress Avenue, Suite 2400, Austin, TX 78701.
    """,

    'team': """
Leadership Team

Dr. Marcus Chen - Chief Executive Officer and Co-Founder
Dr. Marcus Chen leads NovaTech with 15 years of experience in AI and manufacturing.
Before founding NovaTech, Marcus was VP of AI Research at Siemens. He holds a Ph.D.
in Computer Science from MIT with a focus on industrial machine learning systems.

Dr. Priya Patel - Chief Technology Officer and Co-Founder
Dr. Priya Patel drives our technical vision and R&D efforts. Priya was previously
a Principal Scientist at Google DeepMind working on reinforcement learning for
robotics. She holds a Ph.D. in Robotics from Carnegie Mellon University.

James Morrison - Chief Financial Officer
James Morrison oversees financial operations and investor relations. James brings
20 years of experience from roles at Goldman Sachs and Stripe. He has guided
multiple companies through successful fundraising rounds totaling over $2 billion.

Dr. Aisha Williams - VP of Engineering
Dr. Aisha Williams manages our engineering teams across all products. Previously
led platform engineering at Tesla's Autopilot division. Holds a Ph.D. in Electrical
Engineering from Stanford University.

Michael Torres - VP of Sales
Michael Torres leads global sales and partnerships. Michael joined from Rockwell
Automation where he consistently exceeded quotas by 150%. He has 18 years of
enterprise sales experience in industrial technology.

Sarah Kim - VP of Product
Sarah Kim oversees product strategy and roadmap. Previously product lead at
PTC ThingWorx. Known for customer-centric product development methodology.
    """,

    'products': """
Products and Solutions

OptiFlow Platform
OptiFlow is our flagship AI-powered manufacturing optimization platform. It
uses computer vision and machine learning to monitor production lines in real-time,
detecting defects with 99.7% accuracy and predicting equipment failures 48 hours
in advance. OptiFlow integrates with major ERP systems including SAP and Oracle.

Pricing: Starting at $25,000/month for enterprise deployments.

SupplyAI
SupplyAI provides intelligent supply chain optimization. Using advanced
forecasting algorithms, it reduces inventory costs by 25% while maintaining
99.5% order fulfillment rates. Seamlessly connects to existing supply chain
management systems.

QualityGuard
QualityGuard automates quality control through AI-powered visual inspection.
Processes 10,000+ images per minute with sub-pixel accuracy. Reduces manual
inspection costs by 60% while improving detection rates.

EdgeAnalytics
EdgeAnalytics enables real-time analytics at the manufacturing edge. Low-latency
processing for time-critical decisions. Compatible with all major industrial
IoT platforms and sensor systems.

Professional Services
Implementation, integration, and training services to ensure successful
deployment. Average ROI achieved within 6 months of deployment.
    """,

    'news': """
Recent News and Press

Q4 2023 - NovaTech Announces $45M Series A Funding
Austin-based NovaTech Industries announced the closing of a $45 million Series A
round led by Benchmark Capital with participation from Kleiner Perkins. The funds
will accelerate product development and international expansion.

Q3 2023 - Partnership with Toyota North America
NovaTech entered a strategic partnership with Toyota North America to deploy
OptiFlow across 12 manufacturing facilities in the US and Mexico, representing
the company's largest enterprise deal to date.

Q2 2023 - Named Fast Company's Most Innovative Company
NovaTech was recognized as one of Fast Company's Most Innovative Companies in
the manufacturing category, citing breakthrough AI applications in production
optimization.

Q1 2023 - Launch of EdgeAnalytics
NovaTech launched EdgeAnalytics, enabling real-time AI processing directly on
manufacturing equipment, reducing latency from seconds to milliseconds for
critical quality decisions.
    """,
}


# ============================================================================
# MOCK ENTITIES - Simulates extracted entities for analysis context
# ============================================================================

MOCK_ENTITIES = [
    # PERSON entities with roles
    {'type': 'person', 'value': 'Dr. Marcus Chen', 'extra_data': {'role': 'CEO and Co-Founder'}, 'confidence': 0.95},
    {'type': 'person', 'value': 'Dr. Priya Patel', 'extra_data': {'role': 'CTO and Co-Founder'}, 'confidence': 0.95},
    {'type': 'person', 'value': 'James Morrison', 'extra_data': {'role': 'CFO'}, 'confidence': 0.90},
    {'type': 'person', 'value': 'Dr. Aisha Williams', 'extra_data': {'role': 'VP of Engineering'}, 'confidence': 0.90},

    # ORG entities (investors, partners)
    {'type': 'org', 'value': 'Benchmark Capital', 'extra_data': {'relationship': 'investor'}, 'confidence': 0.92},
    {'type': 'org', 'value': 'Kleiner Perkins', 'extra_data': {'relationship': 'investor'}, 'confidence': 0.92},
    {'type': 'org', 'value': 'Toyota North America', 'extra_data': {'relationship': 'partner'}, 'confidence': 0.88},

    # GPE entities (locations)
    {'type': 'gpe', 'value': 'Austin, Texas', 'extra_data': {'type': 'headquarters'}, 'confidence': 0.95},
    {'type': 'gpe', 'value': 'London', 'extra_data': {'type': 'office'}, 'confidence': 0.85},

    # PRODUCT entities
    {'type': 'product', 'value': 'OptiFlow Platform', 'extra_data': {'category': 'flagship'}, 'confidence': 0.93},
    {'type': 'product', 'value': 'SupplyAI', 'extra_data': {'category': 'supply chain'}, 'confidence': 0.90},
    {'type': 'product', 'value': 'QualityGuard', 'extra_data': {'category': 'quality control'}, 'confidence': 0.90},
    {'type': 'product', 'value': 'EdgeAnalytics', 'extra_data': {'category': 'edge computing'}, 'confidence': 0.88},

    # MONEY entity
    {'type': 'money', 'value': '$45 million', 'extra_data': {'context': 'Series A funding'}, 'confidence': 0.94},
]


# ============================================================================
# MOCK CLAUDE RESPONSES - Realistic analysis section content
# ============================================================================

MOCK_SECTION_CONTENT = {
    'executive_summary': """
NovaTech Industries is an AI-powered manufacturing optimization company that helps manufacturers reduce waste and improve efficiency through intelligent automation. Founded in 2019 by Dr. Marcus Chen (CEO) and Dr. Priya Patel (CTO), the company has grown to 150+ employees and serves over 200 manufacturing facilities worldwide.

The company operates a B2B SaaS model, offering its flagship OptiFlow platform starting at $25,000/month for enterprise deployments. Key products include OptiFlow for production line optimization, SupplyAI for supply chain management, QualityGuard for automated quality control, and EdgeAnalytics for real-time edge computing capabilities.

NovaTech raised $45 million in Series A funding from Benchmark Capital and Kleiner Perkins, indicating strong investor confidence. Notable partnerships include Toyota North America, representing significant enterprise traction. The company was recognized by Fast Company as one of the Most Innovative Companies and by Gartner as an emerging leader in industrial AI.

Key strengths include strong technical leadership with deep AI/ML expertise, proven product-market fit with $500M+ in documented client savings, and strategic positioning in the growing industrial AI market. No significant red flags identified; however, limited information on financial metrics and competitive differentiation could be areas for further investigation.
    """,

    'company_overview': """
Founded: 2019
Headquarters: Austin, Texas
Company Size: 150+ employees
Industry: Industrial AI / Manufacturing Technology

Description: NovaTech Industries is an AI-powered manufacturing optimization company that develops software solutions to help manufacturers reduce waste, improve efficiency, and predict equipment failures. The company serves mid-market and enterprise clients in automotive, aerospace, and consumer electronics sectors.

SOURCES: https://novatech.io/about
    """,

    'business_model': """
**Business Model Type**: B2B SaaS (Enterprise)

**Revenue Model**:
Subscription-based pricing with enterprise deployments. The flagship OptiFlow platform starts at $25,000/month, suggesting annual contract values of $300K+ for core product.
Confidence: High

**Key Products/Services**:
1. OptiFlow Platform - Flagship AI-powered production optimization (starting $25K/month)
2. SupplyAI - Supply chain optimization and forecasting
3. QualityGuard - Automated visual inspection and quality control
4. EdgeAnalytics - Real-time edge computing for manufacturing
5. Professional Services - Implementation, integration, and training

**Value Proposition**:
- 40% average efficiency improvement for clients
- 99.7% defect detection accuracy
- 48-hour advance prediction of equipment failures
- $500M+ collective savings for clients
- Average ROI within 6 months

Confidence: High

SOURCES: https://novatech.io/products, https://novatech.io/about
    """,

    'team_leadership': """
| Name | Title | Background | Source |
|------|-------|------------|--------|
| Dr. Marcus Chen | CEO & Co-Founder | 15 years AI/manufacturing, VP AI Research at Siemens, Ph.D. MIT | Team page |
| Dr. Priya Patel | CTO & Co-Founder | Principal Scientist at Google DeepMind, Ph.D. CMU Robotics | Team page |
| James Morrison | CFO | 20 years at Goldman Sachs and Stripe, $2B+ fundraising experience | Team page |
| Dr. Aisha Williams | VP Engineering | Platform engineering lead at Tesla Autopilot, Ph.D. Stanford EE | Team page |
| Michael Torres | VP Sales | 18 years enterprise sales, previously Rockwell Automation | Team page |
| Sarah Kim | VP Product | Former product lead at PTC ThingWorx | Team page |

**Team Composition Observations**:
- Strong technical leadership with Ph.D.-level expertise in AI, robotics, and engineering
- Balanced C-suite with technical founders and experienced business operators
- Enterprise sales experience aligns with target market
- Gap: No dedicated Chief Marketing Officer or Chief People Officer mentioned

Confidence: High
    """,

    'market_position': """
**Target Market**:
- Primary: Mid-market and enterprise manufacturers
- Industries: Automotive, aerospace, consumer electronics
- Geography: Global (US, UK offices mentioned)
Confidence: High

**Geographic Focus**:
- Headquarters: Austin, Texas
- Offices: Chicago, London
- Clients: 200+ facilities worldwide
Confidence: High

**Competitive Landscape**:
Competitors not explicitly mentioned. Based on product offerings, likely competes with:
- Uptake (predictive maintenance)
- Sight Machine (manufacturing analytics)
- Rockwell Automation (industrial automation)
- Siemens MindSphere (industrial IoT)
Note: Competitive positioning not explicitly stated in available content.

**Key Differentiators**:
- AI-native approach (vs. bolt-on AI from traditional automation vendors)
- Strong accuracy metrics (99.7% defect detection)
- Proven ROI claims ($500M+ client savings)
- Edge computing capabilities (EdgeAnalytics)
Confidence: Medium

**Market Position**:
Emerging leader in industrial AI space per Gartner recognition. Strong traction with 200+ facilities but smaller than established industrial automation incumbents.
Confidence: Medium

SOURCES: https://novatech.io/about, https://novatech.io/products
    """,

    'technology': """
**Technology Stack**:
Based on careers page and product descriptions, the company uses:

Confirmed:
- Computer vision and machine learning (core product capability)
- Edge computing (EdgeAnalytics product)
- Industrial IoT integration
- ERP integrations (SAP, Oracle mentioned)
Confidence: High

**Infrastructure**:
- Cloud platform (specific provider not mentioned)
- Edge deployment capabilities
- Processes 1 billion+ data points daily
Confidence: Medium

**Integrations**:
- SAP ERP
- Oracle ERP
- Major industrial IoT platforms
- Supply chain management systems
Confidence: High

**Scale Indicators**:
- 200+ manufacturing facilities served
- 1 billion data points processed daily
- 10,000+ images per minute (QualityGuard)
- Sub-pixel accuracy in visual inspection
Confidence: High

**Security/Compliance**:
Not explicitly mentioned. Given enterprise manufacturing clients, likely has relevant certifications but not confirmed.
Confidence: Low

Note: Specific cloud providers, programming languages, and database technologies not mentioned in available content.
    """,

    'key_insights': """
**Strengths**:
1. Technical Founder Advantage - Both founders have Ph.D.-level expertise and industry experience at Siemens and Google DeepMind
   Confidence: High

2. Proven Product-Market Fit - 200+ facilities, $500M+ documented client savings, major enterprise deals (Toyota)
   Confidence: High

3. Strong Investor Backing - $45M Series A from tier-1 VCs (Benchmark, Kleiner Perkins) validates market opportunity
   Confidence: High

4. Industry Recognition - Fast Company Most Innovative, Gartner emerging leader provides third-party validation
   Confidence: High

5. Comprehensive Product Suite - Four complementary products covering optimization, supply chain, quality, and edge computing
   Confidence: High

**Growth Indicators**:
- 150+ employees, growing from founding to present
- $45M funding for accelerated expansion
- International presence (US, UK)
- Major enterprise partnership (Toyota North America)
Confidence: High

**Strategic Direction**:
- International expansion with Series A funding
- Deepening edge computing capabilities
- Enterprise market focus with professional services
Confidence: Medium

**Opportunities**:
- Adjacent industries (pharma, food & beverage manufacturing)
- Geographic expansion to APAC
- Vertical-specific solutions
- M&A for technology/talent acquisition given funding runway
Confidence: Medium
    """,

    'red_flags': """
**Inconsistencies**: None identified

**Missing Information**:
1. Revenue/ARR metrics - No financial performance disclosed
   Severity: Low (typical for private company)

2. Customer concentration - Unclear if revenue is concentrated among few large clients
   Severity: Low

3. Competitive differentiation - Limited explicit comparison to alternatives
   Severity: Low

**Vague Claims**: None significant - metrics provided are specific and verifiable

**Concerns**:
1. Enterprise sales cycle - Long sales cycles typical in manufacturing could slow growth
   Severity: Low

2. Implementation complexity - Enterprise manufacturing integrations are complex
   Severity: Low

**Information Quality**: Good
- Specific metrics provided (40% efficiency, 99.7% accuracy, $25K/month pricing)
- Third-party validation cited (Fast Company, Gartner)
- Clear team backgrounds with verifiable previous employers

No significant red flags identified. The company presents a professional, substantive web presence with specific claims and third-party validation.
    """,
}


def mock_claude_response(section_id: str) -> dict[str, Any]:
    """
    Generate realistic mock Claude response for a given section.

    Args:
        section_id: ID of the analysis section

    Returns:
        Dict containing mock response content for the section
    """
    content = MOCK_SECTION_CONTENT.get(section_id, f"Mock content for section: {section_id}")
    return {
        'content': content,
        'section_id': section_id,
    }


# ============================================================================
# MOCK ANTHROPIC SERVICE CLASS
# ============================================================================

@dataclass
class MockClaudeResponse:
    """Mock response from Claude API."""
    content: str
    input_tokens: int
    output_tokens: int
    model: str = "claude-sonnet-4-20250514"
    stop_reason: str = "end_turn"
    raw_response: dict = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Total tokens used in this call."""
        return self.input_tokens + self.output_tokens


class MockAnthropicService:
    """
    Mock Anthropic service for testing analysis pipeline.

    This mock:
    - Tracks all API calls with call_log
    - Returns realistic mock responses per section
    - Simulates token usage (configurable)
    - Supports configurable failure mode
    """

    def __init__(
        self,
        input_tokens_range: tuple[int, int] = (500, 1500),
        output_tokens_range: tuple[int, int] = (300, 800),
        fail_on_section: str | None = None,
        fail_with_rate_limit: bool = False,
        fail_with_timeout: bool = False,
    ):
        """
        Initialize the mock service.

        Args:
            input_tokens_range: (min, max) for simulated input tokens
            output_tokens_range: (min, max) for simulated output tokens
            fail_on_section: Section ID to fail on (for error testing)
            fail_with_rate_limit: If True, raise RateLimitError on first call
            fail_with_timeout: If True, raise TimeoutError on first call
        """
        self.call_log: list[dict[str, Any]] = []
        self.input_tokens_range = input_tokens_range
        self.output_tokens_range = output_tokens_range
        self.fail_on_section = fail_on_section
        self.fail_with_rate_limit = fail_with_rate_limit
        self.fail_with_timeout = fail_with_timeout
        self._call_count = 0
        self._rate_limit_raised = False
        self._timeout_raised = False

    def call(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: int | None = None,
    ) -> MockClaudeResponse:
        """
        Mock Claude API call.

        Args:
            prompt: The user prompt
            system_prompt: Optional system prompt
            model: Model to use (ignored in mock)
            max_tokens: Max tokens (ignored in mock)
            temperature: Temperature (ignored in mock)
            timeout: Timeout (ignored in mock)

        Returns:
            MockClaudeResponse with content and token usage

        Raises:
            RateLimitError: If fail_with_rate_limit is set (first call only)
            TimeoutError: If fail_with_timeout is set (first call only)
            APIError: If fail_on_section matches current section
        """
        from app.services.anthropic_service import RateLimitError, TimeoutError, APIError

        self._call_count += 1

        # Handle rate limit failure (first call only)
        if self.fail_with_rate_limit and not self._rate_limit_raised:
            self._rate_limit_raised = True
            raise RateLimitError("Rate limit exceeded")

        # Handle timeout failure (first call only)
        if self.fail_with_timeout and not self._timeout_raised:
            self._timeout_raised = True
            raise TimeoutError("Request timed out")

        # Determine section from prompt
        section_id = self._detect_section_from_prompt(prompt)

        # Handle section-specific failure
        if self.fail_on_section and section_id == self.fail_on_section:
            raise APIError(f"Simulated failure for section: {section_id}")

        # Generate token counts
        import random
        input_tokens = random.randint(*self.input_tokens_range)
        output_tokens = random.randint(*self.output_tokens_range)

        # Get mock content
        content = MOCK_SECTION_CONTENT.get(section_id, f"Mock analysis content for: {section_id}")

        # Log the call
        self.call_log.append({
            'prompt': prompt[:500] + '...' if len(prompt) > 500 else prompt,
            'system_prompt': system_prompt[:200] + '...' if system_prompt and len(system_prompt) > 200 else system_prompt,
            'section_id': section_id,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'call_number': self._call_count,
        })

        return MockClaudeResponse(
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            model=model or "claude-sonnet-4-20250514",
        )

    def _detect_section_from_prompt(self, prompt: str) -> str:
        """Detect which section is being analyzed from prompt content."""
        prompt_lower = prompt.lower()

        if 'executive summary' in prompt_lower:
            return 'executive_summary'
        elif 'company overview' in prompt_lower or 'founded' in prompt_lower and 'headquarters' in prompt_lower:
            return 'company_overview'
        elif 'business model' in prompt_lower or 'revenue model' in prompt_lower:
            return 'business_model'
        elif 'team' in prompt_lower and 'leadership' in prompt_lower:
            return 'team_leadership'
        elif 'market position' in prompt_lower or 'competitive' in prompt_lower:
            return 'market_position'
        elif 'technology' in prompt_lower or 'tech stack' in prompt_lower:
            return 'technology'
        elif 'key insights' in prompt_lower or 'strengths' in prompt_lower:
            return 'key_insights'
        elif 'red flags' in prompt_lower or 'concerns' in prompt_lower:
            return 'red_flags'
        else:
            return 'unknown'

    def analyze_text(
        self,
        text: str,
        analysis_type: str,
        context: dict[str, Any] | None = None,
    ) -> MockClaudeResponse:
        """
        Mock analyze_text method.

        Args:
            text: Text to analyze
            analysis_type: Type of analysis
            context: Additional context

        Returns:
            MockClaudeResponse
        """
        from app.analysis.prompts import get_analysis_prompt

        prompt, system_prompt = get_analysis_prompt(analysis_type, text, context)
        return self.call(prompt, system_prompt=system_prompt)

    def health_check(self) -> dict[str, Any]:
        """Mock health check."""
        return {
            "status": "healthy",
            "model": "claude-sonnet-4-20250514",
            "tokens_used": 10,
        }

    @property
    def total_tokens_used(self) -> int:
        """Total tokens across all calls."""
        return sum(
            call['input_tokens'] + call['output_tokens']
            for call in self.call_log
        )


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_company_with_analysis_context(db) -> dict[str, Any]:
    """
    Create a Company with Pages and Entities ready for analysis testing.

    This factory creates a complete test setup with:
    - Company record with status='analysis'
    - Page records with realistic crawled content
    - Entity records from MOCK_ENTITIES

    Args:
        db: Flask-SQLAlchemy db instance

    Returns:
        Dictionary containing:
            - company: Company model instance
            - pages: Dict of page_type -> Page instance
            - entities: List of Entity instances
            - company_id: UUID string
    """
    from app.models import Company, Page, Entity
    from app.models.enums import CompanyStatus, PageType, ProcessingPhase, EntityType

    # Create company
    company = Company(
        company_name="NovaTech Industries",
        website_url="https://novatech.io",
        industry="Industrial AI / Manufacturing Technology",
        status=CompanyStatus.IN_PROGRESS,
        processing_phase=ProcessingPhase.ANALYZING,
    )
    db.session.add(company)
    db.session.flush()

    # Create pages with mock content
    pages = {}
    page_configs = [
        (PageType.ABOUT, "https://novatech.io/about", MOCK_CRAWLED_CONTENT['about']),
        (PageType.TEAM, "https://novatech.io/team", MOCK_CRAWLED_CONTENT['team']),
        (PageType.PRODUCT, "https://novatech.io/products", MOCK_CRAWLED_CONTENT['products']),
        (PageType.OTHER, "https://novatech.io/news", MOCK_CRAWLED_CONTENT['news']),
    ]

    for page_type, url, text in page_configs:
        page = Page(
            company_id=company.id,
            url=url,
            page_type=page_type,
            extracted_text=text,
        )
        db.session.add(page)
        db.session.flush()
        pages[page_type.value] = page

    # Create entities from MOCK_ENTITIES
    entities = []
    for ent_data in MOCK_ENTITIES:
        try:
            entity_type = EntityType(ent_data['type'])
        except ValueError:
            continue

        entity = Entity(
            company_id=company.id,
            entity_type=entity_type,
            entity_value=ent_data['value'],
            confidence_score=ent_data.get('confidence', 0.8),
            extra_data=ent_data.get('extra_data'),
        )
        db.session.add(entity)
        entities.append(entity)

    db.session.commit()

    return {
        'company': company,
        'pages': pages,
        'entities': entities,
        'company_id': company.id,
    }


def create_empty_content_company(db) -> dict[str, Any]:
    """
    Create a Company with no pages for edge case testing.

    Args:
        db: Flask-SQLAlchemy db instance

    Returns:
        Dictionary containing company info
    """
    from app.models import Company
    from app.models.enums import CompanyStatus, ProcessingPhase

    company = Company(
        company_name="Empty Test Company",
        website_url="https://empty.test",
        status=CompanyStatus.IN_PROGRESS,
        processing_phase=ProcessingPhase.ANALYZING,
    )
    db.session.add(company)
    db.session.commit()

    return {
        'company': company,
        'company_id': company.id,
    }


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def mock_anthropic_service():
    """Provide a mock AnthropicService for testing."""
    return MockAnthropicService()


@pytest.fixture
def mock_anthropic_service_with_failure():
    """Provide a mock AnthropicService that fails on red_flags section."""
    return MockAnthropicService(fail_on_section='red_flags')


@pytest.fixture
def mock_anthropic_service_rate_limited():
    """Provide a mock AnthropicService that raises RateLimitError first."""
    return MockAnthropicService(fail_with_rate_limit=True)


@pytest.fixture
def mock_anthropic_service_timeout():
    """Provide a mock AnthropicService that raises TimeoutError first."""
    return MockAnthropicService(fail_with_timeout=True)


@pytest.fixture
def mock_crawled_content():
    """Provide mock crawled content for analysis."""
    return MOCK_CRAWLED_CONTENT


@pytest.fixture
def mock_entities():
    """Provide mock extracted entities for analysis."""
    return MOCK_ENTITIES


@pytest.fixture
def section_order():
    """Provide expected section order."""
    return SECTION_ORDER
