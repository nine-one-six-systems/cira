"""Token Usage Tracking Service.

Task 6.2: Token Usage Tracking Service
- Record input/output tokens per call (FR-TOK-001)
- Aggregate per company (FR-TOK-002)
- Calculate cost (FR-TOK-004)
- Store in TokenUsage table
"""

import logging
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any

from flask import current_app

logger = logging.getLogger(__name__)


@dataclass
class TokenCost:
    """Token usage with cost calculation."""
    input_tokens: int
    output_tokens: int
    input_cost: float
    output_cost: float

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens

    @property
    def total_cost(self) -> float:
        """Total cost in USD."""
        return self.input_cost + self.output_cost

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'total_tokens': self.total_tokens,
            'input_cost': round(self.input_cost, 6),
            'output_cost': round(self.output_cost, 6),
            'total_cost': round(self.total_cost, 6),
        }


@dataclass
class CompanyTokenUsage:
    """Aggregated token usage for a company."""
    company_id: str
    total_input_tokens: int
    total_output_tokens: int
    total_cost: float
    by_call_type: dict[str, TokenCost]
    by_section: dict[str, TokenCost]

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.total_input_tokens + self.total_output_tokens

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'total_tokens': self.total_tokens,
            'total_input_tokens': self.total_input_tokens,
            'total_output_tokens': self.total_output_tokens,
            'total_cost': round(self.total_cost, 6),
            'by_call_type': {k: v.to_dict() for k, v in self.by_call_type.items()},
            'by_section': {k: v.to_dict() for k, v in self.by_section.items()},
        }


