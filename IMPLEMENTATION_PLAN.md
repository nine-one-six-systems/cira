# CIRA Implementation Plan

## Overview

This implementation plan covers the development of CIRA (Company Intelligence Research Assistant), a web-based application for automated company research and analysis. The plan is organized into 10 phases, with tasks sorted by priority within each phase.

**Project Status:** In Progress - Phase 1-6 Complete (834 backend tests), Phase 7 Complete (136 frontend tests), Phase 8 Tasks 8.1-8.5, 8.7 Complete, Phase 9 Tasks 9.1-9.6 Complete, Phase 10 Task 10.4 Complete (1049 backend tests, 167 frontend tests)

**Tech Stack:**
- Frontend: React 18+, TypeScript 5.0+, Vite 5.0+, TanStack Query 5.0+, Tailwind CSS 3.4+
- Backend: Python 3.11+, Flask 3.0+, SQLAlchemy 2.0+, Celery 5.3+
- Infrastructure: SQLite, Redis 7.0+, Docker
- AI/ML: spaCy 3.7+, Claude API (Anthropic SDK 0.18+)
- Crawling: Playwright 1.40+, BeautifulSoup4 4.12+

---

## Phase 1: Foundation (Project Scaffolding)

### Task 1.1: Initialize Project Repository Structure
**Priority:** P0 | **Component:** Infrastructure

**Description:** Create monorepo structure with frontend/, backend/, docker/, and docs/ directories.

**Acceptance Criteria:**
- Project root contains proper directory structure
- README.md with setup instructions
- .gitignore for Python, Node.js, IDE files
- .env.example with all required variables

**Test Requirements:**
- [ ] Directory structure matches specification
- [ ] .gitignore excludes appropriate files

**Dependencies:** None

---

### Task 1.2: Backend Python Project Setup
**Priority:** P0 | **Component:** Backend Infrastructure

**Description:** Initialize Flask backend with application factory pattern, configuration management, and health endpoint.

**Acceptance Criteria:**
- Flask 3.0+ with app factory (`create_app()`)
- Environment-based config (dev, test, prod)
- Health endpoint: `GET /api/v1/health` returns 200
- Logging configured

**Test Requirements:**
- [ ] Health endpoint returns `{"status": "healthy"}`
- [ ] App starts without errors
- [ ] Config loads from environment

**Dependencies:** Task 1.1

---

### Task 1.3: Frontend React/TypeScript Project Setup
**Priority:** P0 | **Component:** Frontend Infrastructure

**Description:** Initialize React 18+ with Vite, TypeScript, TanStack Query, React Router, and Tailwind CSS.

**Acceptance Criteria:**
- Vite + React + TypeScript template
- TanStack Query configured
- React Router with route structure
- Tailwind CSS with design system tokens
- ESLint and Prettier configured

**Test Requirements:**
- [ ] `npm run dev` starts successfully
- [ ] `npm run build` produces bundle
- [ ] `npm run lint` passes
- [ ] TypeScript strict mode compiles

**Dependencies:** Task 1.1

---

### Task 1.4: Docker Compose Development Environment
**Priority:** P0 | **Component:** Infrastructure

**Description:** Create Docker Compose for local development with backend, frontend, Redis, and Celery.

**Acceptance Criteria:**
- Services: backend (5000), frontend (5173), redis (6379), celery-worker
- Volume mounts for hot-reloading
- Environment variable injection from .env

**Test Requirements:**
- [ ] `docker-compose up` starts all services
- [ ] Backend health accessible at localhost:5000
- [ ] Frontend accessible at localhost:5173
- [ ] Redis responds to ping

**Dependencies:** Tasks 1.2, 1.3

---

### Task 1.5: SQLAlchemy Database Schema Design
**Priority:** P0 | **Component:** Backend - Data Layer

**Description:** Implement SQLAlchemy 2.0+ models for Company, CrawlSession, Page, Entity, Analysis, TokenUsage.

**Acceptance Criteria:**
- Models match PRD data model specs (Section 3.1)
- All relationships defined with cascade deletes
- Indexes on company_id, status, created_at
- Enums: CompanyStatus, CrawlStatus, AnalysisMode, PageType, EntityType, ApiCallType
- JSON columns for CheckpointData, AnalysisSections

**Test Requirements:**
- [ ] Models create tables in SQLite
- [ ] Relationships work correctly
- [ ] Enum validation works
- [ ] JSON serialize/deserialize works

**Dependencies:** Task 1.2

---

### Task 1.6: Database Migration Infrastructure
**Priority:** P0 | **Component:** Backend - Data Layer

**Description:** Configure Alembic with Flask-Migrate for database migrations.

**Acceptance Criteria:**
- Alembic integrated with Flask-Migrate
- Initial migration creates all tables
- Commands: `flask db init`, `flask db migrate`, `flask db upgrade`

**Test Requirements:**
- [ ] Fresh database created via `flask db upgrade`
- [ ] Downgrade removes tables cleanly
- [ ] Autogeneration detects model changes

**Dependencies:** Task 1.5

---

### Task 1.7: Pydantic Request/Response Schemas
**Priority:** P0 | **Component:** Backend - API Layer

**Description:** Implement Pydantic 2.5+ schemas for API validation per PRD Section 7.

**Acceptance Criteria:**
- Request: CompanyCreate, BatchUploadConfig, AnalysisConfig, ExportOptions
- Response: CompanyResponse, ProgressUpdate, AnalysisResponse
- Wrappers: ApiResponse[T], PaginatedResponse[T]
- URL validation, custom validators

**Test Requirements:**
- [ ] Invalid URLs rejected with error
- [ ] Missing required fields return 400
- [ ] Pagination metadata calculated correctly

**Dependencies:** Task 1.2

---

## Phase 2: Backend Core (API Endpoints)

### Task 2.1: Company CRUD API Endpoints
**Priority:** P0 | **Component:** Backend - API

**Description:** Implement company management endpoints: create, list, get, delete.

**Acceptance Criteria:**
- `POST /api/v1/companies` - Create with validation (FR-INP-001, FR-INP-002)
- `GET /api/v1/companies` - List with filtering, sorting, pagination
- `GET /api/v1/companies/:id` - Get with analysis data
- `DELETE /api/v1/companies/:id` - Delete with cascade
- ApiResponse format, error codes per PRD Section 7.4

