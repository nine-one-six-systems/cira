# Phase 6: Batch Processing - Research

**Researched:** 2026-01-19
**Domain:** CSV Batch Upload, Queue Management, Multipart File Processing
**Confidence:** HIGH

## Summary

Phase 6: Batch Processing is **already fully implemented** in the CIRA codebase. The research focus shifts from "how to implement" to "what needs testing and verification." The implementation includes:

1. **Backend**: Complete CSV parsing, batch upload API, batch queue management service with fair scheduling
2. **Frontend**: Batch upload page with drag-and-drop, CSV preview, validation highlighting
3. **Tests**: Comprehensive test suites already exist (test_batch_api.py, test_batch_queue_api.py, test_batch_queue_service.py)

**Primary recommendation:** Create a testing phase plan that verifies the existing implementation against requirements BAT-01 through BAT-04, API-02, and UI-08 through UI-10, ensuring complete coverage of edge cases.

## Implementation Status Analysis

### Already Implemented (Verified in Codebase)

| Requirement | Status | Implementation Location |
|-------------|--------|------------------------|
| BAT-01: CSV file upload | COMPLETE | `backend/app/api/routes/batch.py` |
| BAT-02: Validate CSV, report errors per row | COMPLETE | `batch.py:process_csv_row()` |
| BAT-03: Download CSV template | COMPLETE | `batch.py:download_template()` |
| BAT-04: Queue batch companies | COMPLETE | `batch_queue_service.py` |
| API-02: POST /companies/batch | COMPLETE | `batch.py:batch_upload()` |
| UI-08: Configure analysis options | COMPLETE | `AddCompany.tsx`, Settings page |
| UI-09: Upload batch CSV, preview | COMPLETE | `BatchUpload.tsx` |
| UI-10: Delete company | COMPLETE | `companies.py:delete_company()` |

### Existing Test Coverage

| Test File | Tests | Coverage Area |
|-----------|-------|---------------|
| `test_batch_api.py` | 16 tests | CSV parsing, validation, template download |
| `test_batch_queue_api.py` | 23 tests | Batch CRUD, control operations |
| `test_batch_queue_service.py` | 35 tests | Fair scheduling, progress tracking |

## Standard Stack

The established libraries/tools for this domain:

### Core (Already in Use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python csv module | stdlib | CSV parsing | Built-in, well-tested, handles edge cases |
| Flask multipart/form-data | 3.0+ | File upload handling | Native Flask capability |
| io.StringIO | stdlib | In-memory CSV processing | Memory efficient |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pydantic | 2.5+ | Request/Response validation | All API schemas |
| React useState/useRef | 18+ | File handling state | Frontend upload UI |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Python csv | pandas | Overkill for simple CSV, adds dependency |
| Manual drag-drop | react-dropzone | Library adds features but native HTML5 sufficient |

## Architecture Patterns

### Current Project Structure (Verified)
```
backend/app/
├── api/routes/
│   ├── batch.py           # CSV upload endpoint
│   └── batch_queue.py     # Batch management endpoints
├── models/
│   └── batch.py           # BatchJob model
├── services/
│   └── batch_queue_service.py  # Fair scheduling service
└── schemas/
    └── __init__.py        # BatchUploadResponse, BatchCompanyResult

frontend/src/
├── pages/
│   └── BatchUpload.tsx    # Upload UI with preview
├── hooks/
│   └── useCompanies.ts    # useBatchUpload hook
└── api/
    └── companies.ts       # batchUpload(), downloadTemplate()
```

### Pattern 1: Per-Row Validation with Aggregate Response
**What:** Process each CSV row independently, collect all errors, return partial success
**When to use:** Batch operations where some items may fail
**Example:**
```python
# Source: backend/app/api/routes/batch.py
results = []
companies_to_add = []
urls_in_batch = set()

for row_index, row in enumerate(reader, start=1):
    company, error = process_csv_row(row, row_index)

    if error:
        results.append(BatchCompanyResult(
            companyName=company_name or f'Row {row_index}',
            error=error
        ))
    else:
        companies_to_add.append(company)
        results.append(BatchCompanyResult(
            companyName=company.company_name,
            companyId=None  # Set after commit
        ))

# Atomic transaction for valid companies
for company in companies_to_add:
    db.session.add(company)
db.session.commit()
```

### Pattern 2: Fair Round-Robin Scheduling
**What:** Schedule companies from multiple batches fairly based on priority
**When to use:** Multiple concurrent batches with concurrency limits
**Example:**
```python
# Source: backend/app/services/batch_queue_service.py
def schedule_next_from_all_batches(self) -> int:
    active_batches = BatchJob.query.filter_by(
        status=BatchStatus.PROCESSING
    ).order_by(BatchJob.priority.asc(), BatchJob.created_at.asc()).all()

    # Round-robin across batches
    for batch in batches_with_pending:
        if global_available <= 0:
            break
        # Get next pending company from this batch
        next_company = Company.query.filter_by(
            batch_id=batch.id,
            status=CompanyStatus.PENDING
        ).order_by(Company.created_at.asc()).first()

        if next_company:
            job_service.start_job(next_company.id, batch.config)
```

### Anti-Patterns to Avoid
- **Loading entire CSV into memory:** The current implementation streams with csv.DictReader
- **Validating after commit:** All validation happens before database transaction
- **Blocking on large uploads:** Batch processing uses async Celery tasks

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CSV parsing | Custom parser | Python csv module | Handles quoting, escaping, edge cases |
| File upload | Custom multipart parser | Flask request.files | Battle-tested, secure |
| Progress tracking | Custom polling | Redis + batch_queue_service | Already implemented with caching |
| Fair scheduling | Simple queue | BatchQueueService | Handles priority, concurrency limits |

