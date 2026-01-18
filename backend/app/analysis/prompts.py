"""Content Analysis Prompts for Claude API.

Task 6.3: Content Analysis Prompts
- Prompts for each analysis section
- Executive summary (FR-SUM-001)
- Business model (FR-ANA-002)
- Company stage (FR-ANA-003)
- Team analysis (FR-ANA-001)
- Market analysis (FR-ANA-005)
- Technology analysis
- Red flags (FR-ANA-007)
- Source citation instructions (FR-SUM-004)
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnalysisSection:
    """Definition of an analysis section."""
    id: str
    name: str
    description: str
    prompt_template: str
    system_prompt: str
    priority: int = 0  # Lower = higher priority
    required: bool = True


# System prompt for all analysis sections
BASE_SYSTEM_PROMPT = """You are an expert business analyst specializing in company research and intelligence.
Your task is to analyze company information and provide accurate, insightful analysis.

IMPORTANT GUIDELINES:
1. Be factual and cite sources for all claims
2. Distinguish between facts and inferences
3. Note when information is uncertain or conflicting
4. Use a professional, objective tone
5. Structure your response clearly with sections as requested
6. If information is not available, say so rather than speculating

Format your response as requested in the prompt."""


# Analysis section definitions
ANALYSIS_SECTIONS: dict[str, AnalysisSection] = {
    'company_overview': AnalysisSection(
        id='company_overview',
        name='Company Overview',
        description='Basic company information and description',
        priority=1,
        prompt_template="""Analyze the following company information and provide a structured Company Overview.

COMPANY NAME: {company_name}
WEBSITE: {website_url}
INDUSTRY: {industry}

EXTRACTED INFORMATION:
{content}

EXTRACTED ENTITIES:
{entities}

Please provide:
1. **Founded**: When was the company founded? (year or "Not found")
2. **Headquarters**: Where is the company headquartered?
3. **Company Size**: Estimated company size (employees) if mentioned
4. **Industry**: Primary industry and any sub-industries
5. **Description**: 2-3 sentence description of what the company does

Format your response as:
Founded: [value]
Headquarters: [value]
Company Size: [value]
Industry: [value]
Description: [text]

SOURCES: List any URLs where you found key information.""",
        system_prompt=BASE_SYSTEM_PROMPT,
    ),

    'business_model': AnalysisSection(
        id='business_model',
        name='Business Model & Products',
        description='Business model, revenue model, products and services',
        priority=2,
        prompt_template="""Analyze the company's business model and products/services.

COMPANY: {company_name}

EXTRACTED INFORMATION:
{content}

ENTITIES (products, services, pricing):
{entities}

Please analyze:
1. **Business Model Type**: (B2B, B2C, B2B2C, marketplace, SaaS, etc.)
2. **Revenue Model**: How does the company make money?
3. **Key Products/Services**: List main offerings with brief descriptions
4. **Pricing**: Any pricing information found
5. **Value Proposition**: What problem does the company solve?

Format as structured sections with headers.
Include confidence level (High/Medium/Low) for each finding.
SOURCES: Cite specific pages where information was found.""",
        system_prompt=BASE_SYSTEM_PROMPT,
    ),

    'team_leadership': AnalysisSection(
        id='team_leadership',
        name='Team & Leadership',
        description='Leadership team, founders, key personnel',
        priority=3,
        prompt_template="""Analyze the company's leadership and team.

COMPANY: {company_name}

EXTRACTED PEOPLE:
{people_entities}

TEAM PAGE CONTENT:
{team_content}

Please provide:
1. **Founders**: List founders with their roles
2. **Leadership Team**: Key executives (CEO, CTO, CFO, etc.)
3. **Notable Team Members**: Other key personnel mentioned
4. **Advisors/Board**: Any advisors or board members
5. **Team Composition**: General observations about the team

For each person include:
- Name
- Title/Role
- Brief background if available
- Source URL

Format as a table when possible.
Note any gaps in leadership information.""",
        system_prompt=BASE_SYSTEM_PROMPT,
    ),

    'market_position': AnalysisSection(
        id='market_position',
        name='Market Position',
        description='Target market, competition, differentiators',
        priority=4,
        prompt_template="""Analyze the company's market position.

COMPANY: {company_name}
INDUSTRY: {industry}

CONTENT:
{content}

ENTITIES (organizations, competitors):
{org_entities}

Analyze:
1. **Target Market**: Who are their customers? (segments, industries, company sizes)
2. **Geographic Focus**: What markets/regions do they serve?
3. **Competitive Landscape**: Any competitors mentioned or implied
4. **Key Differentiators**: What makes them unique?
5. **Market Position**: Are they a leader, challenger, or niche player?

Include confidence levels and sources for each finding.
If competitors are not explicitly mentioned, note this.""",
        system_prompt=BASE_SYSTEM_PROMPT,
    ),

    'technology': AnalysisSection(
        id='technology',
        name='Technology & Operations',
        description='Tech stack, infrastructure, operational scale',
        priority=5,
        prompt_template="""Analyze the company's technology and operations.

COMPANY: {company_name}

TECH STACK ENTITIES:
{tech_entities}

CAREERS/JOB POSTINGS:
{careers_content}

CONTENT:
{content}

