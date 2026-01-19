# Phase 1: Web Crawling - Research

**Researched:** 2026-01-19
**Domain:** Web crawling, sitemap parsing, robots.txt compliance, rate limiting, JavaScript rendering
**Confidence:** HIGH

## Summary

Phase 1 focuses on web crawling infrastructure for CIRA - discovering and fetching company website pages with intelligent prioritization, rate limiting, and robots.txt compliance. This research documents the established patterns in the existing codebase, which already has a fully implemented crawling system.

The codebase implements a complete crawl worker architecture using Playwright for JavaScript rendering, BeautifulSoup for HTML parsing, a priority queue for page ordering, per-domain rate limiting with token bucket algorithm, and Redis-backed caching for robots.txt and sitemap data. The implementation follows industry best practices for polite crawling.

**Primary recommendation:** The existing implementation is comprehensive. Phase 1 planning should focus on integration testing, edge case handling, and ensuring all requirements (CRL-01 through CRL-07) are verified against the existing code.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Playwright | 1.40+ | JavaScript rendering | Industry standard for headless browser automation, handles SPAs |
| BeautifulSoup4 | 4.12+ | HTML parsing | De facto Python HTML parser, robust error handling |
| requests | 2.31+ | HTTP client | Standard Python HTTP library for simple fetches |
| lxml | 4.9+ | XML/HTML parsing | Fast parser backend for BeautifulSoup and sitemap XML |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyPDF2 | 3.0+ | PDF text extraction | Extract text from PDF documents linked on sites |
| Redis | 5.0+ | Caching layer | Cache robots.txt rules, sitemap data, rate limit state |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Playwright | Selenium | Selenium is older, slower; Playwright has better async support |
| Playwright | Puppeteer | Puppeteer is JavaScript-only; Playwright has Python bindings |
| requests | httpx | httpx has async support but requests is simpler for sync crawling |

**Installation:**
```bash
pip install playwright beautifulsoup4 requests lxml PyPDF2 redis
playwright install chromium
```

## Architecture Patterns

### Existing Project Structure
```
backend/app/crawlers/
├── __init__.py
├── browser_manager.py    # Playwright browser pool management
├── crawl_worker.py       # Main crawl orchestration
├── external_links.py     # Social media link detection
├── page_classifier.py    # URL/content-based page type classification
├── page_priority_queue.py # Priority queue with BFS within priority levels
├── pdf_extractor.py      # PDF text extraction
├── rate_limiter.py       # Token bucket rate limiter with domain locks
├── robots_parser.py      # robots.txt parsing with 24h caching
└── sitemap_parser.py     # Sitemap XML parsing with gzip support
```

### Pattern 1: CrawlWorker as Orchestrator
**What:** Single CrawlWorker class coordinates all crawling components via dependency injection
**When to use:** Always - this is the main entry point for crawling
**Example:**
```python
# Source: backend/app/crawlers/crawl_worker.py
class CrawlWorker:
    def __init__(
        self,
        config: CrawlConfig | None = None,
        fetcher: SimpleFetcher | None = None,
        robots_parser: RobotsParser | None = None,
        rate_limiter: RateLimiter | None = None,
        page_classifier: PageClassifier | None = None,
        external_link_detector: ExternalLinkDetector | None = None,
        pdf_extractor: PDFExtractor | None = None,
    ):
        self.config = config or CrawlConfig()
        self._fetcher = fetcher or SimpleFetcher()
        self._robots = robots_parser or RobotsParser()
        # ... etc
```

### Pattern 2: Token Bucket Rate Limiting
**What:** Per-domain rate limiting using token bucket algorithm with domain-level locks
**When to use:** Before every HTTP request to respect server limits
**Example:**
```python
# Source: backend/app/crawlers/rate_limiter.py
@dataclass
class DomainBucket:
    domain: str
    tokens: float = 1.0
    max_tokens: float = 1.0
    refill_rate: float = 1.0  # 1 request/sec default
    crawl_delay: float | None = None  # From robots.txt

class RateLimiter:
    def acquire(self, url: str, blocking: bool = True, timeout: float = 30.0) -> bool:
        # Acquires domain lock + token bucket permit
```

### Pattern 3: Priority Queue with BFS
**What:** Heap-based priority queue that orders URLs by page type priority, then depth (BFS)
**When to use:** URL scheduling during crawl
**Example:**
```python
# Source: backend/app/crawlers/page_priority_queue.py
PAGE_TYPE_PRIORITY = {
    'about': 1, 'team': 2, 'product': 3, 'service': 4,
    'contact': 5, 'careers': 6, 'pricing': 7, 'blog': 8, 'news': 9, 'other': 10
}

@dataclass(order=True)
class QueuedURL:
    priority: int      # Page type priority (lower = higher priority)
    depth: int         # BFS ordering within same priority
    insertion_order: int  # Tie-breaker
    url: str
```

