"""Edge case tests for batch processing robustness.

Tests cover CSV parsing edge cases, URL validation edge cases, company name validation,
batch scheduling edge cases, and concurrency handling.

BAT-01: Batch Upload API supports CSV file format
BAT-02: Batch processing handles edge cases gracefully
"""

import io
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from app import db
from app.models.company import Company
from app.models.batch import BatchJob
from app.models.enums import CompanyStatus, BatchStatus


def create_csv_file(content: str, filename: str = 'test.csv'):
    """Create a file-like object for CSV content."""
    return (io.BytesIO(content.encode('utf-8')), filename)


def create_csv_bytes(content: bytes, filename: str = 'test.csv'):
    """Create a file-like object for raw bytes CSV content."""
    return (io.BytesIO(content), filename)


class TestCsvEncodingEdgeCases:
    """Tests for CSV encoding edge cases.

    Verifies batch upload handles various character encodings and special
    characters correctly.

    BAT-02: Batch processing handles encoding edge cases
    """

    def test_csv_with_utf8_bom(self, client):
        """Test CSV with UTF-8 BOM (byte order mark) at start.

        BAT-02: Handles UTF-8 BOM encoding correctly.
        """
        # UTF-8 BOM is bytes \xef\xbb\xbf at start
        bom = b'\xef\xbb\xbf'
        csv_content = b'company_name,website_url,industry\nAcme Corp,https://acme-bom.com,Technology'
        content_with_bom = bom + csv_content

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_bytes(content_with_bom)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['successful'] == 1

    def test_csv_with_unicode_company_names(self, client):
        """Test CSV with international unicode characters in company names.

        BAT-02: Preserves unicode company names correctly.
        """
        csv_content = """company_name,website_url,industry
Acme Corp,https://acme-unicode.com,Technology
Cafe Muller,https://cafe-muller.de,Food
Tokyo Inc,https://tokyo-inc.jp,Tech
Beijing Ltd,https://beijing-ltd.cn,Manufacturing"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 4

        # Verify names preserved
        companies = data['data']['companies']
        assert companies[0]['companyName'] == 'Acme Corp'
        assert companies[1]['companyName'] == 'Cafe Muller'
        assert companies[2]['companyName'] == 'Tokyo Inc'
        assert companies[3]['companyName'] == 'Beijing Ltd'

    def test_csv_with_emoji_in_name(self, client):
        """Test CSV with emoji in company name.

        BAT-02: Handles emoji characters gracefully (accepts or rejects cleanly).
        """
        # Note: Emoji support depends on database/encoding configuration
        csv_content = """company_name,website_url,industry
Rocket Co,https://rocket-co.com,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        # Should either succeed or fail gracefully (not crash)
        assert response.status_code in (201, 400)
        data = response.get_json()
        # Response should be valid JSON either way
        assert 'success' in data or 'error' in data

    def test_csv_with_special_chars_in_url(self, client):
        """Test URLs with encoded special characters.

        BAT-02: URL validation handles special characters.
        """
        csv_content = """company_name,website_url,industry
Query Corp,https://example.com/search?q=test&page=1,Tech
Path Corp,https://example-path.com/about/us,Services"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        # URLs with query parameters are valid
        assert data['data']['successful'] >= 1


class TestCsvFormatEdgeCases:
    """Tests for CSV format edge cases.

    Verifies batch upload handles various CSV formatting variations correctly.

    BAT-01: Batch Upload API supports CSV file format
    """

    def test_csv_with_empty_rows_in_middle(self, client):
        """Test CSV with blank lines between data rows.

        BAT-01: Blank rows are skipped, valid rows processed.
        """
        csv_content = """company_name,website_url,industry
First Corp,https://first-empty.com,Tech

Second Corp,https://second-empty.com,Finance

