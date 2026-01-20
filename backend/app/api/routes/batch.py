"""Batch upload API routes."""

import csv
import io
from flask import request, Response

from app import db
from app.api import api_bp
from app.api.routes.companies import make_error_response, make_success_response, normalize_url
from app.models.company import Company
from app.schemas import BatchUploadResponse, BatchCompanyResult
from app.schemas.company import URL_DOMAIN_PATTERN
from app.services.batch_queue_service import batch_queue_service


# CSV Template
CSV_TEMPLATE = """company_name,website_url,industry
Acme Corp,https://acme.com,Technology
Beta Inc,https://beta.io,Healthcare
"""


def validate_url_format(url: str) -> tuple[bool, str | None]:
    """Validate URL format and return (is_valid, error_message)."""
    if not url:
        return False, 'URL is required'

    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = f'https://{url}'

    # Check domain format
    if not URL_DOMAIN_PATTERN.match(url):
        return False, 'Invalid URL format'

    return True, None


def process_csv_row(row: dict, row_index: int) -> tuple[Company | None, str | None]:
    """
    Process a single CSV row and return (company, error_message).

    Returns:
        (Company, None) if successful
        (None, error_message) if validation failed
    """
    # Get and validate company name
    company_name = row.get('company_name', '').strip()
    if not company_name:
        return None, 'Company name is required'
    if len(company_name) > 200:
        return None, 'Company name exceeds 200 characters'

    # Get and validate URL
    website_url = row.get('website_url', '').strip()
    is_valid, error = validate_url_format(website_url)
    if not is_valid:
        return None, error

    # Normalize URL
    if not website_url.startswith(('http://', 'https://')):
        website_url = f'https://{website_url}'
    website_url = normalize_url(website_url)

    # Check for duplicate URL
    for company in Company.query.all():
        if normalize_url(company.website_url) == website_url:
            return None, f'Company with URL {website_url} already exists'

    # Get optional industry
    industry = row.get('industry', '').strip() or None
    if industry and len(industry) > 100:
        return None, 'Industry exceeds 100 characters'

    # Create company
    company = Company(
        company_name=company_name,
        website_url=website_url,
        industry=industry
    )

    return company, None


@api_bp.route('/companies/batch', methods=['POST'])
def batch_upload():
    """Upload CSV for batch processing."""
    # Check for file
    if 'file' not in request.files:
        return make_error_response(
            'VALIDATION_ERROR',
            'No file provided',
            {'field': 'file'}
        )

    file = request.files['file']

    # Check filename
    if file.filename == '':
        return make_error_response(
            'VALIDATION_ERROR',
            'No file selected'
        )

    # Check file extension
    if not file.filename.endswith('.csv'):
        return make_error_response(
            'VALIDATION_ERROR',
            'File must be a CSV file',
            {'filename': file.filename}
        )

    try:
        # Read CSV content
        # Use 'utf-8-sig' to handle BOM (byte order mark) automatically
        content = file.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(content))

        # Check required columns
        required_columns = {'company_name', 'website_url'}
        if reader.fieldnames is None:
            return make_error_response(
                'VALIDATION_ERROR',
                'CSV file is empty or has no headers'
            )

        missing_columns = required_columns - set(reader.fieldnames)
        if missing_columns:
            return make_error_response(
                'VALIDATION_ERROR',
                f'Missing required columns: {", ".join(missing_columns)}',
                {'missingColumns': list(missing_columns)}
            )

        # Process rows
        results = []
        companies_to_add = []
        urls_in_batch = set()

        for row_index, row in enumerate(reader, start=1):
            company_name = row.get('company_name', '').strip()
            website_url = row.get('website_url', '').strip()

            # Normalize URL for duplicate check within batch
            if website_url:
                if not website_url.startswith(('http://', 'https://')):
                    normalized_for_check = f'https://{website_url}'
                else:
                    normalized_for_check = website_url
                normalized_for_check = normalize_url(normalized_for_check)

                # Check for duplicate within this batch
                if normalized_for_check in urls_in_batch:
                    results.append(BatchCompanyResult(
                        companyName=company_name or f'Row {row_index}',
                        error='Duplicate URL in batch'
                    ))
                    continue

            company, error = process_csv_row(row, row_index)

            if error:
                results.append(BatchCompanyResult(
                    companyName=company_name or f'Row {row_index}',
                    error=error
                ))
            else:
                companies_to_add.append(company)
                urls_in_batch.add(normalize_url(company.website_url))
                results.append(BatchCompanyResult(
                    companyName=company.company_name,
                    companyId=None  # Will be set after commit
                ))

        # Add all valid companies in one transaction
        for company in companies_to_add:
            db.session.add(company)

        db.session.commit()

        # Update results with company IDs
        company_index = 0
        for result in results:
            if result.error is None:
                result.company_id = companies_to_add[company_index].id
                company_index += 1

        # Build response
        successful = sum(1 for r in results if r.error is None)
        failed = sum(1 for r in results if r.error is not None)

        response_data = BatchUploadResponse(
            totalCount=len(results),
            successful=successful,
            failed=failed,
            companies=[r.model_dump(by_alias=True) for r in results]
        ).model_dump(by_alias=True)

        # Create batch job if requested and there are successful companies
        create_batch = request.form.get('createBatch', 'true').lower() == 'true'
        start_processing = request.form.get('startProcessing', 'true').lower() == 'true'
        batch_name = request.form.get('batchName')
        batch_priority = request.form.get('priority', 100, type=int)

        if create_batch and successful > 0:
            company_ids = [c.id for c in companies_to_add]
            batch_result = batch_queue_service.create_batch(
                company_ids=company_ids,
                name=batch_name or f'Batch Upload - {file.filename}',
                config=None,
                priority=batch_priority,
                start_immediately=start_processing,
            )
            if batch_result.get('success'):
                response_data['batchId'] = batch_result['batch_id']
                response_data['batchStatus'] = 'processing' if start_processing else 'pending'

        return make_success_response(response_data, status=201)

    except UnicodeDecodeError:
        return make_error_response(
            'VALIDATION_ERROR',
            'File encoding error. Please ensure the CSV is UTF-8 encoded.'
        )
    except csv.Error as e:
        return make_error_response(
            'VALIDATION_ERROR',
            f'CSV parsing error: {str(e)}'
        )


@api_bp.route('/companies/template', methods=['GET'])
def download_template():
    """Download CSV template."""
    return Response(
        CSV_TEMPLATE,
        mimetype='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename=company_template.csv'
        }
    )
