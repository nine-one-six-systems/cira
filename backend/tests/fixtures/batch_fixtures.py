"""
Batch processing test fixtures.

Provides CSV content samples and factory functions for batch integration testing.

Requirements covered:
- BAT-01: CSV file upload
- BAT-02: Validate CSV, report errors per row
- BAT-03: Download CSV template
- BAT-04: Queue batch companies
- API-02: POST /companies/batch
"""

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import BatchJob, Company


# =============================================================================
# CSV Content Fixtures
# =============================================================================

VALID_CSV_CONTENT = """company_name,website_url,industry
Acme Corp,https://acme.com,Technology
Beta Inc,https://beta.io,Healthcare
Gamma Ltd,https://gamma.co,Finance
Delta LLC,https://delta.org,Manufacturing
Epsilon Co,https://epsilon.net,Retail"""
"""
Valid 5-row CSV for batch upload testing (BAT-01).

All rows have valid company name, URL, and industry.
"""


MIXED_VALIDITY_CSV = """company_name,website_url,industry
Valid One,https://valid1.com,Tech
,https://noname.com,Tech
Valid Two,https://valid2.com,Finance
Invalid URL,not-a-url,Tech
Valid Three,https://valid3.com,Healthcare"""
"""
Mixed validity CSV for per-row error testing (BAT-02).

- Row 1: Valid
- Row 2: Invalid - missing company name
- Row 3: Valid
- Row 4: Invalid - malformed URL
- Row 5: Valid

Expected: 3 successful, 2 failed
"""


CSV_WITH_DUPLICATES = """company_name,website_url,industry
First,https://same.com,Tech
Second,https://same.com,Finance
Third,https://unique.com,Healthcare"""
"""
CSV with duplicate URLs for duplicate detection testing (BAT-02).

- Row 1: Valid (first occurrence of same.com)
- Row 2: Invalid - duplicate URL within batch
- Row 3: Valid (unique URL)

Expected: 2 successful, 1 failed
"""


def generate_large_csv(row_count: int = 50) -> str:
    """
    Generate a large CSV for load testing.

    Args:
        row_count: Number of data rows (default: 50)

    Returns:
        CSV content string with header + row_count rows
    """
    rows = ['company_name,website_url,industry']
    for i in range(row_count):
        rows.append(f'Company {i:04d},https://company{i:04d}.com,Industry{i % 5}')
    return '\n'.join(rows)


LARGE_CSV_CONTENT = generate_large_csv(50)
"""Pre-generated 50-row CSV for load testing."""


# =============================================================================
# File Creation Helpers
# =============================================================================

def create_csv_file(content: str, filename: str = 'test.csv') -> tuple[io.BytesIO, str]:
    """
    Create a file-like object for CSV content upload.

    Args:
        content: CSV content string
        filename: Name of the file (default: 'test.csv')

    Returns:
        Tuple of (BytesIO file object, filename) for multipart upload
    """
    return (io.BytesIO(content.encode('utf-8')), filename)


# =============================================================================
# Database Factory Functions
# =============================================================================