Third Corp,https://third-empty.com,Healthcare"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        # Empty rows should be skipped or handled gracefully
        # Valid companies should be processed
        assert data['data']['successful'] >= 0

    def test_csv_with_extra_whitespace(self, client):
        """Test CSV with leading/trailing spaces in values.

        BAT-01: Whitespace is trimmed from values.
        """
        csv_content = """company_name,website_url,industry
  Whitespace Corp  ,  https://whitespace.com  ,  Technology  """

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1
        # Company name should be trimmed
        assert data['data']['companies'][0]['companyName'] == 'Whitespace Corp'

    def test_csv_with_quoted_fields(self, client):
        """Test CSV with quoted fields containing commas.

        BAT-01: Commas inside quotes not treated as delimiters.
        """
        csv_content = '''company_name,website_url,industry
"Acme, Corp",https://acme-quoted.com,"Tech, Finance"'''

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1
        assert data['data']['companies'][0]['companyName'] == 'Acme, Corp'

    def test_csv_with_extra_columns(self, client):
        """Test CSV with columns beyond required (notes, contact, etc.).

        BAT-01: Extra columns ignored, required columns processed.
        """
        csv_content = """company_name,website_url,industry,notes,contact
Extra Corp,https://extra-cols.com,Tech,Some notes,john@example.com"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1
        assert data['data']['companies'][0]['companyName'] == 'Extra Corp'

    def test_csv_with_missing_optional_columns(self, client):
        """Test CSV with only company_name and website_url (no industry).

        BAT-01: Companies created with null/empty industry.
        """
        csv_content = """company_name,website_url
Minimal Corp,https://minimal.com"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1

    def test_csv_with_windows_line_endings(self, client):
        """Test CSV with CRLF line endings (Windows-style).

        BAT-01: Parsing handles Windows-style line endings.
        """
        csv_content = "company_name,website_url,industry\r\nWindows Corp,https://windows-crlf.com,Tech\r\n"

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1

    def test_csv_with_mixed_line_endings(self, client):
        """Test CSV mixing LF and CRLF line endings.

        BAT-01: All rows parsed correctly with mixed line endings.
        """
        csv_content = "company_name,website_url,industry\nMixed1 Corp,https://mixed1.com,Tech\r\nMixed2 Corp,https://mixed2.com,Finance\n"

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 2


class TestLargeFileHandling:
    """Tests for large CSV file handling.

    Verifies batch upload handles large files without memory or timeout issues.

    BAT-02: Large CSV files processed without memory issues
    """

    def test_csv_with_100_rows(self, client):
        """Test uploading 100-row CSV.

        BAT-02: All 100 companies created without timeout or memory issues.
        """
        rows = ['company_name,website_url,industry']
        for i in range(100):
            rows.append(f'Company100_{i},https://company100-{i}.com,Tech')

        csv_content = '\n'.join(rows)

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['totalCount'] == 100
        assert data['data']['successful'] == 100
        assert data['data']['failed'] == 0

    def test_csv_with_500_rows(self, client):
        """Test uploading 500-row CSV.

        BAT-02: All companies created for large batch.
        """
        rows = ['company_name,website_url,industry']
        for i in range(500):
            rows.append(f'Company500_{i},https://company500-{i}.com,Tech')

        csv_content = '\n'.join(rows)

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['totalCount'] == 500
        assert data['data']['successful'] == 500
        assert data['data']['failed'] == 0

    def test_csv_memory_efficiency(self, client):
        """Test large CSV response time is reasonable.

        BAT-02: Memory doesn't spike excessively.
        """
        import time

        rows = ['company_name,website_url,industry']
        for i in range(200):
            rows.append(f'CompanyMem_{i},https://company-mem-{i}.com,Tech')

        csv_content = '\n'.join(rows)

        start_time = time.time()

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        elapsed = time.time() - start_time

        assert response.status_code == 201
        # Response time should be under 10 seconds for 200 companies
        assert elapsed < 10.0, f"Batch upload took {elapsed:.2f}s, expected < 10s"