**Test Requirements:**
- [ ] Create with valid data returns 201
- [ ] Create with invalid URL returns 400
- [ ] List respects status filter and sort order
- [ ] Pagination returns correct metadata
- [ ] Get non-existent returns 404
- [ ] Delete removes all related records

**Dependencies:** Tasks 1.5, 1.7

---

### Task 2.2: Batch Upload API Endpoint
**Priority:** P0 | **Component:** Backend - API

**Description:** Implement CSV batch upload (POST /api/v1/companies/batch).

**Acceptance Criteria:**
- Accept multipart/form-data CSV (FR-BAT-001)
- Parse CSV: company_name, website_url, industry
- Validate rows independently
- Return BatchUploadResult with per-row status

**Test Requirements:**
- [ ] Valid CSV creates all companies (201)
- [ ] Invalid rows return partial success with errors
- [ ] Missing columns returns 400
- [ ] 100+ rows processes successfully
- [ ] Template download endpoint works (FR-BAT-002)

**Dependencies:** Task 2.1

---

### Task 2.3: Company Control API Endpoints
**Priority:** P0 | **Component:** Backend - API

**Description:** Implement pause, resume, rescan endpoints.

**Acceptance Criteria:**
- `POST /api/v1/companies/:id/pause` - Pause in_progress (FR-STA-003)
- `POST /api/v1/companies/:id/resume` - Resume paused (FR-STA-004)
- `POST /api/v1/companies/:id/rescan` - Re-scan completed (FR-RSC-002)
- State transition validation

**Test Requirements:**
- [ ] Pause on in_progress succeeds, saves checkpoint
- [ ] Pause on other states returns 422
- [ ] Resume on paused succeeds with checkpoint
- [ ] Resume on non-paused returns 422
- [ ] Rescan on completed creates new version
- [ ] Rescan on non-completed returns 422

**Dependencies:** Task 2.1

---

### Task 2.4: Progress Polling API Endpoint
**Priority:** P0 | **Component:** Backend - API

**Description:** Implement progress endpoint for real-time status.

**Acceptance Criteria:**
- `GET /api/v1/companies/:id/progress` returns ProgressUpdate
- Includes: phase, pagesCrawled, entitiesExtracted, tokensUsed, timeElapsed, estimatedTimeRemaining, currentActivity
- Data from Redis cache for performance

**Test Requirements:**
- [ ] Returns correct phase for each stage
- [ ] Time elapsed calculated correctly
- [ ] Estimated time remaining reasonable
- [ ] Response time < 200ms

**Dependencies:** Tasks 2.1, 3.1

---

### Task 2.5: Entity and Page API Endpoints
**Priority:** P1 | **Component:** Backend - API

**Description:** Implement entity and page listing endpoints.

**Acceptance Criteria:**
- `GET /api/v1/companies/:id/entities` - Paginated, filterable by type/confidence
- `GET /api/v1/companies/:id/pages` - Paginated, filterable by pageType

**Test Requirements:**
- [ ] Entity filter by type works
- [ ] Entity filter by minConfidence works
- [ ] Page filter by pageType works
- [ ] External pages marked with isExternal

**Dependencies:** Task 2.1

---

### Task 2.6: Token Usage API Endpoint
**Priority:** P0 | **Component:** Backend - API

**Description:** Implement token usage tracking endpoint.

**Acceptance Criteria:**
- `GET /api/v1/companies/:id/tokens` returns TokenBreakdown
- Includes totalTokens, totalInputTokens, totalOutputTokens, estimatedCost
- byApiCall breakdown with timestamps

**Test Requirements:**
- [ ] Totals match sum of API calls
- [ ] Cost estimation accurate
- [ ] Historical calls queryable

**Dependencies:** Task 2.1

---

### Task 2.7: Configuration API Endpoints
**Priority:** P1 | **Component:** Backend - API

**Description:** Implement configuration management endpoints.

**Acceptance Criteria:**
- `GET /api/v1/config` - Return defaults and mode configs
- `PUT /api/v1/config` - Update configuration
- Persist to database or config file

**Test Requirements:**
- [ ] Get returns all defaults
- [ ] Put updates persist
- [ ] Invalid values rejected

**Dependencies:** Task 2.1

---

### Task 2.8: Version History and Comparison API
**Priority:** P1 | **Component:** Backend - API

**Description:** Implement version history and comparison endpoints.

**Acceptance Criteria:**
- `GET /api/v1/companies/:id/versions` - List versions (max 3)
- `GET /api/v1/companies/:id/compare` - Compare versions (FR-RSC-003, FR-RSC-004)
- Identify changes in team, products, content

**Test Requirements:**
- [ ] Versions endpoint returns correct count
- [ ] Compare identifies field-level changes
- [ ] Change types categorized correctly
- [ ] significantChanges flag set appropriately

**Dependencies:** Tasks 2.1, 2.3

---

## Phase 3: Worker Infrastructure

### Task 3.1: Redis Configuration and Connection
**Priority:** P0 | **Component:** Infrastructure

**Description:** Configure Redis for caching, sessions, and Celery broker.

**Acceptance Criteria:**
- Redis client in Flask app
- Connection pooling
- Health check for Redis
- Cache key namespace

**Test Requirements:**
- [ ] Connection succeeds on startup
- [ ] Cache get/set works
- [ ] Handles Redis unavailability gracefully

**Dependencies:** Task 1.4

---

### Task 3.2: Celery Application Setup
**Priority:** P0 | **Component:** Backend - Workers

**Description:** Configure Celery 5.3+ with Redis broker.

**Acceptance Criteria:**
- Celery integrated with Flask app factory
- Redis as broker and result backend
- Task retry with exponential backoff
- Task routing: crawl, extract, analyze queues

**Test Requirements:**
- [ ] Worker starts without errors
- [ ] Tasks dispatched and received
- [ ] Results stored and retrievable
- [ ] Failed tasks retry with backoff

**Dependencies:** Task 3.1

---

