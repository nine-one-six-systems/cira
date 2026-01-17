# **CIRA - Company Intelligence Research Assistant**

## **Product Requirements Document for AI Development**

---

| Field | Value |
| ----- | ----- |
| **Version** | 1 |
| **Date** | January 17, 2026 |
| **Status** | Draft |

---

## **Table of Contents**

1. [Project Overview](#1-project-overview)
2. [Technical Architecture](#2-technical-architecture)
3. [Data Models & Interfaces](#3-data-models--interfaces)
4. [Functional Requirements](#4-functional-requirements)
5. [User Roles & Access Control](#5-user-roles--access-control)
6. [User Interface Specifications](#6-user-interface-specifications)
7. [API Specifications](#7-api-specifications)
8. [Integration Requirements](#8-integration-requirements)
9. [Non-Functional Requirements](#9-non-functional-requirements)
10. [Glossary](#10-glossary)

---

## **1. Project Overview**

### **1.1 Purpose**

CIRA (Company Intelligence Research Assistant) is an AI-powered company research automation tool that transforms manual due diligence into an intelligent, batch-processable workflow. The system crawls company websites, analyzes content using hybrid AI (spaCy for NER + Claude API for contextual analysis), and generates comprehensive, actionable summaries for evaluating potential clients, partners, and vendors.

The core problem CIRA solves is the time-intensive nature of company research. Currently, evaluating a single company requires hours of manual research across multiple web pages, social profiles, and external sources. This process is inconsistent, prone to missing critical information, and doesn't scale well when evaluating multiple companies simultaneously.

### **1.2 Scope**

**In Scope:**
- Web crawling engine with intelligent page prioritization
- Entity extraction using spaCy NLP
- AI-powered analysis and synthesis using Claude API
- Batch processing with pause/resume capability
- Token usage tracking and cost estimation
- Multiple export formats (Markdown, Word, PDF, JSON)
- Re-scan functionality with change detection
- SQLite-based data persistence

**Out of Scope (V1):**
- Multi-user collaboration features
- CRM/Salesforce integration
- Webhook notifications
- ML-based company fit prediction
- Competitive landscape mapping
- Financial health analysis from public filings
- Custom report templates
- Mobile native applications

### **1.3 Key Features Summary**

| Feature | Description | Priority |
| ------- | ----------- | -------- |
| Intelligent Web Crawler | Crawls company websites with sitemap parsing, JavaScript rendering, and polite crawling | P0 |
| Entity Extraction | spaCy-powered NER for extracting people, organizations, locations, products, and key data | P0 |
| AI Analysis | Claude API integration for contextual analysis, business model identification, and summary generation | P0 |
| Batch Processing | CSV upload for analyzing multiple companies with queue management | P0 |
| Progress Monitoring | Real-time progress tracking with pages crawled, tokens used, and time elapsed | P0 |
| Checkpoint & Resume | State persistence enabling pause/resume without data loss | P0 |
| Token Tracking | Per-company and per-call token usage tracking with cost estimation | P0 |
| Export Generation | 2-page summary export to Markdown, Word, PDF, and JSON formats | P1 |
| External Link Following | Optional crawling of LinkedIn, Twitter, and Facebook company profiles | P1 |
| Re-scan & Comparison | Detect changes between scans with version history | P1 |
| Configuration Options | Quick vs Thorough modes with customizable crawl depth, page limits, and time limits | P1 |

### **1.4 System Context Diagram**

```
                                    ┌─────────────────┐
                                    │   User/Browser  │
                                    └────────┬────────┘
                                             │ HTTPS
                                             ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                              CIRA System                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                        React Frontend                                │  │
│  │   Dashboard │ Company Form │ Progress View │ Results │ Export       │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │ REST API                                 │
│  ┌──────────────────────────────┴──────────────────────────────────────┐  │
│  │                         Flask Backend                                │  │
│  │              API Routes │ Job Management │ State Persistence         │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│  ┌──────────────────────────────┴──────────────────────────────────────┐  │
│  │                       Celery Workers                                 │  │
│  │     Crawl Worker  │  Extract Worker  │  Analyze Worker              │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│  ┌──────────────────────────────┴──────────────────────────────────────┐  │
│  │                        Data Layer                                    │  │
│  │            SQLite Database  │  Redis Cache  │  File Storage         │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
         │                    │                         │
         ▼                    ▼                         ▼
┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│ Target      │    │ Claude API       │    │ Social Platforms    │
│ Company     │    │ (Anthropic)      │    │ (LinkedIn, Twitter, │
│ Websites    │    │                  │    │  Facebook)          │
└─────────────┘    └──────────────────┘    └─────────────────────┘
```

---

## **2. Technical Architecture**

### **2.1 Technology Stack**

#### **Frontend**

| Technology | Version | Purpose |
| ---------- | ------- | ------- |
| React | 18+ | Component-based UI framework |
| TypeScript | 5.0+ | Type-safe JavaScript |
| Vite | 5.0+ | Build tooling and dev server |
| TanStack Query | 5.0+ | Server state management and caching |
| Tailwind CSS | 3.4+ | Utility-first styling |
| Recharts | 2.10+ | Token usage visualization charts |
| React Router | 6.0+ | Client-side routing |
| Axios | 1.6+ | HTTP client |

#### **Backend**

| Technology | Version | Purpose |
| ---------- | ------- | ------- |
| Python | 3.11+ | Runtime environment |
| Flask | 3.0+ | REST API framework |
| SQLAlchemy | 2.0+ | ORM and database abstraction |
| Celery | 5.3+ | Distributed task queue |
| Redis | 7.0+ | Message broker and caching |
| Playwright | 1.40+ | JavaScript-rendered page crawling |
| BeautifulSoup4 | 4.12+ | HTML parsing |
| spaCy | 3.7+ | NLP and entity extraction |
| Anthropic SDK | 0.18+ | Claude API integration |
| python-docx | 1.1+ | Word document generation |
| ReportLab | 4.0+ | PDF generation |
| Pydantic | 2.5+ | Data validation |

#### **Infrastructure**

| Category | Services |
| -------- | -------- |
| Database | SQLite (primary), Redis (cache/broker) |
| Task Queue | Celery with Redis broker |
| File Storage | Local filesystem for exports |
| Containerization | Docker, Docker Compose |
| Deployment | Railway, Render, or self-hosted |

### **2.2 Worker Architecture**

| Worker | Responsibility |
| ------- | -------------- |
| Crawl Worker | Discovers and fetches web pages, handles sitemap parsing, manages crawl state |
| Extract Worker | Runs spaCy NER pipeline, extracts structured data (emails, phones, addresses) |
| Analyze Worker | Calls Claude API, synthesizes insights, generates summaries, tracks tokens |

#### **Inter-Service Communication**

| Type | Technology | Use Case |
| ---- | ---------- | -------- |
| Task Queue | Celery + Redis | Worker job distribution |
| REST API | Flask | Frontend-backend communication |
| Cache | Redis | Progress state, session data |
| Database | SQLite | Persistent storage |

### **2.3 Database Architecture**

| Database | Purpose | Data Types |
| -------- | ------- | ---------- |
| SQLite | Primary storage | Companies, crawl sessions, pages, entities, analyses, token usage |
| Redis | Caching and message broker | Job queues, progress state, session cache |

---

## **3. Data Models & Interfaces**

### **3.1 Core Entities**

```typescript
interface Company {
  id: string;
  companyName: string;
  websiteUrl: string;
  industry: string | null;
  analysisMode: AnalysisMode;
  status: CompanyStatus;
  createdAt: Date;
  startedAt: Date | null;
  completedAt: Date | null;
  timeLimitMinutes: number;
  totalTokensUsed: number;
  estimatedCost: number;
  lastCheckpoint: string | null;
}

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

interface Entity {
  id: string;
  companyId: string;
  entityType: EntityType;
  entityValue: string;
  contextSnippet: string;
  sourceUrl: string;
  confidenceScore: number;
  createdAt: Date;
}

interface Analysis {
  id: string;
  companyId: string;
  versionNumber: number;
  executiveSummary: string;
  fullAnalysis: AnalysisSections;
  rawInsights: Record<string, any>;
  tokenBreakdown: TokenBreakdown;
  createdAt: Date;
}

interface TokenUsage {
  id: string;
  companyId: string;
  apiCallType: ApiCallType;
  inputTokens: number;
  outputTokens: number;
  timestamp: Date;
}

interface CheckpointData {
  pagesVisited: string[];
  pagesQueued: string[];
  externalLinksFound: string[];
  currentDepth: number;
  crawlStartTime: string;
  lastCheckpointTime: string;
  entitiesExtractedCount: number;
  analysisSectionsCompleted: string[];
}

interface AnalysisSections {
  companyOverview: SectionContent;
  businessModelProducts: SectionContent;
  teamLeadership: SectionContent;
  marketPosition: SectionContent;
  technologyOperations: SectionContent;
  keyInsights: SectionContent;
  redFlags: SectionContent | null;
}

interface SectionContent {
  content: string;
  sources: string[];
  confidence: number;
}

interface TokenBreakdown {
  totalInputTokens: number;
  totalOutputTokens: number;
  bySection: Record<string, { input: number; output: number }>;
}

interface AnalysisConfig {
  analysisMode: AnalysisMode;
  timeLimitMinutes: number;
  maxPages: number;
  maxDepth: number;
  followLinkedIn: boolean;
  followTwitter: boolean;
  followFacebook: boolean;
  exclusionPatterns: string[];
}
```

### **3.2 Common Types**

```typescript
interface AuditInfo {
  createdAt: Date;
  createdBy: string;
  updatedAt: Date;
  updatedBy: string;
  version: number;
}

interface PaginatedResponse<T> {
  data: T[];
  meta: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };
}

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}

interface ProgressUpdate {
  companyId: string;
  status: CompanyStatus;
  phase: ProcessingPhase;
  pagesCrawled: number;
  pagesTotal: number | null;
  entitiesExtracted: number;
  tokensUsed: number;
  timeElapsed: number;
  estimatedTimeRemaining: number | null;
  currentActivity: string;
}

interface ExportOptions {
  format: ExportFormat;
  includeRawData: boolean;
  includeSources: boolean;
}

interface BatchUploadResult {
  successful: number;
  failed: number;
  companies: Array<{
    companyName: string;
    companyId: string | null;
    error: string | null;
  }>;
}

interface ComparisonResult {
  companyId: string;
  previousVersion: number;
  currentVersion: number;
  changes: {
    team: ChangeDetail[];
    products: ChangeDetail[];
    content: ChangeDetail[];
  };
  significantChanges: boolean;
}

interface ChangeDetail {
  field: string;
  previousValue: string | null;
  currentValue: string | null;
  changeType: 'added' | 'removed' | 'modified';
}
```

### **3.3 Enums**

```typescript
enum CompanyStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  FAILED = 'failed',
  PAUSED = 'paused'
}

enum CrawlStatus {
  ACTIVE = 'active',
  PAUSED = 'paused',
  COMPLETED = 'completed',
  TIMEOUT = 'timeout'
}

enum AnalysisMode {
  QUICK = 'quick',
  THOROUGH = 'thorough'
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

enum EntityType {
  PERSON = 'person',
  ORGANIZATION = 'org',
  LOCATION = 'location',
  PRODUCT = 'product',
  DATE = 'date',
  MONEY = 'money',
  EMAIL = 'email',
  PHONE = 'phone',
  ADDRESS = 'address',
  SOCIAL_HANDLE = 'social_handle',
  TECH_STACK = 'tech_stack'
}

enum ApiCallType {
  EXTRACTION = 'extraction',
  SUMMARIZATION = 'summarization',
  ANALYSIS = 'analysis'
}

enum ExportFormat {
  MARKDOWN = 'markdown',
  WORD = 'word',
  PDF = 'pdf',
  JSON = 'json'
}

enum ProcessingPhase {
  QUEUED = 'queued',
  CRAWLING = 'crawling',
  EXTRACTING = 'extracting',
  ANALYZING = 'analyzing',
  GENERATING = 'generating',
  COMPLETED = 'completed'
}
```

---

## **4. Functional Requirements**

### **4.1 Company Input Management**

#### **4.1.1 Single Company Input**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-INP-001 | System shall provide a form to add a single company with name, website URL, and optional industry | P0 | Form renders with all fields; validation prevents submission without required fields |
| FR-INP-002 | System shall validate URL format and check reachability before accepting | P0 | Invalid URLs show error message; unreachable sites show warning with option to proceed |
| FR-INP-003 | System shall provide industry selection via dropdown with custom option | P1 | Dropdown shows common industries; custom text input available |
| FR-INP-004 | System shall expose advanced configuration options (mode, time limit, max pages, crawl depth, external links, exclusions) | P1 | All config options functional; defaults applied when not specified |

#### **4.1.2 Batch Upload**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-BAT-001 | System shall accept CSV file upload with columns: company_name, website_url, industry | P0 | CSV parsed correctly; preview shown before submission |
| FR-BAT-002 | System shall provide downloadable CSV template | P0 | Template download link works; template has correct headers |
| FR-BAT-003 | System shall validate all rows before processing and show errors per row | P0 | Invalid rows highlighted; valid rows can proceed while skipping invalid |
| FR-BAT-004 | System shall create analysis jobs for all valid companies in batch | P0 | All valid companies appear in queue with pending status |

### **4.2 Web Crawling Engine**

#### **4.2.1 Page Discovery**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-CRL-001 | System shall parse sitemap.xml when available for efficient page discovery | P0 | Sitemap detected and parsed; pages added to queue |
| FR-CRL-002 | System shall prioritize key page types: About, Team, Products, Services, Contact, Careers | P0 | Priority pages crawled first regardless of discovery order |
| FR-CRL-003 | System shall implement breadth-first crawling with configurable depth limit | P0 | Crawl respects depth limit; pages discovered in BFS order |
| FR-CRL-004 | System shall detect and skip duplicate content using content hashing | P1 | Duplicate pages not re-processed; hash stored for comparison |

#### **4.2.2 Crawl Behavior**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-CRL-005 | System shall respect robots.txt directives | P0 | Disallowed paths not crawled |
| FR-CRL-006 | System shall implement rate limiting (1 request/second default) | P0 | Request timing verified; no parallel requests to same domain |
| FR-CRL-007 | System shall handle JavaScript-rendered content using Playwright | P0 | SPA pages render fully before extraction |
| FR-CRL-008 | System shall skip binary files except text-containing PDFs | P1 | Images, videos ignored; PDFs with text extracted |
| FR-CRL-009 | System shall stop crawling when time limit reached | P0 | Crawl stops at time limit; checkpoint saved |
| FR-CRL-010 | System shall stop crawling when max page limit reached | P0 | Crawl stops at page limit; final state persisted |

#### **4.2.3 External Link Following**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-EXT-001 | System shall extract and optionally follow LinkedIn company profile links | P1 | LinkedIn URLs detected; profile data extracted when enabled |
| FR-EXT-002 | System shall extract and optionally follow Twitter/X company profile links | P1 | Twitter URLs detected; profile data extracted when enabled |
| FR-EXT-003 | System shall extract and optionally follow Facebook business page links | P1 | Facebook URLs detected; profile data extracted when enabled |
| FR-EXT-004 | System shall mark external pages distinctly in storage | P1 | is_external flag set correctly for all external pages |

### **4.3 State Management & Resume**

#### **4.3.1 Checkpointing**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-STA-001 | System shall persist crawl state every 10 pages or 2 minutes | P0 | Checkpoint written at defined intervals; data recoverable |
| FR-STA-002 | Checkpoint shall store: pages_visited, pages_queued, external_links_found, current_depth, timestamps, extraction counts, analysis progress | P0 | All checkpoint fields populated and accurate |
| FR-STA-003 | System shall allow user to pause an in-progress analysis | P0 | Pause button functional; status changes to paused; checkpoint saved |
| FR-STA-004 | System shall allow user to resume a paused analysis | P0 | Resume continues from last checkpoint; no duplicate work |

#### **4.3.2 Recovery**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-STA-005 | System shall automatically resume in_progress jobs on startup | P0 | Jobs resume after server restart; progress not lost |
| FR-STA-006 | System shall handle timeout gracefully with checkpoint preservation | P0 | Timeout triggers checkpoint; job marked appropriately |
| FR-STA-007 | System shall skip already-visited URLs on resume | P0 | No re-crawling of visited pages after resume |

### **4.4 Data Extraction (spaCy)**

#### **4.4.1 Entity Extraction**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-NER-001 | System shall extract company name variations | P0 | Multiple name forms captured; stored in entities table |
| FR-NER-002 | System shall extract locations (headquarters, offices) | P0 | Location entities extracted with context |
| FR-NER-003 | System shall extract people names with roles (CEO, founders, executives) | P0 | Person entities include role context; leadership identified |
| FR-NER-004 | System shall extract product and service names | P0 | Product entities linked to descriptions |
| FR-NER-005 | System shall extract organization mentions (partners, clients, investors) | P1 | Org relationships categorized |
| FR-NER-006 | System shall extract dates (founded, milestones) | P1 | Date entities with context preserved |
| FR-NER-007 | System shall extract monetary values (revenue, funding) | P1 | Money entities captured with currency |

#### **4.4.2 Structured Data Extraction**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-STR-001 | System shall extract email patterns | P0 | Emails validated and stored |
| FR-STR-002 | System shall extract phone numbers | P1 | Phone numbers normalized and stored |
| FR-STR-003 | System shall extract physical addresses | P1 | Addresses parsed and stored |
| FR-STR-004 | System shall extract social media handles | P1 | Handles linked to platforms |
| FR-STR-005 | System shall extract tech stack indicators from job postings and about pages | P2 | Technology mentions categorized |

### **4.5 AI Analysis (Claude API)**

#### **4.5.1 Content Analysis**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-ANA-001 | System shall summarize company mission and value proposition | P0 | Mission summary accurate and concise |
| FR-ANA-002 | System shall identify business model (B2B/B2C/SaaS/marketplace/etc.) | P0 | Business model correctly categorized |
| FR-ANA-003 | System shall assess company stage (startup/growth/established/enterprise) | P0 | Stage assessment with supporting evidence |
| FR-ANA-004 | System shall detect industry classification | P0 | Industry aligned with content |
| FR-ANA-005 | System shall identify target market and customer segments | P1 | Target market described with evidence |
| FR-ANA-006 | System shall extract competitive differentiators | P1 | Unique value propositions identified |
| FR-ANA-007 | System shall identify potential red flags | P1 | Inconsistencies and concerns flagged |

#### **4.5.2 Summary Generation**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-SUM-001 | System shall generate executive summary (3-4 paragraphs) | P0 | Summary readable and comprehensive |
| FR-SUM-002 | System shall generate structured sections: Overview, Business Model, Team, Market Position, Technology, Insights, Red Flags | P0 | All sections populated with relevant content |
| FR-SUM-003 | System shall include confidence indicators for uncertain data | P1 | Confidence scores visible for low-certainty claims |
| FR-SUM-004 | System shall cite sources for all factual claims | P0 | Source URLs linked throughout summary |

#### **4.5.3 Token Tracking**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-TOK-001 | System shall track input and output tokens per Claude API call | P0 | Token counts accurate per call |
| FR-TOK-002 | System shall aggregate total tokens per company analysis | P0 | Total matches sum of individual calls |
| FR-TOK-003 | System shall display cumulative token count in UI during processing | P0 | Real-time token counter updates |
| FR-TOK-004 | System shall calculate approximate cost based on token usage | P0 | Cost estimate based on current API pricing |

### **4.6 Output Generation**

#### **4.6.1 Summary Document**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-OUT-001 | System shall generate 2-page markdown summary with defined structure | P0 | Summary follows template; fits 2 pages when rendered |
| FR-OUT-002 | Summary shall include metadata: analysis date, website, industry, mode, tokens used | P0 | All metadata fields populated |
| FR-OUT-003 | Summary shall include source page count and links to key pages | P0 | Source links functional |

#### **4.6.2 Export Formats**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-EXP-001 | System shall export to Markdown (UTF-8) | P0 | Valid markdown file downloads |
| FR-EXP-002 | System shall export to Word (.docx) with formatting | P1 | Word document opens correctly with styles |
| FR-EXP-003 | System shall export to PDF with formatting | P1 | PDF renders correctly with styles |
| FR-EXP-004 | System shall export to JSON with all structured data | P1 | JSON contains all analysis fields |

### **4.7 Re-scan & Comparison**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| FR-RSC-001 | System shall store content hashes for key pages | P1 | Hashes stored and retrievable |
| FR-RSC-002 | System shall enable re-scan for any completed analysis | P1 | Re-scan button initiates new analysis |
| FR-RSC-003 | System shall compare new scan against previous version | P1 | Changes identified and categorized |
| FR-RSC-004 | System shall highlight changes in team, products, content | P1 | Change summary clearly shows differences |
| FR-RSC-005 | System shall store version history (last 3 scans) | P1 | Historical versions accessible |

---

## **5. User Roles & Access Control**

### **5.1 Role Definitions**

| Role | Description | Primary Responsibilities |
| ---- | ----------- | ------------------------ |
| User | Primary system user conducting company research | Submit companies for analysis, monitor progress, review results, export summaries |
| Admin | System administrator (future multi-user) | Manage configuration, view all analyses, system maintenance |

*Note: V1 is designed as a single-user application. Role-based access control infrastructure is included for future multi-user expansion.*

### **5.2 Feature Access Matrix**

| Feature/Permission | User | Admin |
| ------------------ | :--: | :---: |
| Add single company | ✅ | ✅ |
| Upload batch CSV | ✅ | ✅ |
| View company list | ✅ | ✅ |
| View analysis results | ✅ | ✅ |
| Export summaries | ✅ | ✅ |
| Pause/resume jobs | ✅ | ✅ |
| Delete companies | ✅ | ✅ |
| Re-scan companies | ✅ | ✅ |
| Configure analysis settings | ✅ | ✅ |
| View token usage | ✅ | ✅ |
| System configuration | ❌ | ✅ |
| View all users' data | ❌ | ✅ |

### **5.3 Role-Based Workflows**

**User Workflow:**
1. Submit company or batch for analysis via web interface
2. Monitor real-time progress on dashboard
3. Pause/resume jobs as needed
4. Review completed analysis summaries
5. Export results in preferred format
6. Re-scan companies to detect updates
7. Delete companies no longer needed

---

## **6. User Interface Specifications**

### **6.1 Design System**

#### **Design Principles**

| Principle | Description |
| --------- | ----------- |
| Desktop-First | Optimize for desktop productivity workflows |
| Accessibility | WCAG 2.1 Level AA compliance |
| Consistency | Unified component library across all views |
| Efficiency | Minimize clicks, progressive disclosure for advanced options |
| Clarity | Clear visual hierarchy with status-driven UI |

#### **Color Palette**

| Color | Hex | Usage |
| ----- | --- | ----- |
| Primary Blue | #2563eb | Primary actions, links |
| Success Green | #10b981 | Completed status, success messages |
| Warning Yellow | #f59e0b | In-progress status, warnings |
| Error Red | #ef4444 | Failed status, errors |
| Neutral Gray | #6b7280 | Secondary text, borders |
| Background | #f9fafb | Page background |
| Surface | #ffffff | Card backgrounds |
| Text Primary | #111827 | Primary text |
| Text Secondary | #6b7280 | Secondary text |

#### **Typography**

| Element | Font | Size | Weight |
| ------- | ---- | ---- | ------ |
| H1 | Inter / system-ui | 30px | 700 |
| H2 | Inter / system-ui | 24px | 600 |
| H3 | Inter / system-ui | 20px | 600 |
| Body | System font stack | 16px | 400 |
| Small | System font stack | 14px | 400 |
| Code/Data | Monospace | 14px | 400 |

#### **Spacing System (8px Base)**

| Token | Value | Usage |
| ----- | ----- | ----- |
| space-1 | 4px | Tight spacing, inline elements |
| space-2 | 8px | Default spacing |
| space-3 | 12px | Related element spacing |
| space-4 | 16px | Section padding |
| space-6 | 24px | Component gaps |
| space-8 | 32px | Large section breaks |

### **6.2 Component Library**

#### **Core UI Components**

| Component | Purpose |
| --------- | ------- |
| Button | Primary, secondary, danger, and ghost variants |
| Input | Text, URL, number inputs with validation |
| Select | Dropdown with search and custom option |
| Checkbox | Toggle options for external links |
| Slider | Time limit and numeric configuration |
| Table | Sortable, filterable data display |
| Card | Container for company items and summaries |
| Modal | Confirmations, raw data view |
| Toast | Action feedback notifications |
| Progress Bar | Visual progress indication |
| Badge | Status indicators |
| Tabs | Section navigation in results view |
| Skeleton | Loading state placeholders |

#### **Domain-Specific Components**

| Component | Purpose | Key Props |
| --------- | ------- | --------- |
| CompanyCard | Display company in list | company, onView, onExport, onDelete |
| ProgressTracker | Real-time progress display | progress: ProgressUpdate |
| TokenCounter | Live token usage display | tokensUsed, estimatedCost |
| AnalysisSummary | Rendered markdown summary | analysis: Analysis |
| EntityTable | Filterable entity list | entities: Entity[], filters |
| ExportDropdown | Format selection dropdown | onExport: (format) => void |
| ConfigPanel | Analysis configuration form | config: AnalysisConfig, onChange |
| BatchPreview | CSV upload preview table | rows: ParsedRow[], onConfirm |
| VersionSelector | Historical version picker | versions: Analysis[], onSelect |
| ChangeHighlight | Show differences between versions | comparison: ComparisonResult |

### **6.3 Page Layouts**

#### **Dashboard / Company List**

```
┌─────────────────────────────────────────────────────────────────┐
│  CIRA    [+ Add Company]  [Upload CSV]              [Settings]  │
├─────────────────────────────────────────────────────────────────┤
│  Filters: [Status ▼] [Date Range ▼]           Search: [______]  │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ Company Name    │ Website     │ Status  │ Tokens │ Actions│  │
│  ├───────────────────────────────────────────────────────────┤  │
│  │ Acme Corp       │ acme.com    │ ████ 65%│ 45,230 │ ⋮      │  │
│  │ Example Inc     │ example.com │ ✓ Done  │ 82,100 │ ⋮      │  │
│  │ Beta Labs       │ beta.io     │ ○ Pending│   -   │ ⋮      │  │
│  │ ...             │ ...         │ ...     │ ...    │ ...    │  │
│  └───────────────────────────────────────────────────────────┘  │
│                         [1] [2] [3] ... [10]                    │
└─────────────────────────────────────────────────────────────────┘
```

#### **Progress View**

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back    Acme Corp - acme.com                    [Pause] [✕]  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    Status: Analyzing...                                         │
│    ████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  45%          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Pages       │  │ Entities    │  │ Tokens      │              │
│  │   42 / 65   │  │    156      │  │   45,230    │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Time Elapsed: 12:34  │  Est. Remaining: ~8 min              ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Activity Log:                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ 12:45:32  Analyzing business model section...               ││
│  │ 12:45:28  Extracted 12 entities from /team                  ││
│  │ 12:45:20  Crawled /about-us                                 ││
│  │ 12:45:15  Following external: linkedin.com/company/acme     ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

#### **Results View**

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back    Acme Corp                    [Export ▼] [Re-scan]    │
├─────────────────────────────────────────────────────────────────┤
│  [Summary] [Entities] [Pages] [Token Usage]                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────┬──────────────────────────┐│
│  │                                  │ Analysis Info            ││
│  │  # Acme Corp - Intelligence     │ ────────────────────────  ││
│  │  Brief                          │ Date: Jan 15, 2026       ││
│  │                                  │ Mode: Thorough           ││
│  │  **Analysis Date:** Jan 15...   │ Tokens: 82,100           ││
│  │                                  │ Est. Cost: $0.82         ││
│  │  ## Executive Summary           │                          ││
│  │                                  │ Version: 2               ││
│  │  Acme Corp is a B2B SaaS...    │ [View v1]                ││
│  │                                  │                          ││
│  │  ## Company Overview            │ Sources                  ││
│  │  - **Founded:** 2018            │ ────────────────────────  ││
│  │  - **HQ:** San Francisco        │ • acme.com/about         ││
│  │  ...                            │ • acme.com/team          ││
│  │                                  │ • linkedin.com/acme      ││
│  └──────────────────────────────────┴──────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### **6.4 Application Structure**

| View | Primary Purpose | Key Features | Component Count |
| ---- | --------------- | ------------ | --------------- |
| Dashboard | Company management hub | List, filter, batch actions, quick stats | ~15 |
| Add Company | Single company input | Form validation, config options | ~10 |
| Batch Upload | Multi-company import | CSV parsing, preview, validation | ~8 |
| Progress | Real-time monitoring | Live updates, pause/cancel, activity log | ~12 |
| Results | Analysis review | Markdown rendering, tabs, export, compare | ~18 |
| Settings | Configuration | API keys, defaults, data management | ~8 |

---

## **7. API Specifications**

### **7.1 API Design Principles**

- RESTful design with consistent resource naming
- JSON request/response bodies
- No authentication required for V1 (single-user)
- Rate limiting on external API calls (Claude)
- Versioned endpoints: `/api/v1/`

### **7.2 Company Endpoints**

#### **POST /api/v1/companies**

Create a single company analysis job.

**Request:**
```json
{
  "companyName": "Acme Corp",
  "websiteUrl": "https://www.acmecorp.com",
  "industry": "Technology",
  "config": {
    "analysisMode": "thorough",
    "timeLimitMinutes": 30,
    "maxPages": 100,
    "maxDepth": 3,
    "followLinkedIn": true,
    "followTwitter": true,
    "followFacebook": false,
    "exclusionPatterns": ["/blog/*", "/news/*"]
  }
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "companyId": "cmp_abc123",
    "status": "pending",
    "createdAt": "2026-01-17T10:30:00Z"
  }
}
```

#### **POST /api/v1/companies/batch**

Upload CSV for batch processing.

**Request:** `multipart/form-data` with CSV file

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "totalCount": 10,
    "successful": 9,
    "failed": 1,
    "companies": [
      { "companyName": "Acme Corp", "companyId": "cmp_abc123", "error": null },
      { "companyName": "Bad URL Inc", "companyId": null, "error": "Invalid URL format" }
    ]
  }
}
```

#### **GET /api/v1/companies**

List all companies with filtering and pagination.

**Query Parameters:**
- `status`: Filter by status (pending, in_progress, completed, failed, paused)
- `sort`: Sort field (created_at, company_name, tokens_used)
- `order`: Sort order (asc, desc)
- `page`: Page number (default: 1)
- `pageSize`: Items per page (default: 20, max: 100)

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "cmp_abc123",
      "companyName": "Acme Corp",
      "websiteUrl": "https://acmecorp.com",
      "status": "completed",
      "totalTokensUsed": 82100,
      "estimatedCost": 0.82,
      "createdAt": "2026-01-15T10:30:00Z",
      "completedAt": "2026-01-15T10:52:00Z"
    }
  ],
  "meta": {
    "total": 45,
    "page": 1,
    "pageSize": 20,
    "totalPages": 3
  }
}
```

#### **GET /api/v1/companies/:id**

Get company details with analysis.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "company": {
      "id": "cmp_abc123",
      "companyName": "Acme Corp",
      "websiteUrl": "https://acmecorp.com",
      "industry": "Technology",
      "analysisMode": "thorough",
      "status": "completed",
      "totalTokensUsed": 82100,
      "estimatedCost": 0.82
    },
    "analysis": {
      "id": "ana_xyz789",
      "versionNumber": 2,
      "executiveSummary": "Acme Corp is a B2B SaaS company...",
      "fullAnalysis": { ... },
      "createdAt": "2026-01-15T10:52:00Z"
    },
    "entityCount": 156,
    "pageCount": 65
  }
}
```

#### **GET /api/v1/companies/:id/progress**

Get real-time progress for in-progress job.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "companyId": "cmp_abc123",
    "status": "in_progress",
    "phase": "analyzing",
    "pagesCrawled": 42,
    "pagesTotal": 65,
    "entitiesExtracted": 128,
    "tokensUsed": 45230,
    "timeElapsed": 754,
    "estimatedTimeRemaining": 480,
    "currentActivity": "Analyzing business model section..."
  }
}
```

#### **POST /api/v1/companies/:id/pause**

Pause an in-progress analysis.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "paused",
    "checkpointSaved": true,
    "pausedAt": "2026-01-17T11:15:00Z"
  }
}
```

#### **POST /api/v1/companies/:id/resume**

Resume a paused analysis.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "in_progress",
    "resumedFrom": {
      "pagesCrawled": 42,
      "entitiesExtracted": 128,
      "phase": "analyzing"
    }
  }
}
```

#### **POST /api/v1/companies/:id/rescan**

Initiate re-scan for updates.

**Response (202 Accepted):**
```json
{
  "success": true,
  "data": {
    "newAnalysisId": "ana_new456",
    "versionNumber": 3,
    "status": "pending"
  }
}
```

#### **GET /api/v1/companies/:id/export**

Export analysis in specified format.

**Query Parameters:**
- `format`: Export format (markdown, word, pdf, json)
- `includeRawData`: Include all extracted data (default: false)

**Response:** File download with appropriate Content-Type

#### **GET /api/v1/companies/:id/tokens**

Get detailed token usage breakdown.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "totalTokens": 82100,
    "totalInputTokens": 68500,
    "totalOutputTokens": 13600,
    "estimatedCost": 0.82,
    "byApiCall": [
      {
        "callType": "analysis",
        "section": "executive_summary",
        "inputTokens": 12500,
        "outputTokens": 1200,
        "timestamp": "2026-01-15T10:48:00Z"
      }
    ]
  }
}
```

#### **GET /api/v1/companies/:id/entities**

Get all extracted entities for a company.

**Query Parameters:**
- `type`: Filter by entity type
- `minConfidence`: Minimum confidence score (0-1)
- `page`, `pageSize`: Pagination

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "ent_001",
      "entityType": "person",
      "entityValue": "John Smith",
      "contextSnippet": "John Smith, CEO and founder...",
      "sourceUrl": "https://acmecorp.com/team",
      "confidenceScore": 0.95
    }
  ],
  "meta": { ... }
}
```

#### **GET /api/v1/companies/:id/pages**

Get all crawled pages for a company.

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "id": "pag_001",
      "url": "https://acmecorp.com/about",
      "pageType": "about",
      "crawledAt": "2026-01-15T10:32:00Z",
      "isExternal": false
    }
  ]
}
```

#### **GET /api/v1/companies/:id/versions**

Get analysis version history.

**Response (200 OK):**
```json
{
  "success": true,
  "data": [
    {
      "analysisId": "ana_xyz789",
      "versionNumber": 2,
      "createdAt": "2026-01-15T10:52:00Z",
      "tokenUsed": 82100
    },
    {
      "analysisId": "ana_abc456",
      "versionNumber": 1,
      "createdAt": "2026-01-10T14:30:00Z",
      "tokenUsed": 75400
    }
  ]
}
```

#### **GET /api/v1/companies/:id/compare**

Compare two analysis versions.

**Query Parameters:**
- `version1`: First version number
- `version2`: Second version number

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "companyId": "cmp_abc123",
    "previousVersion": 1,
    "currentVersion": 2,
    "changes": {
      "team": [
        { "field": "CTO", "previousValue": "Jane Doe", "currentValue": "Bob Wilson", "changeType": "modified" }
      ],
      "products": [],
      "content": [
        { "field": "Mission statement", "previousValue": null, "currentValue": "...", "changeType": "added" }
      ]
    },
    "significantChanges": true
  }
}
```

