# Codebase Structure

**Analysis Date:** 2026-01-19

## Directory Layout

```
Cira/
├── backend/                    # Python Flask backend
│   ├── app/                    # Application package
│   │   ├── api/                # REST API routes
│   │   │   └── routes/         # Route handlers by resource
│   │   ├── analysis/           # AI analysis logic
│   │   ├── crawlers/           # Web crawling modules
│   │   ├── extractors/         # NLP entity extraction
│   │   ├── middleware/         # Request middleware
│   │   ├── models/             # SQLAlchemy ORM models
│   │   ├── schemas/            # Pydantic request/response schemas
│   │   ├── services/           # Business logic services
│   │   ├── utils/              # Utility functions
│   │   └── workers/            # Celery background tasks
│   ├── migrations/             # Alembic database migrations
│   ├── tests/                  # Backend test suite
│   ├── logs/                   # Application logs (generated)
│   ├── venv/                   # Python virtual environment
│   └── run.py                  # Application entry point
├── frontend/                   # React TypeScript frontend
│   ├── src/                    # Source code
│   │   ├── api/                # API client and functions
│   │   ├── assets/             # Static assets
│   │   ├── components/         # React components
│   │   │   ├── ui/             # Reusable UI components
│   │   │   └── domain/         # Domain-specific components
│   │   ├── hooks/              # React Query hooks
│   │   ├── lib/                # Utility libraries
│   │   ├── pages/              # Page components
│   │   ├── test/               # Test setup
│   │   └── types/              # TypeScript type definitions
│   ├── public/                 # Static public files
│   ├── e2e/                    # Playwright E2E tests
│   └── dist/                   # Build output (generated)
├── docker/                     # Docker configuration
├── specs/                      # Project specifications
├── .claude/                    # Claude agent configurations
│   └── agents/                 # Agent definitions
└── .planning/                  # Planning documents
    └── codebase/               # Codebase analysis docs
```

## Directory Purposes

**`backend/app/`:**
- Purpose: Flask application package with all backend code
- Contains: Application factory, extensions, modules
- Key files: `__init__.py` (app factory), `config.py` (settings)

**`backend/app/api/routes/`:**
- Purpose: REST API endpoint handlers
- Contains: Route files by resource (companies, batch, health, etc.)
- Key files: `companies.py`, `batch.py`, `health.py`, `progress.py`, `export.py`

**`backend/app/models/`:**
- Purpose: SQLAlchemy database models
- Contains: ORM class definitions, enum definitions
- Key files: `company.py` (Company, Page, Entity, Analysis), `enums.py`, `batch.py`

**`backend/app/schemas/`:**
- Purpose: Pydantic request/response schemas
- Contains: Validation models with camelCase serialization
- Key files: `base.py`, `company.py`, `health.py`, `version.py`

**`backend/app/services/`:**
- Purpose: Business logic and external integrations
- Contains: Service classes for specific functionality
- Key files: `job_service.py`, `redis_service.py`, `export_service.py`, `anthropic_service.py`

**`backend/app/workers/`:**
- Purpose: Celery background task definitions
- Contains: Task functions for async processing
- Key files: `celery_app.py` (Celery config), `tasks.py` (task definitions)

**`backend/app/crawlers/`:**
- Purpose: Web crawling and content fetching
- Contains: Crawler components and parsers
- Key files: `crawl_worker.py`, `sitemap_parser.py`, `robots_parser.py`, `rate_limiter.py`

**`backend/app/extractors/`:**
- Purpose: NLP entity extraction pipeline
- Contains: spaCy integration and deduplication
- Key files: `nlp_pipeline.py`, `deduplicator.py`

**`backend/app/analysis/`:**
- Purpose: AI-powered content analysis
- Contains: Prompt templates and synthesis logic
- Key files: `prompts.py`, `synthesis.py`

**`frontend/src/api/`:**
- Purpose: Backend API communication
- Contains: Axios client, endpoint functions
- Key files: `client.ts` (Axios config), `companies.ts` (company endpoints), `health.ts`

**`frontend/src/components/ui/`:**
- Purpose: Reusable UI component library
- Contains: Design system components
- Key files: `Button.tsx`, `Table.tsx`, `Modal.tsx`, `Toast.tsx`, `index.ts` (exports)

**`frontend/src/components/domain/`:**
- Purpose: Domain-specific composite components
- Contains: Components tied to business logic
- Key files: `ChangeHighlight.tsx`, `VersionSelector.tsx`