### Task 3.3: Job Queue Management Service
**Priority:** P0 | **Component:** Backend - Workers

**Description:** Implement job orchestration for analysis pipeline.

**Acceptance Criteria:**
- Pipeline: QUEUED -> CRAWLING -> EXTRACTING -> ANALYZING -> GENERATING -> COMPLETED
- Stage transitions logged
- Failure handling with status updates
- Auto-resume in_progress on startup (FR-STA-005)

**Test Requirements:**
- [ ] Jobs progress through all stages
- [ ] Failures stop pipeline and set status
- [ ] Resume after restart works
- [ ] Parallel jobs work correctly

**Dependencies:** Task 3.2

---

### Task 3.4: Progress State Management
**Priority:** P0 | **Component:** Backend - Workers

**Description:** Implement Redis-based progress tracking.

**Acceptance Criteria:**
- Progress updates every 2 seconds (NFR-PER-006)
- All ProgressUpdate fields included
- Stale progress detection (worker crash)

**Test Requirements:**
- [ ] Updates visible within 2 seconds
- [ ] Concurrent jobs maintain separate progress
- [ ] Stale progress detected after 60 seconds

**Dependencies:** Tasks 3.1, 3.3

---

### Task 3.5: Checkpoint Persistence Service
**Priority:** P0 | **Component:** Backend - Workers

**Description:** Implement checkpoint save/load for pause/resume.

**Acceptance Criteria:**
- Checkpoint every 10 pages or 2 minutes (FR-STA-001)
- CheckpointData contains all PRD fields
- Stored in CrawlSession.checkpointData
- Resume skips visited URLs (FR-STA-007)

**Test Requirements:**
- [ ] Checkpoint has accurate counts/timestamps
- [ ] Resume skips visited URLs
- [ ] Checkpoint survives restart
- [ ] Partial checkpoint handled gracefully

**Dependencies:** Tasks 3.3, 1.5

---

## Phase 4: Crawling Engine

### Task 4.1: robots.txt Parser and Cache
**Priority:** P0 | **Component:** Backend - Crawler

**Description:** Implement robots.txt parsing with caching.

**Acceptance Criteria:**
- Parse robots.txt for domains (FR-CRL-005)
- Cache rules for 24 hours
- Respect Disallow directives
- Honor Crawl-delay
- Handle missing robots.txt gracefully

**Test Requirements:**
- [ ] Disallowed paths blocked
- [ ] Allowed paths permitted
- [ ] Crawl-delay extracted
- [ ] Cache hit avoids re-fetch
- [ ] Malformed robots.txt doesn't crash

**Dependencies:** Task 3.3

---

### Task 4.2: Rate Limiter Service
**Priority:** P0 | **Component:** Backend - Crawler

**Description:** Implement per-domain rate limiting.

**Acceptance Criteria:**
- Default 1 req/sec per domain (FR-CRL-006)
- Respect Crawl-delay if higher
- Token bucket for bursts
- No parallel requests to same domain

**Test Requirements:**
- [ ] Same-domain requests spaced correctly
- [ ] Different domains crawled in parallel
- [ ] Crawl-delay override respected

**Dependencies:** Task 4.1

---

### Task 4.3: Playwright Browser Manager
**Priority:** P0 | **Component:** Backend - Crawler

**Description:** Implement Playwright for JS-rendered pages.

**Acceptance Criteria:**
- Headless mode, 30s timeout, 1920x1080 viewport (FR-CRL-007)
- User-Agent: "CIRA Bot/1.0"
- Browser pool for concurrency
- Graceful cleanup on shutdown

**Test Requirements:**
- [ ] SPA pages render JS content
- [ ] Timeout fires after 30 seconds
- [ ] Browser crash recovery works
- [ ] Memory stable over many pages

**Dependencies:** Task 3.3

---

### Task 4.4: Sitemap Parser
**Priority:** P0 | **Component:** Backend - Crawler

**Description:** Implement sitemap.xml parsing.

**Acceptance Criteria:**
- Detect sitemap at domain root (FR-CRL-001)
- Support sitemap index files
- Extract URLs with lastmod
- Handle gzipped sitemaps
- Fallback to crawl-based discovery

**Test Requirements:**
- [ ] Standard sitemap parsed
- [ ] Sitemap index handled
- [ ] Gzipped sitemap decompressed
- [ ] Missing sitemap doesn't block crawling

**Dependencies:** Task 4.3

---

### Task 4.5: Page Priority Queue
**Priority:** P0 | **Component:** Backend - Crawler

**Description:** Implement URL prioritization.

**Acceptance Criteria:**
- Priority for: About, Team, Products, Services, Contact, Careers (FR-CRL-002)
- BFS within same priority (FR-CRL-003)
- Configurable max depth
- URL normalization and deduplication

**Test Requirements:**
- [ ] /about prioritized over /blog
- [ ] Depth limit enforced
- [ ] Duplicates deduplicated
- [ ] Normalized URLs matched

**Dependencies:** Task 4.4

---

### Task 4.6: Crawl Worker Implementation
**Priority:** P0 | **Component:** Backend - Crawler

**Description:** Implement main crawl worker.

**Acceptance Criteria:**
- Fetches from priority queue
- Respects rate limits and robots.txt
- Extracts links, adds to queue
- Stores HTML and text to Page table
- Content hash for duplicates (FR-CRL-004)
- Stops on time/page limit (FR-CRL-009, FR-CRL-010)
- Updates checkpoint every 10 pages/2 min

**Test Requirements:**
- [ ] Crawl speed 1-2 pages/sec
- [ ] Pages stored with correct metadata
- [ ] Content hash detects duplicates
- [ ] Time limit triggers clean stop
- [ ] Page limit triggers clean stop

**Dependencies:** Tasks 4.1, 4.2, 4.3, 4.5, 3.5

---

### Task 4.7: Page Type Classification
**Priority:** P1 | **Component:** Backend - Crawler

**Description:** Implement automatic page type classification.

**Acceptance Criteria:**
- Classify: about, team, product, service, contact, careers, pricing, blog, news, other
- Use URL patterns and content
- Store in Page.pageType

**Test Requirements:**
- [ ] /about-us classified as 'about'
- [ ] /team classified as 'team'
- [ ] Ambiguous pages classified as 'other'

