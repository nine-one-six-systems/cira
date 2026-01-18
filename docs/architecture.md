# CIRA Architecture Overview

This document describes the system architecture of CIRA (Company Intelligence Research Assistant).

## System Overview

CIRA is a full-stack web application that automates company research and analysis using web crawling, NLP entity extraction, and AI-powered analysis.

```
┌─────────────────────────────────────────────────────────────────┐
│                         CIRA Architecture                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐       ┌──────────────┐       ┌──────────────┐ │
│  │   Frontend   │──────▶│   Backend    │──────▶│   Workers    │ │
│  │   (React)    │◀──────│   (Flask)    │◀──────│   (Celery)   │ │
│  └──────────────┘       └──────────────┘       └──────────────┘ │
│         │                      │                      │         │
│         │                      ▼                      ▼         │
│         │               ┌──────────────┐       ┌──────────────┐ │
│         │               │   Database   │       │    Redis     │ │
│         │               │  (SQLite)    │       │   (Cache)    │ │
│         │               └──────────────┘       └──────────────┘ │
│         │                      │                      │         │
│         │                      └──────────┬───────────┘         │
│         │                                 │                     │
│         │                      ┌──────────▼───────────┐         │
│         │                      │   External Services  │         │
│         │                      │ • Claude API         │         │
│         │                      │ • Target Websites    │         │
│         └──────────────────────┴──────────────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend (React)

**Technology Stack:**
- React 18+ with TypeScript
- TanStack Query for data fetching
- React Router for navigation
- Tailwind CSS for styling
- Axios for HTTP client

**Key Components:**
- `Dashboard` - Company list with filtering, sorting, pagination
- `AddCompany` - Single company input form
- `BatchUpload` - CSV batch upload interface
- `CompanyProgress` - Real-time progress monitoring
- `CompanyResults` - Analysis results with tabs
- `Settings` - Configuration management

**State Management:**
- Server state via TanStack Query (caching, invalidation)
- Local state via React hooks
- Settings persistence via localStorage

### Backend (Flask)

**Technology Stack:**
- Flask 3.0+ with application factory pattern
- SQLAlchemy 2.0+ ORM
- Pydantic for request/response validation
- Flask-CORS for cross-origin requests
- Gunicorn for production serving

**API Structure:**
```
/api/v1/
├── health              # Health check
├── companies/          # Company CRUD
│   ├── POST            # Create company
│   ├── GET             # List companies
│   ├── GET /:id        # Get company details
│   ├── DELETE /:id     # Delete company
│   ├── POST /batch     # Batch upload
│   ├── POST /:id/pause     # Pause analysis
│   ├── POST /:id/resume    # Resume analysis
│   ├── POST /:id/rescan    # Re-scan company
│   ├── GET /:id/progress   # Progress polling
│   ├── GET /:id/entities   # Entity listing
│   ├── GET /:id/pages      # Page listing
│   ├── GET /:id/tokens     # Token usage
│   ├── GET /:id/versions   # Version history
│   ├── GET /:id/compare    # Version comparison
│   └── GET /:id/export     # Export analysis
├── batches/            # Batch operations
└── config/             # Configuration
```

### Workers (Celery)

**Technology Stack:**
- Celery 5.3+ for distributed task processing
- Redis as message broker and result backend

**Processing Pipeline:**
```
QUEUED → CRAWLING → EXTRACTING → ANALYZING → GENERATING → COMPLETED
```

**Task Types:**
- `process_company` - Main orchestration task
- `crawl_company` - Web crawling phase
- `extract_entities` - NLP extraction phase
- `analyze_company` - Claude API analysis
- `generate_analysis` - Summary synthesis

### Data Layer

**Database (SQLAlchemy Models):**
- `Company` - Main entity with status, config, token usage
- `CrawlSession` - Crawl tracking with checkpoints
- `Page` - Crawled pages with content
- `Entity` - Extracted entities (people, orgs, etc.)
- `Analysis` - AI analysis results
- `TokenUsage` - Per-call token tracking
- `BatchJob` - Batch operation tracking

**Caching (Redis):**
- Progress updates (2-second polling)
- Checkpoint data for pause/resume
- Rate limiting state
- robots.txt cache (24 hours)

## Processing Flow

### Company Analysis Flow

```
1. User submits company URL
   │
2. Company created in DB (status: PENDING)
   │
3. Celery task queued
   │
4. CRAWLING PHASE
   ├── Fetch robots.txt
   ├── Parse sitemap.xml
   ├── Prioritize URLs (About, Team, Products, etc.)
   ├── Crawl pages with rate limiting
   ├── Render JS pages with Playwright
   └── Store pages in DB
   │
5. EXTRACTING PHASE
   ├── Run spaCy NLP pipeline
   ├── Extract named entities
   ├── Extract structured data (emails, phones)
   └── Deduplicate and merge entities
   │
6. ANALYZING PHASE
   ├── Prepare content for Claude
   ├── Call Claude API per section
   ├── Track token usage
   └── Store raw insights
   │
7. GENERATING PHASE
   ├── Synthesize analysis sections
   ├── Generate executive summary
   └── Store final analysis
   │
8. Company status: COMPLETED
```

### Checkpoint & Recovery

```
Every 10 pages or 2 minutes:
├── Save checkpoint to DB
│   ├── pages_visited
│   ├── pages_queued
│   ├── current_depth
│   └── entities_extracted
│
On pause:
├── Save final checkpoint
├── Stop workers gracefully
└── Update status: PAUSED

On resume:
├── Load checkpoint
├── Skip visited URLs
└── Continue from queue
```

## Security Architecture

### Input Validation
- Pydantic schemas for all API requests
- URL format and reachability validation
- File type validation for uploads

### Authentication & Authorization
- Currently single-user (no auth required)
- API keys for external services (env vars)

### Security Headers
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; ...
Strict-Transport-Security: max-age=31536000 (production)
```

### Data Protection
- SQLAlchemy ORM prevents SQL injection
- HTML escaping for user-generated content
- Secure file download headers
- SSRF protection (blocked private IPs)

## Performance Considerations

### Web Crawling
- Rate limiting: 1 request/second per domain
- robots.txt compliance
- Parallel crawling across domains
- Content hash deduplication

### API Performance
- Redis caching for progress updates
- Indexed database columns
- Connection pooling
- Response time target: <200ms

### Export Generation
- Target: <5 seconds
- Formats: Markdown, Word, PDF, JSON

## Scalability

### Horizontal Scaling
- Stateless backend (scale with load balancer)
- Celery workers (scale independently)
- Redis cluster (if needed)

### Vertical Scaling
- Worker concurrency configuration
- Database connection pooling
- Memory limits per container

## External Dependencies

| Service | Purpose | Fallback |
|---------|---------|----------|
| Claude API | AI analysis | Required |
| Target websites | Data source | Graceful handling |
| Redis | Caching/queuing | In-memory fallback |

## Monitoring Points

### Health Endpoints
- `/api/v1/health` - Backend health
- Redis ping
- Celery worker inspection

### Key Metrics
- API response times
- Task queue depth
- Token usage per analysis
- Error rates

### Logging
- Structured logging to files
- Log levels: DEBUG, INFO, WARNING, ERROR
- Request/response logging
- Task execution logging
