"""Tests for Batch Upload API endpoints."""

import io
import pytest
from app import db
from app.models.company import Company


def create_csv_file(content: str, filename: str = 'test.csv'):
    """Create a file-like object for CSV content."""
    return (io.BytesIO(content.encode('utf-8')), filename)


class TestBatchUpload:
    """Tests for POST /api/v1/companies/batch."""

    def test_batch_upload_valid_csv(self, client):
        """Test uploading a valid CSV creates all companies."""
        csv_content = """company_name,website_url,industry
Acme Corp,https://acme.com,Technology
Beta Inc,https://beta.io,Healthcare
Gamma Ltd,https://gamma.co,Finance"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['totalCount'] == 3
        assert data['data']['successful'] == 3
        assert data['data']['failed'] == 0

        # Verify all companies have IDs
        for company in data['data']['companies']:
            assert company['companyId'] is not None
            assert company['error'] is None

    def test_batch_upload_with_errors(self, client):
        """Test batch upload with some invalid rows returns partial success."""
        csv_content = """company_name,website_url,industry
Valid Corp,https://valid.com,Technology
,https://noname.com,Healthcare
No URL Corp,,Finance
Invalid URL Corp,not-a-valid-url,Tech"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['totalCount'] == 4
        assert data['data']['successful'] == 1
        assert data['data']['failed'] == 3

        # Check specific results
        companies = data['data']['companies']
        assert companies[0]['companyId'] is not None  # Valid
        assert companies[1]['error'] == 'Company name is required'
        assert companies[2]['error'] == 'URL is required'
        assert 'Invalid URL' in companies[3]['error']

    def test_batch_upload_missing_columns(self, client):
        """Test batch upload with missing required columns returns 400."""
        csv_content = """company_name,industry
Acme Corp,Technology
Beta Inc,Healthcare"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert 'website_url' in data['error']['message']

    def test_batch_upload_no_file(self, client):
        """Test batch upload without file returns 400."""
        response = client.post(
            '/api/v1/companies/batch',
            data={},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_batch_upload_wrong_file_type(self, client):
        """Test batch upload with non-CSV file returns 400."""
        response = client.post(
            '/api/v1/companies/batch',
            data={'file': (io.BytesIO(b'test content'), 'test.txt')},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_ERROR'
        assert 'CSV' in data['error']['message']

    def test_batch_upload_duplicate_url_in_database(self, client, app):
        """Test batch upload detects existing URLs."""
        # Create existing company
        with app.app_context():
            company = Company(
                company_name='Existing Corp',
                website_url='https://existing.com'
            )
            db.session.add(company)
            db.session.commit()

        csv_content = """company_name,website_url,industry
New Corp,https://new.com,Technology
Duplicate Corp,https://existing.com,Healthcare"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1
        assert data['data']['failed'] == 1
        assert 'already exists' in data['data']['companies'][1]['error']

    def test_batch_upload_duplicate_url_in_batch(self, client):
        """Test batch upload detects duplicate URLs within same batch."""
        csv_content = """company_name,website_url,industry
First Corp,https://same.com,Technology
Second Corp,https://same.com,Healthcare"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1
        assert data['data']['failed'] == 1
        assert 'Duplicate URL' in data['data']['companies'][1]['error']

    def test_batch_upload_100_plus_rows(self, client):
        """Test batch upload handles 100+ rows successfully."""
        rows = ['company_name,website_url,industry']
        for i in range(105):
            rows.append(f'Company {i},https://company{i}.com,Tech')

        csv_content = '\n'.join(rows)

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['totalCount'] == 105
        assert data['data']['successful'] == 105
        assert data['data']['failed'] == 0

    def test_batch_upload_empty_csv(self, client):
        """Test batch upload with empty CSV returns 400."""
        csv_content = ""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['error']['code'] == 'VALIDATION_ERROR'

    def test_batch_upload_headers_only(self, client):
        """Test batch upload with only headers returns empty success."""
        csv_content = "company_name,website_url,industry"

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['totalCount'] == 0
        assert data['data']['successful'] == 0
        assert data['data']['failed'] == 0

    def test_batch_upload_url_without_protocol(self, client):
        """Test batch upload handles URLs without protocol."""
        csv_content = """company_name,website_url,industry
Acme Corp,acme.com,Technology"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 1

    def test_batch_upload_optional_industry(self, client):
        """Test batch upload works with empty industry field."""
        csv_content = """company_name,website_url,industry
Acme Corp,https://acme.com,
Beta Inc,https://beta.io,Healthcare"""

        response = client.post(
            '/api/v1/companies/batch',
            data={'file': create_csv_file(csv_content)},
            content_type='multipart/form-data'
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data['data']['successful'] == 2


class TestTemplateDownload:
    """Tests for GET /api/v1/companies/template."""

    def test_download_template(self, client):
        """Test downloading CSV template."""
        response = client.get('/api/v1/companies/template')

        assert response.status_code == 200
        assert response.content_type == 'text/csv; charset=utf-8'
        assert 'attachment' in response.headers['Content-Disposition']
        assert 'company_template.csv' in response.headers['Content-Disposition']

        # Verify template content
        content = response.data.decode('utf-8')
        assert 'company_name' in content
        assert 'website_url' in content
        assert 'industry' in content

    def test_template_has_example_rows(self, client):
        """Test template includes example rows."""
        response = client.get('/api/v1/companies/template')
        content = response.data.decode('utf-8')

        # Should have header + at least one example row
        lines = [line for line in content.strip().split('\n') if line]
        assert len(lines) >= 2
