# CIRA - Company Intelligence Research Assistant

## What This Is

CIRA is an AI-powered company research automation tool that crawls company websites, extracts entities using spaCy NLP, analyzes content with Claude API, and generates comprehensive 2-page intelligence summaries. It automates the time-consuming process of researching companies for evaluating clients, partners, and vendors.

## Core Value

Users can research any company by entering a URL and receive a comprehensive intelligence brief without manual research work.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope. Building toward these. -->

**Web Crawling**
- [ ] Intelligent crawling with sitemap parsing and page prioritization
- [ ] JavaScript rendering via Playwright for dynamic content
- [ ] Rate limiting (1 req/sec, 3 concurrent) and robots.txt compliance
- [ ] Configurable depth and page limits
- [ ] External link following for LinkedIn, Twitter, Facebook profiles

**Entity Extraction**
- [ ] Named Entity Recognition using spaCy (PERSON, ORG, GPE, DATE, MONEY)
- [ ] Person extraction with role detection (CEO, Founder, CTO, etc.)
- [ ] Structured data extraction (emails, phones, addresses, social handles)
- [ ] Deduplication across multiple pages with confidence scoring

**AI Analysis**
- [ ] Claude API integration for contextual content analysis
- [ ] Section-based analysis (executive summary, business model, team, market position)
- [ ] Token tracking per-company and per-call with cost estimation
- [ ] Prompt templates for consistent analysis quality

**State Management**
- [ ] Checkpoint persistence every 10 pages or 2 minutes
- [ ] Pause/resume functionality for in-progress jobs
- [ ] Automatic recovery of in_progress jobs on startup
- [ ] Graceful timeout handling with partial results preserved

**Batch Processing**
- [ ] CSV upload for multiple companies
- [ ] Queue management with pause/resume
- [ ] Real-time progress monitoring via polling

**Export**
- [ ] Markdown export with 2-page summary template
- [ ] Word (.docx) export with professional formatting
- [ ] PDF export with clickable links
- [ ] JSON export with all structured data

**UI**
- [ ] Single company submission form with URL and config options
- [ ] Company list with status, progress, and actions
- [ ] Progress tracker with phase, stats, and current activity
- [ ] Analysis viewer with markdown rendering
- [ ] Entity browser with filtering and search
- [ ] Version history with comparison view

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

Existing codebase has infrastructure for:
- React/TypeScript frontend with TanStack Query
- Flask/Python backend with SQLAlchemy
- Celery worker architecture with Redis
- Basic UI components and routing

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
| spaCy + Claude hybrid | spaCy fast for NER, Claude for understanding | — Pending |
| 2-page summary format | Consistent, scannable output | — Pending |
| Checkpoint every 10 pages | Balance between I/O and recovery | — Pending |
| Polling for progress | Simpler than WebSocket, sufficient for UX | — Pending |
| Desktop-first (1024px min) | Business users on desktop | — Pending |

---
*Last updated: 2026-01-19 after project initialization*
