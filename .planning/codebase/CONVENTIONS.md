# Coding Conventions

**Analysis Date:** 2026-01-19

## Naming Patterns

**Files:**
- TypeScript/React components: PascalCase (`Button.tsx`, `Dashboard.tsx`)
- TypeScript utilities/hooks: camelCase (`useCompanies.ts`, `client.ts`)
- TypeScript test files: `{Component}.test.tsx` or `{module}.test.ts`
- Python modules: snake_case (`company.py`, `redis_service.py`)
- Python test files: `test_{module}.py`

**Functions:**
- TypeScript/JavaScript: camelCase (`formatDate`, `getErrorMessage`, `useCompanies`)
- React components: PascalCase (`Button`, `Dashboard`, `CompanyProgress`)
- Python: snake_case (`create_app`, `health_check`, `validate_url`)
- Custom hooks: prefixed with `use` (`useCompanies`, `useProgress`, `useToast`)

**Variables:**
- TypeScript: camelCase (`queryClient`, `statusFilter`, `companyToDelete`)
- Constants: SCREAMING_SNAKE_CASE (`BASE_URL`, `STATUS_OPTIONS`)
- Python: snake_case (`company_name`, `website_url`, `redis_service`)
- Python constants: SCREAMING_SNAKE_CASE in config (`CELERY_BROKER_URL`)

**Types:**
- TypeScript interfaces: PascalCase (`Company`, `ButtonProps`, `ApiResponse`)
- TypeScript type aliases: PascalCase (`CompanyStatus`, `ExportFormat`)
- Python Enums: PascalCase class, SCREAMING_SNAKE_CASE values (`CompanyStatus.PENDING`)
- Pydantic models: PascalCase (`CreateCompanyRequest`, `CamelCaseModel`)

## Code Style

**Formatting:**
- Frontend: Prettier
- Config: `frontend/.prettierrc`
  - Semi: true
  - Single quotes: true
  - Tab width: 2
  - Trailing comma: es5
  - Print width: 100

- Backend: Black + Ruff
- Config: `backend/pyproject.toml`
  - Line length: 100
  - Target: Python 3.11

**Linting:**
- Frontend: ESLint (flat config)
- Config: `frontend/eslint.config.js`
- Plugins: `react-hooks`, `react-refresh`, `typescript-eslint`
- Extends: `js.configs.recommended`, `tseslint.configs.recommended`

- Backend: Ruff + mypy
- Config: `backend/pyproject.toml`
- Ruff rules: E, F, W, I, N (errors, pyflakes, warnings, isort, naming)
- mypy: strict return typing, ignore missing imports

## Import Organization

**TypeScript Order:**
1. React imports (`import { useState } from 'react'`)
2. Third-party libraries (`import { useQuery } from '@tanstack/react-query'`)
3. Internal modules (`import { Button } from '../components/ui'`)
4. Types (often at end: `import type { Company } from '../types'`)
5. CSS imports (`import './index.css'`)

**Python Order:**
1. Standard library (`from datetime import datetime`)
2. Third-party (`from flask import Flask`, `from pydantic import BaseModel`)
3. Local application (`from app import db`, `from app.models.company import Company`)
4. Type checking imports wrapped in `if TYPE_CHECKING:`

**Path Aliases:**
- Frontend: None configured (uses relative imports)
- Backend: None (uses absolute imports from `app.*`)

## Error Handling

**Frontend Patterns:**
- API errors via Axios interceptor in `frontend/src/api/client.ts`
- Error messages extracted via `getErrorMessage(error)` helper
- Console logging for debug, user-facing via toast notifications
- Mutations handle errors in `onError` callbacks

```typescript
// frontend/src/api/client.ts - Error extraction pattern
export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const axiosError = error as AxiosError<ApiErrorResponse>;
    if (axiosError.response?.data?.error?.message) {
      return axiosError.response.data.error.message;
    }
  }
  return 'An unexpected error occurred';
}
```

