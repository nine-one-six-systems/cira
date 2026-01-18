"""Tests for the Token Usage Tracking Service (Task 6.2)."""

import pytest
from datetime import datetime


class TestTokenCost:
    """Test TokenCost dataclass."""

    def test_token_cost_creation(self):
        """Test creating a TokenCost."""
        from app.services.token_tracker import TokenCost

        cost = TokenCost(
            input_tokens=1000,
            output_tokens=500,
            input_cost=0.003,
            output_cost=0.0075,
        )

        assert cost.input_tokens == 1000
        assert cost.output_tokens == 500
        assert cost.total_tokens == 1500
        assert abs(cost.total_cost - 0.0105) < 0.0001  # Floating point comparison

    def test_token_cost_to_dict(self):
        """Test TokenCost to_dict method."""
        from app.services.token_tracker import TokenCost

        cost = TokenCost(
            input_tokens=100,
            output_tokens=50,
            input_cost=0.0003,
            output_cost=0.00075,
        )

        result = cost.to_dict()

        assert result['input_tokens'] == 100
        assert result['output_tokens'] == 50
        assert result['total_tokens'] == 150
        assert 'input_cost' in result
        assert 'output_cost' in result
        assert 'total_cost' in result


class TestCompanyTokenUsage:
    """Test CompanyTokenUsage dataclass."""

    def test_company_token_usage_creation(self):
        """Test creating CompanyTokenUsage."""
        from app.services.token_tracker import CompanyTokenUsage, TokenCost

        usage = CompanyTokenUsage(
            company_id='test-id',
            total_input_tokens=5000,
            total_output_tokens=2500,
            total_cost=0.0525,
            by_call_type={},
            by_section={},
        )

        assert usage.company_id == 'test-id'
        assert usage.total_tokens == 7500
        assert usage.total_cost == 0.0525

    def test_company_token_usage_to_dict(self):
        """Test CompanyTokenUsage to_dict method."""
        from app.services.token_tracker import CompanyTokenUsage, TokenCost

        analysis_cost = TokenCost(
            input_tokens=1000,
            output_tokens=500,
            input_cost=0.003,
            output_cost=0.0075,
        )

        usage = CompanyTokenUsage(
            company_id='test-id',
            total_input_tokens=1000,
            total_output_tokens=500,
            total_cost=0.0105,
            by_call_type={'analysis': analysis_cost},
            by_section={'company_overview': analysis_cost},
        )

        result = usage.to_dict()

        assert result['total_tokens'] == 1500
        assert 'by_call_type' in result
        assert 'by_section' in result
        assert 'analysis' in result['by_call_type']


class TestTokenTrackerInit:
    """Test TokenTracker initialization."""

    def test_tracker_initializes(self):
        """Test that tracker initializes without error."""
        from app.services.token_tracker import TokenTracker

        tracker = TokenTracker()
        assert tracker is not None

    def test_global_instance_exists(self):
        """Test that global instance is available."""
        from app.services.token_tracker import token_tracker

        assert token_tracker is not None


class TestTokenTrackerCalculateCost:
    """Test cost calculation."""

    def test_calculate_cost_default_prices(self):
        """Test cost calculation with default prices."""
        from app.services.token_tracker import TokenTracker

        tracker = TokenTracker()

        # 1M tokens should cost $3 input, $15 output
        cost = tracker.calculate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )

        assert cost.input_tokens == 1_000_000
        assert cost.output_tokens == 1_000_000
        assert cost.input_cost == 3.0
        assert cost.output_cost == 15.0
        assert cost.total_cost == 18.0

    def test_calculate_cost_small_usage(self):
        """Test cost calculation for small usage."""
        from app.services.token_tracker import TokenTracker

        tracker = TokenTracker()

        # Small usage
        cost = tracker.calculate_cost(
            input_tokens=1000,
            output_tokens=500,
        )

        assert cost.total_tokens == 1500
        assert cost.total_cost < 0.02  # Very small cost

    def test_calculate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        from app.services.token_tracker import TokenTracker

        tracker = TokenTracker()

        cost = tracker.calculate_cost(
            input_tokens=0,
            output_tokens=0,
        )

        assert cost.total_tokens == 0
        assert cost.total_cost == 0.0