### Pattern 4: Checkpoint/Resume Architecture
**What:** Periodic checkpoint saving for pause/resume capability
**When to use:** Every 10 pages or 2 minutes during crawl
**Example:**
```python
# Source: backend/app/crawlers/crawl_worker.py
@dataclass
class CrawlCheckpoint:
    visited_urls: set[str]
    content_hashes: set[str]
    queue_state: list[dict[str, Any]]
    progress: dict[str, Any]
    timestamp: str
```

### Anti-Patterns to Avoid
- **Global mutable state:** Use dependency injection, not module-level singletons for stateful components
- **Blocking the event loop:** Use async browser operations, sync fallback only for simple fetches
- **Ignoring robots.txt:** Always check `robots_parser.is_allowed(url)` before fetching
- **Parallel same-domain requests:** Rate limiter prevents this, but don't bypass it

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| robots.txt parsing | Regex-based parser | `RobotsParser` class | Handles wildcards, crawl-delay, user-agent matching |
| URL normalization | String manipulation | `PagePriorityQueue.normalize_url()` | Handles trailing slashes, ports, query params, fragments |
| Content deduplication | MD5 hash | SHA-256 with text normalization | `CrawlWorker._compute_hash()` handles whitespace |
| Social link detection | Domain checking | `ExternalLinkDetector` | Handles platform-specific URL patterns, filters generic links |
| Page type classification | URL regex | `PageClassifier` | Combined URL + content patterns with confidence scoring |

**Key insight:** The existing codebase has solved all the edge cases. Don't rewrite - extend if needed.

## Common Pitfalls

### Pitfall 1: JavaScript-Heavy Sites Not Rendering
**What goes wrong:** Content appears empty because site uses React/Vue/Angular
**Why it happens:** SimpleFetcher uses requests (no JS), some sites need Playwright
**How to avoid:** Default to Playwright; SimpleFetcher only for known static sites
**Warning signs:** Empty text content, suspiciously short pages

### Pitfall 2: Rate Limit Bypass Under Concurrency
**What goes wrong:** Multiple Celery workers overwhelm target server
**Why it happens:** Each worker has its own rate limiter instance
**How to avoid:** Use Redis-backed rate limiting for distributed coordination
**Warning signs:** HTTP 429 errors, IP blocks

### Pitfall 3: Infinite Crawl Loops
**What goes wrong:** Crawler follows calendar/pagination generating infinite URLs
**Why it happens:** URL normalization doesn't handle dynamic parameters
**How to avoid:** Use exclusion patterns, max depth, page limits, content hash deduplication
**Warning signs:** Pages crawled >> expected, same content hash repeated

### Pitfall 4: Memory Growth from Browser Contexts
**What goes wrong:** Playwright contexts accumulate, memory exhausted
**Why it happens:** Contexts not properly closed on errors
**How to avoid:** Use context pool with proper cleanup in finally blocks
**Warning signs:** Increasing memory usage, "out of memory" errors

### Pitfall 5: Sitemap Parsing Failures
**What goes wrong:** Sitemap exists but URLs not discovered
**Why it happens:** XML namespace issues, gzip not detected, sitemap index not followed
**How to avoid:** Use existing `SitemapParser` which handles all these cases
**Warning signs:** Zero URLs from sitemap for sites that clearly have one

## Code Examples

Verified patterns from existing implementation:

### Starting a Crawl
```python
# Source: backend/app/crawlers/crawl_worker.py
from app.crawlers.crawl_worker import CrawlWorker, CrawlConfig

config = CrawlConfig(
    max_pages=50,
    max_time_seconds=300,
    max_depth=3,
    respect_robots=True,
    checkpoint_interval_pages=10,
)

worker = CrawlWorker(config=config)
worker.set_callbacks(
    on_progress=lambda p: print(f"Progress: {p.pages_crawled}"),
    on_page=lambda page: store_page(page),
)

result = worker.crawl(start_url="https://example.com")
print(f"Crawled {result.progress.pages_crawled} pages, stopped: {result.stopped_reason}")
```

### Checking robots.txt
```python
# Source: backend/app/crawlers/robots_parser.py
from app.crawlers.robots_parser import RobotsParser

parser = RobotsParser()

# Check if URL is allowed
if parser.is_allowed("https://example.com/admin"):
    print("Can crawl")
else:
    print("Blocked by robots.txt")

# Get crawl delay
delay = parser.get_crawl_delay("https://example.com")
if delay:
    print(f"Respect {delay}s delay")

# Get sitemaps from robots.txt
sitemaps = parser.get_sitemaps("https://example.com")
```

### Fetching with Rate Limiting
```python
# Source: backend/app/crawlers/rate_limiter.py
from app.crawlers.rate_limiter import RateLimiter, RateLimitedContext

limiter = RateLimiter()

# Blocking acquire
if limiter.acquire(url, blocking=True, timeout=30.0):
    try:
        response = requests.get(url)
    finally:
        limiter.release(url)

# Or use context manager
with RateLimitedContext(limiter, url):
    response = requests.get(url)
```

