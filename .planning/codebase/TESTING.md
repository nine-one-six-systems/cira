# Testing Patterns

**Analysis Date:** 2026-01-19

## Test Frameworks

### Frontend

**Unit Test Runner:**
- Vitest 4.0.17
- Config: `frontend/vite.config.ts`

**Assertion Library:**
- Vitest built-in (`expect`)
- `@testing-library/jest-dom` matchers (`toBeInTheDocument`, `toBeDisabled`, etc.)

**E2E Runner:**
- Playwright 1.40.0
- Config: `frontend/playwright.config.ts`

**Run Commands:**
```bash
npm run test              # Run all unit tests once
npm run test:watch        # Watch mode
npm run test:coverage     # Coverage report
npm run test:e2e          # Playwright E2E tests
npm run test:e2e:ui       # Playwright with UI
npm run test:e2e:report   # View Playwright report
```

### Backend

**Test Runner:**
- pytest
- Config: `backend/pyproject.toml`

**Run Commands:**
```bash
cd backend && pytest                     # Run all tests
cd backend && pytest -v                  # Verbose output
cd backend && pytest --tb=short          # Short tracebacks
cd backend && pytest tests/test_health.py  # Single file
```

## Test File Organization

### Frontend

**Location:**
- Unit tests: Co-located with source (`src/components/ui/Button.test.tsx`)
- E2E tests: Dedicated directory (`frontend/e2e/`)

**Naming:**
- Unit tests: `{Component}.test.tsx` or `{module}.test.ts`
- E2E tests: `{feature}.spec.ts`

**Structure:**
```
frontend/
├── src/
│   ├── components/
│   │   └── ui/
│   │       ├── Button.tsx
│   │       ├── Button.test.tsx
│   │       ├── Modal.tsx
│   │       └── Modal.test.tsx
│   └── test/
│       └── setup.ts
└── e2e/
    ├── add-company.spec.ts
    ├── dashboard.spec.ts
    └── progress.spec.ts
```

### Backend

**Location:**
- Separate `tests/` directory at package root

**Naming:**
- `test_{module}.py` (e.g., `test_health.py`, `test_companies_api.py`)

**Structure:**
```
backend/
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_app.py
    ├── test_health.py
    ├── test_companies_api.py
    ├── test_models.py
    ├── test_schemas.py
    └── test_{service}.py
```

## Test Structure

### Frontend Unit Tests (Vitest)

**Suite Organization:**
```typescript
// frontend/src/components/ui/Button.test.tsx
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button } from './Button';

describe('Button', () => {
  it('renders children correctly', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<Button onClick={handleClick}>Click me</Button>);
    await user.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

**Patterns:**
- `describe` blocks for component/feature grouping
- `it` with descriptive action-result names
- Arrange-Act-Assert structure
- `userEvent.setup()` before interactions
- Query by accessible role first (`getByRole`, `getByLabelText`)

### Frontend E2E Tests (Playwright)

**Suite Organization:**
```typescript
// frontend/e2e/add-company.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Add Company Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/add');
  });

  test('should display add company form', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /add company/i })).toBeVisible();
    await expect(page.getByLabel(/company name/i)).toBeVisible();
  });

  test('should validate required fields', async ({ page }) => {
    await page.getByRole('button', { name: /start analysis/i }).click();
    await expect(page.getByText(/company name is required/i)).toBeVisible();
  });
});
```

**Patterns:**
- `test.describe` for feature grouping
- `test.beforeEach` for navigation setup
- Locators: `getByRole`, `getByLabel`, `getByText`
- `.or()` for flexible locators
- `toBeVisible()` for visibility assertions

### Backend Tests (pytest)

**Suite Organization:**
```python
# backend/tests/test_companies_api.py
import pytest
from app import db
from app.models.company import Company

