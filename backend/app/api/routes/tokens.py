"""Token usage API route."""

from app import db
from app.api import api_bp
from app.api.routes.companies import make_error_response, make_success_response
from app.models.company import Company, TokenUsage
from app.schemas import TokenUsageItem, TokenUsageResponse


@api_bp.route('/companies/<company_id>/tokens', methods=['GET'])
def get_token_usage(company_id: str):
    """Get token usage breakdown for a company."""
    company = db.session.get(Company, company_id)
    if not company:
        return make_error_response('NOT_FOUND', 'Company not found', status=404)

    # Get all token usage records
    usages = (
        TokenUsage.query
        .filter_by(company_id=company_id)
        .order_by(TokenUsage.timestamp.desc())
        .all()
    )

    # Calculate totals
    total_input_tokens = sum(u.input_tokens for u in usages)
    total_output_tokens = sum(u.output_tokens for u in usages)
    total_tokens = total_input_tokens + total_output_tokens

    # Build usage items
    items = []
    for u in usages:
        item = TokenUsageItem(
            callType=u.api_call_type,
            section=u.section,
            inputTokens=u.input_tokens,
            outputTokens=u.output_tokens,
            timestamp=u.timestamp
        )
        items.append(item)

    response = TokenUsageResponse(
        totalTokens=total_tokens,
        totalInputTokens=total_input_tokens,
        totalOutputTokens=total_output_tokens,
        estimatedCost=company.estimated_cost,
        byApiCall=[i.model_dump(by_alias=True, mode='json') for i in items]
    )

    return make_success_response(response.model_dump(by_alias=True, mode='json'))