def create_batch_with_companies(
    db,
    company_count: int,
    batch_status=None,
    company_status=None
) -> tuple['BatchJob', list['Company']]:
    """
    Create a BatchJob with associated Company records.

    Factory function for setting up batch test scenarios (BAT-04).

    Args:
        db: SQLAlchemy database session
        company_count: Number of companies to create
        batch_status: BatchStatus for the batch (default: PENDING)
        company_status: CompanyStatus for all companies (default: PENDING)

    Returns:
        Tuple of (BatchJob, list of Company records)
    """
    from app.models import BatchJob, Company
    from app.models.enums import BatchStatus, CompanyStatus

    if batch_status is None:
        batch_status = BatchStatus.PENDING
    if company_status is None:
        company_status = CompanyStatus.PENDING

    # Create batch job
    batch = BatchJob(
        name=f'Test Batch - {company_count} companies',
        status=batch_status,
        total_companies=company_count,
        pending_companies=company_count if company_status == CompanyStatus.PENDING else 0,
        processing_companies=company_count if company_status == CompanyStatus.IN_PROGRESS else 0,
        completed_companies=company_count if company_status == CompanyStatus.COMPLETED else 0,
        failed_companies=company_count if company_status == CompanyStatus.FAILED else 0,
        max_concurrent=3,
        priority=100,
    )
    db.session.add(batch)
    db.session.flush()  # Get batch ID

    # Create companies
    companies = []
    for i in range(company_count):
        company = Company(
            company_name=f'Test Company {i + 1}',
            website_url=f'https://testcompany{i + 1}.com',
            industry='Testing',
            batch_id=batch.id,
            status=company_status,
        )
        db.session.add(company)
        companies.append(company)

    db.session.commit()
    return batch, companies


def create_processing_batch(db) -> tuple['BatchJob', list['Company']]:
    """
    Create a BatchJob in PROCESSING state with mixed company statuses.

    Factory function for testing batch progress tracking and status updates.

    Creates:
    - 2 PENDING companies
    - 1 IN_PROGRESS company
    - 1 COMPLETED company

    Args:
        db: SQLAlchemy database session

    Returns:
        Tuple of (BatchJob, list of Company records)
    """
    from app.models import BatchJob, Company
    from app.models.enums import BatchStatus, CompanyStatus

    # Create batch job in PROCESSING state
    batch = BatchJob(
        name='Processing Batch - Mixed Status',
        status=BatchStatus.PROCESSING,
        total_companies=4,
        pending_companies=2,
        processing_companies=1,
        completed_companies=1,
        failed_companies=0,
        max_concurrent=3,
        priority=100,
    )
    db.session.add(batch)
    db.session.flush()

    # Create companies with mixed statuses
    companies = []
    status_config = [
        (CompanyStatus.PENDING, 'Pending Company 1'),
        (CompanyStatus.PENDING, 'Pending Company 2'),
        (CompanyStatus.IN_PROGRESS, 'In Progress Company'),
        (CompanyStatus.COMPLETED, 'Completed Company'),
    ]

    for i, (status, name) in enumerate(status_config):
        company = Company(
            company_name=name,
            website_url=f'https://mixed{i + 1}.com',
            industry='Testing',
            batch_id=batch.id,
            status=status,
        )
        db.session.add(company)
        companies.append(company)

    db.session.commit()
    return batch, companies


def create_batch_ready_for_completion(db) -> tuple['BatchJob', list['Company']]:
    """
    Create a BatchJob where all but one company are completed.

    Factory function for testing batch auto-completion on last company done.

    Creates:
    - 2 COMPLETED companies
    - 1 IN_PROGRESS company (ready to complete)

    Args:
        db: SQLAlchemy database session

    Returns:
        Tuple of (BatchJob, list of Company records)
    """
    from app.models import BatchJob, Company
    from app.models.enums import BatchStatus, CompanyStatus

    batch = BatchJob(
        name='Almost Complete Batch',
        status=BatchStatus.PROCESSING,
        total_companies=3,
        pending_companies=0,
        processing_companies=1,
        completed_companies=2,
        failed_companies=0,
        max_concurrent=3,
        priority=100,
    )
    db.session.add(batch)
    db.session.flush()

    companies = []
    status_config = [
        (CompanyStatus.COMPLETED, 'Done Company 1'),
        (CompanyStatus.COMPLETED, 'Done Company 2'),
        (CompanyStatus.IN_PROGRESS, 'Last Company'),
    ]

    for i, (status, name) in enumerate(status_config):
        company = Company(
            company_name=name,
            website_url=f'https://almostdone{i + 1}.com',
            industry='Testing',
            batch_id=batch.id,
            status=status,
        )
        db.session.add(company)
        companies.append(company)

    db.session.commit()
    return batch, companies