class TestCreateCompany:
    """Tests for POST /api/v1/companies."""

    def test_create_company_with_valid_data(self, client):
        """Test creating a company with valid data returns 201."""
        response = client.post('/api/v1/companies', json={
            'companyName': 'Acme Corp',
            'websiteUrl': 'https://acme.com'
        })

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert 'companyId' in data['data']

    def test_create_company_invalid_url(self, client):
        """Test creating a company with invalid URL returns 400."""
        response = client.post('/api/v1/companies', json={
            'companyName': 'Bad URL Corp',
            'websiteUrl': 'not-a-url'
        })

        assert response.status_code == 400
        assert data['error']['code'] == 'VALIDATION_ERROR'
```

**Patterns:**
- Classes group related tests (`TestCreateCompany`, `TestListCompanies`)
- Docstrings describe test purpose
- Fixtures via pytest (`client`, `app`)
- Direct assertions with `assert`
- JSON response via `response.get_json()`

## Mocking

### Frontend (Vitest)

**Framework:** `vi` from Vitest

**Patterns:**
```typescript
// Function mock
const handleClick = vi.fn();

// Verify calls
expect(handleClick).toHaveBeenCalledTimes(1);
expect(handleClick).not.toHaveBeenCalled();

// Module mock (if needed)
vi.mock('../api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));
```

**What to Mock:**
- Event handlers (`onClick`, `onChange`)
- API calls (when testing component logic)
- Timer functions

**What NOT to Mock:**
- DOM rendering (use Testing Library)
- User interactions (use userEvent)
- Component children (render real components)

### Backend (pytest + unittest.mock)

**Framework:** `unittest.mock.Mock`, `MagicMock`, `patch`

**Patterns:**
```python
# backend/tests/test_redis_service.py
from unittest.mock import Mock, patch, MagicMock

class TestRedisServiceHealthCheck:
    def test_health_check_with_connection(self):
        """Test health check with mocked connection."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        service._client = mock_client

        result = service.health_check()
        assert result['status'] == 'healthy'

    def test_health_check_connection_error(self):
        """Test health check when connection fails."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")
        service._client = mock_client

        result = service.health_check()
        assert result['status'] == 'unhealthy'
```

**What to Mock:**
- External services (Redis, Celery)
- Network calls
- Database for unit tests (but integration tests use real DB)

**What NOT to Mock:**
- Flask test client (use real)
- Database in API tests (use test fixture)
- Pydantic validation

## Fixtures and Factories

### Frontend

**Test Setup:**
```typescript
// frontend/src/test/setup.ts
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    // ...
  }),
});

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}
```

**Location:**
- Global setup: `frontend/src/test/setup.ts`
- Referenced in: `frontend/vite.config.ts` (`setupFiles`)

### Backend

**Fixtures:**
```python
# backend/tests/conftest.py
import pytest
from app import create_app, db