**Dependencies:** Task 4.6

---

### Task 4.8: External Link Detection and Following
**Priority:** P1 | **Component:** Backend - Crawler

**Description:** Detect and optionally crawl social media profiles.

**Acceptance Criteria:**
- Detect LinkedIn URLs (FR-EXT-001)
- Detect Twitter/X URLs (FR-EXT-002)
- Detect Facebook URLs (FR-EXT-003)
- Follow based on config
- Mark with isExternal flag (FR-EXT-004)

**Test Requirements:**
- [ ] Social URLs detected
- [ ] Following respects config
- [ ] External pages marked correctly

**Dependencies:** Task 4.6

---

### Task 4.9: PDF Text Extraction
**Priority:** P1 | **Component:** Backend - Crawler

**Description:** Extract text from PDF files.

**Acceptance Criteria:**
- Detect PDF links
- Extract text from PDFs with text layers (FR-CRL-008)
- Skip image-only PDFs
- Store text in Page table

**Test Requirements:**
- [ ] Text PDF extracts correctly
- [ ] Image PDF skipped without error
- [ ] Large PDF doesn't timeout

**Dependencies:** Task 4.6

---

## Phase 5: Entity Extraction

### Task 5.1: spaCy NLP Pipeline Setup
**Priority:** P0 | **Component:** Backend - Extraction

**Description:** Configure spaCy 3.7+ with en_core_web_lg model.

**Acceptance Criteria:**
- spaCy with en_core_web_lg installed
- Custom pipeline for domain entities
- Optimized for batch processing
- Configurable confidence thresholds

**Test Requirements:**
- [ ] Standard NER categories extracted
- [ ] Pipeline processes 1000+ tokens/sec
- [ ] Batch more efficient than single-doc

**Dependencies:** Task 3.3

---

### Task 5.2: Named Entity Extraction Worker
**Priority:** P0 | **Component:** Backend - Extraction

**Description:** Implement extraction worker with spaCy.

**Acceptance Criteria:**
- Extract: company names (FR-NER-001), locations (FR-NER-002), people with roles (FR-NER-003), products (FR-NER-004), orgs (FR-NER-005), dates (FR-NER-006), money (FR-NER-007)
- Store with confidence scores and context snippets

**Test Requirements:**
- [ ] CEO names extracted with role
- [ ] Products linked to descriptions
- [ ] Confidence scores > 0.7 for clear entities
- [ ] Context snippets useful

**Dependencies:** Tasks 5.1, 4.6

---

### Task 5.3: Structured Data Extraction (Regex)
**Priority:** P0 | **Component:** Backend - Extraction

**Description:** Pattern-based extraction for structured data.

**Acceptance Criteria:**
- Emails with validation (FR-STR-001)
- Phone numbers normalized (FR-STR-002)
- Physical addresses (FR-STR-003)
- Social handles (FR-STR-004)

**Test Requirements:**
- [ ] Valid emails extracted
- [ ] Phone formats handled
- [ ] Handles linked to platforms

**Dependencies:** Task 5.2

---

### Task 5.4: Tech Stack Detection
**Priority:** P2 | **Component:** Backend - Extraction

**Description:** Detect technology stack from content.

**Acceptance Criteria:**
- Detect languages, frameworks, tools (FR-STR-005)
- Source from job postings
- Categorize by type

**Test Requirements:**
- [ ] Common frameworks detected
- [ ] Categories assigned correctly

**Dependencies:** Task 5.2

---

### Task 5.5: Entity Deduplication and Merging
**Priority:** P1 | **Component:** Backend - Extraction

**Description:** Merge equivalent entities across pages.

**Acceptance Criteria:**
- Detect duplicates across pages
- Merge with highest confidence
- Maintain all source URLs

**Test Requirements:**
- [ ] Same person from multiple pages appears once
- [ ] Confidence reflects multiple mentions
- [ ] All source URLs preserved

**Dependencies:** Task 5.2

---

## Phase 6: AI Analysis

### Task 6.1: Anthropic Claude API Client
**Priority:** P0 | **Component:** Backend - Analysis

**Description:** Implement Claude API client with error handling.

**Acceptance Criteria:**
- API key from ANTHROPIC_API_KEY env
- Exponential backoff on 429
- Max 3 retries
- Timeout handling
- Response parsing with token counts

**Test Requirements:**
- [ ] Valid call returns response
- [ ] 429 triggers backoff
- [ ] 500 retries up to 3 times
- [ ] Timeout fires correctly

**Dependencies:** Task 3.3

---

### Task 6.2: Token Usage Tracking Service
**Priority:** P0 | **Component:** Backend - Analysis

**Description:** Track per-call token usage and cost.

**Acceptance Criteria:**
- Record input/output tokens per call (FR-TOK-001)
- Aggregate per company (FR-TOK-002)
- Calculate cost (FR-TOK-004)
- Store in TokenUsage table

**Test Requirements:**
- [ ] Counts match API response
- [ ] Aggregates sum correctly
- [ ] Cost accurate

**Dependencies:** Task 6.1

---

### Task 6.3: Content Analysis Prompts
**Priority:** P0 | **Component:** Backend - Analysis

**Description:** Design prompts for each analysis section.

**Acceptance Criteria:**
- Prompts for: executive summary (FR-SUM-001), overview, business model (FR-ANA-002), stage (FR-ANA-003), team (FR-ANA-001), market (FR-ANA-005), technology, red flags (FR-ANA-007)
- Include source citation instructions (FR-SUM-004)

**Test Requirements:**
- [ ] Prompts produce structured output
- [ ] Sources cited in responses
- [ ] Confidence indicators present

**Dependencies:** Task 6.1

---

### Task 6.4: Analysis Worker Implementation
**Priority:** P0 | **Component:** Backend - Analysis

**Description:** Implement analysis worker calling Claude API.

**Acceptance Criteria:**
- Process sections sequentially
- Pass entities and page content
- Store in Analysis table
- Update checkpoint per section
- Handle API errors with partial results

**Test Requirements:**
- [ ] All sections generated
- [ ] Partial results saved on failure
- [ ] Resume from last section
- [ ] Token tracking accurate

