# Technology Stack

**Analysis Date:** 2026-01-19

## Languages

**Primary:**
- Python 3.11+ - Backend API, crawling, NLP, AI integration (`/backend/`)
- TypeScript 5.9+ - Frontend application (`/frontend/`)

**Secondary:**
- SQL - Database queries via SQLAlchemy ORM
- HTML/CSS - Frontend templates with Tailwind CSS

## Runtime

**Backend Environment:**
- Python 3.11+
- Flask development server (dev)
- Gunicorn WSGI server (prod) - 4 workers, 2 threads

**Frontend Environment:**
- Node.js (ES2022 target)
- Vite 7.2+ dev server
- Nginx (prod)

**Package Managers:**
- pip with `requirements.txt` for Python
- npm with `package.json` for Node.js
- Lockfile: `package-lock.json` present (npm)

## Frameworks

**Backend Core:**
- Flask 3.0+ - Web framework (`backend/app/__init__.py`)
- Flask-SQLAlchemy 3.1+ - ORM integration
- Flask-Migrate 4.0+ - Database migrations (`backend/migrations/`)
- Flask-CORS 4.0+ - Cross-origin support
- Pydantic 2.5+ - Request/response validation (`backend/app/schemas/`)

**Frontend Core:**
- React 19.2+ - UI framework
- React Router DOM 7.12+ - Client-side routing (`frontend/src/router.tsx`)
- TanStack React Query 5.90+ - Server state management
- Tailwind CSS 4.1+ - Utility-first styling (`frontend/tailwind.config.js`)

**Task Queue:**
- Celery 5.3+ - Distributed task queue (`backend/app/workers/celery_app.py`)
- Kombu - Message transport for Celery
- Redis 5.0+ - Message broker and result backend

**Testing:**
- pytest 7.4+ - Backend testing (`backend/tests/`)
- pytest-cov - Coverage reporting
- pytest-asyncio - Async test support
- Vitest 4.0+ - Frontend unit testing
- Testing Library React 16.3+ - React component testing
- Playwright 1.40+ - E2E testing (`frontend/e2e/`, `frontend/playwright.config.ts`)

**Build/Dev:**
- Vite 7.2+ - Frontend build tool (`frontend/vite.config.ts`)
- ESLint 9.39+ - JavaScript/TypeScript linting (`frontend/eslint.config.js`)
- typescript-eslint 8.46+ - TypeScript ESLint rules
- ruff 0.1+ - Python linting
- black 23.12+ - Python formatting
- mypy 1.7+ - Python type checking

## Key Dependencies

**AI/ML Critical:**
- anthropic 0.18+ - Claude API client (`backend/app/services/anthropic_service.py`)
- spacy 3.7+ - NLP/NER processing (`backend/app/extractors/nlp_pipeline.py`)
- en_core_web_lg - spaCy large English model (installed via `python -m spacy download`)

**Web Crawling:**
- playwright 1.40+ - JavaScript rendering (`backend/app/crawlers/browser_manager.py`)
- beautifulsoup4 4.12+ - HTML parsing
- lxml 4.9+ - XML/HTML parser
- requests 2.31+ - HTTP client

**Data Storage:**
- SQLAlchemy 2.0+ - ORM (`backend/app/models/`)
- redis 5.0+ - Caching and job state (`backend/app/services/redis_service.py`)

**Export Generation:**
- python-docx 1.1+ - Word document generation (`backend/app/services/export_service.py`)
- reportlab 4.0+ - PDF generation
- PyPDF2 3.0+ - PDF text extraction

**Frontend HTTP:**
- axios 1.13+ - HTTP client (`frontend/src/api/client.ts`)

## Configuration

**Environment Variables (Required):**
- `ANTHROPIC_API_KEY` - Claude API access (required in production)
- `SECRET_KEY` - Flask session secret (required in production)
- `DATABASE_URL` - Database connection string (default: `sqlite:///cira.db`)
- `REDIS_URL` - Redis connection (default: `redis://localhost:6379/0`)
- `CELERY_BROKER_URL` - Celery broker (default: `redis://localhost:6379/1`)

**Environment Variables (Optional):**
- `FLASK_ENV` - Environment mode (development/testing/production)
- `FRONTEND_URL` - CORS allowed origin (default: `http://localhost:5173`)
- `LOG_LEVEL` - Logging level (default: `INFO`)
- `CRAWL_DEFAULT_MAX_PAGES` - Max pages per crawl (default: 100)
- `CRAWL_DEFAULT_MAX_DEPTH` - Max crawl depth (default: 3)
- `ANALYSIS_DEFAULT_MODE` - Analysis mode (default: thorough)
- `CLAUDE_INPUT_TOKEN_PRICE` - Input token cost per 1M (default: 3.00)
- `CLAUDE_OUTPUT_TOKEN_PRICE` - Output token cost per 1M (default: 15.00)

**Configuration Files:**
- `backend/app/config.py` - Flask configuration classes
- `frontend/vite.config.ts` - Vite build configuration
- `frontend/tsconfig.json` - TypeScript configuration
- `frontend/tailwind.config.js` - Tailwind CSS theme
- `.env.example` - Environment variable template

## Build Configuration

**Backend:**
- No build step required for development
- Production uses multi-stage Docker build (`docker/Dockerfile.backend.prod`)
- Gunicorn command: `gunicorn --bind 0.0.0.0:5000 --workers 4 --threads 2 --timeout 120 app:create_app('production')`

**Frontend:**
- Development: `npm run dev` (Vite dev server on port 5173)
- Production build: `npm run build` (outputs to `dist/`)
- TypeScript compilation: `tsc -b`
- Production served via Nginx (`docker/nginx.conf`)

## Platform Requirements

**Development:**
- Python 3.11+
- Node.js (ES2022 compatible)
- Redis server
- Chromium browser (for Playwright crawling)

**Production (Docker):**
- Docker 20.10+
- Docker Compose 3.8+
- 4GB+ RAM recommended (spaCy model + Celery workers)
- Ports: 80 (frontend), 5000 (backend), 6379 (Redis)

**Resource Limits (Production):**
- Backend: 2 CPU, 2GB RAM
- Frontend: 0.5 CPU, 256MB RAM
- Celery Worker: 2 CPU, 2GB RAM
- Redis: 0.5 CPU, 512MB RAM (256MB maxmemory)

---

*Stack analysis: 2026-01-19*
