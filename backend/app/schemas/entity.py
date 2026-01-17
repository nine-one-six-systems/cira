"""Entity-related Pydantic schemas."""

from datetime import datetime

from pydantic import Field

from app.models.enums import EntityType
from app.schemas.base import CamelCaseModel


class EntityItem(CamelCaseModel):
    """Entity item in responses."""

    id: str
    entity_type: EntityType = Field(..., alias='entityType')
    entity_value: str = Field(..., alias='entityValue')
    context_snippet: str | None = Field(default=None, alias='contextSnippet')
    source_url: str | None = Field(default=None, alias='sourceUrl')
    confidence_score: float = Field(..., alias='confidenceScore')


class EntityQueryParams(CamelCaseModel):
    """Query parameters for entity list endpoint."""

    type: EntityType | None = None
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        alias='minConfidence'
    )
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=100,
        alias='pageSize'
    )
