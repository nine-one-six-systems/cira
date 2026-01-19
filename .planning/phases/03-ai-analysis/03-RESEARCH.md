# Phase 3: AI Analysis - Research

**Researched:** 2026-01-19
**Domain:** Claude API Integration, Token Tracking, AI-Powered Analysis
**Confidence:** HIGH

## Summary

This research covers Phase 3: AI Analysis for the CIRA (Company Intelligence Research Assistant) project. The phase focuses on integrating Claude API via the Anthropic SDK to generate comprehensive intelligence summaries, with token tracking and cost estimation.

**Key finding:** The existing codebase already contains a complete implementation of the AI Analysis phase. All core services (AnthropicService, TokenTracker, AnalysisSynthesizer), prompt templates, Celery tasks, API endpoints, and UI components are fully implemented and tested. The project status in IMPLEMENTATION_PLAN.md confirms "Project Status: COMPLETE - All Phases 1-10 Complete (1049 backend tests @ 84% coverage, 167 frontend tests, 7 E2E test suites)."

**Primary recommendation:** Phase 3 requires verification testing rather than new implementation. The planning should focus on integration testing between crawled content/extracted entities and the analysis pipeline, edge case handling, and ensuring all requirements (ANA-01 through ANA-10, UI-03, UI-04) are fully covered by tests.

## Existing Infrastructure Analysis

### Already Implemented Components

The codebase contains complete implementations for all Phase 3 deliverables:

| Component | File | Status |
|-----------|------|--------|
| Claude API Client | `backend/app/services/anthropic_service.py` | COMPLETE |
| Token Tracker | `backend/app/services/token_tracker.py` | COMPLETE |
| Analysis Prompts | `backend/app/analysis/prompts.py` | COMPLETE |
| Analysis Synthesis | `backend/app/analysis/synthesis.py` | COMPLETE |
| Analysis Celery Task | `backend/app/workers/tasks.py` (analyze_content, generate_summary) | COMPLETE |
| Token Usage Endpoint | `backend/app/api/routes/tokens.py` | COMPLETE |
| Progress Endpoint | `backend/app/api/routes/progress.py` | COMPLETE |
| Progress UI | `frontend/src/pages/CompanyProgress.tsx` | COMPLETE |
| Results UI | `frontend/src/pages/CompanyResults.tsx` | COMPLETE |

### Existing Tests

Comprehensive test coverage exists:

| Test File | Coverage |
|-----------|----------|
| `test_anthropic_service.py` | API client, retries, error handling |
| `test_token_tracker.py` | Cost calculation, usage recording, aggregation |
| `test_analysis_prompts.py` | Prompt templates, section order |
| `test_analysis_synthesis.py` | Section analysis, full analysis workflow |

## Standard Stack

The analysis system uses an established, well-tested stack:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.18.0 | Official Anthropic Python SDK | Only official SDK for Claude API |
| Flask | >=3.0.0 | Web framework | Already used by project |
| Celery | >=5.3.0 | Task queue | Already used for background jobs |
| Redis | >=5.0.0 | Progress caching | Already used by project |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy | >=2.0.0 | Database ORM | Token usage persistence |
| Pydantic | >=2.5.0 | Schema validation | API request/response validation |

### Already Installed

All required packages are present in `backend/requirements.txt`:
```bash
# AI/ML (already in requirements.txt)
anthropic>=0.18.0
```

## Architecture Patterns

### Existing Project Structure
```
backend/
├── app/
│   ├── analysis/           # Analysis module
│   │   ├── __init__.py
│   │   ├── prompts.py      # Prompt templates for all sections
│   │   └── synthesis.py    # Analysis orchestration
│   ├── services/
│   │   ├── anthropic_service.py  # Claude API client
│   │   └── token_tracker.py      # Token usage tracking
│   ├── workers/
│   │   └── tasks.py        # Celery tasks (analyze_content, generate_summary)
│   ├── api/routes/
│   │   ├── tokens.py       # GET /api/v1/companies/:id/tokens
│   │   └── progress.py     # GET /api/v1/companies/:id/progress
│   └── models/
│       └── company.py      # Analysis, TokenUsage models
frontend/
├── src/
│   ├── pages/
│   │   ├── CompanyProgress.tsx  # Progress display with token counter
│   │   └── CompanyResults.tsx   # Analysis display with markdown rendering
│   └── hooks/
│       └── useCompanies.ts      # useProgress, useTokens hooks
```

### Pattern 1: Lazy Client Initialization
**What:** AnthropicService initializes the API client lazily on first use
**When to use:** External service clients that need app context
**Example:**
```python
# Source: backend/app/services/anthropic_service.py
class AnthropicService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            api_key = current_app.config.get('ANTHROPIC_API_KEY')
            self._client = anthropic.Anthropic(api_key=api_key)
        return self._client
```