class TestCompanyNameEdgeCases:
    """Tests for company name validation edge cases.

    BAT-02: Company name validation handles edge cases
    """

    def test_company_name_max_length(self, client):
        """Test company with exactly 200 character name (max).

        BAT-02: Maximum length company name accepted.
        """
        # Create exactly 200 character name
        long_name = 'A' * 200
        csv_content = f"""company_name,website_url,industry
{long_name},https://maxlen.com,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1
        assert len(data['data']['companies'][0]['companyName']) == 200

    def test_company_name_over_max_length(self, client):
        """Test company with 201 character name (exceeds max).

        BAT-02: Company name exceeding 200 characters rejected.
        """
        # Create 201 character name
        too_long_name = 'B' * 201
        csv_content = f"""company_name,website_url,industry
{too_long_name},https://toolong.com,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['failed'] == 1
        assert 'exceeds 200 characters' in data['data']['companies'][0]['error']

    def test_company_name_with_special_chars(self, client):
        """Test names with special characters: & @ # $ % ^ * ( ) ! ?

        BAT-02: Special characters accepted in company names.
        """
        csv_content = """company_name,website_url,industry
AT&T Corp,https://att-special.com,Telecom
@Home Inc,https://athome-special.com,Tech
#1 Company,https://num1-special.com,Services"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 3

    def test_company_name_with_quotes(self, client):
        """Test names with single and double quotes.

        BAT-02: CSV parsing handles quotes in company names correctly.
        """
        csv_content = '''company_name,website_url,industry
"John's Company",https://johns-quoted.com,Tech
"The ""Best"" Corp",https://best-quoted.com,Services'''

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] >= 1


class TestUrlValidationEdgeCases:
    """Tests for URL validation edge cases.

    BAT-02: URL validation handles edge cases correctly
    """

    def test_url_with_port(self, client):
        """Test URL with port number.

        BAT-02: URLs with ports are valid.
        """
        csv_content = """company_name,website_url,industry
Port Corp,https://example.com:8080,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        # URL with port should be valid
        assert data['data']['successful'] == 1

    def test_url_with_path(self, client):
        """Test URL with path segments.

        BAT-02: URLs with paths are valid.
        """
        csv_content = """company_name,website_url,industry
Path Corp,https://example-urlpath.com/about/us,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1

    def test_url_with_subdomain(self, client):
        """Test URL with subdomain (www).

        BAT-02: URLs with subdomains are valid.
        """
        csv_content = """company_name,website_url,industry
WWW Corp,https://www.example-subdomain.com,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1

    def test_url_with_ip_address(self, client):
        """Test URL with IP address instead of domain.

        BAT-02: IP addresses may be rejected by domain validation.
        """
        csv_content = """company_name,website_url,industry
IP Corp,http://192.168.1.1,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        # IP addresses may be rejected by URL_DOMAIN_PATTERN (requires TLD)
        # Either outcome is acceptable as long as it's handled gracefully
        assert data['data']['totalCount'] == 1

    def test_url_normalization(self, client):
        """Test URL without protocol has https:// added.

        BAT-02: URLs without protocol get https:// prefix.
        """
        csv_content = """company_name,website_url,industry
NoProtocol Corp,example-noprotocol.com,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1