**Key insight:** The CIRA codebase already has comprehensive batch processing implementation. Focus testing efforts rather than re-implementation.

## Common Pitfalls

### Pitfall 1: Duplicate URL Detection
**What goes wrong:** Same URL uploaded twice in same batch or existing in database
**Why it happens:** User copies rows or uploads file multiple times
**How to avoid:**
- Check for duplicates within batch using a set
- Check for existing URLs in database before adding
**Warning signs:** Test for `urls_in_batch` set usage in batch.py

### Pitfall 2: Character Encoding Issues
**What goes wrong:** Non-UTF8 CSV files cause parse errors
**Why it happens:** Users export from Excel in different encodings
**How to avoid:**
- Explicitly decode as UTF-8
- Catch UnicodeDecodeError and return helpful message
**Warning signs:** Test with Windows-1252 encoded files

### Pitfall 3: Large File Memory Issues
**What goes wrong:** Loading 10,000+ row CSV exhausts memory
**Why it happens:** Naive implementation loads entire file
**How to avoid:**
- Stream parsing with csv.DictReader
- Process in chunks if needed
**Warning signs:** Test with 105+ row CSV (already covered)

### Pitfall 4: Batch Progress Stale Data
**What goes wrong:** Progress shows outdated counts
**Why it happens:** Redis cache not updated on company status change
**How to avoid:**
- on_company_status_change() hook updates batch counts
- Redis cache has TTL for freshness
**Warning signs:** Integration tests for progress after company completion

## Code Examples

Verified patterns from official sources:

### CSV Validation Pattern
```python
# Source: backend/app/api/routes/batch.py
def process_csv_row(row: dict, row_index: int) -> tuple[Company | None, str | None]:
    company_name = row.get('company_name', '').strip()
    if not company_name:
        return None, 'Company name is required'
    if len(company_name) > 200:
        return None, 'Company name exceeds 200 characters'

    website_url = row.get('website_url', '').strip()
    is_valid, error = validate_url_format(website_url)
    if not is_valid:
        return None, error

    return Company(...), None
```

### Frontend File Upload Pattern
```typescript
// Source: frontend/src/pages/BatchUpload.tsx
const handleFileSelect = useCallback(async (file: File) => {
  if (!file.name.endsWith('.csv')) {
    showToast({ type: 'error', message: 'Please select a CSV file' });
    return;
  }

  const content = await file.text();
  const result = parseCsv(content);
  setParseResult(result);
}, [showToast]);
```

### Batch Upload Mutation
```typescript
// Source: frontend/src/hooks/useCompanies.ts
export function useBatchUpload() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => batchUpload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: companyKeys.lists() });
    },
  });
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Synchronous batch | Async Celery queue | Already in place | Handles large batches |
| Single batch at a time | Fair multi-batch scheduling | Already in place | Better UX |
| Manual polling | Redis-backed progress | Already in place | 2-second updates |

**Deprecated/outdated:**
- None - implementation is current

## Testing Gap Analysis

Based on requirements and existing tests:

### Well-Covered Areas
- CSV parsing with valid/invalid data
- Missing/extra columns handling
- Duplicate URL detection (within batch and database)
- Template download
- Batch CRUD operations
- Fair scheduling with priority
- Progress tracking

### Potential Testing Gaps to Verify
1. **UI-10: Delete company** - Delete confirmation modal UI tests
2. **UI-08: Configuration panel** - Quick/Thorough mode preset tests
3. **Edge Cases:**
   - Very large CSV files (>1000 rows)
   - Special characters in company names (unicode, quotes)
   - CSV with BOM (Byte Order Mark)
   - Empty rows in middle of CSV
4. **Integration:**
   - Full flow: upload -> queue -> process -> verify results
   - Batch pause/resume with checkpoints

## Open Questions

Things that couldn't be fully resolved:

1. **UI Test Coverage**
   - What we know: E2E tests exist in `batch-upload.spec.ts`
   - What's unclear: Are delete confirmation modal tests comprehensive?
   - Recommendation: Review existing E2E tests and add missing scenarios

2. **Load Testing**
   - What we know: 105-row test exists
   - What's unclear: Performance at 1000+ rows
   - Recommendation: Add load test if not covered

## Sources

### Primary (HIGH confidence)
- `/Users/stephenhollifield/Cira/backend/app/api/routes/batch.py` - Batch upload implementation
- `/Users/stephenhollifield/Cira/backend/app/services/batch_queue_service.py` - Queue management
- `/Users/stephenhollifield/Cira/backend/tests/test_batch_api.py` - Existing tests
- `/Users/stephenhollifield/Cira/backend/tests/test_batch_queue_service.py` - Service tests
- `/Users/stephenhollifield/Cira/frontend/src/pages/BatchUpload.tsx` - Upload UI

### Secondary (MEDIUM confidence)
- IMPLEMENTATION_PLAN.md - Phase status and completion notes

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified in codebase
- Architecture: HIGH - Code review confirms patterns
- Pitfalls: HIGH - Based on existing test coverage
- Testing gaps: MEDIUM - Requires verification of test completeness

**Research date:** 2026-01-19
**Valid until:** Ongoing (implementation complete, needs testing verification)
