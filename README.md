# CIRA - Company Intelligence Research Assistant

A web-based application for automated company research and analysis. CIRA crawls company websites, extracts structured data using NLP, and generates comprehensive intelligence briefs using AI.

## Features

- **Intelligent Web Crawling**: Automatically discovers and crawls company websites with JavaScript rendering support
- **Entity Extraction**: Extracts people, products, locations, and structured data using spaCy NLP
- **AI-Powered Analysis**: Generates executive summaries and insights using Claude API
- **Multiple Export Formats**: Export reports in Markdown, Word, PDF, or JSON
- **Pause/Resume**: Long-running analyses can be paused and resumed
- **Batch Processing**: Upload CSV files to analyze multiple companies

## Tech Stack

### Frontend
- React 18+ with TypeScript
- Vite for build tooling
- TanStack Query for data fetching
- React Router for navigation
- Tailwind CSS for styling

### Backend
- Python 3.11+ with Flask
- SQLAlchemy 2.0+ for database ORM
- Celery for background job processing
- Redis for caching and job queue

### AI/ML
- spaCy 3.7+ for NER
- Anthropic Claude API for analysis

### Infrastructure
- Docker & Docker Compose
- SQLite database
- Redis for caching

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 18+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Using Docker (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd cira

# Copy environment variables
cp .env.example .env

# Edit .env and add your ANTHROPIC_API_KEY

# Start all services
docker-compose up -d

# Frontend: http://localhost:5173
# Backend API: http://localhost:5000
```

### Local Development

#### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
flask db upgrade

# Start the development server
flask run
```

#### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

## Project Structure

```
cira/
├── frontend/           # React frontend application
│   ├── src/
│   │   ├── components/ # UI components
│   │   ├── pages/      # Page components
│   │   ├── hooks/      # Custom React hooks
│   │   ├── api/        # API client
│   │   └── types/      # TypeScript types
│   └── ...
├── backend/            # Flask backend application
│   ├── app/
│   │   ├── api/        # API endpoints
│   │   ├── models/     # SQLAlchemy models
│   │   ├── services/   # Business logic
│   │   ├── workers/    # Celery workers
│   │   └── schemas/    # Pydantic schemas
│   └── ...
├── docker/             # Docker configuration
├── docs/               # Documentation
└── specs/              # Feature specifications
```

## API Documentation

See [API Endpoints](./specs/05-api-endpoints.md) for detailed API documentation.

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `development` |
| `DATABASE_URL` | Database connection string | `sqlite:///cira.db` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `ANTHROPIC_API_KEY` | Claude API key | (required) |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/1` |

## License

MIT License