class TokenTracker:
    """
    Service for tracking token usage and costs.

    Provides:
    - Per-call token recording
    - Per-company aggregation
    - Real-time cost calculation
    - Historical usage queries
    """

    # Default pricing (Claude 3 Sonnet pricing as of 2024)
    # Prices are per million tokens
    DEFAULT_INPUT_PRICE = 3.00   # $3.00 per 1M input tokens
    DEFAULT_OUTPUT_PRICE = 15.00  # $15.00 per 1M output tokens

    def __init__(self):
        """Initialize the token tracker."""
        pass

    def _get_prices(self) -> tuple[float, float]:
        """Get configured token prices."""
        try:
            input_price = current_app.config.get(
                'CLAUDE_INPUT_TOKEN_PRICE', self.DEFAULT_INPUT_PRICE
            )
            output_price = current_app.config.get(
                'CLAUDE_OUTPUT_TOKEN_PRICE', self.DEFAULT_OUTPUT_PRICE
            )
        except RuntimeError:
            # Outside of app context
            input_price = self.DEFAULT_INPUT_PRICE
            output_price = self.DEFAULT_OUTPUT_PRICE

        return input_price, output_price

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int
    ) -> TokenCost:
        """
        Calculate cost for a given token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            TokenCost with usage and cost breakdown
        """
        input_price, output_price = self._get_prices()

        # Calculate costs (prices are per million tokens)
        input_cost = (input_tokens * input_price) / 1_000_000
        output_cost = (output_tokens * output_price) / 1_000_000

        return TokenCost(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
        )

    def record_usage(
        self,
        company_id: str,
        api_call_type: str,
        input_tokens: int,
        output_tokens: int,
        section: str | None = None,
    ) -> dict[str, Any]:
        """
        Record token usage for an API call.

        Args:
            company_id: UUID of the company
            api_call_type: Type of API call (extraction, summarization, analysis)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            section: Optional section identifier (e.g., 'executive_summary')

        Returns:
            Dict with recorded usage and cost
        """
        from app import db
        from app.models import TokenUsage, Company
        from app.models.enums import ApiCallType

        # Calculate cost
        cost = self.calculate_cost(input_tokens, output_tokens)

        # Map call type string to enum
        try:
            call_type_enum = ApiCallType(api_call_type.lower())
        except ValueError:
            logger.warning(f"Unknown API call type: {api_call_type}, using ANALYSIS")
            call_type_enum = ApiCallType.ANALYSIS

        # Create token usage record
        usage = TokenUsage(
            company_id=company_id,
            api_call_type=call_type_enum,
            section=section,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            timestamp=datetime.now(UTC),
        )
        db.session.add(usage)

        # Update company totals
        company = db.session.get(Company, company_id)
        if company:
            company.total_tokens_used = (company.total_tokens_used or 0) + cost.total_tokens
            company.estimated_cost = (company.estimated_cost or 0.0) + cost.total_cost

        db.session.commit()

        logger.info(
            f"Recorded token usage for company {company_id}: "
            f"{cost.total_tokens} tokens, ${cost.total_cost:.6f}"
        )

        return {
            'company_id': company_id,
            'api_call_type': api_call_type,
            'section': section,
            **cost.to_dict(),
            'timestamp': usage.timestamp.isoformat(),
        }

    def get_company_usage(self, company_id: str) -> CompanyTokenUsage:
        """
        Get aggregated token usage for a company.

        Args:
            company_id: UUID of the company

        Returns:
            CompanyTokenUsage with aggregated data
        """
        from app.models import TokenUsage

        # Query all usage records for the company
        usages = TokenUsage.query.filter_by(company_id=company_id).all()

        # Aggregate totals
        total_input = 0
        total_output = 0
        by_call_type: dict[str, dict] = {}
        by_section: dict[str, dict] = {}

        for usage in usages:
            total_input += usage.input_tokens
            total_output += usage.output_tokens

            # Aggregate by call type
            call_type = usage.api_call_type.value
            if call_type not in by_call_type:
                by_call_type[call_type] = {'input': 0, 'output': 0}
            by_call_type[call_type]['input'] += usage.input_tokens
            by_call_type[call_type]['output'] += usage.output_tokens

            # Aggregate by section
            if usage.section:
                if usage.section not in by_section:
                    by_section[usage.section] = {'input': 0, 'output': 0}
                by_section[usage.section]['input'] += usage.input_tokens
                by_section[usage.section]['output'] += usage.output_tokens

        # Calculate costs
        total_cost = self.calculate_cost(total_input, total_output)

        by_call_type_costs = {
            k: self.calculate_cost(v['input'], v['output'])
            for k, v in by_call_type.items()
        }
        by_section_costs = {
            k: self.calculate_cost(v['input'], v['output'])
            for k, v in by_section.items()
        }

        return CompanyTokenUsage(
            company_id=company_id,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cost=total_cost.total_cost,
            by_call_type=by_call_type_costs,
            by_section=by_section_costs,
        )

    def get_usage_history(
        self,
        company_id: str,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        Get detailed usage history for a company.

        Args:
            company_id: UUID of the company
            limit: Maximum number of records to return

        Returns:
            List of usage records with timestamps
        """
        from app.models import TokenUsage

        usages = (
            TokenUsage.query
            .filter_by(company_id=company_id)
            .order_by(TokenUsage.timestamp.desc())
            .limit(limit)
            .all()
        )

        return [
            {
                'id': str(usage.id),
                'api_call_type': usage.api_call_type.value,
                'section': usage.section,
                'input_tokens': usage.input_tokens,
                'output_tokens': usage.output_tokens,
                'total_tokens': usage.input_tokens + usage.output_tokens,
                **self.calculate_cost(usage.input_tokens, usage.output_tokens).to_dict(),
                'timestamp': usage.timestamp.isoformat(),
            }
            for usage in usages
        ]

    def estimate_remaining_cost(
        self,
        company_id: str,
        remaining_sections: list[str],
        avg_tokens_per_section: int = 2000,
    ) -> float:
        """
        Estimate remaining cost for incomplete analysis.

        Args:
            company_id: UUID of the company
            remaining_sections: List of sections still to be analyzed
            avg_tokens_per_section: Average tokens per section (input + output)

        Returns:
            Estimated remaining cost in USD
        """
        if not remaining_sections:
            return 0.0

        # Estimate input/output split (roughly 60% input, 40% output for analysis)
        total_estimated_tokens = len(remaining_sections) * avg_tokens_per_section
        estimated_input = int(total_estimated_tokens * 0.6)
        estimated_output = int(total_estimated_tokens * 0.4)

        cost = self.calculate_cost(estimated_input, estimated_output)
        return cost.total_cost


# Global tracker instance
token_tracker = TokenTracker()
