"""Base Pydantic schemas and utilities."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field


T = TypeVar('T')


class CamelCaseModel(BaseModel):
    """Base model with camelCase serialization."""

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class ApiResponse(CamelCaseModel, Generic[T]):
    """Standard API success response wrapper."""

    success: bool = True
    data: T


class ApiError(CamelCaseModel):
    """API error details."""

    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiErrorResponse(CamelCaseModel):
    """Standard API error response wrapper."""

    success: bool = False
    error: ApiError


class PaginationMeta(CamelCaseModel):
    """Pagination metadata."""

    total: int
    page: int
    page_size: int = Field(..., alias='pageSize')
    total_pages: int = Field(..., alias='totalPages')


class PaginatedResponse(CamelCaseModel, Generic[T]):
    """Paginated API response wrapper."""

    success: bool = True
    data: list[T]
    meta: PaginationMeta
