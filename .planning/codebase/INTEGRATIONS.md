# External Integrations

**Analysis Date:** 2026-01-19

## APIs & External Services

**AI/LLM:**
- Anthropic Claude API - Company intelligence analysis and synthesis
  - SDK/Client: `anthropic` Python package (`backend/app/services/anthropic_service.py`)
  - Auth: `ANTHROPIC_API_KEY` environment variable
  - Model: `claude-sonnet-4-20250514` (configurable via `CLAUDE_MODEL`)
  - Features: Exponential backoff on 429, max 3 retries, 60s timeout
  - Token tracking: Input/output tokens tracked per API call
  - Cost calculation: $3/1M input tokens, $15/1M output tokens

**Web Crawling:**
- Target websites (user-provided) - Company information extraction
  - Client: Playwright headless browser (`backend/app/crawlers/browser_manager.py`)
  - Fallback: requests + BeautifulSoup for non-JS pages
  - Config: 30s timeout, 1920x1080 viewport, "CIRA Bot/1.0" user-agent
  - Features: robots.txt compliance, rate limiting, sitemap parsing

## Data Storage

**Primary Database:**
- SQLite (development/default)
  - Connection: `DATABASE_URL` env var (default: `sqlite:///cira.db`)
  - ORM: SQLAlchemy 2.0+ with Flask-SQLAlchemy
  - Models: `backend/app/models/company.py`, `backend/app/models/batch.py`
  - Migrations: Flask-Migrate in `backend/migrations/`

- PostgreSQL (production-ready)
  - Same `DATABASE_URL` format: `postgresql://user:pass@host:port/db`
  - Connection pooling configured in `backend/app/config.py`
  - Pool size: 10 (configurable via `DB_POOL_SIZE`)

**Caching/State:**
- Redis 7.x
  - Connection: `REDIS_URL` env var (default: `redis://localhost:6379/0`)
  - Client: `redis` Python package with connection pooling (`backend/app/services/redis_service.py`)
  - Uses:
    - Job progress/status tracking (24h TTL)
    - Distributed locking for concurrent jobs
    - General caching (1h default TTL)
  - Key namespace: `cira:` prefix for all keys

**File Storage:**
- Local filesystem only
  - Logs: `backend/logs/`, `logs/`
  - Database file: `backend/instance/cira.db`
  - Export files: Generated on-demand, returned as response (not persisted)

## Task Queue

**Celery:**
- Broker: Redis (separate DB: `redis://localhost:6379/1`)
- Result Backend: Redis (same as broker)
- Configuration: `backend/app/workers/celery_app.py`
- Queues:
  - `default` - General tasks
  - `crawl` - Web crawling tasks
  - `extract` - Entity extraction tasks
  - `analyze` - Claude analysis tasks
- Task routing:
  - `crawl_company`, `crawl_page` -> `crawl` queue
  - `extract_entities` -> `extract` queue
  - `analyze_content`, `generate_summary` -> `analyze` queue
- Worker config: 4 concurrent workers, 10/s rate limit, 1h soft timeout

## Authentication & Identity

**Auth Provider:**
- None implemented
  - No user authentication currently
  - CORS configured for frontend origin only
  - Security headers via middleware (`backend/app/middleware/security.py`)

**API Security:**
- CORS: Restricted to `FRONTEND_URL` origins
- No API keys or JWT tokens for client access
- Anthropic API key server-side only (never exposed to frontend)

## Monitoring & Observability

**Error Tracking:**
- None (no Sentry, Bugsnag, etc.)

**Logging:**
- Python `logging` module
- File handler in production: `logs/cira.log` (10MB rotation, 10 backups)
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Level: Configurable via `LOG_LEVEL` env var

**Health Checks:**
- Backend: `GET /api/v1/health` endpoint (`backend/app/api/routes/health.py`)
  - Checks: Database connectivity, Redis connectivity, Celery worker status
- Docker: Health checks configured in `docker-compose.yml` and `docker-compose.prod.yml`
- Celery: Worker health via `celery inspect ping`

## CI/CD & Deployment

**Hosting:**
- Docker containers (self-hosted or any Docker-compatible platform)
- No specific cloud provider integration
- Docker Compose for orchestration

**CI Pipeline:**
- GitHub Actions (inferred from `.github/` directory)
- No CI configuration files examined

**Deployment Files:**
- `docker-compose.yml` - Development environment
- `docker-compose.prod.yml` - Production environment
- `docker/Dockerfile.backend` - Backend dev image
- `docker/Dockerfile.backend.prod` - Backend production image (multi-stage)
- `docker/Dockerfile.frontend` - Frontend dev image
- `docker/Dockerfile.frontend.prod` - Frontend production image with Nginx
- `docker/nginx.conf`, `docker/nginx.default.conf` - Production web server config

## Environment Configuration

**Required env vars (production):**
```
SECRET_KEY=<flask-secret>
ANTHROPIC_API_KEY=<claude-api-key>
```

**Optional env vars:**
```
DATABASE_URL=sqlite:///cira.db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
FRONTEND_URL=http://localhost:5173
FLASK_ENV=development
LOG_LEVEL=INFO
```

**Secrets location:**
- Environment variables (no vault integration)
- `.env` file (gitignored)
- `.env.example` and `docker/env.example` for templates

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None

## Frontend-Backend Communication

**API Client:**
- Axios instance configured in `frontend/src/api/client.ts`
- Base URL: `VITE_API_URL` env var (default: `http://localhost:5000/api/v1`)
- Timeout: 30 seconds
- Error handling: Interceptors for logging and status code handling
- No authentication headers (prepared but not implemented)

**API Endpoints:**
- `GET /api/v1/health` - Health check
- `POST /api/v1/companies` - Create company analysis job
- `GET /api/v1/companies/{id}` - Get company details
- `GET /api/v1/companies/{id}/progress` - Poll job progress
- `POST /api/v1/companies/{id}/control` - Pause/resume/cancel jobs
- `GET /api/v1/companies/{id}/export` - Download reports
- `POST /api/v1/batch` - Create batch job
- `GET /api/v1/batch/{id}` - Get batch status
- Additional routes: entities, tokens, config, versions

---

*Integration audit: 2026-01-19*