**`frontend/src/hooks/`:**
- Purpose: React Query data fetching hooks
- Contains: Custom hooks for API operations
- Key files: `useCompanies.ts` (all company-related hooks), `index.ts`

**`frontend/src/pages/`:**
- Purpose: Page-level route components
- Contains: Full page layouts for routes
- Key files: `Dashboard.tsx`, `AddCompany.tsx`, `CompanyResults.tsx`, `CompanyProgress.tsx`

**`frontend/src/types/`:**
- Purpose: TypeScript type definitions
- Contains: Shared interfaces and type aliases
- Key files: `index.ts` (all types)

## Key File Locations

**Entry Points:**
- `backend/run.py`: Flask application entry point
- `frontend/src/main.tsx`: React application entry point
- `backend/app/workers/celery_app.py`: Celery worker entry point

**Configuration:**
- `backend/app/config.py`: Flask configuration classes
- `frontend/vite.config.ts`: Vite build configuration
- `frontend/tsconfig.json`: TypeScript configuration
- `frontend/eslint.config.js`: ESLint configuration

**Core Logic:**
- `backend/app/__init__.py`: Flask app factory with `create_app()`
- `frontend/src/router.tsx`: React Router configuration
- `backend/app/api/__init__.py`: API blueprint registration

**Testing:**
- `backend/tests/`: Pytest test files
- `backend/tests/conftest.py`: Test fixtures
- `frontend/src/test/setup.ts`: Vitest setup
- `frontend/src/components/ui/*.test.tsx`: Component unit tests

## Naming Conventions

**Files:**
- Python: `snake_case.py` (e.g., `job_service.py`, `crawl_worker.py`)
- TypeScript: `PascalCase.tsx` for components, `camelCase.ts` for utilities
- Test files: `*.test.tsx` or `test_*.py`

**Directories:**
- Python: `snake_case` (e.g., `api/routes/`)
- TypeScript: `camelCase` or `lowercase` (e.g., `components/ui/`)

**Components:**
- React: PascalCase (e.g., `Button.tsx`, `Dashboard.tsx`)
- Exports match filename

**Models/Classes:**
- Python: PascalCase (e.g., `Company`, `JobService`)
- TypeScript: PascalCase for interfaces/types

## Where to Add New Code

**New API Endpoint:**
- Create route handler in `backend/app/api/routes/`
- Add schema in `backend/app/schemas/` if needed
- Import route in `backend/app/api/__init__.py`
- Add frontend API function in `frontend/src/api/`
- Create React Query hook in `frontend/src/hooks/`

**New Page:**
- Create page component in `frontend/src/pages/`
- Add route in `frontend/src/router.tsx` with lazy loading
- Use existing UI components from `frontend/src/components/ui/`

**New UI Component:**
- Create component in `frontend/src/components/ui/`
- Create test file `*.test.tsx` alongside
- Export from `frontend/src/components/ui/index.ts`

**New Background Task:**
- Add task function in `backend/app/workers/tasks.py`
- Configure queue routing in `backend/app/workers/celery_app.py`

**New Database Model:**
- Add model class in `backend/app/models/`
- Export from `backend/app/models/__init__.py`
- Create Alembic migration: `flask db migrate`

**New Service:**
- Create service class in `backend/app/services/`
- Export from `backend/app/services/__init__.py`
- Use lazy imports to avoid circular dependencies

**New Domain Component:**
- Create in `frontend/src/components/domain/`
- Export from `frontend/src/components/domain/index.ts`

## Special Directories

**`backend/venv/`:**
- Purpose: Python virtual environment
- Generated: Yes (via `python -m venv venv`)
- Committed: No (in .gitignore)

**`frontend/node_modules/`:**
- Purpose: npm dependencies
- Generated: Yes (via `npm install`)
- Committed: No (in .gitignore)

**`frontend/dist/`:**
- Purpose: Production build output
- Generated: Yes (via `npm run build`)
- Committed: No (in .gitignore)

**`backend/logs/`:**
- Purpose: Application log files
- Generated: Yes (at runtime)
- Committed: No (in .gitignore)

**`backend/migrations/versions/`:**
- Purpose: Alembic database migration scripts
- Generated: Yes (via `flask db migrate`)
- Committed: Yes (version controlled)

**`.planning/codebase/`:**
- Purpose: Codebase analysis documentation
- Generated: Yes (by Claude agents)
- Committed: Yes (version controlled)

---

*Structure analysis: 2026-01-19*
