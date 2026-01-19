# CIRA v1 Roadmap

**Created:** 2026-01-19
**Milestone:** v1.0 - Core Intelligence Platform

## Overview

6 phases building toward a complete company intelligence research tool.

| Phase | Name | Goal | Requirements | Status |
|-------|------|------|--------------|--------|
| 1 | Web Crawling | Crawl company websites intelligently | CRL-01 to CRL-07 | Complete |
| 2 | Entity Extraction | Extract people, orgs, products from content | NER-01 to NER-07 | In Progress |
| 3 | AI Analysis | Generate intelligence summaries with Claude | ANA-01 to ANA-10 | Complete |
| 4 | State Management | Pause/resume and checkpoint reliability | STA-01 to STA-05 | Planned |
| 5 | Export | Output analysis in multiple formats | EXP-01 to EXP-05 | Pending |
| 6 | Batch Processing | Process multiple companies from CSV | BAT-01 to BAT-04 | Pending |

---

## Phase 1: Web Crawling

**Goal:** Crawl company websites with intelligent prioritization, rate limiting, and robots.txt compliance.

**Requirements:** CRL-01 to CRL-07, API-01, API-03, API-04, UI-01, UI-02

**Status:** Complete (2026-01-19)

**Plans:** 5/5 complete

Plans:
- [x] 01-01-PLAN.md — Crawl pipeline integration tests
- [x] 01-02-PLAN.md — API integration tests for company CRUD
- [x] 01-03-PLAN.md — Crawler edge case and robustness tests
- [x] 01-04-PLAN.md — Frontend component tests (AddCompany, Dashboard)
- [x] 01-05-PLAN.md — Verification and requirement mapping

**Verification:** 463 tests passing, all requirements verified

### Deliverables

- Sitemap parser that discovers pages from sitemap.xml
- Playwright-based crawler for JavaScript-rendered content
- Rate limiter (1 req/sec, 3 concurrent max)
- robots.txt parser and compliance checker
- Page prioritization (about, team, products, contact first)
- Configuration options for max pages and depth
- External link extraction for social profiles

### API Endpoints

- `POST /api/v1/companies` - Create company and start crawl
- `GET /api/v1/companies` - List companies with status
- `GET /api/v1/companies/:id` - Get company details
- `GET /api/v1/companies/:id/pages` - Get crawled pages

### UI Components

- Company submission form (name, URL, config options)
- Company list table with status badges
- Basic progress indicator (pages crawled)

### Success Criteria

- Can crawl a company website and store pages
- Respects robots.txt directives
- Rate limits requests correctly
- Prioritizes high-value pages
- UI shows company list and basic status

---

## Phase 2: Entity Extraction

**Goal:** Extract structured entities (people, organizations, products, contact info) from crawled pages using spaCy NLP.

**Requirements:** NER-01 to NER-07, API-10, UI-05

**Status:** In Progress

**Plans:** 5 plans

Plans:
- [ ] 02-01-PLAN.md — Extraction pipeline integration tests
- [ ] 02-02-PLAN.md — Entities API integration tests
- [ ] 02-03-PLAN.md — Extraction edge case and robustness tests
- [ ] 02-04-PLAN.md — Frontend entity browser tests
- [ ] 02-05-PLAN.md — Verification and requirement mapping

### Deliverables

- spaCy pipeline with en_core_web_lg model
- PERSON entity extraction with role detection
- ORG entity extraction with relationship context
- GPE (location) extraction for headquarters/offices
- PRODUCT entity extraction
- Structured data patterns (email, phone, address, social handles)
- Entity deduplication with confidence scoring
- Context snippet preservation (50 chars before/after)

### API Endpoints

- `GET /api/v1/companies/:id/entities` - Get extracted entities with filtering

### UI Components

- Entity browser table with type filter
- Confidence threshold slider
- Search within entities
- Context snippet display on click

### Success Criteria

- Extracts people with roles (CEO, Founder, etc.)
- Extracts organizations with relationship context
- Extracts locations (headquarters, offices)
- Extracts products and services
- Extracts emails, phones, addresses
- Deduplicates across pages
- UI displays entities with filtering

---

## Phase 3: AI Analysis

**Goal:** Generate comprehensive intelligence summaries using Claude API with token tracking and cost estimation.

**Requirements:** ANA-01 to ANA-10, UI-03, UI-04

**Status:** Complete (2026-01-19)

**Plans:** 5/5 complete

Plans:
- [x] 03-01-PLAN.md — Analysis pipeline integration tests
- [x] 03-02-PLAN.md — Tokens API integration tests
- [x] 03-03-PLAN.md — Analysis edge case and robustness tests
- [x] 03-04-PLAN.md — Frontend analysis UI tests
- [x] 03-05-PLAN.md — Phase verification and requirement mapping

**Verification:** 198 tests passing, all requirements verified

### Deliverables

- Claude API integration via Anthropic SDK
- Prompt templates for each analysis section
- Executive summary generation
- Company overview section
- Business model & products section
- Team & leadership section
- Market position section
- Key insights section
- Red flags identification
- Token usage tracking per API call
- Cost estimation calculation