**Dependencies:** Tasks 6.1, 6.2, 6.3, 5.2

---

### Task 6.5: Analysis Synthesis and Summary Generation
**Priority:** P0 | **Component:** Backend - Analysis

**Description:** Synthesize sections into coherent analysis.

**Acceptance Criteria:**
- 3-4 paragraph executive summary (FR-SUM-001)
- Structured sections per AnalysisSections (FR-SUM-002)
- Include metadata (FR-OUT-002)
- Store complete analysis

**Test Requirements:**
- [ ] Summary coherent and comprehensive
- [ ] All sections populated
- [ ] Sources linked
- [ ] Fits ~2 pages rendered

**Dependencies:** Task 6.4

---

### Task 6.6: Cost Estimation Display
**Priority:** P0 | **Component:** Backend - Analysis

**Description:** Real-time cost estimation.

**Acceptance Criteria:**
- Calculate from token usage
- Include in progress updates (FR-TOK-003)
- Display in results

**Test Requirements:**
- [ ] Cost updates during analysis
- [ ] Final cost matches sum
- [ ] Currency format correct

**Dependencies:** Task 6.2

---

## Phase 7: Frontend Core

### Task 7.1: Design System Implementation
**Priority:** P0 | **Component:** Frontend - Core

**Description:** Implement Tailwind config with PRD design system.

**Acceptance Criteria:**
- Color palette configured
- Typography scale
- Spacing system (8px base)
- Custom components

**Test Requirements:**
- [ ] Colors render correctly
- [ ] Typography matches spec
- [ ] Spacing tokens correct

**Dependencies:** Task 1.3

---

### Task 7.2: Core UI Component Library
**Priority:** P0 | **Component:** Frontend - Components

**Description:** Implement base UI components from PRD Section 6.2.

**Acceptance Criteria:**
- Button, Input, Select, Checkbox, Slider
- Table, Card, Modal, Toast
- Progress Bar, Badge, Tabs, Skeleton

**Test Requirements:**
- [ ] All components render correctly
- [ ] Variants have correct styles
- [ ] Interactive elements functional

**Dependencies:** Task 7.1

---

### Task 7.3: React Router Configuration
**Priority:** P0 | **Component:** Frontend - Routing

**Description:** Configure routes for all pages.

**Acceptance Criteria:**
- Routes: /, /companies/:id, /companies/:id/progress, /add, /batch, /settings
- Layout with header
- 404 page
- Code splitting

**Test Requirements:**
- [ ] All routes render correct components
- [ ] Navigation works
- [ ] 404 for invalid paths

**Dependencies:** Task 1.3

---

### Task 7.4: TanStack Query API Hooks
**Priority:** P0 | **Component:** Frontend - Data

**Description:** Implement React Query hooks for API.

**Acceptance Criteria:**
- useCompanies(), useCompany(), useProgress()
- useCreateCompany(), useBatchUpload()
- usePauseCompany(), useResumeCompany(), useRescanCompany()
- Auto-refetch and cache invalidation

**Test Requirements:**
- [ ] List respects filters
- [ ] Progress polls correctly
- [ ] Mutations invalidate queries
- [ ] Errors handled

**Dependencies:** Tasks 1.3, 2.1-2.8

---

### Task 7.5: Axios API Client Configuration
**Priority:** P0 | **Component:** Frontend - Data

**Description:** Configure Axios with interceptors.

**Acceptance Criteria:**
- Base URL from env
- Request interceptor for headers
- Response interceptor for errors
- Standardized error format

**Test Requirements:**
- [ ] Requests have correct URL
- [ ] 4xx errors surfaced
- [ ] 5xx show friendly message
- [ ] Network errors handled

**Dependencies:** Task 1.3

---

## Phase 8: Frontend Features

### Task 8.1: Dashboard / Company List Page
**Priority:** P0 | **Component:** Frontend - Pages

**Description:** Main dashboard with company list.

**Acceptance Criteria:**
- Table: Name, Website, Status, Tokens, Actions
- Filters: status, date range, search
- Pagination
- Actions: View, Export, Delete
- Add/Upload buttons

**Test Requirements:**
- [ ] Companies display correctly
- [ ] Filters work
- [ ] Pagination works
- [ ] Actions trigger operations

**Dependencies:** Tasks 7.2, 7.4

---

### Task 8.2: Add Company Form Page
**Priority:** P0 | **Component:** Frontend - Pages

**Description:** Single company input form.

**Acceptance Criteria:**
- Fields: name, URL (with validation), industry
- Advanced config panel (collapsible)
- Submit creates and redirects to progress

**Test Requirements:**
- [ ] Required fields enforced
- [ ] Invalid URL shows error
- [ ] Submit succeeds

**Dependencies:** Tasks 7.2, 7.4

---

### Task 8.3: Batch Upload Page
**Priority:** P0 | **Component:** Frontend - Pages

**Description:** CSV batch upload interface.

**Acceptance Criteria:**
- File drop zone
- Template download
- Preview table with validation
- Confirm valid rows

**Test Requirements:**
- [ ] CSV parses correctly
- [ ] Errors highlighted
- [ ] Template downloads
- [ ] Shows success/failure counts

**Dependencies:** Tasks 7.2, 7.4

---

### Task 8.4: Progress View Page
**Priority:** P0 | **Component:** Frontend - Pages

**Description:** Real-time progress monitoring.

**Acceptance Criteria:**
- Progress bar with percentage
- Stats: Pages, Entities, Tokens
- Time elapsed/remaining
- Activity log
- Pause/Cancel buttons
- Auto-redirect on completion

**Test Requirements:**
- [ ] Updates every 2 seconds
- [ ] Stats increment
- [ ] Pause changes to Resume
- [ ] Redirect on completion

**Dependencies:** Tasks 7.2, 7.4, 2.4

---

### Task 8.5: Results View Page
**Priority:** P0 | **Component:** Frontend - Pages

**Description:** Analysis results display.

**Acceptance Criteria:**
- Tabs: Summary, Entities, Pages, Token Usage
- Summary: markdown, sidebar info
- Export dropdown
- Re-scan button

