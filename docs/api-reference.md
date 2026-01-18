# CIRA API Reference

REST API documentation for CIRA backend.

Base URL: `/api/v1`

## Authentication

Currently no authentication required (single-user deployment).

## Response Format

All responses follow this format:

**Success:**
```json
{
  "success": true,
  "data": { ... }
}
```

**Error:**
```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable message",
    "details": { ... }
  }
}
```

**Paginated:**
```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "total": 100,
    "page": 1,
    "pageSize": 20,
    "totalPages": 5
  }
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `NOT_FOUND` | 404 | Resource not found |
| `CONFLICT` | 409 | State conflict |
| `INVALID_STATE` | 422 | Invalid state transition |
| `RATE_LIMITED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Server error |

---

## Health Check

### GET /health

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-18T12:00:00Z",
  "redis": "connected"
}
```

---

## Companies

### POST /companies

Create a new company for analysis.

**Request Body:**
```json
{
  "name": "Acme Corp",
  "website_url": "https://acme.com",
  "industry": "Technology",
  "config": {
    "analysis_mode": "thorough",
    "max_pages": 100,
    "max_depth": 3,
    "time_limit_minutes": 30,
    "follow_linkedin": true,
    "follow_twitter": false,
    "follow_facebook": false
  }
}
```

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Acme Corp",
    "website_url": "https://acme.com",
    "industry": "Technology",
    "status": "pending",
    "created_at": "2024-01-18T12:00:00Z"
  }
}
```

### GET /companies

List all companies with filtering and pagination.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number (default: 1) |
| `page_size` | int | Items per page (default: 20, max: 100) |
| `status` | string | Filter by status |
| `search` | string | Search by name |
| `sort` | string | Sort field (created_at, name, status) |
| `order` | string | Sort order (asc, desc) |

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "name": "Acme Corp",
      "website_url": "https://acme.com",
      "industry": "Technology",
      "status": "completed",
      "total_tokens_used": 12500,
      "created_at": "2024-01-18T12:00:00Z"
    }
  ],
  "pagination": {
    "total": 50,
    "page": 1,
    "pageSize": 20,
    "totalPages": 3
  }
}
```

### GET /companies/:id

Get company details with latest analysis.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "Acme Corp",
    "website_url": "https://acme.com",
    "industry": "Technology",
    "status": "completed",
    "analysis_mode": "thorough",
    "total_tokens_used": 12500,
    "estimated_cost": 0.05,
    "created_at": "2024-01-18T12:00:00Z",
    "started_at": "2024-01-18T12:00:05Z",
    "completed_at": "2024-01-18T12:05:00Z",
    "analysis": {
      "version_number": 1,
      "executive_summary": "Acme Corp is...",
      "sections": {
        "company_overview": { ... },
        "business_model": { ... },
        "team_leadership": { ... },
        "market_position": { ... },
        "technology": { ... },
        "key_insights": { ... },
        "red_flags": { ... }
      }
    }
  }
}
```

### DELETE /companies/:id

Delete a company and all related data.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "message": "Company deleted successfully"
  }
}
```

### POST /companies/batch

Upload CSV for batch company creation.

**Request:** `multipart/form-data`
- `file`: CSV file with columns: `company_name`, `website_url`, `industry` (optional)

**Response:** `201 Created`
```json
{
  "success": true,
  "data": {
    "total_rows": 10,
    "successful": 8,
    "failed": 2,
    "companies": [
      { "name": "Acme Corp", "id": "uuid", "status": "created" },
      { "name": "Invalid Corp", "error": "Invalid URL format" }
    ]
  }
}
```

---

## Company Control

### POST /companies/:id/pause

Pause an in-progress analysis.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "paused",
    "checkpoint": {
      "pages_crawled": 45,
      "entities_extracted": 120
    }
  }
}
```

### POST /companies/:id/resume

Resume a paused analysis.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "in_progress"
  }
}
```

### POST /companies/:id/rescan

Start a new analysis version for a completed company.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "status": "in_progress",
    "version": 2
  }
}
```

---

## Progress

### GET /companies/:id/progress

