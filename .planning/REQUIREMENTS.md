# Requirements: CIRA

**Defined:** 2026-01-19
**Core Value:** Users can research any company by entering a URL and receive a comprehensive intelligence brief without manual research work.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Web Crawling

- [x] **CRL-01**: System discovers pages via sitemap.xml parsing
- [x] **CRL-02**: System renders JavaScript content via Playwright
- [x] **CRL-03**: System respects robots.txt directives
- [x] **CRL-04**: System rate limits requests (1/sec, 3 concurrent max)
- [x] **CRL-05**: System prioritizes high-value pages (about, team, products, contact)
- [x] **CRL-06**: User can configure max pages and depth limits
- [x] **CRL-07**: System extracts and queues external social links (LinkedIn, Twitter, Facebook)

### Entity Extraction

- [ ] **NER-01**: System extracts PERSON entities with spaCy NER
- [ ] **NER-02**: System extracts ORG entities (partners, clients, investors)
- [ ] **NER-03**: System extracts GPE entities (locations, headquarters)
- [ ] **NER-04**: System extracts PRODUCT entities (products, services)
- [ ] **NER-05**: System detects person roles (CEO, Founder, CTO, VP, etc.)
- [ ] **NER-06**: System extracts structured data (emails, phones, addresses)
- [ ] **NER-07**: System deduplicates entities across pages with confidence scoring

### AI Analysis

- [x] **ANA-01**: System analyzes content using Claude API
- [x] **ANA-02**: System generates executive summary section
- [x] **ANA-03**: System generates company overview section
- [x] **ANA-04**: System generates business model & products section
- [x] **ANA-05**: System generates team & leadership section
- [x] **ANA-06**: System generates market position section
- [x] **ANA-07**: System generates key insights section
- [x] **ANA-08**: System identifies red flags and concerns
- [x] **ANA-09**: System tracks token usage per API call
- [x] **ANA-10**: System calculates estimated cost from token usage

### State Management

- [x] **STA-01**: System persists checkpoint every 10 pages or 2 minutes
- [x] **STA-02**: User can pause an in-progress analysis
- [x] **STA-03**: User can resume a paused analysis from checkpoint
- [x] **STA-04**: System automatically resumes in_progress jobs on startup
- [x] **STA-05**: System handles timeout gracefully with partial results

### Batch Processing

- [x] **BAT-01**: User can upload CSV file with multiple companies
- [x] **BAT-02**: System validates CSV and reports errors per row
- [x] **BAT-03**: User can download CSV template
- [x] **BAT-04**: System queues batch companies for processing

### Export

- [x] **EXP-01**: User can export analysis as Markdown (.md)
- [x] **EXP-02**: User can export analysis as Word (.docx)
- [x] **EXP-03**: User can export analysis as PDF
- [x] **EXP-04**: User can export analysis as JSON with all structured data
- [x] **EXP-05**: Export follows 2-page summary template structure

### API

- [x] **API-01**: POST /companies creates single company job
- [x] **API-02**: POST /companies/batch uploads CSV batch
- [x] **API-03**: GET /companies lists companies with pagination and filtering
- [x] **API-04**: GET /companies/:id returns company with latest analysis
- [x] **API-05**: GET /companies/:id/progress returns real-time progress
- [x] **API-06**: POST /companies/:id/pause pauses in-progress job
- [x] **API-07**: POST /companies/:id/resume resumes paused job
- [x] **API-08**: GET /companies/:id/export returns export in specified format
- [x] **API-09**: DELETE /companies/:id removes company and all data
- [ ] **API-10**: GET /companies/:id/entities returns extracted entities

### UI

- [x] **UI-01**: User can submit single company via form (name, URL, config)
- [x] **UI-02**: User can view company list with status badges
- [x] **UI-03**: User can view real-time progress during analysis
- [x] **UI-04**: User can view completed analysis with markdown rendering
- [ ] **UI-05**: User can browse extracted entities with filtering
- [x] **UI-06**: User can export analysis from dropdown menu
- [x] **UI-07**: User can pause/resume in-progress analysis
- [x] **UI-08**: User can configure analysis options (mode, limits, exclusions)
- [x] **UI-09**: User can upload batch CSV and preview before submission
- [x] **UI-10**: User can delete company and associated data

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Versioning & Comparison

- **VER-01**: User can initiate re-scan of completed company
- **VER-02**: User can view analysis version history
- **VER-03**: User can compare two analysis versions side-by-side
- **VER-04**: System highlights changes between versions

### Advanced Configuration

- **CFG-01**: User can define custom exclusion patterns
- **CFG-02**: User can save and reuse configuration presets
- **CFG-03**: Admin can update global default configuration

### Notifications

- **NOT-01**: System displays toast notifications for job completion
- **NOT-02**: System displays error notifications with details

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Multi-user authentication | Single-user sufficient for v1, adds auth complexity |
| CRM/Salesforce integration | External dependencies, defer post-v1 |
| Webhook notifications | Polling sufficient for progress UX |
| ML-based prediction | Requires training data, focus on extraction |
| Competitive landscape mapping | Requires multi-company correlation logic |
| Financial health analysis | Requires external data sources (SEC, etc.) |
| Custom report templates | Standard 2-page template sufficient |
| Mobile apps | Desktop-first (1024px min), web responsive later |
| Real-time streaming | Polling-based progress sufficient for UX |
| OAuth social login | Email/password or no auth sufficient |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CRL-01 to CRL-07 | Phase 1 | Complete |
| API-01, API-03, API-04 | Phase 1 | Complete |
| UI-01, UI-02 | Phase 1 | Complete |
| NER-01 to NER-07 | Phase 2 | Pending |
| ANA-01 to ANA-10 | Phase 3 | Complete |
| STA-01 to STA-05 | Phase 4 | Complete |
| EXP-01 to EXP-05 | Phase 5 | Complete |
| BAT-01 to BAT-04 | Phase 6 | Complete |
| API-05 to API-07 | Phase 4 | Complete |
| API-08 | Phase 5 | Complete |
| API-02, API-09 | Phase 6 | Complete |
| API-10 | Phase 2 | Pending |
| UI-03, UI-04 | Phase 3 | Complete |
| UI-07 | Phase 4 | Complete |
| UI-06 | Phase 5 | Complete |
| UI-08, UI-09, UI-10 | Phase 6 | Complete |
| UI-05 | Phase 2 | Pending |

**Coverage:**
- v1 requirements: 52 total
- Mapped to phases: 52
- Unmapped: 0 ✓

---
*Requirements defined: 2026-01-19*
*Last updated: 2026-01-19 after Phase 6 completion (Milestone v1.0)*