**Test Requirements:**
- [ ] Markdown renders correctly
- [ ] Tabs switch content
- [ ] Export triggers download
- [ ] Re-scan initiates analysis

**Dependencies:** Tasks 7.2, 7.4, 8.6

---

### Task 8.6: Domain-Specific Components
**Priority:** P0 | **Component:** Frontend - Components

**Description:** Domain components from PRD Section 6.2.

**Acceptance Criteria:**
- CompanyCard, ProgressTracker, TokenCounter
- AnalysisSummary, EntityTable, ExportDropdown
- ConfigPanel, BatchPreview
- VersionSelector, ChangeHighlight

**Test Requirements:**
- [ ] Each renders with mock data
- [ ] Interactive elements work
- [ ] Props passed correctly

**Dependencies:** Tasks 7.2, 8.1-8.5

---

### Task 8.7: Settings Page
**Priority:** P1 | **Component:** Frontend - Pages

**Description:** Configuration settings page.

**Acceptance Criteria:**
- Default analysis config
- Quick/Thorough mode presets
- Save/Reset options

**Test Requirements:**
- [ ] Settings display correctly
- [ ] Changes save
- [ ] Reset restores defaults

**Dependencies:** Tasks 7.2, 7.4, 2.7

---

## Phase 9: Advanced Features

### Task 9.1: Export Generation Service
**Priority:** P0 | **Component:** Backend - Export

**Description:** Generate exports in all formats.

**Acceptance Criteria:**
- Markdown (UTF-8) (FR-EXP-001)
- Word (.docx) with python-docx (FR-EXP-002)
- PDF with ReportLab (FR-EXP-003)
- JSON with all data (FR-EXP-004)
- Generation < 5 seconds (NFR-PER-005)

**Test Requirements:**
- [ ] Markdown valid
- [ ] Word opens in Microsoft Word
- [ ] PDF renders correctly
- [ ] JSON contains all fields
- [ ] Large exports within time limit

**Dependencies:** Tasks 6.5, 2.1

---

### Task 9.2: Export API Endpoint
**Priority:** P0 | **Component:** Backend - API

**Description:** Export download endpoint.

**Acceptance Criteria:**
- `GET /api/v1/companies/:id/export?format=X`
- Correct Content-Type and Content-Disposition
- includeRawData option
- File cleanup after 7 days

**Test Requirements:**
- [ ] Each format downloads correctly
- [ ] Raw data included when requested

**Dependencies:** Task 9.1

---

### Task 9.3: Re-scan with Change Detection
**Priority:** P1 | **Component:** Backend - Analysis

**Description:** Re-scan with version comparison.

**Acceptance Criteria:**
- Re-scan creates new version (FR-RSC-002)
- Compare using content hashes (FR-RSC-001)
- Identify changes (FR-RSC-003, FR-RSC-004)
- Keep max 3 versions (FR-RSC-005)

**Test Requirements:**
- [ ] New version created
- [ ] Changes identified
- [ ] Old versions auto-deleted
- [ ] Comparison accurate

**Dependencies:** Tasks 6.5, 2.8, 4.6

---

### Task 9.4: Batch Processing Queue Management
**Priority:** P0 | **Component:** Backend - Workers

**Description:** Robust batch queue management.

**Acceptance Criteria:**
- Batch queues all companies
- Fair scheduling
- Batch-level progress
- Batch cancellation

**Test Requirements:**
- [ ] 100+ batch queues correctly
- [ ] Multiple batches process fairly
- [ ] Progress shows completion count

**Dependencies:** Tasks 2.2, 3.3

---

### Task 9.5: Automatic Job Recovery
**Priority:** P0 | **Component:** Backend - Workers

**Description:** Recover interrupted jobs on startup.

**Acceptance Criteria:**
- Detect in_progress on startup (FR-STA-005)
- Resume from checkpoint
- Handle stale jobs
- Log recovery actions

**Test Requirements:**
- [ ] Restart recovers jobs
- [ ] Resume from checkpoint
- [ ] Stale jobs marked failed

**Dependencies:** Tasks 3.3, 3.5

---

### Task 9.6: URL Reachability Check
**Priority:** P0 | **Component:** Backend - Validation

**Description:** Validate URL reachability before accepting.

**Acceptance Criteria:**
- Validate format (FR-INP-002)
- HEAD request for reachability
- 10 second timeout
- Warning (not error) for unreachable

**Test Requirements:**
- [ ] Valid reachable accepted
- [ ] Invalid format rejected
- [ ] Unreachable shows warning

**Dependencies:** Task 2.1

---

## Phase 10: Polish

### Task 10.1: Accessibility Audit and Fixes
**Priority:** P1 | **Component:** Frontend - Accessibility

**Description:** WCAG 2.1 Level AA compliance.

**Acceptance Criteria:**
- Full keyboard navigation (NFR-ACC-002)
- Screen reader compatible (NFR-ACC-003)
- Contrast >= 4.5:1 (NFR-ACC-004)
- Focus indicators (NFR-ACC-005)
- ARIA labels

**Test Requirements:**
- [ ] axe audit passes
- [ ] Tab navigation works
- [ ] VoiceOver/NVDA compatible
- [ ] Contrast checker passes

**Dependencies:** Tasks 8.1-8.7

---

### Task 10.2: Frontend Performance Optimization
**Priority:** P1 | **Component:** Frontend - Performance

**Description:** Optimize frontend performance.

**Acceptance Criteria:**
- UI responsiveness < 200ms (NFR-PER-002)
- Code splitting
- Lazy loading
- Virtualized lists

**Test Requirements:**
- [ ] Lighthouse >= 90
- [ ] Initial load < 3 seconds
- [ ] Large lists scroll smoothly

**Dependencies:** Tasks 8.1-8.7

---

### Task 10.3: Backend Performance Optimization
**Priority:** P1 | **Component:** Backend - Performance

**Description:** Optimize backend performance.

**Acceptance Criteria:**
- API < 200ms (NFR-PER-001)
- Queries < 100ms (NFR-PER-004)
- Connection pooling optimized

**Test Requirements:**
- [ ] Load test: 50 concurrent requests
- [ ] p95 < 200ms
- [ ] No N+1 queries

