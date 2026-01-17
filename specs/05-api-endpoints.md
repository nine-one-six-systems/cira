# API Endpoints Specification

## Overview

RESTful API with consistent resource naming, JSON request/response bodies, and versioned endpoints at `/api/v1/`.

## Base URL

```
http://localhost:5000/api/v1
```

## Response Format

### Success Response

```typescript
interface ApiResponse<T> {
  success: true;
  data: T;
}
```

### Error Response

```typescript
interface ApiErrorResponse {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, any>;
  };
}
```

### Paginated Response

```typescript
interface PaginatedResponse<T> {
  success: true;
  data: T[];
  meta: {
    total: number;
    page: number;
    pageSize: number;
    totalPages: number;
  };
}
```

## Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| VALIDATION_ERROR | 400 | Request validation failed |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource conflict |
| INVALID_STATE | 422 | Operation invalid for current state |
| RATE_LIMITED | 429 | Too many requests |
| EXTERNAL_API_ERROR | 502 | External service error |
| INTERNAL_ERROR | 500 | Server error |

## Endpoints

### Health Check

#### GET /api/v1/health

Check service health.

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "database": "connected",
    "redis": "connected"
  }
}
```

---

### Companies

#### POST /api/v1/companies

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

**Validation:**
- companyName: required, 1-200 characters
- websiteUrl: required, valid URL format
- industry: optional, 1-100 characters
- config: optional, defaults applied if missing

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

**Errors:**
- 400 VALIDATION_ERROR: Invalid URL format, missing required fields
- 409 CONFLICT: Company with same URL already exists

---

#### POST /api/v1/companies/batch

Upload CSV for batch processing.

**Request:** `multipart/form-data` with CSV file

**CSV Format:**
```csv
company_name,website_url,industry
Acme Corp,https://acme.com,Technology
Beta Inc,https://beta.io,Healthcare
```

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

---

#### GET /api/v1/companies/template

Download CSV template.

**Response:** CSV file download

---

#### GET /api/v1/companies

List companies with filtering and pagination.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| status | string | - | Filter by status |
| sort | string | created_at | Sort field |
| order | string | desc | Sort order (asc/desc) |
| page | number | 1 | Page number |
| pageSize | number | 20 | Items per page (max 100) |
| search | string | - | Search company name |

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

---

#### GET /api/v1/companies/:id

Get company details with latest analysis.

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
      "estimatedCost": 0.82,
      "createdAt": "2026-01-15T10:30:00Z",
      "completedAt": "2026-01-15T10:52:00Z"
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

---

#### GET /api/v1/companies/:id/progress

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

---

#### POST /api/v1/companies/:id/pause

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

**Errors:**
- 404 NOT_FOUND: Company not found
- 422 INVALID_STATE: Company not in_progress

---

#### POST /api/v1/companies/:id/resume

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

**Errors:**
- 404 NOT_FOUND: Company not found
- 422 INVALID_STATE: Company not paused

---

#### POST /api/v1/companies/:id/rescan

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

**Errors:**
- 404 NOT_FOUND: Company not found
- 422 INVALID_STATE: Company not completed

---

#### GET /api/v1/companies/:id/export

Export analysis in specified format.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| format | string | markdown | Export format (markdown, word, pdf, json) |
| includeRawData | boolean | false | Include all extracted data |

**Response:** File download with appropriate Content-Type

---

#### DELETE /api/v1/companies/:id

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

---

### Entities

#### GET /api/v1/companies/:id/entities

Get extracted entities for a company.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| type | string | - | Filter by entity type |
| minConfidence | number | 0 | Minimum confidence (0-1) |
| page | number | 1 | Page number |
| pageSize | number | 50 | Items per page |

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

---

### Pages

#### GET /api/v1/companies/:id/pages

Get crawled pages for a company.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| pageType | string | - | Filter by page type |
| page | number | 1 | Page number |
| pageSize | number | 50 | Items per page |

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
  ],
  "meta": { ... }
}
```

---

### Token Usage

#### GET /api/v1/companies/:id/tokens

Get token usage breakdown.

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

---

### Versions

#### GET /api/v1/companies/:id/versions

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
      "tokensUsed": 82100
    }
  ]
}
```

---

#### GET /api/v1/companies/:id/compare

Compare two analysis versions.

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| version1 | number | Yes | First version number |
| version2 | number | Yes | Second version number |

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

---

### Configuration

#### GET /api/v1/config

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

---

#### PUT /api/v1/config

Update configuration.

**Request:**
```json
{
  "defaults": {
    "timeLimitMinutes": 45
  }
}
```

**Response (200 OK):** Updated configuration

---

## Performance Requirements

- API response time < 200ms for non-blocking operations
- Progress endpoint polled every 2 seconds
- Pagination limits enforced (max 100 items)