@pytest.fixture
def app():
    """Create application for testing."""
    app = create_app('testing')
    app.config['TESTING'] = True

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create test CLI runner."""
    return app.test_cli_runner()
```

**Test Data Patterns:**
```python
# Create test entities inline
def test_list_companies_with_data(self, client, app):
    with app.app_context():
        for i in range(3):
            company = Company(
                company_name=f'Company {i}',
                website_url=f'https://company{i}.com'
            )
            db.session.add(company)
        db.session.commit()

    response = client.get('/api/v1/companies')
    # ...
```

## Coverage

**Frontend:**
- Tool: Vitest built-in coverage (v8)
- Requirements: Not enforced
- Config in `frontend/vite.config.ts`:
```typescript
coverage: {
  reporter: ['text', 'json', 'html'],
  include: ['src/**/*.{ts,tsx}'],
  exclude: ['src/**/*.test.{ts,tsx}', 'src/test/**/*'],
}
```

**View Coverage:**
```bash
cd frontend && npm run test:coverage
# Opens: frontend/coverage/index.html
```

**Backend:**
- Tool: pytest-cov (implied by `.coverage` file)
- Requirements: Not explicitly enforced

## Test Types

### Unit Tests

**Frontend:**
- Component rendering
- User interactions
- Props/state behavior
- Hook logic

**Backend:**
- Service class methods
- Schema validation
- Utility functions
- Model relationships

### Integration Tests

**Frontend:**
- Not explicitly separated (component tests often test integration)

**Backend:**
- API endpoint tests (use real Flask client + test DB)
- Full request/response cycle
- Database operations

### E2E Tests (Frontend only)

**Playwright Config:**
```typescript
// frontend/playwright.config.ts
{
  testDir: './e2e',
  fullyParallel: true,
  retries: process.env.CI ? 2 : 0,
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
  },
}
```

**E2E Test Areas:**
- `e2e/add-company.spec.ts` - Single company creation flow
- `e2e/batch-upload.spec.ts` - CSV upload flow
- `e2e/dashboard.spec.ts` - Company list and navigation
- `e2e/progress.spec.ts` - Progress monitoring
- `e2e/results.spec.ts` - Results viewing
- `e2e/export.spec.ts` - Export functionality
- `e2e/settings.spec.ts` - Settings page

## Common Patterns

### Async Testing (Frontend)

```typescript
// Using userEvent
it('calls onClick when clicked', async () => {
  const handleClick = vi.fn();
  const user = userEvent.setup();

  render(<Button onClick={handleClick}>Click me</Button>);
  await user.click(screen.getByRole('button'));

  expect(handleClick).toHaveBeenCalledTimes(1);
});

// Using Playwright
test('should fill form and submit', async ({ page }) => {
  await page.getByLabel(/company name/i).fill('Anthropic');
  await page.getByRole('button', { name: /start/i }).click();
  await expect(page).toHaveURL(/\/progress/);
});
```

### Async Testing (Backend)

```python
# pytest with asyncio_mode = "auto" in pyproject.toml
# Async fixtures/tests automatically handled

class TestAsyncService:
    async def test_async_operation(self, app):
        async with app.app_context():
            result = await some_async_function()
            assert result is not None
```

### Error Testing

**Frontend:**
```typescript
it('is disabled when disabled prop is true', () => {
  render(<Button disabled>Click me</Button>);
  expect(screen.getByRole('button')).toBeDisabled();
});

it('does not call onClick when disabled', async () => {
  const handleClick = vi.fn();
  const user = userEvent.setup();

  render(<Button disabled onClick={handleClick}>Click me</Button>);
  await user.click(screen.getByRole('button'));

  expect(handleClick).not.toHaveBeenCalled();
});
```

**Backend:**
```python
def test_create_company_invalid_url(self, client):
    """Test creating a company with invalid URL returns 400."""
    response = client.post('/api/v1/companies', json={
        'companyName': 'Bad URL Corp',
        'websiteUrl': 'not-a-url'
    })

    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert data['error']['code'] == 'VALIDATION_ERROR'

def test_get_company_not_found(self, client):
    """Test getting a non-existent company returns 404."""
    response = client.get('/api/v1/companies/nonexistent-id')

    assert response.status_code == 404
    data = response.get_json()
    assert data['error']['code'] == 'NOT_FOUND'
```

### Testing with Database State

```python
def test_delete_company_cascades_related_records(self, client, app):
    """Test deleting company removes all related records."""
    with app.app_context():
        company = Company(company_name='Test', website_url='https://test.com')
        db.session.add(company)
        db.session.flush()

        page = Page(company_id=company.id, url='https://test.com/about')
        entity = Entity(company_id=company.id, entity_type=EntityType.PERSON, entity_value='John')
        db.session.add_all([page, entity])
        db.session.commit()
        company_id = company.id

    response = client.delete(f'/api/v1/companies/{company_id}')

    assert response.status_code == 200
    with app.app_context():
        assert Page.query.filter_by(company_id=company_id).count() == 0
```

---

*Testing analysis: 2026-01-19*
