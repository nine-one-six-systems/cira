"""Token usage Pydantic schemas."""

from datetime import datetime

from pydantic import Field

from app.models.enums import ApiCallType
from app.schemas.base import CamelCaseModel


class TokenUsageItem(CamelCaseModel):
    """Individual token usage record."""

    call_type: ApiCallType = Field(..., alias='callType')
    section: str | None = None
    input_tokens: int = Field(..., alias='inputTokens')
    output_tokens: int = Field(..., alias='outputTokens')
    timestamp: datetime


class TokenUsageResponse(CamelCaseModel):
    """Token usage breakdown response."""

    total_tokens: int = Field(..., alias='totalTokens')
    total_input_tokens: int = Field(..., alias='totalInputTokens')
    total_output_tokens: int = Field(..., alias='totalOutputTokens')
    estimated_cost: float = Field(..., alias='estimatedCost')
    by_api_call: list[TokenUsageItem] = Field(..., alias='byApiCall')