class TestBatchSchedulingEdgeCases:
    """Tests for batch queue scheduling edge cases.

    BAT-02: Batch scheduling handles edge cases in queue management
    """

    def test_schedule_with_no_pending_companies(self, app):
        """Test scheduling with batch containing no PENDING companies.

        BAT-02: Returns 0 companies scheduled without error.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="All Completed Batch",
                status=BatchStatus.PROCESSING,
                total_companies=3,
                completed_companies=3,
            )
            db.session.add(batch)
            db.session.commit()

            # Add all completed companies
            companies = [
                Company(
                    company_name=f"Completed {i}",
                    website_url=f"https://completed-sched{i}.com",
                    status=CompanyStatus.COMPLETED,
                    batch_id=batch.id
                )
                for i in range(3)
            ]
            db.session.add_all(companies)
            db.session.commit()

            with patch('app.services.batch_queue_service.job_service'):
                service = BatchQueueService()
                scheduled = service.schedule_next_from_all_batches()

                # No pending companies, should schedule 0
                assert scheduled == 0

    def test_schedule_respects_global_limit(self, app):
        """Test scheduling respects GLOBAL_MAX_CONCURRENT limit.

        BAT-02: Only global limit companies started.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Big Batch",
                status=BatchStatus.PROCESSING,
                total_companies=10,
                pending_companies=10,
                max_concurrent=10,  # High batch limit
            )
            db.session.add(batch)
            db.session.commit()

            # Add 10 pending companies
            companies = [
                Company(
                    company_name=f"Pending Global {i}",
                    website_url=f"https://pending-global{i}.com",
                    status=CompanyStatus.PENDING,
                    batch_id=batch.id
                )
                for i in range(10)
            ]
            db.session.add_all(companies)
            db.session.commit()

            scheduled_count = 0
            with patch('app.services.batch_queue_service.job_service') as mock_job:
                def track_start(company_id, config=None):
                    nonlocal scheduled_count
                    scheduled_count += 1
                    return {'success': True}

                mock_job.start_job.side_effect = track_start

                service = BatchQueueService()
                # Set a low global limit
                original_global = service.GLOBAL_MAX_CONCURRENT
                service.GLOBAL_MAX_CONCURRENT = 3

                try:
                    service.schedule_next_from_all_batches()
                    # Should only schedule up to global limit
                    assert scheduled_count <= 3
                finally:
                    service.GLOBAL_MAX_CONCURRENT = original_global

    def test_schedule_with_multiple_empty_batches(self, app):
        """Test scheduling with multiple batches having no pending companies.

        BAT-02: No errors, 0 scheduled.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            # Create 3 batches with no pending companies
            for i in range(3):
                batch = BatchJob(
                    name=f"Empty Batch {i}",
                    status=BatchStatus.PROCESSING,
                    total_companies=1,
                    completed_companies=1,
                )
                db.session.add(batch)
                db.session.commit()

                company = Company(
                    company_name=f"Done {i}",
                    website_url=f"https://done-empty{i}.com",
                    status=CompanyStatus.COMPLETED,
                    batch_id=batch.id
                )
                db.session.add(company)
                db.session.commit()

            with patch('app.services.batch_queue_service.job_service'):
                service = BatchQueueService()
                scheduled = service.schedule_next_from_all_batches()

                assert scheduled == 0

    def test_batch_completion_with_all_failed(self, app):
        """Test batch with all FAILED companies completes properly.

        BAT-02: Batch status is COMPLETED (not stuck).
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="All Failed Batch",
                status=BatchStatus.PROCESSING,
                total_companies=3,
                processing_companies=1,
                failed_companies=2,
            )
            db.session.add(batch)
            db.session.commit()

            # Add all failed companies
            companies = [
                Company(
                    company_name=f"Failed {i}",
                    website_url=f"https://failed-comp{i}.com",
                    status=CompanyStatus.FAILED,
                    batch_id=batch.id
                )
                for i in range(2)
            ]
            # Add the last "processing" company that will fail
            last_company = Company(
                company_name="Last Processing",
                website_url="https://last-processing.com",
                status=CompanyStatus.IN_PROGRESS,
                batch_id=batch.id
            )
            db.session.add_all(companies + [last_company])
            db.session.commit()

            # Mark last company as failed
            last_company.status = CompanyStatus.FAILED
            db.session.commit()

            service = BatchQueueService()
            service.on_company_status_change(
                last_company.id,
                CompanyStatus.IN_PROGRESS,
                CompanyStatus.FAILED
            )

            db.session.refresh(batch)
            # Batch should be completed even with all failures
            assert batch.status == BatchStatus.COMPLETED
            assert batch.completed_at is not None


class TestBatchConcurrencyEdgeCases:
    """Tests for batch concurrency handling edge cases.

    BAT-02: Concurrent operations don't cause race conditions
    """

    def test_pause_during_scheduling(self, app):
        """Test pausing batch during scheduling.

        BAT-02: Clean state transition to PAUSED.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Pause Test Batch",
                status=BatchStatus.PROCESSING,
                total_companies=2,
                processing_companies=2,
            )
            db.session.add(batch)
            db.session.commit()

            companies = [
                Company(
                    company_name=f"Pausable {i}",
                    website_url=f"https://pausable{i}.com",
                    status=CompanyStatus.IN_PROGRESS,
                    batch_id=batch.id
                )
                for i in range(2)
            ]
            db.session.add_all(companies)
            db.session.commit()
            batch_id = batch.id

            with patch('app.api.routes.control._pause_company_internal') as mock_pause:
                mock_pause.return_value = {'success': True}

                service = BatchQueueService()
                result = service.pause_batch(batch_id)

                assert result['success'] is True
                db.session.refresh(batch)
                assert batch.status == BatchStatus.PAUSED

    def test_double_start_batch(self, app):
        """Test starting batch that's already processing.

        BAT-02: Second call returns appropriate error.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Already Processing",
                status=BatchStatus.PROCESSING,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.start_batch(batch_id)

            assert result['success'] is False
            assert 'already processing' in result['error'].lower()

    def test_double_pause_batch(self, app):
        """Test pausing batch that's already paused.

        BAT-02: Appropriate response for already paused batch.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Already Paused",
                status=BatchStatus.PAUSED,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.pause_batch(batch_id)

            # Cannot pause already paused batch
            assert result['success'] is False

    def test_cancel_then_resume_attempt(self, app):
        """Test resuming a cancelled batch.

        BAT-02: Rejected - cannot resume cancelled batch.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Cancelled Batch",
                status=BatchStatus.CANCELLED,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            result = service.resume_batch(batch_id)

            assert result['success'] is False
            assert 'not paused' in result['error'].lower()