### Parsing Sitemaps
```python
# Source: backend/app/crawlers/sitemap_parser.py
from app.crawlers.sitemap_parser import SitemapParser

parser = SitemapParser()
result = parser.get_urls("https://example.com", max_urls=1000)

print(f"Found {len(result.urls)} URLs")
for sitemap_url in result.urls:
    print(f"  {sitemap_url.url} (lastmod: {sitemap_url.lastmod})")
```

### Detecting External Links
```python
# Source: backend/app/crawlers/external_links.py
from app.crawlers.external_links import ExternalLinkDetector

detector = ExternalLinkDetector()
links = detector.detect_links(html_content, source_url="https://example.com")

for link in links:
    print(f"{link.platform}: {link.url} ({link.link_type})")
    # e.g., "linkedin: https://linkedin.com/company/example (company)"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Selenium WebDriver | Playwright | 2020-2022 | Faster, better async support, cross-browser |
| robots.txt ignored | robots.txt mandatory | Always | Legal/ethical requirement |
| Sequential crawling | Concurrent with rate limits | Always | 3-5x faster while respectful |
| MD5 content hash | SHA-256 | SHA-256 is standard | Better collision resistance |

**Deprecated/outdated:**
- PhantomJS: Discontinued, use Playwright
- Mechanize: Outdated, use requests + BeautifulSoup
- urllib2: Use requests library instead

## Open Questions

Things that couldn't be fully resolved:

1. **Browser resource limits under high load**
   - What we know: Pool size is 3 contexts by default
   - What's unclear: Optimal pool size for production with multiple concurrent crawls
   - Recommendation: Start with 3, monitor memory, adjust based on load testing

2. **Social media rate limits**
   - What we know: External link following is configurable
   - What's unclear: LinkedIn/Twitter may block even polite crawlers
   - Recommendation: May need platform-specific user-agent or API integration

3. **Very large sitemaps**
   - What we know: MAX_URLS is 10000, MAX_SITEMAPS is 50
   - What's unclear: Performance with enterprise sites having 100k+ URLs
   - Recommendation: Current limits are reasonable; stream processing if needed

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/crawlers/*.py` - Fully implemented and tested
- IMPLEMENTATION_PLAN.md - Task definitions for Phase 4 (Crawling Engine)
- Project STACK.md - Technology versions and configuration

### Secondary (MEDIUM confidence)
- Playwright Python documentation - API patterns verified against implementation
- Python requests library documentation - HTTP client usage patterns

### Tertiary (LOW confidence)
- None - All findings verified against existing implementation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified against existing implementation
- Architecture: HIGH - Patterns extracted from working code
- Pitfalls: HIGH - Common issues documented with existing mitigations

**Research date:** 2026-01-19
**Valid until:** Indefinite - codebase is the source of truth

## Requirement Coverage Analysis

Based on codebase analysis, here is the implementation status of Phase 1 requirements:

### Web Crawling Requirements

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| CRL-01: Sitemap.xml parsing | IMPLEMENTED | `backend/app/crawlers/sitemap_parser.py` |
| CRL-02: JS rendering via Playwright | IMPLEMENTED | `backend/app/crawlers/browser_manager.py` |
| CRL-03: robots.txt compliance | IMPLEMENTED | `backend/app/crawlers/robots_parser.py` |
| CRL-04: Rate limiting (1/sec, 3 concurrent) | IMPLEMENTED | `backend/app/crawlers/rate_limiter.py` |
| CRL-05: High-value page prioritization | IMPLEMENTED | `backend/app/crawlers/page_priority_queue.py` |
| CRL-06: Max pages/depth config | IMPLEMENTED | `CrawlConfig` in `crawl_worker.py` |
| CRL-07: External social link extraction | IMPLEMENTED | `backend/app/crawlers/external_links.py` |

### API Requirements

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| API-01: POST /companies | IMPLEMENTED | `backend/app/api/routes/companies.py` |
| API-03: GET /companies (list) | IMPLEMENTED | `backend/app/api/routes/companies.py` |
| API-04: GET /companies/:id | IMPLEMENTED | `backend/app/api/routes/companies.py` |

### UI Requirements

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| UI-01: Company submission form | IMPLEMENTED | `frontend/src/pages/AddCompany.tsx` |
| UI-02: Company list with status | IMPLEMENTED | `frontend/src/pages/Dashboard.tsx` |

### Summary

All Phase 1 requirements appear to be implemented in the existing codebase. Planning should focus on:
1. Integration testing of the full crawl pipeline
2. End-to-end verification that all components work together
3. Edge case testing (error handling, timeouts, malformed content)
4. Performance validation under realistic loads