### Pattern 2: Section-by-Section Analysis with Progress Callbacks
**What:** Analysis proceeds through sections sequentially with progress updates
**When to use:** Long-running operations that need real-time progress tracking
**Example:**
```python
# Source: backend/app/analysis/synthesis.py
def run_full_analysis(self, company_id: str, progress_callback: callable | None = None):
    for i, section_id in enumerate(section_order):
        if progress_callback:
            progress_callback(section_id, i, total_sections)
        result = self.analyze_section(company_id, section_id, context, results)
        results[section_id] = result
```

### Pattern 3: Exponential Backoff for Rate Limits
**What:** Retry with increasing delays on 429 errors
**When to use:** External API calls that may be rate limited
**Example:**
```python
# Source: backend/app/services/anthropic_service.py
for attempt in range(max_retries):
    try:
        response = client.messages.create(...)
    except anthropic.RateLimitError:
        if attempt < max_retries - 1:
            delay = self.BASE_RETRY_DELAY * (2 ** attempt)
            time.sleep(delay)
            continue
        raise RateLimitError("Rate limit exceeded") from e
```

### Anti-Patterns to Avoid
- **Hardcoded API keys:** Use environment variables (ANTHROPIC_API_KEY)
- **Synchronous API calls in request handlers:** Use Celery tasks for analysis
- **Unbounded content length:** Truncate content before sending to Claude

## Don't Hand-Roll

The existing implementation already handles these correctly:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Claude API calls | Custom HTTP client | `anthropic` SDK | Handles auth, retries, streaming |
| Token counting | Manual estimation | API response `usage` field | Exact counts from Claude |
| Cost calculation | Hardcoded prices | Configurable pricing in TokenTracker | Prices change over time |
| Retry logic | Simple retry loops | Exponential backoff with jitter | Prevents thundering herd |

## Common Pitfalls

### Pitfall 1: Token Count Mismatch
**What goes wrong:** Estimated tokens before call differ from actual usage
**Why it happens:** Claude's tokenizer is not publicly available; estimates are approximate
**How to avoid:** Always use the actual token counts from API response, not pre-estimates
**Warning signs:** Cost estimates wildly different from actual costs
**Existing mitigation:** TokenTracker records actual tokens from ClaudeResponse

### Pitfall 2: Rate Limiting During Analysis
**What goes wrong:** Analysis fails midway due to 429 errors
**Why it happens:** Multiple section analyses can hit rate limits
**How to avoid:** Implement exponential backoff (already done), save checkpoint per section
**Warning signs:** Frequent RateLimitError exceptions
**Existing mitigation:** AnthropicService has retry logic with backoff

### Pitfall 3: Content Truncation
**What goes wrong:** Analysis misses important information
**Why it happens:** Content exceeds Claude's context window
**How to avoid:** Prioritize content by page type, truncate intelligently
**Warning signs:** Analysis sections missing expected information
**Existing mitigation:** AnalysisSynthesizer truncates content (50000 chars total, 10000 per type)

### Pitfall 4: Progress Not Updating
**What goes wrong:** UI shows stale progress during analysis
**Why it happens:** Redis updates not frequent enough or task crashes
**How to avoid:** Update progress at each section, detect stale progress
**Warning signs:** Progress stuck at same percentage
**Existing mitigation:** Progress callback in run_full_analysis, Redis progress tracking

## Code Examples

### Claude API Call with Error Handling
```python
# Source: backend/app/services/anthropic_service.py
def call(self, prompt: str, system_prompt: str | None = None, ...):
    client = self._get_client()
    messages = [{"role": "user", "content": prompt}]

    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=system_prompt or "",
        messages=messages,
        timeout=timeout,
    )

    return ClaudeResponse(
        content="".join(block.text for block in response.content if block.type == "text"),
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        model=response.model,
        stop_reason=response.stop_reason,
    )
```

### Token Usage Recording
```python
# Source: backend/app/services/token_tracker.py
def record_usage(self, company_id: str, api_call_type: str,
                 input_tokens: int, output_tokens: int, section: str | None = None):
    cost = self.calculate_cost(input_tokens, output_tokens)

    usage = TokenUsage(
        company_id=company_id,
        api_call_type=ApiCallType(api_call_type.lower()),
        section=section,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        timestamp=datetime.now(UTC),
    )
    db.session.add(usage)

    # Update company totals
    company = db.session.get(Company, company_id)
    if company:
        company.total_tokens_used += cost.total_tokens
        company.estimated_cost += cost.total_cost

    db.session.commit()
```