**Backend Patterns:**
- Standard API error response via `make_error_response()` helper
- Pydantic validation errors caught and transformed to API format
- Error codes: `VALIDATION_ERROR`, `NOT_FOUND`, `CONFLICT`, etc.
- HTTP status codes: 400 (validation), 404 (not found), 409 (conflict), 422 (invalid state)

```python
# backend/app/api/routes/companies.py - Error response pattern
def make_error_response(code: str, message: str, details: dict | None = None, status: int = 400):
    error = ApiError(code=code, message=message, details=details)
    response = ApiErrorResponse(error=error)
    return jsonify(response.model_dump(by_alias=True)), status
```

## Logging

**Frontend:**
- `console.error()` for API errors and network issues
- `console.warn()` for rate limiting
- No structured logging framework

**Backend:**
- Python `logging` module with RotatingFileHandler
- Format: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Log files: `backend/logs/cira.log` (10MB rotation, 10 backups)
- Log level configurable via `LOG_LEVEL` config

```python
# backend/app/__init__.py - Logging setup
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

## Comments

**When to Comment:**
- File/module headers with purpose description
- Complex business logic
- Non-obvious behavior
- API endpoint documentation

**TSDoc/JSDoc:**
- Component documentation with `@example` blocks
- Interface properties with `/** description */`
- Hook and function documentation

```typescript
// frontend/src/components/ui/Button.tsx - Example documentation
/**
 * Button component with support for multiple variants, sizes, and loading state.
 *
 * @example
 * ```tsx
 * <Button variant="primary" onClick={handleClick}>
 *   Click me
 * </Button>
 * ```
 */
```

**Python Docstrings:**
- Triple-quoted docstrings for functions/classes
- Args/Returns sections for complex functions

```python
# backend/app/__init__.py - Docstring example
def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory for creating Flask app instances.

    Args:
        config_name: Configuration environment name ('development', 'testing', 'production')

    Returns:
        Configured Flask application instance.
    """
```

## Function Design

**Size:** Functions are typically 10-50 lines, with longer ones for complex UI components

**Parameters:**
- TypeScript: Destructured props with defaults (`{ variant = 'primary', size = 'md' }`)
- Python: Type-hinted parameters with defaults (`config_name: str | None = None`)

**Return Values:**
- TypeScript: Explicit return types on hooks and utilities
- Python: Type hints for return values (`-> Flask`, `-> dict`, `-> None`)
- API responses wrapped in standard response schemas

## Module Design

**Exports:**
- TypeScript: Named exports preferred, default for page components
- Barrel files for component libraries (`frontend/src/components/ui/index.ts`)

```typescript
// frontend/src/components/ui/index.ts - Barrel pattern
export { Button } from './Button';
export type { ButtonProps } from './Button';
```

**Python:**
- `__init__.py` for package initialization
- Explicit `__all__` when needed
- Services as singletons (`redis_service = RedisService()`)

## API Conventions

**Request/Response:**
- Frontend uses camelCase for all fields
- Backend Pydantic models use `CamelCaseModel` base for automatic conversion
- Field aliases map snake_case to camelCase (`company_name` -> `companyName`)

```python
# backend/app/schemas/base.py - CamelCase conversion
class CamelCaseModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
```

**Response Wrapper:**
```typescript
// Success: { success: true, data: T }
// Error: { success: false, error: { code, message, details? } }
// Paginated: { success: true, data: T[], meta: { total, page, pageSize, totalPages } }
```

## Component Conventions

**React Components:**
- Functional components with hooks
- forwardRef for form elements
- Props interface exported separately
- Default props via destructuring defaults

```typescript
// frontend/src/components/ui/Button.tsx - Component pattern
export interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, 'children'> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  children: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', ...props }, ref) => {
    // ...
  }
);
Button.displayName = 'Button';
```

**Hooks:**
- Query keys as const arrays in objects
- Mutations invalidate related queries
- Enabled flag for conditional fetching

```typescript
// frontend/src/hooks/useCompanies.ts - Hook pattern
export const companyKeys = {
  all: ['companies'] as const,
  lists: () => [...companyKeys.all, 'list'] as const,
  detail: (id: string) => [...companyKeys.details(), id] as const,
};
```

---

*Convention analysis: 2026-01-19*
