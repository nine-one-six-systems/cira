"""Page-related Pydantic schemas."""

from datetime import datetime

from pydantic import Field

from app.models.enums import PageType
from app.schemas.base import CamelCaseModel


class PageItem(CamelCaseModel):
    """Page item in responses."""

    id: str
    url: str
    page_type: PageType = Field(..., alias='pageType')
    crawled_at: datetime = Field(..., alias='crawledAt')
    is_external: bool = Field(..., alias='isExternal')


class PageQueryParams(CamelCaseModel):
    """Query parameters for page list endpoint."""

    page_type: PageType | None = Field(default=None, alias='pageType')
    page: int = Field(default=1, ge=1)
    page_size: int = Field(
        default=50,
        ge=1,
        le=100,
        alias='pageSize'
    )