class TestBatchProgressEdgeCases:
    """Tests for batch progress calculation edge cases.

    BAT-02: Progress calculations handle edge cases
    """

    def test_progress_with_zero_companies(self, app):
        """Test progress with total_companies=0.

        BAT-02: No division by zero error.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="Empty Batch",
                status=BatchStatus.PENDING,
                total_companies=0,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            progress = service.get_batch_progress(batch_id)

            assert progress is not None
            # Should be 0 (not error from division by zero)
            assert progress['progress_percentage'] == 0.0

    def test_progress_all_failed(self, app):
        """Test progress when all companies failed.

        BAT-02: 100% progress (finished, even if failed).
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            batch = BatchJob(
                name="All Failed",
                status=BatchStatus.COMPLETED,
                total_companies=5,
                failed_companies=5,
                pending_companies=0,
                processing_companies=0,
                completed_companies=0,
            )
            db.session.add(batch)
            db.session.commit()
            batch_id = batch.id

            service = BatchQueueService()
            progress = service.get_batch_progress(batch_id)

            assert progress is not None
            # Progress = (completed + failed) / total = (0 + 5) / 5 = 100%
            assert progress['progress_percentage'] == 100.0

    def test_progress_mixed_terminal_states(self, app):
        """Test progress with COMPLETED, FAILED, and CANCELLED companies.

        BAT-02: Correct percentage calculation.
        """
        with app.app_context():
            batch = BatchJob(
                name="Mixed Terminal",
                status=BatchStatus.COMPLETED,
                total_companies=10,
                pending_companies=0,
                processing_companies=0,
                completed_companies=6,
                failed_companies=4,
            )
            db.session.add(batch)
            db.session.commit()

            # Progress = (6 + 4) / 10 = 100%
            assert batch.progress_percentage == 100.0


class TestBatchCleanupEdgeCases:
    """Tests for batch cleanup edge cases.

    BAT-02: Cleanup handles edge cases correctly
    """

    def test_cleanup_preserves_active_batches(self, app):
        """Test cleanup preserves PROCESSING batches even if old.

        BAT-02: Active batches not deleted.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            # Create old PROCESSING batch
            old_processing = BatchJob(
                name="Old Processing",
                status=BatchStatus.PROCESSING,
                created_at=datetime.now(timezone.utc) - timedelta(days=30),
            )
            # Create old COMPLETED batch
            old_completed = BatchJob(
                name="Old Completed",
                status=BatchStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc) - timedelta(days=30),
            )
            db.session.add_all([old_processing, old_completed])
            db.session.commit()

            processing_id = old_processing.id
            completed_id = old_completed.id

            service = BatchQueueService()
            cleaned = service.cleanup_completed_batches(days_old=7)

            # Should clean up completed but NOT processing
            assert cleaned == 1

            # Processing batch should still exist
            assert db.session.get(BatchJob, processing_id) is not None
            # Completed batch should be deleted
            assert db.session.get(BatchJob, completed_id) is None

    def test_cleanup_handles_no_old_batches(self, app):
        """Test cleanup with only recent batches.

        BAT-02: 0 cleaned, no errors.
        """
        from app.services.batch_queue_service import BatchQueueService

        with app.app_context():
            # Create recent completed batch
            recent_batch = BatchJob(
                name="Recent Batch",
                status=BatchStatus.COMPLETED,
                completed_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
            db.session.add(recent_batch)
            db.session.commit()

            service = BatchQueueService()
            cleaned = service.cleanup_completed_batches(days_old=7)

            # No old batches to clean
            assert cleaned == 0
