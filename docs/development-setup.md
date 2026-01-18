# Development Setup Guide

This guide covers setting up a local development environment for CIRA.

## Prerequisites

- Python 3.11+
- Node.js 20+
- Redis 7+
- Docker & Docker Compose (optional, recommended)

## Option 1: Docker Development (Recommended)

The easiest way to get started is with Docker Compose:

```bash
# Clone repository
git clone https://github.com/nine-one-six-systems/cira.git
cd cira

# Copy environment template
cp docker/env.example .env

# Edit .env and add your ANTHROPIC_API_KEY
nano .env

# Start all services
docker-compose up

# Access the application:
# Frontend: http://localhost:5173
# Backend API: http://localhost:5000/api/v1
# Redis: localhost:6379
```

### Useful Docker Commands

```bash
# Start in background
docker-compose up -d

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
docker-compose logs -f celery-worker

# Rebuild after changes to requirements/packages
docker-compose build

# Stop all services
docker-compose down

# Reset everything (including volumes)
docker-compose down -v
```

## Option 2: Manual Setup

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install spaCy language model
python -m spacy download en_core_web_lg

# Install Playwright browsers (for JS-rendered pages)
playwright install chromium
playwright install-deps chromium

# Set environment variables
export FLASK_ENV=development
export FLASK_DEBUG=1
export REDIS_URL=redis://localhost:6379/0
export CELERY_BROKER_URL=redis://localhost:6379/1
export CELERY_RESULT_BACKEND=redis://localhost:6379/1
export ANTHROPIC_API_KEY=your-api-key

# Initialize database
flask db upgrade

# Start Flask development server
flask run
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Redis Setup

```bash
# macOS with Homebrew
brew install redis
brew services start redis

# Ubuntu/Debian
sudo apt-get install redis-server
sudo systemctl start redis

# Windows
# Download from https://github.com/microsoftarchive/redis/releases
```

### Celery Worker

```bash
cd backend
source venv/bin/activate

# Start Celery worker
celery -A app.workers worker --loglevel=info
```

## Environment Variables

Key environment variables (see `docker/env.example` for full list):

| Variable | Required | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | Yes | Claude API key |
| `SECRET_KEY` | Production | Flask secret key |
| `DATABASE_URL` | No | Database URL (default: SQLite) |
| `REDIS_URL` | No | Redis URL (default: localhost:6379) |
| `FRONTEND_URL` | No | Frontend URL for CORS |

## Running Tests

### Backend Tests

```bash
cd backend
source venv/bin/activate

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Run specific test file
pytest tests/test_companies_api.py -v

# Run tests matching pattern
pytest tests/ -k "test_create"
```

### Frontend Tests

```bash
cd frontend

# Run all tests
npm test

# Run in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage
```

## Code Quality

### Backend

```bash
cd backend

# Format code
black app/

# Lint
ruff check app/

# Type check
mypy app/ --ignore-missing-imports
```

### Frontend

```bash
cd frontend

# Lint
npm run lint

# Type check
npx tsc --noEmit
```

## Database Migrations

```bash
cd backend
source venv/bin/activate

# Create a new migration
flask db migrate -m "Description of changes"

# Apply migrations
flask db upgrade

# Rollback
flask db downgrade
```

## Troubleshooting

### Redis Connection Error

```
Error: Cannot connect to Redis
```

Ensure Redis is running:
```bash
redis-cli ping  # Should return PONG
```

### Celery Worker Not Processing

1. Check Redis is running
2. Check CELERY_BROKER_URL is correct
3. Restart worker with debug logging:
   ```bash
   celery -A app.workers worker --loglevel=debug
   ```

### spaCy Model Not Found

```bash
python -m spacy download en_core_web_lg
```

### Playwright Browsers Missing

```bash
playwright install chromium
playwright install-deps chromium
```

## IDE Setup

### VS Code Extensions
- Python (ms-python.python)
- Pylance (ms-python.vscode-pylance)
- ESLint (dbaeumer.vscode-eslint)
- Prettier (esbenp.prettier-vscode)
- Tailwind CSS IntelliSense (bradlc.vscode-tailwindcss)

### Recommended settings.json

```json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  }
}
```