### API Endpoints

- `GET /api/v1/companies/:id/tokens` - Get token usage breakdown

### UI Components

- Progress tracker with phase indicator
- Current activity text display
- Token counter with cost display
- Analysis viewer with markdown rendering
- Collapsible sections

### Success Criteria

- Generates all analysis sections via Claude API
- Tracks token usage accurately
- Estimates cost correctly
- UI shows progress during analysis
- UI renders completed analysis with sections

---

## Phase 4: State Management

**Goal:** Enable pause/resume functionality and checkpoint persistence for reliable long-running jobs.

**Requirements:** STA-01 to STA-05, API-05, API-06, API-07, UI-07

**Status:** Planned

**Plans:** 5 plans

Plans:
- [ ] 04-01-PLAN.md — Checkpoint/resume integration tests
- [ ] 04-02-PLAN.md — Control API integration tests (pause, resume, progress)
- [ ] 04-03-PLAN.md — State management edge case tests
- [ ] 04-04-PLAN.md — Frontend pause/resume UI tests
- [ ] 04-05-PLAN.md — Phase verification and requirement mapping

### Deliverables

- Checkpoint data model (pages visited, queued, entities, progress)
- Checkpoint persistence every 10 pages or 2 minutes
- Pause operation (save checkpoint, update status)
- Resume operation (load checkpoint, continue processing)
- Automatic recovery of in_progress jobs on startup
- Graceful timeout handling
- Redis keys for distributed locking

### API Endpoints

- `GET /api/v1/companies/:id/progress` - Real-time progress polling
- `POST /api/v1/companies/:id/pause` - Pause in-progress job
- `POST /api/v1/companies/:id/resume` - Resume paused job

### UI Components

- Pause/Resume buttons (context-aware)
- Progress bar with percentage
- Time elapsed and estimated remaining
- Status transition feedback

### Success Criteria

- Can pause an in-progress job
- Can resume from checkpoint
- Jobs resume on server restart
- Timeout preserves partial results
- UI reflects pause/resume state

---

## Phase 5: Export

**Goal:** Export completed analyses in multiple formats following the 2-page summary template.

**Requirements:** EXP-01 to EXP-05, API-08, UI-06

### Deliverables

- 2-page summary template structure
- Markdown exporter (UTF-8)
- Word exporter via python-docx
- PDF exporter via ReportLab
- JSON exporter with all structured data
- File download endpoint with content-type handling

### API Endpoints

- `GET /api/v1/companies/:id/export?format={md|word|pdf|json}` - Export analysis

### UI Components

- Export dropdown with format options
- Loading state during export generation
- Download trigger

### Success Criteria

- Markdown export renders correctly
- Word document opens in MS Word and Google Docs
- PDF has clickable links and proper formatting
- JSON includes all structured data
- UI provides easy export access

---

## Phase 6: Batch Processing

**Goal:** Process multiple companies from CSV upload with queue management.

**Requirements:** BAT-01 to BAT-04, API-02, UI-08, UI-09, UI-10

### Deliverables

- CSV parser with validation
- Batch upload endpoint (multipart/form-data)
- CSV template generation
- Error reporting per row
- Queue management for batch jobs
- Batch progress aggregation

### API Endpoints

- `POST /api/v1/companies/batch` - Upload CSV batch
- `GET /api/v1/companies/template` - Download CSV template
- `DELETE /api/v1/companies/:id` - Delete company

### UI Components

- File upload component
- Batch preview table with error highlighting
- Valid/invalid row counts
- Confirm/cancel batch buttons
- Delete confirmation modal
- Configuration panel (Quick/Thorough mode, limits)

### Success Criteria

- Can upload CSV with multiple companies
- Validates CSV and shows errors per row
- Can download CSV template
- Companies queue and process in order
- Can delete individual companies
- UI shows batch status overview

---

## Phase Dependencies

```
Phase 1 (Crawling)
    └── Phase 2 (Extraction) [depends on crawled pages]
           └── Phase 3 (Analysis) [depends on entities + content]
                  └── Phase 5 (Export) [depends on analysis]

Phase 4 (State Management) [parallel, integrates with Phases 1-3]
Phase 6 (Batch) [depends on Phase 1 API, enhances workflow]
```

**Recommended execution order:** 1 -> 2 -> 3 -> 4 -> 5 -> 6

Phase 4 can be developed in parallel after Phase 1, then integrated.

---

## Milestone Success Criteria

v1.0 is complete when:

1. User can submit a company URL and receive a complete analysis
2. Analysis includes all sections (overview, products, team, market, insights)
3. Entities extracted and browsable
4. Token usage tracked with cost estimation
5. Jobs can be paused, resumed, and recovered
6. Export works in all 4 formats
7. Batch CSV upload processes multiple companies
8. UI provides full workflow from submission to export

---

*Roadmap created: 2026-01-19*
*Phase 3 complete: 2026-01-19*
*Phase 4 planned: 2026-01-19*
