# Deployment Guide

This guide covers deploying CIRA to production environments.

## Quick Start (Docker)

```bash
# Clone repository
git clone https://github.com/nine-one-six-systems/cira.git
cd cira

# Copy and configure environment
cp docker/env.example .env
nano .env  # Set SECRET_KEY and ANTHROPIC_API_KEY

# Start production services
docker-compose -f docker-compose.prod.yml up -d
```

## Prerequisites

- Docker 20+ and Docker Compose
- At least 4GB RAM
- 10GB disk space
- Valid Anthropic API key

## Environment Configuration

### Required Variables

```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_hex(32))"

# Required in .env
SECRET_KEY=your-generated-secret-key
ANTHROPIC_API_KEY=sk-ant-api-key-from-anthropic
```

### Optional Variables

```bash
# Database (default: SQLite)
DATABASE_URL=postgresql://user:pass@host:5432/cira

# Frontend URL (for CORS)
FRONTEND_URL=https://cira.example.com

# Logging
LOG_LEVEL=INFO

# Crawl configuration
CRAWL_DEFAULT_MAX_PAGES=100
CRAWL_DEFAULT_MAX_DEPTH=3
CRAWL_DEFAULT_TIME_LIMIT_MINUTES=30
```

See `docker/env.example` for full configuration options.

## Production Deployment Steps

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin
```

### 2. Clone and Configure

```bash
# Clone repository
git clone https://github.com/nine-one-six-systems/cira.git
cd cira

# Create environment file
cp docker/env.example .env

# Edit with production values
nano .env
```

### 3. Start Services

```bash
# Build and start
docker-compose -f docker-compose.prod.yml up -d --build

# Verify services are running
docker-compose -f docker-compose.prod.yml ps

# Check logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 4. Verify Deployment

```bash
# Health check
curl http://localhost:5000/api/v1/health

# Frontend
curl http://localhost:80/
```

## Service Architecture

```
                    ┌─────────────┐
                    │   nginx     │
                    │ (Frontend)  │
                    │   :80       │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Backend   │
                    │   (Flask)   │
                    │   :5000     │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──────┐ ┌───▼───┐ ┌──────▼──────┐
       │   Celery    │ │ Redis │ │  Database   │
       │   Worker    │ │ :6379 │ │  (SQLite)   │
       └─────────────┘ └───────┘ └─────────────┘
```

## Scaling

### Horizontal Scaling (Multiple Workers)

```bash
# Scale Celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=4
```

### Resource Allocation

Edit `docker-compose.prod.yml` to adjust resource limits:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 4G
```

## Reverse Proxy (nginx)

For SSL termination, add a reverse proxy in front:

```nginx
server {
    listen 443 ssl http2;
    server_name cira.example.com;

    ssl_certificate /etc/ssl/certs/cira.crt;
    ssl_certificate_key /etc/ssl/private/cira.key;

    # Frontend
    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # API
    location /api {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring

### Health Checks

```bash
# Backend health
curl http://localhost:5000/api/v1/health

# Redis
redis-cli ping

# Celery worker
celery -A app.workers inspect ping
```

### Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs

# Specific service
docker-compose -f docker-compose.prod.yml logs backend
docker-compose -f docker-compose.prod.yml logs celery-worker

# Follow logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

### Metrics

Backend logs include timing information. For advanced monitoring, integrate with:
- Prometheus (metrics export)
- Grafana (visualization)
- ELK Stack (log aggregation)

## Backup & Restore

### Database Backup (SQLite)

```bash
# Backup
docker-compose -f docker-compose.prod.yml exec backend \
    cp /app/cira.db /app/backup/cira-$(date +%Y%m%d).db

# Restore
docker-compose -f docker-compose.prod.yml exec backend \
    cp /app/backup/cira-20240118.db /app/cira.db
```

### Redis Backup

```bash
# Backup
docker-compose -f docker-compose.prod.yml exec redis redis-cli BGSAVE
docker cp cira-redis:/data/dump.rdb ./backup/

# Restore
docker cp ./backup/dump.rdb cira-redis:/data/
docker-compose -f docker-compose.prod.yml restart redis
```

## Updating

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.prod.yml up -d --build

# Or just specific service
docker-compose -f docker-compose.prod.yml up -d --build backend
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Common issues:
# - Missing environment variables
# - Port conflicts
# - Insufficient memory
```

### API Returns 500

```bash
# Check backend logs
docker-compose -f docker-compose.prod.yml logs --tail=100 backend

# Common issues:
# - Database connection
# - Redis connection
# - Invalid API key
```

### Celery Tasks Not Processing

```bash
# Check worker status
docker-compose -f docker-compose.prod.yml logs celery-worker

# Verify Redis connectivity
docker-compose -f docker-compose.prod.yml exec celery-worker \
    celery -A app.workers inspect ping
```

### High Memory Usage

```bash
# Check container stats
docker stats

# Limit memory in docker-compose.prod.yml
# Restart services
docker-compose -f docker-compose.prod.yml restart
```
