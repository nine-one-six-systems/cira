# Web Crawling Engine Specification

## Overview

The web crawling engine is responsible for discovering and fetching pages from company websites. It handles sitemap parsing, JavaScript rendering, polite crawling with rate limiting, and robots.txt compliance.

## Functional Requirements

### Page Discovery (FR-CRL-001 to FR-CRL-004)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CRL-001 | Parse sitemap.xml when available for efficient page discovery | P0 |
| FR-CRL-002 | Prioritize key page types: About, Team, Products, Services, Contact, Careers | P0 |
| FR-CRL-003 | Implement breadth-first crawling with configurable depth limit | P0 |
| FR-CRL-004 | Detect and skip duplicate content using content hashing | P1 |

### Crawl Behavior (FR-CRL-005 to FR-CRL-010)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-CRL-005 | Respect robots.txt directives | P0 |
| FR-CRL-006 | Implement rate limiting (1 request/second default) | P0 |
| FR-CRL-007 | Handle JavaScript-rendered content using Playwright | P0 |
| FR-CRL-008 | Skip binary files except text-containing PDFs | P1 |
| FR-CRL-009 | Stop crawling when time limit reached | P0 |
| FR-CRL-010 | Stop crawling when max page limit reached | P0 |

### External Link Following (FR-EXT-001 to FR-EXT-004)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-EXT-001 | Extract and optionally follow LinkedIn company profile links | P1 |
| FR-EXT-002 | Extract and optionally follow Twitter/X company profile links | P1 |
| FR-EXT-003 | Extract and optionally follow Facebook business page links | P1 |
| FR-EXT-004 | Mark external pages distinctly in storage | P1 |

## Acceptance Criteria

### Sitemap Parsing
- Sitemap detected at domain root (`/sitemap.xml`)
- Sitemap index files with multiple sitemaps handled
- Gzipped sitemaps decompressed and parsed
- URLs extracted with lastmod dates when available
- Falls back to crawl-based discovery if no sitemap

### Page Prioritization
- Pages scored by URL pattern matching
- Priority order: About > Team > Products > Services > Contact > Careers > Pricing > Other
- BFS order maintained within same priority level

### Rate Limiting
- Default 1 request/second per domain
- Respects Crawl-delay from robots.txt if higher
- No parallel requests to same domain
- Token bucket algorithm for burst handling

### Playwright Rendering
- Headless browser mode
- 30-second timeout per page
- Viewport: 1920x1080
- User-Agent: "CIRA Bot/1.0"
- Waits for JavaScript content to render

## Test Requirements

### Programmatic Tests

1. **Sitemap Parser Tests**
   - Valid sitemap.xml returns list of URLs
   - Sitemap index returns aggregated URLs
   - Gzipped sitemap decompresses correctly
   - Invalid XML doesn't crash parser
   - Missing sitemap returns empty list gracefully

2. **Rate Limiter Tests**
   - Requests to same domain spaced >= 1 second apart
   - Different domains can be crawled in parallel
   - Crawl-delay override from robots.txt respected
   - Burst requests queued correctly

3. **robots.txt Tests**
   - Disallowed paths blocked
   - Allowed paths permitted
   - User-agent specific rules applied
   - Crawl-delay extracted
   - Missing robots.txt defaults to allow all

4. **Page Priority Tests**
   - /about-us scores higher than /blog
   - /team scores higher than /careers
   - URLs normalized before comparison

5. **Duplicate Detection Tests**
   - Same content on different URLs detected
   - Content hash computed consistently
   - Hash stored and retrieved correctly

### Performance Tests

- Crawl speed: 1-2 pages/second (with rate limiting)
- Memory stable over 100+ pages
- Browser crash recovery works

## Data Models

### Page

```typescript
interface Page {
  id: string;
  companyId: string;
  url: string;
  pageType: PageType;
  contentHash: string;
  rawHtml: string;
  extractedText: string;
  crawledAt: Date;
  isExternal: boolean;
}

enum PageType {
  ABOUT = 'about',
  TEAM = 'team',
  PRODUCT = 'product',
  SERVICE = 'service',
  CONTACT = 'contact',
  CAREERS = 'careers',
  PRICING = 'pricing',
  BLOG = 'blog',
  NEWS = 'news',
  OTHER = 'other'
}
```

### CrawlSession

```typescript
interface CrawlSession {
  id: string;
  companyId: string;
  pagesCrawled: number;
  pagesQueued: number;
  crawlDepthReached: number;
  externalLinksFollowed: number;
  status: CrawlStatus;
  checkpointData: CheckpointData;
  createdAt: Date;
  updatedAt: Date;
}

enum CrawlStatus {
  ACTIVE = 'active',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  TIMEOUT = 'timeout'
}
```

## Configuration

```typescript
interface CrawlConfig {
  maxPages: number;        // Default: 100 (thorough), 20 (quick)
  maxDepth: number;        // Default: 3 (thorough), 2 (quick)
  timeLimitMinutes: number; // Default: 30
  rateLimit: number;       // Requests per second, default: 1
  followLinkedIn: boolean;
  followTwitter: boolean;
  followFacebook: boolean;
  exclusionPatterns: string[];
}
```

## Dependencies

- Playwright 1.40+ for JavaScript rendering
- BeautifulSoup4 for HTML parsing
- Redis for crawl state and rate limiting
