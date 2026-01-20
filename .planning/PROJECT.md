# CIRA - Company Intelligence Research Assistant

## What This Is

CIRA is an AI-powered company research automation tool that crawls company websites, extracts entities using spaCy NLP, analyzes content with Claude API, and generates comprehensive 2-page intelligence summaries. It automates the time-consuming process of researching companies for evaluating clients, partners, and vendors.

## Core Value

Users can research any company by entering a URL and receive a comprehensive intelligence brief without manual research work.

## Current State

**v1.0 Core Intelligence Platform — Shipped 2026-01-19**

All core functionality complete and tested:
- 93,255 lines of code (Python + TypeScript)
- 6 phases, 30 plans executed
- 1,672+ tests passing
- 52/52 requirements satisfied

See `.planning/MILESTONES.md` for full milestone history.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

**Web Crawling** (v1.0)
- [x] Intelligent crawling with sitemap parsing and page prioritization
- [x] JavaScript rendering via Playwright for dynamic content
- [x] Rate limiting (1 req/sec, 3 concurrent) and robots.txt compliance
- [x] Configurable depth and page limits
- [x] External link following for LinkedIn, Twitter, Facebook profiles

**Entity Extraction** (v1.0)
- [x] Named Entity Recognition using spaCy (PERSON, ORG, GPE, PRODUCT)
- [x] Person extraction with role detection (CEO, Founder, CTO, etc.)
- [x] Structured data extraction (emails, phones, addresses, social handles)
- [x] Deduplication across multiple pages with confidence scoring

**AI Analysis** (v1.0)
- [x] Claude API integration for contextual content analysis
- [x] Section-based analysis (executive summary, business model, team, market position)
- [x] Token tracking per-company and per-call with cost estimation
- [x] Prompt templates for consistent analysis quality
- [x] Red flags and concerns identification

**State Management** (v1.0)
- [x] Checkpoint persistence every 10 pages or 2 minutes
- [x] Pause/resume functionality for in-progress jobs
- [x] Automatic recovery of in_progress jobs on startup
- [x] Graceful timeout handling with partial results preserved

**Batch Processing** (v1.0)
- [x] CSV upload for multiple companies with validation
- [x] Queue management with ordered processing
- [x] CSV template download
- [x] Error reporting per row

**Export** (v1.0)
- [x] Markdown export with 2-page summary template
- [x] Word (.docx) export with professional formatting
- [x] PDF export with clickable links
- [x] JSON export with all structured data

**API** (v1.0)
- [x] Full CRUD for companies with pagination and filtering
- [x] Real-time progress polling
- [x] Pause/resume endpoints
- [x] Export endpoint with format selection
- [x] Batch upload endpoint
- [x] Entity retrieval with filtering

**UI** (v1.0)
- [x] Single company submission form with URL and config options
- [x] Company list with status badges and actions
- [x] Progress tracker with phase, stats, and current activity
- [x] Analysis viewer with markdown rendering
- [x] Entity browser with filtering and search
- [x] Export dropdown with format options
- [x] Batch CSV upload with preview
- [x] Delete with confirmation

### Active

<!-- Current scope. Building toward these. -->

(No active development — see v2 ideas below)

### Future Ideas (v2+)

**Versioning & Comparison**
- [ ] Re-scan completed company
- [ ] View analysis version history
- [ ] Side-by-side version comparison
- [ ] Highlight changes between versions

**Advanced Configuration**
- [ ] Custom exclusion patterns
- [ ] Save/reuse configuration presets
- [ ] Global default configuration

**Notifications**
- [ ] Toast notifications for job completion
- [ ] Error notifications with details

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Multi-user collaboration — Adds auth complexity, single-user sufficient for v1
- CRM/Salesforce integration — External dependencies, can add post-v1
- Webhook notifications — Polling sufficient, webhooks add complexity
- ML-based prediction — Requires training data, focus on extraction first
- Competitive landscape mapping — Requires multi-company correlation
- Financial health analysis — Requires external data sources
- Custom report templates — Standard template sufficient for v1
- Mobile apps — Web-first, desktop minimum 1024px
- Real-time chat/streaming — Polling-based progress sufficient

## Context

CIRA targets business professionals who need to research companies quickly:
- Sales teams evaluating prospects
- Investors performing due diligence
- Procurement teams vetting vendors
- BD teams assessing partnership opportunities

The tool combines:
1. **Intelligent crawling** — Prioritizes valuable pages (about, team, products) over low-value content
2. **Hybrid AI** — spaCy for fast entity extraction, Claude for contextual understanding
3. **Checkpoint/resume** — Long-running jobs can be paused and resumed without data loss

## Architecture

- React/TypeScript frontend with TanStack Query
- Flask/Python backend with SQLAlchemy
- Celery worker architecture with Redis
- spaCy en_core_web_lg for NLP
- Claude API via Anthropic SDK
- Playwright for JavaScript rendering

## Constraints

- **Tech stack**: Python backend (Flask, Celery, spaCy), React frontend (TypeScript, Tailwind)
- **AI provider**: Claude API via Anthropic SDK — cost tracking essential
- **NLP model**: spaCy en_core_web_lg — pre-trained, no custom training
- **Browser**: Playwright for JS rendering — headless Chrome
- **Database**: SQLite for development, PostgreSQL for production
- **Queue**: Redis for Celery task queue and progress state

## Key Decisions

<!-- Decisions that constrain future work. Add throughout project lifecycle. -->

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| spaCy + Claude hybrid | spaCy fast for NER, Claude for understanding | Validated v1.0 |
| 2-page summary format | Consistent, scannable output | Validated v1.0 |
| Checkpoint every 10 pages | Balance between I/O and recovery | Validated v1.0 |
| Polling for progress | Simpler than WebSocket, sufficient for UX | Validated v1.0 |
| Desktop-first (1024px min) | Business users on desktop | Validated v1.0 |

---
*Last updated: 2026-01-19 after v1.0 milestone completion*
