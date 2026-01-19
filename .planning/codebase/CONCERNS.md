# Codebase Concerns

**Analysis Date:** 2026-01-19

## Tech Debt

**Incomplete Crawl Task Implementation:**
- Issue: Two TODO comments in crawl tasks indicating placeholder implementation
- Files: `backend/app/workers/tasks.py` (lines 96, 144)
- Impact: Crawling functionality not fully implemented; `crawl_company` and `crawl_page` tasks return placeholder data
- Fix approach: Implement actual crawling logic using `CrawlWorker` from `backend/app/crawlers/crawl_worker.py`

**Unreachable Code in URL Normalization:**
- Issue: Dead code after early return statement in `_normalize_url` method
- Files: `backend/app/crawlers/crawl_worker.py` (lines 617-619)
- Impact: Query strings are never preserved in normalized URLs, which could cause duplicate crawling of parameterized URLs
- Fix approach: Remove early return on line 616 and restructure to include query string logic

**Overuse of Empty Returns in Error Handling:**
- Issue: Multiple functions return empty lists/dicts on error instead of raising exceptions
- Files:
  - `backend/app/services/redis_service.py` (line 543)
  - `backend/app/services/checkpoint_service.py` (lines 347, 362)
  - `backend/app/services/export_service.py` (line 89)
  - `backend/app/extractors/structured_extractor.py` (line 501)
  - `backend/app/extractors/nlp_pipeline.py` (line 212)
  - `backend/app/extractors/deduplicator.py` (lines 88, 158, 219, 280)
  - `backend/app/crawlers/browser_manager.py` (line 309)
- Impact: Silent failures mask errors; callers cannot distinguish between "no results" and "error occurred"
- Fix approach: Raise specific exceptions or use Result types to distinguish error states from empty results

**Silent Exception Swallowing:**
- Issue: Bare `pass` statements in exception handlers throughout the codebase
- Files:
  - `backend/app/services/job_service.py` (lines 282, 360)
  - `backend/app/services/token_tracker.py` (line 95)
  - `backend/app/services/anthropic_service.py` (lines 39, 44, 49, 54 - these are exception class definitions, acceptable)
  - `backend/app/crawlers/browser_manager.py` (lines 265, 291)
  - `backend/app/crawlers/robots_parser.py` (line 374)
  - `backend/app/crawlers/sitemap_parser.py` (lines 50, 285, 404)
  - `backend/app/crawlers/crawl_worker.py` (line 548)
  - `backend/app/crawlers/rate_limiter.py` (line 296)
  - `backend/app/analysis/synthesis.py` (line 108)
  - `backend/app/workers/tasks.py` (line 433)
  - `backend/app/extractors/deduplicator.py` (line 66)
- Impact: Errors are hidden, making debugging difficult; potential data loss or inconsistent state
- Fix approach: Add logging at minimum, or re-raise exceptions where appropriate

## Known Bugs

**Query String Stripping:**
- Symptoms: URLs with query parameters may be normalized incorrectly, losing the query string
- Files: `backend/app/crawlers/crawl_worker.py` (line 616-619)
- Trigger: Crawl any URL with query parameters (e.g., `?page=2`)
- Workaround: None - query parameters are silently stripped

## Security Considerations

**Hardcoded Development Secret Key:**
- Risk: Default secret key in config could be deployed to production if env var not set
- Files: `backend/app/config.py` (line 11)
- Current mitigation: `ProductionConfig.init_app()` validates SECRET_KEY is set (line 87-90)
- Recommendations: Consider failing fast in all environments if SECRET_KEY is default value

**Default SQLite Database:**
- Risk: SQLite is used by default, which is unsuitable for production concurrent access
- Files: `backend/app/config.py` (lines 14, 62)
- Current mitigation: Production should set DATABASE_URL env var
- Recommendations: Add explicit check in ProductionConfig to require PostgreSQL

**CORS Configuration:**
- Risk: CORS origins configured via comma-separated env var could be misconfigured
- Files: `backend/app/config.py` (line 34)
- Current mitigation: Defaults to localhost:5173
- Recommendations: Validate CORS origins are valid URLs; consider allowlist approach

**Content Security Policy Allows Unsafe Inline:**
- Risk: `'unsafe-inline'` for script-src and style-src weakens XSS protection
- Files: `backend/app/middleware/security.py` (lines 32-34)
- Current mitigation: Other security headers are properly configured
- Recommendations: Remove unsafe-inline and use nonces or hashes for legitimate inline scripts/styles

## Performance Bottlenecks

