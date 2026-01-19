"""API Integration tests for Token Usage endpoint.

These tests verify the GET /companies/:id/tokens endpoint returns
token usage breakdown with per-section counts, totals, and cost estimation.

Requirements verified:
- ANA-09: Token tracking per API call type
- ANA-10: Cost estimation exposure via API
"""

from datetime import datetime, timezone, timedelta

import pytest
from app import db
from app.models.company import Company, TokenUsage
from app.models.enums import ApiCallType


def create_token_usage(
    company_id: str,
    section: str | None,
    input_tokens: int,
    output_tokens: int,
    api_call_type: ApiCallType = ApiCallType.ANALYSIS,
    timestamp: datetime | None = None
) -> TokenUsage:
    """Helper function to create a TokenUsage record.

    Args:
        company_id: Company UUID
        section: Section name (e.g., 'executive_summary')
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        api_call_type: Type of API call (default: ANALYSIS)
        timestamp: Optional timestamp (default: now)

    Returns:
        TokenUsage: Created record (not committed)
    """
    usage = TokenUsage(
        company_id=company_id,
        section=section,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        api_call_type=api_call_type,
        timestamp=timestamp or datetime.now(timezone.utc)
    )
    db.session.add(usage)
    return usage


class TestGetTokenUsage:
    """Tests for GET /api/v1/companies/:id/tokens endpoint."""

    def test_get_tokens_returns_empty_for_new_company(self, client, app):
        """
        ANA-09: New company with no analysis should return empty token usage.
        Expected: totalTokens=0, estimatedCost=0, byApiCall=[]
        """
        with app.app_context():
            company = Company(
                company_name='No Tokens Corp',
                website_url='https://no-tokens.com'
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data']['totalTokens'] == 0
        assert data['data']['estimatedCost'] == 0.0
        assert data['data']['byApiCall'] == []

    def test_get_tokens_returns_usage_breakdown(self, client, app):
        """
        ANA-09: Token usage breakdown returned with per-section counts.
        Create 3 sections, verify all appear in response.
        """
        with app.app_context():
            company = Company(
                company_name='Token Breakdown Corp',
                website_url='https://token-breakdown.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 3 token usage records for different sections
            create_token_usage(company.id, 'executive_summary', 500, 300)
            create_token_usage(company.id, 'company_overview', 400, 250)
            create_token_usage(company.id, 'business_model', 600, 400)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        by_api_call = data['data']['byApiCall']
        assert len(by_api_call) == 3

        # Verify each item has required fields
        for item in by_api_call:
            assert 'section' in item
            assert 'inputTokens' in item
            assert 'outputTokens' in item

        # Verify all sections present
        sections = {item['section'] for item in by_api_call}
        assert sections == {'executive_summary', 'company_overview', 'business_model'}

    def test_get_tokens_calculates_totals(self, client, app):
        """
        ANA-09: Total token counts calculated correctly across sections.
        Section1: 500 in, 300 out | Section2: 600 in, 400 out
        Expected: totalInputTokens=1100, totalOutputTokens=700, totalTokens=1800
        """
        with app.app_context():
            company = Company(
                company_name='Token Totals Corp',
                website_url='https://token-totals.com'
            )
            db.session.add(company)
            db.session.flush()

            create_token_usage(company.id, 'section1', 500, 300)
            create_token_usage(company.id, 'section2', 600, 400)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        assert data['data']['totalInputTokens'] == 1100
        assert data['data']['totalOutputTokens'] == 700
        assert data['data']['totalTokens'] == 1800

    def test_get_tokens_includes_estimated_cost(self, client, app):
        """
        ANA-10: Response includes estimatedCost field from company.
        Cost should be a positive number when tokens have been used.
        """
        with app.app_context():
            company = Company(
                company_name='Token Cost Corp',
                website_url='https://token-cost.com',
                estimated_cost=0.0042  # Set a known cost
            )
            db.session.add(company)
            db.session.flush()

            create_token_usage(company.id, 'summary', 1000, 500)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        assert 'estimatedCost' in data['data']
        assert isinstance(data['data']['estimatedCost'], (int, float))
        assert data['data']['estimatedCost'] == 0.0042

    def test_get_tokens_sections_ordered_by_timestamp(self, client, app):
        """
        ANA-09: Token records returned in chronological order (newest first).
        """
        with app.app_context():
            company = Company(
                company_name='Token Order Corp',
                website_url='https://token-order.com'
            )
            db.session.add(company)
            db.session.flush()

            # Create records with specific timestamps
            base_time = datetime.now(timezone.utc)
            create_token_usage(
                company.id, 'oldest_section', 100, 50,
                timestamp=base_time - timedelta(hours=2)
            )
            create_token_usage(
                company.id, 'middle_section', 200, 100,
                timestamp=base_time - timedelta(hours=1)
            )
            create_token_usage(
                company.id, 'newest_section', 300, 150,
                timestamp=base_time
            )
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        by_api_call = data['data']['byApiCall']
        # API orders by timestamp DESC, so newest first
        assert by_api_call[0]['section'] == 'newest_section'
        assert by_api_call[1]['section'] == 'middle_section'
        assert by_api_call[2]['section'] == 'oldest_section'


class TestTokensResponseFormat:
    """Tests for token usage response format validation."""

    def test_response_includes_all_required_fields(self, client, app):
        """
        ANA-09/ANA-10: Response has all required fields.
        Required: totalInputTokens, totalOutputTokens, totalTokens, estimatedCost, byApiCall
        """
        with app.app_context():
            company = Company(
                company_name='Format Test Corp',
                website_url='https://format-test.com',
                estimated_cost=0.01
            )
            db.session.add(company)
            db.session.flush()

            create_token_usage(company.id, 'test_section', 100, 50)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()['data']

        required_fields = [
            'totalInputTokens',
            'totalOutputTokens',
            'totalTokens',
            'estimatedCost',
            'byApiCall'
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_section_response_includes_api_call_type(self, client, app):
        """
        ANA-09: Each section includes callType field.
        """
        with app.app_context():
            company = Company(
                company_name='Call Type Corp',
                website_url='https://call-type.com'
            )
            db.session.add(company)
            db.session.flush()

            create_token_usage(
                company.id, 'analysis_section', 200, 100,
                api_call_type=ApiCallType.ANALYSIS
            )
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        by_api_call = data['data']['byApiCall']
        assert len(by_api_call) == 1
        assert 'callType' in by_api_call[0]
        assert by_api_call[0]['callType'] == 'analysis'

    def test_section_response_includes_timestamp(self, client, app):
        """
        ANA-09: Each section includes timestamp in ISO format.
        """
        with app.app_context():
            company = Company(
                company_name='Timestamp Corp',
                website_url='https://timestamp.com'
            )
            db.session.add(company)
            db.session.flush()

            create_token_usage(company.id, 'timed_section', 300, 150)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        by_api_call = data['data']['byApiCall']
        assert len(by_api_call) == 1
        assert 'timestamp' in by_api_call[0]

        # Verify ISO format (should be parseable)
        timestamp_str = by_api_call[0]['timestamp']
        assert isinstance(timestamp_str, str)
        # ISO format contains 'T' and ends with 'Z' or has timezone
        assert 'T' in timestamp_str or '-' in timestamp_str

    def test_cost_formatted_as_decimal(self, client, app):
        """
        ANA-10: estimatedCost is a decimal with reasonable precision.
        """
        with app.app_context():
            company = Company(
                company_name='Decimal Cost Corp',
                website_url='https://decimal-cost.com',
                estimated_cost=0.00421234  # 8 decimal places
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        estimated_cost = data['data']['estimatedCost']
        assert isinstance(estimated_cost, float)
        # Should preserve precision (at least 4 decimal places)
        assert abs(estimated_cost - 0.00421234) < 0.0001


class TestTokensErrorHandling:
    """Tests for token usage endpoint error handling."""

    def test_get_tokens_company_not_found(self, client):
        """
        ANA-09: Non-existent company returns 404 with NOT_FOUND code.
        """
        # Use a valid UUID format that doesn't exist
        response = client.get('/api/v1/companies/00000000-0000-0000-0000-000000000000/tokens')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_get_tokens_invalid_uuid_format(self, client):
        """
        ANA-09: Invalid UUID format returns 404 (not 500).
        """
        response = client.get('/api/v1/companies/not-a-valid-uuid/tokens')

        # Should return 404, not 500 server error
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'


class TestTokensAggregation:
    """Tests for token usage aggregation and calculation."""

    def test_aggregates_multiple_calls_per_section(self, client, app):
        """
        ANA-09: Multiple API calls for same section appear separately.
        E.g., retry scenarios where same section is analyzed twice.
        """
        with app.app_context():
            company = Company(
                company_name='Multi Call Corp',
                website_url='https://multi-call.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 2 token records for same section (retry scenario)
            base_time = datetime.now(timezone.utc)
            create_token_usage(
                company.id, 'summary', 500, 300,
                timestamp=base_time - timedelta(minutes=5)
            )
            create_token_usage(
                company.id, 'summary', 600, 400,
                timestamp=base_time  # Retry
            )
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        # Both records should appear (chronologically)
        by_api_call = data['data']['byApiCall']
        assert len(by_api_call) == 2

        # Verify totals include both
        assert data['data']['totalInputTokens'] == 1100
        assert data['data']['totalOutputTokens'] == 700

    def test_handles_large_token_counts(self, client, app):
        """
        ANA-09: Large token values (100k+) handled without overflow.
        """
        with app.app_context():
            company = Company(
                company_name='Large Tokens Corp',
                website_url='https://large-tokens.com'
            )
            db.session.add(company)
            db.session.flush()

            # Create records with large token counts
            create_token_usage(company.id, 'large_section_1', 150000, 75000)
            create_token_usage(company.id, 'large_section_2', 200000, 100000)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        # Verify no overflow or truncation
        assert data['data']['totalInputTokens'] == 350000
        assert data['data']['totalOutputTokens'] == 175000
        assert data['data']['totalTokens'] == 525000

    def test_cost_aggregates_across_sections(self, client, app):
        """
        ANA-10: Estimated cost reflects total across all sections.
        Cost is stored on company, not calculated from sections.
        """
        with app.app_context():
            company = Company(
                company_name='Aggregated Cost Corp',
                website_url='https://aggregated-cost.com',
                estimated_cost=0.0525  # Total cost for all sections
            )
            db.session.add(company)
            db.session.flush()

            # Create 5 sections
            for i in range(5):
                create_token_usage(company.id, f'section_{i}', 200, 100)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        # Verify 5 sections present
        assert len(data['data']['byApiCall']) == 5

        # Verify aggregated cost
        assert data['data']['estimatedCost'] == 0.0525

    def test_handles_different_api_call_types(self, client, app):
        """
        ANA-09: Different API call types (extraction, summarization, analysis) tracked.
        """
        with app.app_context():
            company = Company(
                company_name='Mixed Call Types Corp',
                website_url='https://mixed-types.com'
            )
            db.session.add(company)
            db.session.flush()

            # Create records with different call types
            create_token_usage(
                company.id, 'entity_extraction', 100, 50,
                api_call_type=ApiCallType.EXTRACTION
            )
            create_token_usage(
                company.id, 'page_summary', 200, 100,
                api_call_type=ApiCallType.SUMMARIZATION
            )
            create_token_usage(
                company.id, 'full_analysis', 500, 300,
                api_call_type=ApiCallType.ANALYSIS
            )
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        by_api_call = data['data']['byApiCall']
        assert len(by_api_call) == 3

        # Verify call types present
        call_types = {item['callType'] for item in by_api_call}
        assert call_types == {'extraction', 'summarization', 'analysis'}

    def test_handles_null_section(self, client, app):
        """
        ANA-09: Token records without a section (null) are handled gracefully.
        """
        with app.app_context():
            company = Company(
                company_name='Null Section Corp',
                website_url='https://null-section.com'
            )
            db.session.add(company)
            db.session.flush()

            # Create record with null section
            create_token_usage(company.id, None, 300, 150)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/tokens')

        assert response.status_code == 200
        data = response.get_json()

        by_api_call = data['data']['byApiCall']
        assert len(by_api_call) == 1
        assert by_api_call[0]['section'] is None
        assert by_api_call[0]['inputTokens'] == 300
        assert by_api_call[0]['outputTokens'] == 150