**Dependencies:** Tasks 2.1-2.8

---

### Task 10.4: Security Hardening
**Priority:** P0 | **Component:** Full Stack - Security

**Description:** Implement security requirements.

**Acceptance Criteria:**
- API keys in env only (NFR-SEC-001)
- Input validation (NFR-SEC-002)
- ORM prevents SQLi (NFR-SEC-003)
- Secure download headers (NFR-SEC-005)
- XSS prevention

**Test Requirements:**
- [ ] No secrets in codebase
- [ ] SQLi attempts blocked
- [ ] XSS sanitized
- [ ] OWASP ZAP clean

**Dependencies:** All previous tasks

---

### Task 10.5: Backend Test Suite
**Priority:** P0 | **Component:** Backend - Testing

**Description:** Comprehensive backend tests.

**Acceptance Criteria:**
- Unit tests for services
- Integration tests for API
- Worker tests with mocks
- 80% code coverage

**Test Requirements:**
- [ ] pytest passes
- [ ] Tests isolated
- [ ] CI runs tests

**Dependencies:** All backend tasks

---

### Task 10.6: Frontend Test Suite
**Priority:** P0 | **Component:** Frontend - Testing

**Description:** Comprehensive frontend tests.

**Acceptance Criteria:**
- Unit tests (Vitest + Testing Library)
- Integration tests for pages
- MSW for API mocking
- 70% coverage

**Test Requirements:**
- [ ] npm test passes
- [ ] Tests isolated
- [ ] CI runs tests

**Dependencies:** All frontend tasks

---

### Task 10.7: End-to-End Test Suite
**Priority:** P1 | **Component:** Full Stack - Testing

**Description:** E2E tests for critical flows.

**Acceptance Criteria:**
- Playwright E2E framework
- Flows: add company, batch upload, progress, results, export
- Run in CI with Docker

**Test Requirements:**
- [ ] E2E tests pass
- [ ] Happy path and errors covered
- [ ] Screenshots on failure

**Dependencies:** Tasks 10.5, 10.6

---

### Task 10.8: Documentation
**Priority:** P1 | **Component:** Documentation

**Description:** Comprehensive project documentation.

**Acceptance Criteria:**
- API docs (OpenAPI/Swagger)
- Development setup guide
- Deployment guide
- Architecture overview
- User guide

**Test Requirements:**
- [ ] API docs match implementation
- [ ] Setup works on fresh machine
- [ ] Deployment covers Docker

**Dependencies:** All previous tasks

---

### Task 10.9: Production Docker Configuration
**Priority:** P1 | **Component:** Infrastructure

**Description:** Production-ready Docker config.

**Acceptance Criteria:**
- Multi-stage Dockerfile
- Production docker-compose.yml
- Env var documentation
- Health checks
- Volume config

**Test Requirements:**
- [ ] Images build successfully
- [ ] Containers start correctly
- [ ] Health checks pass

**Dependencies:** Task 1.4

---

### Task 10.10: CI/CD Pipeline
**Priority:** P1 | **Component:** Infrastructure

**Description:** Continuous integration pipeline.

**Acceptance Criteria:**
- GitHub Actions CI
- Lint and test on PR
- Build images on merge
- Security scanning

**Test Requirements:**
- [ ] CI runs on PRs
- [ ] Failed tests block merge
- [ ] Images tagged correctly

**Dependencies:** Tasks 10.5-10.7

---

## Completed Tasks

### Task 7.2: Core UI Component Library ✅
**Completed:** Phase 7 Frontend Components
- Button (variants: primary/secondary/danger/ghost, sizes: sm/md/lg, loading state)
- Input (label, error state, helper text, required indicator)
- Select (options, placeholder, error state)
- Checkbox (label, description, disabled state)
- Table (generic with sorting, row click, loading state, empty message)
- Card (title, actions, padding variants: none/sm/md/lg)
- Modal (backdrop, focus management, escape key, size variants)
- Toast (ToastProvider context, useToast hook, auto-dismiss, types: success/error/warning/info)
- ProgressBar (value, label, percentage display, color variants)
- Badge (status variants: default/success/warning/error/info)
- Tabs (keyboard navigation, ARIA attributes, disabled tab support)
- Skeleton (variants: text/rect/circle, compound components)
- Slider (label, value display, units, min/max/step)

**Tests:** 136 passing tests across 13 test files

---

### Task 7.3-7.5: Frontend Infrastructure ✅
**Completed:** Phase 7 Frontend Core Setup
- React Router configuration with all routes (/, /companies/:id, /companies/:id/progress, /add, /batch, /settings)
- TanStack Query API hooks (useCompanies, useCompany, useProgress, useCreateCompany, etc.)
- Axios API client with interceptors and error handling

---

### Task 8.1: Dashboard / Company List Page ✅
**Completed:** Full functionality dashboard
- Table with Name, Website, Status, Tokens, Actions columns
- Filtering by status and search query
- Sorting by multiple fields with ascending/descending toggle
- Pagination with configurable page size
- Delete confirmation modal
- Export functionality for completed companies
- Row click navigation to results/progress pages

---

### Task 8.2: Add Company Form Page ✅
**Completed:** Company creation form
- Form validation for company name and URL (with format normalization)
- Industry selection dropdown
- Advanced config panel (collapsible) with analysis mode presets
- Sliders for maxPages, maxDepth, timeLimitMinutes
- Social media link following toggles
- Submit creates company and redirects to progress page

---

### Task 8.3: Batch Upload Page ✅
**Completed:** CSV batch upload interface
- Drag-and-drop file zone
- CSV parsing with row validation
- Preview table showing valid/invalid rows with errors
- Template download functionality
- Confirm upload for valid rows only

---

### Task 8.4: Progress View Page ✅
**Completed:** Real-time progress monitoring
- Progress bar with percentage and phase labels
- Stats: Pages crawled, Entities found, Tokens used
- Time elapsed and estimated remaining
- Current activity indicator
- Pause/Resume/Cancel actions
- Auto-redirect to results on completion

---