**Large Frontend Page Components:**
- Problem: Several page components exceed 400 lines, mixing UI, state, and logic
- Files:
  - `frontend/src/pages/CompanyResults.tsx` (916 lines)
  - `frontend/src/pages/Dashboard.tsx` (519 lines)
  - `frontend/src/pages/BatchUpload.tsx` (483 lines)
  - `frontend/src/pages/CompanyProgress.tsx` (480 lines)
- Cause: All concerns in single component; complex render logic
- Improvement path: Extract into smaller components; separate hooks for data fetching; consider React.memo for expensive renders

**No Pagination for External Link Following:**
- Problem: External links are all processed synchronously during crawl
- Files: `backend/app/crawlers/crawl_worker.py` (lines 646-660)
- Cause: No batching or rate limiting for external link queue additions
- Improvement path: Batch external link processing; add separate queue

## Fragile Areas

**Exception Hierarchy in Anthropic Service:**
- Files: `backend/app/services/anthropic_service.py` (lines 37-54)
- Why fragile: Custom exception classes are empty (just `pass`); no additional context captured
- Safe modification: Add meaningful error context to exception classes
- Test coverage: Test file exists (`backend/tests/test_anthropic_service.py`)

**CrawlWorker State Management:**
- Files: `backend/app/crawlers/crawl_worker.py`
- Why fragile: Multiple mutable instance variables (`_visited_urls`, `_content_hashes`, `_pages`, `_progress`); checkpoint/resume logic depends on correct state
- Safe modification: Thoroughly test checkpoint serialization/deserialization; verify state consistency
- Test coverage: Test file exists (`backend/tests/test_crawl_worker.py`)

**Redis Service Progress/Job Status:**
- Files: `backend/app/services/redis_service.py`
- Why fragile: Multiple key formats for different data types; TTL expiration could cause data loss; silent error handling
- Safe modification: Add comprehensive logging; test TTL edge cases; verify key format consistency
- Test coverage: Test file exists (`backend/tests/test_redis_service.py`)

## Scaling Limits

**In-Memory URL Sets:**
- Current capacity: `_visited_urls` and `_content_hashes` sets grow unbounded during crawl
- Files: `backend/app/crawlers/crawl_worker.py` (lines 190-191)
- Limit: Memory exhaustion for very large sites (100k+ pages)
- Scaling path: Use Redis sets or bloom filters for visited URL tracking

**SQLite Default Database:**
- Current capacity: Works for development and small deployments
- Files: `backend/app/config.py` (line 14)
- Limit: Concurrent write locking in SQLite limits throughput
- Scaling path: Already configured to use DATABASE_URL env var for PostgreSQL in production

## Dependencies at Risk

**Python 3.14 in venv:**
- Risk: Python 3.14 is a future version (current stable is 3.12); potential compatibility issues
- Files: `backend/venv/lib/python3.14/` (directory structure observed)
- Impact: Dependencies may not be tested against Python 3.14
- Migration plan: Verify compatibility or downgrade to stable Python version

## Missing Critical Features

**No Rate Limiting on API Endpoints:**
- Problem: No request rate limiting middleware
- Files: `backend/app/middleware/security.py` (security middleware exists but no rate limiting)
- Blocks: Production deployment without DOS protection

**No Authentication System:**
- Problem: API endpoints appear to be publicly accessible
- Files: `backend/app/api/routes/*.py`
- Blocks: Multi-user deployment; access control

## Test Coverage Gaps

**Frontend Page Components:**
- What's not tested: No test files for page components
- Files:
  - `frontend/src/pages/Dashboard.tsx`
  - `frontend/src/pages/CompanyResults.tsx`
  - `frontend/src/pages/CompanyProgress.tsx`
  - `frontend/src/pages/AddCompany.tsx`
  - `frontend/src/pages/BatchUpload.tsx`
  - `frontend/src/pages/Settings.tsx`
- Risk: UI regressions; broken user flows
- Priority: High - these are primary user interfaces

**Frontend Hooks:**
- What's not tested: No test file for `useCompanies.ts` hooks
- Files: `frontend/src/hooks/useCompanies.ts`
- Risk: API integration failures; stale data issues
- Priority: Medium - hooks encapsulate critical data fetching logic

**Frontend API Client:**
- What's not tested: No test files for API client
- Files:
  - `frontend/src/api/client.ts`
  - `frontend/src/api/companies.ts`
- Risk: API contract changes could break silently
- Priority: Medium - integration point with backend

---

*Concerns audit: 2026-01-19*