Analyze:
1. **Technology Stack**: Programming languages, frameworks, databases
2. **Infrastructure**: Cloud providers, hosting, architecture patterns
3. **Integrations**: Third-party services or APIs mentioned
4. **Scale Indicators**: Any metrics about scale, users, transactions
5. **Security/Compliance**: Any security or compliance mentions

Format findings by category.
Note which technologies are confirmed vs. inferred from job postings.""",
        system_prompt=BASE_SYSTEM_PROMPT,
    ),

    'key_insights': AnalysisSection(
        id='key_insights',
        name='Key Insights',
        description='Strengths, growth indicators, strategic direction',
        priority=6,
        prompt_template="""Provide key insights about this company.

COMPANY: {company_name}

ANALYSIS SO FAR:
{previous_analysis}

ADDITIONAL CONTENT:
{content}

Provide insights on:
1. **Strengths**: 3-5 key strengths or competitive advantages
2. **Growth Indicators**: Signs of growth, traction, or momentum
3. **Strategic Direction**: Where is the company heading?
4. **Opportunities**: Potential opportunities for the company
5. **Unique Observations**: Anything notable or distinctive

Be specific and cite evidence for each insight.
Rate confidence level for each insight.""",
        system_prompt=BASE_SYSTEM_PROMPT,
    ),

    'red_flags': AnalysisSection(
        id='red_flags',
        name='Red Flags & Concerns',
        description='Potential concerns, risks, missing information',
        priority=7,
        prompt_template="""Identify any red flags or concerns about this company.

COMPANY: {company_name}

ALL CONTENT ANALYZED:
{content}

ENTITIES:
{entities}

Look for:
1. **Inconsistencies**: Conflicting information across pages
2. **Missing Information**: Expected information that's absent
3. **Vague Claims**: Unsubstantiated or exaggerated claims
4. **Concerns**: Any potential business or operational concerns
5. **Information Quality**: Assessment of website information quality

For each item:
- Describe the finding
- Explain why it's a concern
- Rate severity (Low/Medium/High)
- Provide source

If no significant red flags, state that clearly.
Be objective - not everything is a red flag.""",
        system_prompt=BASE_SYSTEM_PROMPT,
    ),

    'executive_summary': AnalysisSection(
        id='executive_summary',
        name='Executive Summary',
        description='3-4 paragraph summary of the company',
        priority=0,  # Generated last, highest display priority
        required=True,
        prompt_template="""Generate an executive summary for this company.

COMPANY: {company_name}
WEBSITE: {website_url}
INDUSTRY: {industry}

ANALYSIS SECTIONS COMPLETED:
{full_analysis}

Write a 3-4 paragraph executive summary that covers:

PARAGRAPH 1: What the company does and who they serve
- Core business/product
- Target market
- Key value proposition

PARAGRAPH 2: Business model and market position
- How they make money
- Competitive position
- Key differentiators

PARAGRAPH 3: Team and traction
- Leadership highlights
- Notable achievements or milestones
- Growth indicators

PARAGRAPH 4: Key takeaways
- Main strengths
- Any notable concerns
- Overall assessment

Guidelines:
- Write in a professional, objective tone
- Be concise but comprehensive
- Include specific facts and figures when available
- Note areas of uncertainty
- This should give a complete picture in ~2 minutes of reading""",
        system_prompt=BASE_SYSTEM_PROMPT + """

You are writing an executive summary for a company intelligence report.
This will be the first section readers see, so make it informative and engaging.
Focus on actionable intelligence rather than generic descriptions.""",
    ),
}


def get_analysis_prompt(
    section_id: str,
    text: str = '',
    context: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """
    Get the prompt and system prompt for an analysis section.

    Args:
        section_id: ID of the analysis section
        text: Text content to analyze
        context: Additional context variables for the prompt

    Returns:
        Tuple of (user_prompt, system_prompt)

    Raises:
        ValueError: If section_id is not found
    """
    if section_id not in ANALYSIS_SECTIONS:
        raise ValueError(f"Unknown analysis section: {section_id}")

    section = ANALYSIS_SECTIONS[section_id]
    context = context or {}

    # Build prompt variables
    variables = {
        'content': text,
        'company_name': context.get('company_name', 'Unknown Company'),
        'website_url': context.get('website_url', ''),
        'industry': context.get('industry', 'Unknown'),
        'entities': context.get('entities', ''),
        'people_entities': context.get('people_entities', ''),
        'org_entities': context.get('org_entities', ''),
        'tech_entities': context.get('tech_entities', ''),
        'team_content': context.get('team_content', ''),
        'careers_content': context.get('careers_content', ''),
        'previous_analysis': context.get('previous_analysis', ''),
        'full_analysis': context.get('full_analysis', ''),
    }

    # Format the prompt template
    prompt = section.prompt_template.format(**variables)
    system_prompt = section.system_prompt

    return prompt, system_prompt


def get_section_order() -> list[str]:
    """Get the order in which sections should be analyzed."""
    # Sort by priority, excluding executive_summary which is generated last
    sections = [
        (section.priority, section_id)
        for section_id, section in ANALYSIS_SECTIONS.items()
        if section_id != 'executive_summary'
    ]
    sections.sort()
    return [section_id for _, section_id in sections] + ['executive_summary']


def get_required_sections() -> list[str]:
    """Get list of required section IDs."""
    return [
        section_id
        for section_id, section in ANALYSIS_SECTIONS.items()
        if section.required
    ]