#### **DELETE /api/v1/companies/:id**

Delete company and all associated data.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "deleted": true,
    "deletedRecords": {
      "pages": 65,
      "entities": 156,
      "analyses": 2
    }
  }
}
```

### **7.3 Configuration Endpoints**

#### **GET /api/v1/config**

Get current configuration.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "defaults": {
      "analysisMode": "thorough",
      "timeLimitMinutes": 30,
      "maxPages": 100,
      "maxDepth": 3
    },
    "quickMode": {
      "maxPages": 20,
      "maxDepth": 2,
      "followExternal": false
    },
    "thoroughMode": {
      "maxPages": 100,
      "maxDepth": 3,
      "followExternal": true
    }
  }
}
```

#### **PUT /api/v1/config**

Update configuration.

**Request:**
```json
{
  "defaults": {
    "timeLimitMinutes": 45
  }
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": { ... }
}
```

### **7.4 Error Responses**

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": {
      "websiteUrl": ["Invalid URL format"]
    }
  }
}
```

| Error Code | HTTP Status | Description |
| ---------- | ----------- | ----------- |
| VALIDATION_ERROR | 400 | Request validation failed |
| NOT_FOUND | 404 | Company or resource not found |
| CONFLICT | 409 | Company already exists or operation conflict |
| INVALID_STATE | 422 | Operation not valid for current state |
| RATE_LIMITED | 429 | Too many requests |
| EXTERNAL_API_ERROR | 502 | Claude API or external service error |
| INTERNAL_ERROR | 500 | Server error |

---

## **8. Integration Requirements**

### **8.1 External System Integrations**

| System | Integration Type | Purpose | Data Flow |
| ------ | ---------------- | ------- | --------- |
| Anthropic Claude API | REST API | AI-powered content analysis and summarization | Outbound: page content, prompts; Inbound: analysis text, token counts |
| Target Company Websites | Web Crawling | Source data extraction | Inbound: HTML, text content |
| LinkedIn | Web Scraping | Company profile data extraction | Inbound: profile data (when enabled) |
| Twitter/X | Web Scraping | Company profile data extraction | Inbound: profile data (when enabled) |
| Facebook | Web Scraping | Business page data extraction | Inbound: page data (when enabled) |

### **8.2 Claude API Integration Specifications**

**Authentication:**
- API key stored in environment variable `ANTHROPIC_API_KEY`
- Key passed via `x-api-key` header

**Rate Limiting:**
- Implement exponential backoff on 429 responses
- Queue management for concurrent requests
- Maximum 3 retries per request

**Error Handling:**
- Retry on transient errors (5xx, timeouts)
- Fall back gracefully if API unavailable
- Log all API errors for debugging

**Token Management:**
- Track input_tokens and output_tokens from response
- Calculate cost using current pricing
- Store per-call and aggregate metrics

### **8.3 Web Crawling Integration**

**Playwright Configuration:**
- Headless browser mode
- 30-second timeout per page
- Viewport: 1920x1080
- User-Agent: "CIRA Bot/1.0"

**Rate Limiting:**
- 1 request per second to same domain
- Respect Crawl-delay from robots.txt
- Exponential backoff on errors

**robots.txt Compliance:**
- Parse and cache robots.txt
- Honor Disallow directives
- Check before each request

---

## **9. Non-Functional Requirements**

### **9.1 Security Requirements**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| NFR-SEC-001 | API keys stored in environment variables, never in code | P0 | No secrets in codebase |
| NFR-SEC-002 | Input validation on all user inputs to prevent injection | P0 | SQLi, XSS tests pass |
| NFR-SEC-003 | SQL injection prevention via parameterized queries (SQLAlchemy ORM) | P0 | Security scan clean |
| NFR-SEC-004 | No storage of sensitive PII beyond business information | P0 | Data audit verification |
| NFR-SEC-005 | Secure file export with proper Content-Disposition headers | P1 | File download security verified |

### **9.2 Performance Requirements**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| NFR-PER-001 | API response time < 200ms for non-blocking operations | P0 | Load testing verification |
| NFR-PER-002 | UI responsiveness < 200ms for user interactions | P0 | Performance monitoring |
| NFR-PER-003 | Crawl speed of 1-2 pages/second (respecting rate limits) | P0 | Crawl timing logs |
| NFR-PER-004 | Database queries < 100ms for most operations | P0 | Query profiling |
| NFR-PER-005 | Export generation < 5 seconds for standard formats | P1 | Export timing tests |
| NFR-PER-006 | Progress updates every 2 seconds during active processing | P0 | Real-time update verification |

### **9.3 Availability & Reliability**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| NFR-AVL-001 | System available 99% of uptime (excluding maintenance) | P0 | Uptime monitoring |
| NFR-AVL-002 | Automatic retry on transient network failures (3 attempts) | P0 | Retry logic verification |
| NFR-AVL-003 | Graceful degradation if Claude API unavailable | P0 | Failover testing |
| NFR-AVL-004 | Data integrity with database transactions | P0 | Transaction verification |
| NFR-AVL-005 | Resume capability works 100% after interruptions | P0 | Resume testing |

### **9.4 Scalability Requirements**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| NFR-SCA-001 | Support 100+ companies in single batch | P0 | Batch testing |
| NFR-SCA-002 | Database optimized for 10,000+ company records | P1 | Performance at scale |
| NFR-SCA-003 | Configurable number of concurrent Celery workers | P1 | Worker scaling tests |
| NFR-SCA-004 | Efficient pagination for large datasets | P1 | Pagination performance |

### **9.5 Accessibility Requirements**

| ID | Requirement | Priority | Acceptance Criteria |
| -- | ----------- | -------- | ------------------- |
| NFR-ACC-001 | WCAG 2.1 Level AA compliance | P1 | Accessibility audit |
| NFR-ACC-002 | Full keyboard navigation support | P1 | Manual testing |
| NFR-ACC-003 | Screen reader compatibility (NVDA, VoiceOver) | P1 | Screen reader testing |
| NFR-ACC-004 | Color contrast ratios ≥ 4.5:1 | P1 | Automated checking |
| NFR-ACC-005 | Focus indicators visible on all interactive elements | P1 | Visual verification |

### **9.6 Browser & Device Support**

**Web Application:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Minimum Screen Resolution:**
- 1280x720 (desktop-first design)
- Responsive down to 1024px width

---

## **10. Glossary**

| Term | Definition |
| ---- | ---------- |
| Analysis | The AI-generated intelligence report for a company including summary and structured sections |
| Batch Processing | Submitting multiple companies for analysis simultaneously via CSV upload |
| Checkpoint | A saved state of crawl/analysis progress enabling resume after interruption |
| Crawl Depth | The number of link-follows from the starting URL (homepage = depth 0) |
| Entity | A structured piece of information extracted via NLP (person, organization, location, etc.) |
| NER | Named Entity Recognition - NLP technique for identifying and classifying entities in text |
| Quick Mode | Analysis configuration with lower page limits and depth for faster results |
| Re-scan | Running a new analysis on a previously analyzed company to detect changes |
| spaCy | Open-source NLP library used for entity extraction |
| Thorough Mode | Analysis configuration with higher limits for comprehensive coverage |
| Token | Unit of text processed by Claude API; used for usage tracking and cost calculation |

---

## **Appendix A: User Stories**

### **Research Analyst Stories**

> "As a research analyst, I want to submit a batch of companies via CSV so that I can analyze multiple potential partners simultaneously."

> "As a research analyst, I want to monitor the real-time progress of my analysis jobs so that I can estimate when results will be ready."

> "As a research analyst, I want to pause and resume analysis jobs so that I can manage long-running tasks without losing progress."

> "As a research analyst, I want to choose between quick and thorough analysis modes so that I can balance speed versus comprehensiveness based on my needs."

> "As a research analyst, I want to view a structured 2-page summary so that I can quickly understand a company's key information."

> "As a research analyst, I want to export summaries to Word and PDF so that I can share findings with colleagues who don't use the system."

> "As a research analyst, I want to re-scan companies so that I can detect changes since my last analysis."

> "As a research analyst, I want to see token usage and cost estimates so that I can manage my API budget."

> "As a research analyst, I want to view the raw extracted entities so that I can verify and explore the source data."

> "As a research analyst, I want to follow LinkedIn company profiles so that I can get additional professional context."

---

## **Appendix B: Wireframes & Mockups**

Wireframe diagrams are provided in Section 6.3 (Page Layouts) using ASCII representations. High-fidelity mockups should be created during the design phase following the design system specifications in Section 6.1.

---

## **Appendix C: Data Retention & Privacy**

| Data Type | Retention Period | Deletion Policy |
| --------- | ---------------- | --------------- |
| Company Records | Indefinite (user-controlled) | Deleted on user request |
| Crawled Page Content | Indefinite (user-controlled) | Deleted with company record |
| Extracted Entities | Indefinite (user-controlled) | Deleted with company record |
| Analysis Summaries | Keep last 3 versions per company | Older versions auto-deleted |
| Token Usage Logs | 1 year | Auto-deleted after retention period |
| Export Files | 7 days | Auto-deleted from server; user retains downloads |

**Privacy Considerations:**
- System only processes publicly available information
- No personal data beyond business context is stored
- Users responsible for compliance with their jurisdiction's data laws
- No data shared with third parties except Claude API for processing

---

## **Priority Definitions**

| Priority | Definition | Implementation |
| -------- | ---------- | -------------- |
| **P0** | Must-have for MVP | Required before launch |
| **P1** | Important for completeness | Implement in first iteration |
| **P2** | Nice-to-have | Future enhancement |
| **P3** | Future consideration | Backlog |

---

*— End of Document —*