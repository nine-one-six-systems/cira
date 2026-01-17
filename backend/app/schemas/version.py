"""Analysis version Pydantic schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from app.schemas.base import CamelCaseModel


class VersionItem(CamelCaseModel):
    """Analysis version in list response."""

    analysis_id: str = Field(..., alias='analysisId')
    version_number: int = Field(..., alias='versionNumber')
    created_at: datetime = Field(..., alias='createdAt')
    tokens_used: int = Field(..., alias='tokensUsed')


class VersionChange(CamelCaseModel):
    """A single change between versions."""

    field: str
    previous_value: Any | None = Field(..., alias='previousValue')
    current_value: Any | None = Field(..., alias='currentValue')
    change_type: Literal['added', 'removed', 'modified'] = Field(..., alias='changeType')


class VersionChanges(CamelCaseModel):
    """Changes grouped by category."""

    team: list[VersionChange] = Field(default_factory=list)
    products: list[VersionChange] = Field(default_factory=list)
    content: list[VersionChange] = Field(default_factory=list)


class CompareVersionsResponse(CamelCaseModel):
    """Response for version comparison."""

    company_id: str = Field(..., alias='companyId')
    previous_version: int = Field(..., alias='previousVersion')
    current_version: int = Field(..., alias='currentVersion')
    changes: VersionChanges
    significant_changes: bool = Field(..., alias='significantChanges')


class CompareQueryParams(CamelCaseModel):
    """Query parameters for version comparison."""

    version1: int = Field(..., ge=1)
    version2: int = Field(..., ge=1)