class TestTokenTrackerRecordUsage:
    """Test recording token usage."""

    def test_record_usage_creates_record(self, app):
        """Test that record_usage creates a database record."""
        from app.services.token_tracker import token_tracker
        from app.models import Company, TokenUsage
        from app import db

        with app.app_context():
            # Create a test company
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.commit()

            # Record usage
            result = token_tracker.record_usage(
                company_id=company.id,
                api_call_type='analysis',
                input_tokens=1000,
                output_tokens=500,
                section='company_overview',
            )

            # Verify result
            assert result['company_id'] == company.id
            assert result['input_tokens'] == 1000
            assert result['output_tokens'] == 500
            assert 'total_cost' in result

            # Verify database record
            usage = TokenUsage.query.filter_by(company_id=company.id).first()
            assert usage is not None
            assert usage.input_tokens == 1000
            assert usage.output_tokens == 500

    def test_record_usage_updates_company_totals(self, app):
        """Test that record_usage updates company totals."""
        from app.services.token_tracker import token_tracker
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
                total_tokens_used=0,
                estimated_cost=0.0,
            )
            db.session.add(company)
            db.session.commit()

            # Record usage
            token_tracker.record_usage(
                company_id=company.id,
                api_call_type='analysis',
                input_tokens=1000,
                output_tokens=500,
            )

            # Refresh company
            db.session.refresh(company)

            # Company totals should be updated
            assert company.total_tokens_used == 1500
            assert company.estimated_cost > 0

    def test_record_usage_with_different_call_types(self, app):
        """Test recording different call types."""
        from app.services.token_tracker import token_tracker
        from app.models import Company, TokenUsage
        from app.models.enums import ApiCallType
        from app import db

        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.commit()

            # Record different types
            for call_type in ['analysis', 'extraction', 'summarization']:
                token_tracker.record_usage(
                    company_id=company.id,
                    api_call_type=call_type,
                    input_tokens=100,
                    output_tokens=50,
                )

            # Should have 3 records
            usages = TokenUsage.query.filter_by(company_id=company.id).all()
            assert len(usages) == 3


class TestTokenTrackerGetCompanyUsage:
    """Test getting aggregated company usage."""

    def test_get_company_usage_empty(self, app):
        """Test getting usage for company with no records."""
        from app.services.token_tracker import token_tracker
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.commit()

            usage = token_tracker.get_company_usage(company.id)

            assert usage.total_tokens == 0
            assert usage.total_cost == 0.0

    def test_get_company_usage_aggregates_correctly(self, app):
        """Test that get_company_usage aggregates correctly."""
        from app.services.token_tracker import token_tracker
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.commit()

            # Record multiple usages
            token_tracker.record_usage(
                company_id=company.id,
                api_call_type='analysis',
                input_tokens=1000,
                output_tokens=500,
                section='company_overview',
            )
            token_tracker.record_usage(
                company_id=company.id,
                api_call_type='analysis',
                input_tokens=800,
                output_tokens=400,
                section='business_model',
            )

            usage = token_tracker.get_company_usage(company.id)

            assert usage.total_input_tokens == 1800
            assert usage.total_output_tokens == 900
            assert usage.total_tokens == 2700
            assert 'analysis' in usage.by_call_type
            assert 'company_overview' in usage.by_section


class TestTokenTrackerGetUsageHistory:
    """Test getting usage history."""

    def test_get_usage_history(self, app):
        """Test getting usage history."""
        from app.services.token_tracker import token_tracker
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.commit()

            # Record usages
            for i in range(5):
                token_tracker.record_usage(
                    company_id=company.id,
                    api_call_type='analysis',
                    input_tokens=100 * (i + 1),
                    output_tokens=50 * (i + 1),
                    section=f'section_{i}',
                )

            history = token_tracker.get_usage_history(company.id, limit=10)

            assert len(history) == 5
            assert 'timestamp' in history[0]
            assert 'total_tokens' in history[0]

    def test_get_usage_history_limit(self, app):
        """Test that limit works correctly."""
        from app.services.token_tracker import token_tracker
        from app.models import Company
        from app import db

        with app.app_context():
            company = Company(
                company_name='Test Company',
                website_url='https://test.com',
            )
            db.session.add(company)
            db.session.commit()

            # Record many usages
            for i in range(10):
                token_tracker.record_usage(
                    company_id=company.id,
                    api_call_type='analysis',
                    input_tokens=100,
                    output_tokens=50,
                )

            history = token_tracker.get_usage_history(company.id, limit=3)

            assert len(history) == 3


class TestTokenTrackerEstimateRemainingCost:
    """Test remaining cost estimation."""

    def test_estimate_remaining_cost(self):
        """Test estimating remaining cost."""
        from app.services.token_tracker import TokenTracker

        tracker = TokenTracker()

        # Estimate for 5 remaining sections
        cost = tracker.estimate_remaining_cost(
            company_id='test-id',
            remaining_sections=['s1', 's2', 's3', 's4', 's5'],
            avg_tokens_per_section=2000,
        )

        # Should estimate some cost
        assert cost > 0

    def test_estimate_remaining_cost_no_sections(self):
        """Test estimate with no remaining sections."""
        from app.services.token_tracker import TokenTracker

        tracker = TokenTracker()

        cost = tracker.estimate_remaining_cost(
            company_id='test-id',
            remaining_sections=[],
        )

        assert cost == 0.0