### Task 8.5: Results View Page ✅
**Completed:** Analysis results display
- Tabs: Summary, Entities, Pages, Token Usage (using Tabs component with content)
- Summary tab with executive summary and analysis sections
- Sidebar with company info, statistics, version info
- Entity table with type filtering and pagination
- Page table with type filtering and pagination
- Token usage breakdown with cost estimation
- Export dropdown
- Re-scan confirmation modal

---

### Task 8.7: Settings Page ✅
**Completed:** Configuration settings
- Default analysis config persistence (localStorage)
- Quick/Thorough mode presets
- Sliders for crawling parameters
- Social media following toggles
- Save/Reset functionality
- Unsaved changes indicator

---

### Task 9.1: Export Generation Service ✅
**Completed:** Export generation for multiple formats
- Markdown export with proper formatting and sections
- Word (.docx) export using python-docx with styled headings, tables
- PDF export using ReportLab with professional layout
- JSON export with optional raw data (entities, pages)
- File: `backend/app/services/export_service.py`

**Tests:** 36 passing tests in `tests/test_export_service.py`

---

### Task 9.2: Export API Endpoint ✅
**Completed:** Export download endpoint
- `GET /api/v1/companies/:id/export?format=markdown|word|pdf|json`
- Query params: `includeRawData`, `version`
- Correct Content-Type and Content-Disposition headers
- Error handling for invalid formats, non-completed companies
- File: `backend/app/api/routes/export.py`

**Tests:** 28 passing tests in `tests/test_export_api.py`

---

### Task 9.5: Automatic Job Recovery ✅
**Completed:** Job recovery on application startup
- Detects in_progress jobs on startup
- Resumes from checkpoint if available
- Marks stale jobs (>1 hour without activity) as failed
- Logs recovery actions
- Updated `backend/app/__init__.py` with startup recovery
- Uses `backend/app/services/job_service.py` recovery methods

**Tests:** 14 passing tests in `tests/test_job_recovery.py`

---

### Task 9.6: URL Reachability Check ✅
**Completed:** URL validation and reachability checking
- Format validation (http/https, valid domain)
- HEAD request reachability check with 10 second timeout
- Returns warning (not error) for unreachable URLs
- Normalizes URLs (adds https://, trailing slash)
- `skipReachabilityCheck` query parameter support
- File: `backend/app/services/url_validator.py`

**Tests:** 38 passing tests in `tests/test_url_validator.py`

---

### Task 9.3: Re-scan with Change Detection ✅
**Completed:** Version comparison and change detection
- Backend: Version history API endpoint (`GET /api/v1/companies/:id/versions`)
- Backend: Version comparison API endpoint (`GET /api/v1/companies/:id/compare`)
- Backend: Re-scan creates new analysis version (max 3, auto-deletes oldest)
- Frontend: Versions tab in CompanyResults page
- Frontend: VersionSelector component for selecting versions
- Frontend: ChangeHighlight component for displaying version changes
- Change detection for team, products, and content sections
- Color-coded diff display (green=added, red=removed, yellow=modified)
- Files:
  - `backend/app/api/routes/versions.py` - Version history and comparison endpoints
  - `backend/app/api/routes/control.py` - Rescan endpoint
  - `frontend/src/pages/CompanyResults.tsx` - Versions tab integration
  - `frontend/src/components/domain/VersionSelector.tsx` - Version selector component
  - `frontend/src/components/domain/ChangeHighlight.tsx` - Change visualization component

**Tests:** 4 backend tests in `tests/test_remaining_api.py`, 31 frontend tests in domain component tests

---

### Task 9.4: Batch Processing Queue Management ✅
**Completed:** Batch queue management for orchestrating company processing
- BatchJob model for tracking batch-level state and progress
- BatchQueueService with fair round-robin scheduling across batches
- Batch operations: create, start, pause, resume, cancel
- Progress tracking with Redis caching and DB fallback
- API endpoints for batch CRUD and control operations
- Files:
  - `backend/app/models/batch.py` - BatchJob model
  - `backend/app/services/batch_queue_service.py` - Batch orchestration service
  - `backend/app/api/routes/batch_queue.py` - REST API endpoints

**Tests:** 57 passing tests in `tests/test_batch_queue_service.py` and `tests/test_batch_queue_api.py`

---

### Task 10.4: Security Hardening ✅
**Completed:** Security hardening per OWASP recommendations
- NFR-SEC-001: API keys in environment only (verified)
- NFR-SEC-002: Input validation via Pydantic schemas (verified)
- NFR-SEC-003: ORM prevents SQLi via SQLAlchemy (verified)
- NFR-SEC-005: Secure download headers (enhanced)
- XSS prevention with sanitization utilities
- Security headers: X-Content-Type-Options, X-Frame-Options, CSP, Referrer-Policy, Permissions-Policy
- HTTPS headers for production: Strict-Transport-Security (HSTS)
- Content-Type validation for API requests
- Filename sanitization for downloads
- URL validation for SSRF protection
- Files:
  - `backend/app/middleware/__init__.py` - Middleware package
  - `backend/app/middleware/security.py` - Security middleware and utilities
  - `backend/tests/test_security.py` - Security tests

**Tests:** 42 passing tests in `tests/test_security.py`

---

[Previous completed tasks will be moved here]

---

## Notes & Discoveries

[Document findings during implementation]

---

## Critical Files Reference

Based on comprehensive PRD analysis, these are the 5 most critical files to implement:

1. **`backend/app/models/company.py`** - Core SQLAlchemy models (foundation)
2. **`backend/app/workers/crawl_worker.py`** - Crawl worker (system heart)
3. **`backend/app/services/analysis_service.py`** - Claude API integration (AI capability)
4. **`frontend/src/pages/Dashboard.tsx`** - Main dashboard (primary UI)
5. **`backend/app/api/routes/companies.py`** - Company API routes (frontend-backend interface)

---

## Specifications Reference

See `specs/` directory for detailed feature specifications:
- `01-web-crawling.md` - Crawling engine spec
- `02-entity-extraction.md` - NER and structured extraction
- `03-ai-analysis.md` - Claude API and analysis
- `04-state-management.md` - Checkpoint and resume
- `05-api-endpoints.md` - REST API specification
- `06-export-formats.md` - Export formats spec
- `07-ui-components.md` - Frontend components
