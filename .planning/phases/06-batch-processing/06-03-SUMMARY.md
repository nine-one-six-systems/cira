---
phase: 06
plan: 03
subsystem: batch-processing
tags: [testing, edge-cases, csv-parsing, validation, concurrency]

dependency-graph:
  requires:
    - 06-01  # Batch API tests
    - 06-02  # Batch queue service tests
  provides:
    - batch-edge-case-tests
    - csv-encoding-tests
    - batch-scheduling-edge-tests
  affects:
    - 06-04  # Batch UI tests
    - 06-05  # Phase verification

tech-stack:
  added: []
  patterns:
    - edge-case-testing
    - encoding-validation

key-files:
  created:
    - backend/tests/test_batch_edge_cases.py
  modified:
    - backend/app/api/routes/batch.py

decisions:
  - id: UTF8_BOM_ENCODING
    choice: "Use utf-8-sig encoding for CSV decoding"
    rationale: "Automatically handles UTF-8 BOM without manual stripping"

metrics:
  duration: "5 minutes"
  completed: "2026-01-19"
---

# Phase 6 Plan 3: Batch Error Handling Tests Summary

Edge case tests ensuring batch processing handles unusual inputs, encoding issues, and concurrent operations robustly.

## One-liner

36 edge case tests covering CSV encoding (BOM, unicode), format variations, large files, URL/name validation, and batch queue scheduling edge cases with a BOM handling fix.

## What Was Built

Created comprehensive edge case tests for batch processing at `/Users/stephenhollifield/Cira/backend/tests/test_batch_edge_cases.py`.

### Test Classes Created

| Class | Tests | Coverage |
|-------|-------|----------|
| TestCsvEncodingEdgeCases | 4 | UTF-8 BOM, unicode, emoji, special chars |
| TestCsvFormatEdgeCases | 7 | Empty rows, whitespace, quoting, CRLF |
| TestLargeFileHandling | 3 | 100/500 rows, memory efficiency |
| TestCompanyNameEdgeCases | 4 | Max length, special chars, quotes |
| TestUrlValidationEdgeCases | 5 | Port, path, subdomain, IP, normalization |
| TestBatchSchedulingEdgeCases | 4 | No pending, global limit, empty batches |
| TestBatchConcurrencyEdgeCases | 4 | Pause, double start, cancel then resume |
| TestBatchProgressEdgeCases | 3 | Zero companies, all failed, mixed states |
| TestBatchCleanupEdgeCases | 2 | Preserve active, no old batches |

**Total: 36 tests, 985 lines**

### Test Coverage Details

**CSV Encoding (BAT-02):**
- UTF-8 BOM handling (discovered bug, fixed)
- Unicode company names (international characters)
- Emoji in names (graceful handling)
- Special characters in URLs

**CSV Format (BAT-01):**
- Empty rows between data rows
- Leading/trailing whitespace (trimmed)
- Quoted fields with embedded commas
- Extra columns beyond required
- Missing optional columns
- Windows CRLF line endings
- Mixed line endings

**Large Files (BAT-02):**
- 100-row CSV upload
- 500-row CSV upload
- Memory efficiency validation (< 10s for 200 companies)

**Validation Edge Cases:**
- Company name at exactly 200 chars (max)
- Company name over 200 chars (rejected)
- Special characters in names (& @ # accepted)
- URLs with port numbers
- URLs with paths and subdomains
- IP addresses (gracefully handled)
- URL normalization (https:// added)

**Batch Queue Edge Cases:**
- Scheduling with no pending companies
- Global concurrency limit respected
- Multiple empty batches
- Batch completion with all failed companies
- Pause during scheduling
- Double start/pause attempts
- Cancel then resume attempt (rejected)

**Progress Edge Cases:**
- Zero companies (no division by zero)
- All failed companies (100% progress)
- Mixed terminal states

**Cleanup Edge Cases:**
- Preserves active (PROCESSING) batches
- Handles no old batches gracefully

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed UTF-8 BOM handling in CSV upload**

- **Found during:** Task 1 - test_csv_with_utf8_bom
- **Issue:** CSV files with UTF-8 BOM (byte order mark) failed to parse because the BOM character was prepended to the first column header
- **Fix:** Changed `decode('utf-8')` to `decode('utf-8-sig')` which automatically strips the BOM
- **Files modified:** backend/app/api/routes/batch.py
- **Commit:** 08048b4

## Key Artifacts

```
backend/tests/test_batch_edge_cases.py  # 985 lines, 36 tests
backend/app/api/routes/batch.py         # BOM handling fix
```

## Requirement Traceability

| Requirement | Tests | Status |
|-------------|-------|--------|
| BAT-01 | 7 (format tests) | Verified |
| BAT-02 | 29 (encoding, validation, scheduling) | Verified |

## Commits

| Hash | Type | Description |
|------|------|-------------|
| 08048b4 | test | Add batch processing edge case tests |

## Next Phase Readiness

Phase 6 Plan 4 (Batch UI tests) can proceed. All batch API and service edge cases are now tested.

### Blockers

None.

### Concerns

- Deprecation warnings for `datetime.utcnow()` in job_service.py (not blocking, cosmetic)