Get real-time progress for an in-progress analysis.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "phase": "crawling",
    "pages_crawled": 45,
    "pages_queued": 30,
    "entities_extracted": 120,
    "tokens_used": 0,
    "time_elapsed_seconds": 120,
    "estimated_time_remaining_seconds": 180,
    "current_activity": "Crawling https://acme.com/about"
  }
}
```

---

## Entities

### GET /companies/:id/entities

List extracted entities for a company.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `page_size` | int | Items per page |
| `type` | string | Filter by entity type |
| `min_confidence` | float | Minimum confidence (0-1) |

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "entity_type": "PERSON",
      "entity_value": "John Smith",
      "context_snippet": "CEO John Smith leads...",
      "confidence_score": 0.95,
      "source_url": "https://acme.com/about"
    }
  ],
  "pagination": { ... }
}
```

---

## Pages

### GET /companies/:id/pages

List crawled pages for a company.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | int | Page number |
| `page_size` | int | Items per page |
| `page_type` | string | Filter by page type |

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": "uuid",
      "url": "https://acme.com/about",
      "page_type": "about",
      "is_external": false,
      "crawled_at": "2024-01-18T12:00:30Z"
    }
  ],
  "pagination": { ... }
}
```

---

## Token Usage

### GET /companies/:id/tokens

Get token usage breakdown for a company.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "total_tokens": 12500,
    "total_input_tokens": 10000,
    "total_output_tokens": 2500,
    "estimated_cost": 0.05,
    "by_api_call": [
      {
        "call_type": "company_overview",
        "input_tokens": 2000,
        "output_tokens": 500,
        "timestamp": "2024-01-18T12:03:00Z"
      }
    ]
  }
}
```

---

## Versions

### GET /companies/:id/versions

List analysis versions for a company.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "version_number": 2,
      "created_at": "2024-01-18T15:00:00Z",
      "is_current": true
    },
    {
      "version_number": 1,
      "created_at": "2024-01-18T12:00:00Z",
      "is_current": false
    }
  ]
}
```

### GET /companies/:id/compare

Compare two analysis versions.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `version1` | int | First version number |
| `version2` | int | Second version number |

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "significant_changes": true,
    "changes": {
      "team": [
        {
          "type": "added",
          "field": "ceo",
          "new_value": "Jane Doe"
        }
      ],
      "products": [
        {
          "type": "modified",
          "field": "main_product",
          "old_value": "Product A",
          "new_value": "Product A Pro"
        }
      ]
    }
  }
}
```

---

## Export

### GET /companies/:id/export

Export analysis in specified format.

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `format` | string | Required: markdown, word, pdf, json |
| `includeRawData` | bool | Include entities/pages (JSON only) |
| `version` | int | Specific version (default: latest) |

**Response:** File download with appropriate Content-Type

**Supported Formats:**
- `markdown` - UTF-8 text/markdown
- `word` - application/vnd.openxmlformats-officedocument.wordprocessingml.document
- `pdf` - application/pdf
- `json` - application/json

---

## Configuration

### GET /config

Get current configuration defaults.

**Response:** `200 OK`
```json
{
  "success": true,
  "data": {
    "defaults": {
      "analysis_mode": "thorough",
      "max_pages": 100,
      "max_depth": 3,
      "time_limit_minutes": 30
    },
    "modes": {
      "quick": {
        "max_pages": 20,
        "max_depth": 2
      },
      "thorough": {
        "max_pages": 100,
        "max_depth": 3
      }
    }
  }
}
```

### PUT /config

Update configuration defaults.

**Request Body:**
```json
{
  "defaults": {
    "analysis_mode": "quick",
    "max_pages": 50
  }
}
```

**Response:** `200 OK`

---

## Batch Operations

### POST /batches

Create a new batch operation.

**Request Body:**
```json
{
  "name": "Q1 Prospects",
  "company_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### GET /batches/:id

Get batch details and progress.

### POST /batches/:id/start

Start batch processing.

### POST /batches/:id/pause

Pause batch processing.

### POST /batches/:id/resume

Resume batch processing.

### POST /batches/:id/cancel

Cancel batch processing.
