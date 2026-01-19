# Architecture

**Analysis Date:** 2026-01-19

## Pattern Overview

**Overall:** Monorepo with separate Frontend SPA and Backend REST API

**Key Characteristics:**
- React SPA frontend with React Query for server state
- Flask backend with application factory pattern
- Celery for async background job processing
- SQLAlchemy ORM with SQLite/PostgreSQL
- Redis for caching, job queues, and real-time progress

## Layers

**Frontend Presentation Layer:**
- Purpose: User interface and user interactions
- Location: `frontend/src/`
- Contains: React components, pages, routing
- Depends on: API layer, UI component library
- Used by: End users via browser

**Frontend API Layer:**
- Purpose: HTTP communication with backend
- Location: `frontend/src/api/`
- Contains: Axios client, API endpoint functions
- Depends on: Backend REST API
- Used by: React Query hooks, components

**Frontend State Management:**
- Purpose: Server state caching and synchronization
- Location: `frontend/src/hooks/`
- Contains: React Query hooks for data fetching/mutations
- Depends on: API layer
- Used by: Page components

**Backend API Routes:**
- Purpose: REST endpoints and request handling
- Location: `backend/app/api/routes/`
- Contains: Flask route handlers, request validation
- Depends on: Services, Models, Schemas
- Used by: Frontend via HTTP

**Backend Services:**
- Purpose: Business logic and orchestration
- Location: `backend/app/services/`
- Contains: JobService, ExportService, RedisService, etc.
- Depends on: Models, Workers, External APIs
- Used by: API routes, Workers

**Backend Workers:**
- Purpose: Async background job processing
- Location: `backend/app/workers/`
- Contains: Celery tasks for crawling, extraction, analysis
- Depends on: Services, Models, Redis
- Used by: Job queue system

**Backend Models:**
- Purpose: Data persistence and ORM mapping
- Location: `backend/app/models/`
- Contains: SQLAlchemy models (Company, Page, Entity, Analysis)
- Depends on: SQLAlchemy, database
- Used by: Services, Routes, Workers

**Backend Schemas:**
- Purpose: Request/response validation and serialization
- Location: `backend/app/schemas/`
- Contains: Pydantic models with camelCase conversion
- Depends on: Pydantic
- Used by: API routes

**Crawlers Module:**
- Purpose: Web page fetching and content extraction
- Location: `backend/app/crawlers/`
- Contains: CrawlWorker, sitemap/robots parsers, rate limiter
- Depends on: External websites, Redis (rate limiting)
- Used by: Workers

**Extractors Module:**
- Purpose: NLP and structured data extraction
- Location: `backend/app/extractors/`
- Contains: spaCy NLP pipeline, deduplicator
- Depends on: spaCy models
- Used by: Workers

**Analysis Module:**
- Purpose: AI-powered content analysis
- Location: `backend/app/analysis/`
- Contains: Prompt templates, synthesis logic
- Depends on: Anthropic Claude API
- Used by: Workers

## Data Flow

**Company Creation Flow:**

1. User submits company form in frontend `AddCompany.tsx`
2. `useCreateCompany` hook calls `createCompany` API function
3. POST `/api/v1/companies` handled by `companies.py` route
4. Company record created in database with `pending` status
5. Response returned with `companyId`

**Analysis Pipeline Flow:**

1. JobService starts job via `start_job(company_id)`
2. Celery task `crawl_company` dispatched to `crawl` queue
3. Crawl worker fetches pages, stores in database
4. Task `extract_entities` processes pages with spaCy
5. Task `analyze_content` calls Claude API for analysis
6. Task `generate_summary` finalizes and marks complete
7. Progress updates pushed to Redis throughout

**Real-time Progress Flow:**

1. Frontend polls `/api/v1/companies/{id}/progress` every 2 seconds
2. Route handler fetches progress from Redis via `redis_service`
3. Progress includes: phase, pages crawled, entities, activity
4. Frontend `CompanyProgress.tsx` renders live status

**State Management:**
- React Query manages server state with automatic caching
- 5-minute stale time for queries
- Optimistic updates for mutations
- Query invalidation on successful mutations

## Key Abstractions

**Company:**
- Purpose: Central entity representing a company to analyze
- Examples: `backend/app/models/company.py`
- Pattern: SQLAlchemy model with relationships to Pages, Entities, Analyses

**Celery Task:**
- Purpose: Async background job unit of work
- Examples: `backend/app/workers/tasks.py`
- Pattern: Decorated functions with retry logic and error handling

**Pydantic Schema:**
- Purpose: Type-safe request/response validation
- Examples: `backend/app/schemas/base.py`, `backend/app/schemas/company.py`
- Pattern: CamelCaseModel base class for snake_case to camelCase conversion

**React Query Hook:**
- Purpose: Data fetching with caching and mutations
- Examples: `frontend/src/hooks/useCompanies.ts`
- Pattern: Custom hooks wrapping useQuery/useMutation

**UI Component:**
- Purpose: Reusable presentation element
- Examples: `frontend/src/components/ui/Button.tsx`, `frontend/src/components/ui/Table.tsx`
- Pattern: TypeScript React components with typed props

## Entry Points

**Frontend Application:**
- Location: `frontend/src/main.tsx`
- Triggers: Browser loading index.html
- Responsibilities: Initialize React, QueryClient, Router, render app

**Backend Application:**
- Location: `backend/run.py`
- Triggers: `python run.py` or WSGI server
- Responsibilities: Load env, create Flask app via factory, start server

**Celery Worker:**
- Location: `backend/app/workers/celery_app.py`
- Triggers: `celery -A app.workers.celery_app worker`
- Responsibilities: Process background jobs from Redis queues

**API Blueprint:**
- Location: `backend/app/api/__init__.py`
- Triggers: Request to `/api/v1/*`
- Responsibilities: Route registration, prefix handling

## Error Handling

**Strategy:** Multi-layer error handling with typed responses

**Patterns:**
- Backend: Try/except with `make_error_response` helper returning `ApiErrorResponse`
- Celery: Auto-retry with exponential backoff, `RetryableError` vs `PermanentError`
- Frontend: Axios interceptors log errors, callers handle via try/catch
- React Query: `isError` state exposed to components for UI feedback

## Cross-Cutting Concerns

**Logging:**
- Backend uses Python logging with RotatingFileHandler
- Configured in `create_app()` based on LOG_LEVEL env var
- Logs to `backend/logs/cira.log` in production

**Validation:**
- Backend: Pydantic models validate request bodies, return `VALIDATION_ERROR`
- Frontend: TypeScript types provide compile-time checking
- URL validation via `url_validator.py` with reachability checks

**Authentication:**
- Currently not implemented (prepared structure in Axios interceptors)
- Security middleware adds headers via `init_security_middleware`

**CORS:**
- Configured in Flask app factory via `flask_cors`
- Origins read from `CORS_ORIGINS` config

---

*Architecture analysis: 2026-01-19*
