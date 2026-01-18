# CIRA Documentation

Company Intelligence Research Assistant - Automated company research and analysis platform.

## Documentation Index

### Getting Started
- [Development Setup](development-setup.md) - Local development environment setup
- [Deployment Guide](deployment.md) - Production deployment instructions

### Architecture
- [Architecture Overview](architecture.md) - System design and components
- [API Reference](api-reference.md) - REST API endpoints documentation

### User Guide
- [User Guide](user-guide.md) - How to use CIRA

## Quick Start

```bash
# Clone repository
git clone https://github.com/nine-one-six-systems/cira.git
cd cira

# Development with Docker
cp docker/env.example .env
# Edit .env with your ANTHROPIC_API_KEY
docker-compose up

# Access
# Frontend: http://localhost:5173
# Backend API: http://localhost:5000/api/v1
```

## Project Structure

```
cira/
├── backend/              # Flask API server
│   ├── app/              # Application code
│   │   ├── api/          # REST API routes
│   │   ├── models/       # SQLAlchemy models
│   │   ├── services/     # Business logic
│   │   ├── crawlers/     # Web crawling engine
│   │   ├── extractors/   # Entity extraction
│   │   ├── analysis/     # AI analysis
│   │   └── workers/      # Celery tasks
│   └── tests/            # Backend tests
├── frontend/             # React frontend
│   └── src/
│       ├── pages/        # Page components
│       ├── components/   # Reusable components
│       ├── hooks/        # React Query hooks
│       └── api/          # API client
├── docker/               # Docker configuration
├── specs/                # Feature specifications
└── docs/                 # Documentation
```
