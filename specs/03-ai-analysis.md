# AI Analysis Specification

## Overview

The AI analysis system uses Claude API to analyze extracted content and entities, generating comprehensive company intelligence summaries. It includes token tracking, cost estimation, and structured output generation.

## Functional Requirements

### Content Analysis (FR-ANA-001 to FR-ANA-007)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-ANA-001 | Summarize company mission and value proposition | P0 |
| FR-ANA-002 | Identify business model (B2B/B2C/SaaS/marketplace/etc.) | P0 |
| FR-ANA-003 | Assess company stage (startup/growth/established/enterprise) | P0 |
| FR-ANA-004 | Detect industry classification | P0 |
| FR-ANA-005 | Identify target market and customer segments | P1 |
| FR-ANA-006 | Extract competitive differentiators | P1 |
| FR-ANA-007 | Identify potential red flags | P1 |

### Summary Generation (FR-SUM-001 to FR-SUM-004)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-SUM-001 | Generate executive summary (3-4 paragraphs) | P0 |
| FR-SUM-002 | Generate structured sections: Overview, Business Model, Team, Market Position, Technology, Insights, Red Flags | P0 |
| FR-SUM-003 | Include confidence indicators for uncertain data | P1 |
| FR-SUM-004 | Cite sources for all factual claims | P0 |

### Token Tracking (FR-TOK-001 to FR-TOK-004)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-TOK-001 | Track input and output tokens per Claude API call | P0 |
| FR-TOK-002 | Aggregate total tokens per company analysis | P0 |
| FR-TOK-003 | Display cumulative token count in UI during processing | P0 |
| FR-TOK-004 | Calculate approximate cost based on token usage | P0 |

## Acceptance Criteria

### Claude API Integration
- API key from ANTHROPIC_API_KEY environment variable
- Exponential backoff on 429 (rate limit) responses
- Maximum 3 retries per request
- Timeout handling (60 seconds default)
- Response parsing extracts token counts

### Analysis Sections
Each section generated with:
- Relevant content from extracted pages/entities
- Source citations as URLs
- Confidence score (0-1)

#### Executive Summary
- 3-4 paragraphs
- Covers: what company does, who they serve, key differentiators, notable facts
- Written in professional, objective tone

#### Company Overview
- Founded date
- Headquarters location
- Company size (if available)
- Industry classification
- Brief description

#### Business Model & Products
- Business model type (B2B, B2C, SaaS, etc.)
- Revenue model
- Key products/services
- Pricing information (if available)

#### Team & Leadership
- Key executives with roles
- Founders
- Notable advisors/board members
- Team size and composition

#### Market Position
- Target market segments
- Geographic focus
- Competitive landscape
- Market differentiators

#### Technology & Operations
- Tech stack (if detected)
- Infrastructure indicators
- Operational scale indicators

#### Key Insights
- Notable strengths
- Growth indicators
- Strategic direction

#### Red Flags (optional)
- Inconsistencies found
- Missing expected information
- Concerns or risks

### Token Tracking
- Input tokens = tokens sent to API
- Output tokens = tokens in response
- Cost = (input_tokens * input_price) + (output_tokens * output_price)
- Current pricing tracked and configurable

## Test Requirements

### Programmatic Tests

1. **API Client Tests**
   - Valid request returns response with token counts
   - 429 response triggers exponential backoff
   - 500 response retries up to 3 times
   - Timeout after configured duration
   - Invalid API key returns auth error

2. **Token Tracking Tests**
   - Per-call tokens recorded correctly
   - Aggregates sum to total
   - Cost calculation accurate
   - Historical calls queryable by company

3. **Prompt Tests**
   - Each prompt produces valid JSON structure
   - Source citations included in responses
   - Confidence scores present
   - Output fits expected schema

4. **Analysis Generation Tests**
   - All sections generated for typical company
   - Missing data handled gracefully
   - Partial results saved on failure
   - Resume continues from last section

### Quality Assessment (Human Review)

Some analysis quality aspects require human judgment:

1. **Summary Coherence**
   - Executive summary reads naturally
   - No contradictions between sections
   - Appropriate level of detail

2. **Accuracy Spot-Check**
   - Random sample of facts verified against source
   - No hallucinated information
   - Citations accurate

3. **Tone Appropriateness**
   - Professional, objective language
   - No marketing language or bias
   - Appropriate confidence hedging

## Data Models

### Analysis

```typescript
interface Analysis {
  id: string;
  companyId: string;
  versionNumber: number;
  executiveSummary: string;
  fullAnalysis: AnalysisSections;
  rawInsights: Record<string, any>;
  tokenBreakdown: TokenBreakdown;
  createdAt: Date;
}

interface AnalysisSections {
  companyOverview: SectionContent;
  businessModelProducts: SectionContent;
  teamLeadership: SectionContent;
  marketPosition: SectionContent;
  technologyOperations: SectionContent;
  keyInsights: SectionContent;
  redFlags: SectionContent | null;
}

interface SectionContent {
  content: string;
  sources: string[];
  confidence: number;
}

interface TokenBreakdown {
  totalInputTokens: number;
  totalOutputTokens: number;
  bySection: Record<string, { input: number; output: number }>;
}
```

### TokenUsage

```typescript
interface TokenUsage {
  id: string;
  companyId: string;
  apiCallType: ApiCallType;
  inputTokens: number;
  outputTokens: number;
  timestamp: Date;
}

enum ApiCallType {
  EXTRACTION = 'extraction',
  SUMMARIZATION = 'summarization',
  ANALYSIS = 'analysis'
}
```

## Prompts

### Executive Summary Prompt

```
Analyze the following company information and generate a 3-4 paragraph executive summary.

Company: {company_name}
Website: {website_url}

Extracted Content:
{page_contents}

Extracted Entities:
{entities}

Requirements:
1. First paragraph: What the company does and their core value proposition
2. Second paragraph: Who they serve and their business model
3. Third paragraph: Key differentiators and competitive position
4. Fourth paragraph (optional): Notable facts, recent developments, or concerns

Include source URLs for factual claims. Use professional, objective language.
```

### Section Prompts

Similar structured prompts for each section with:
- Relevant input data
- Specific output requirements
- JSON schema for response
- Source citation instructions

## Configuration

```typescript
interface AnalysisConfig {
  model: string;           // Default: "claude-3-sonnet"
  maxTokensPerCall: number; // Default: 4000
  temperature: number;      // Default: 0.3
  retryAttempts: number;    // Default: 3
  timeoutSeconds: number;   // Default: 60
}

interface PricingConfig {
  inputTokenPrice: number;  // per 1M tokens
  outputTokenPrice: number; // per 1M tokens
}
```

## Dependencies

- Anthropic SDK 0.18+
- Token counting library for pre-flight estimation