### Analysis Section Generation
```python
# Source: backend/app/analysis/synthesis.py
def analyze_section(self, company_id: str, section_id: str, context: dict,
                    previous_results: dict | None = None):
    prompt, system_prompt = get_analysis_prompt(section_id, context=context)

    response = anthropic_service.call(prompt=prompt, system_prompt=system_prompt)

    token_tracker.record_usage(
        company_id=company_id,
        api_call_type='analysis',
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
        section=section_id,
    )

    return SectionResult(
        section_id=section_id,
        content=response.content,
        sources=self._extract_sources(response.content),
        confidence=0.8,
        input_tokens=response.input_tokens,
        output_tokens=response.output_tokens,
    )
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Claude 2 API | Claude 3 Messages API | 2024 | Structured messages, better token tracking |
| Manual retry | SDK retry handling | anthropic 0.15+ | Built-in retry with backoff |
| Hardcoded model | Configurable model | Current | Easy model upgrades |

**Current best practices:**
- Use claude-sonnet-4-20250514 (or latest sonnet) for analysis tasks
- Temperature 0.3 for factual analysis
- Max tokens 4000 for section generation
- System prompts for context and guidelines

## Requirements Verification Checklist

Based on the phase requirements, here's the verification status:

### AI Analysis (ANA-01 to ANA-10)
- [x] **ANA-01**: System analyzes content using Claude API - `AnthropicService.call()`
- [x] **ANA-02**: Executive summary generation - `ANALYSIS_SECTIONS['executive_summary']`
- [x] **ANA-03**: Company overview section - `ANALYSIS_SECTIONS['company_overview']`
- [x] **ANA-04**: Business model & products section - `ANALYSIS_SECTIONS['business_model']`
- [x] **ANA-05**: Team & leadership section - `ANALYSIS_SECTIONS['team_leadership']`
- [x] **ANA-06**: Market position section - `ANALYSIS_SECTIONS['market_position']`
- [x] **ANA-07**: Key insights section - `ANALYSIS_SECTIONS['key_insights']`
- [x] **ANA-08**: Red flags identification - `ANALYSIS_SECTIONS['red_flags']`
- [x] **ANA-09**: Token usage tracking per API call - `TokenTracker.record_usage()`
- [x] **ANA-10**: Cost estimation calculation - `TokenTracker.calculate_cost()`

### UI Requirements (UI-03, UI-04)
- [x] **UI-03**: Real-time progress during analysis - `CompanyProgress.tsx`
- [x] **UI-04**: Completed analysis with markdown rendering - `CompanyResults.tsx`

### API Endpoint
- [x] `GET /api/v1/companies/:id/tokens` - `backend/app/api/routes/tokens.py`

## Open Questions

### Question 1: Integration Test Coverage
**What we know:** Unit tests exist for individual components
**What's unclear:** Are there integration tests covering the full flow from crawled pages to analysis output?
**Recommendation:** Planning should include integration tests that:
- Start with mock crawled content and entities
- Run through full analysis pipeline
- Verify all sections generated with expected structure

### Question 2: Error Recovery Scenarios
**What we know:** Checkpoint system exists for pause/resume
**What's unclear:** Are analysis section checkpoints fully tested?
**Recommendation:** Add tests for:
- Resume after API failure mid-analysis
- Partial results when some sections fail
- Cost tracking accuracy on resume

### Question 3: Content Preparation Edge Cases
**What we know:** `prepare_content_for_analysis()` truncates content
**What's unclear:** How does it handle companies with very little or no crawled content?
**Recommendation:** Add edge case tests for:
- Company with 0 pages
- Company with only external pages
- Company with pages but no extracted text

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/app/services/anthropic_service.py` - Full implementation reviewed
- Codebase: `backend/app/services/token_tracker.py` - Full implementation reviewed
- Codebase: `backend/app/analysis/prompts.py` - All section prompts reviewed
- Codebase: `backend/app/analysis/synthesis.py` - Full orchestration logic reviewed
- Codebase: `backend/tests/test_anthropic_service.py` - 27 tests reviewed
- Codebase: `backend/tests/test_token_tracker.py` - 18 tests reviewed
- Codebase: `backend/tests/test_analysis_synthesis.py` - Tests reviewed

### Secondary (MEDIUM confidence)
- `IMPLEMENTATION_PLAN.md` - Project status and task definitions
- `specs/03-ai-analysis.md` - Specification requirements

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Anthropic SDK is the only option, already installed
- Architecture: HIGH - Patterns well-established and tested
- Pitfalls: HIGH - Based on existing error handling code

**Research date:** 2026-01-19
**Valid until:** 60 days (stable implementation, no major changes expected)

## Planning Recommendations

Given that Phase 3 is fully implemented, the planning should focus on:

1. **Verification Testing Plan**
   - Create integration tests for the full analysis pipeline
   - Test edge cases (empty content, partial failures, resume scenarios)
   - Verify requirements traceability (each ANA-XX requirement has corresponding test)

2. **Performance Validation**
   - Verify progress updates occur within 2 seconds (NFR-PER-006)
   - Test concurrent analysis requests
   - Validate token tracking accuracy

3. **Error Scenario Testing**
   - API rate limiting recovery
   - Network failures mid-analysis
   - Invalid/corrupt content handling

4. **Documentation Verification**
   - Ensure API documentation matches implementation
   - Verify cost estimation formula is documented
