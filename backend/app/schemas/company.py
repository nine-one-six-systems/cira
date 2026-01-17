"""Company-related Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import Field, HttpUrl, field_validator

from app.models.enums import AnalysisMode, CompanyStatus, ProcessingPhase
from app.schemas.base import CamelCaseModel


# Request Schemas

class CompanyConfig(CamelCaseModel):
    """Company analysis configuration."""

    analysis_mode: AnalysisMode = Field(
        default=AnalysisMode.THOROUGH,
        alias='analysisMode'
    )
    time_limit_minutes: int = Field(
        default=30,
        ge=5,
        le=120,
        alias='timeLimitMinutes'
    )
    max_pages: int = Field(
        default=100,
        ge=10,
        le=500,
        alias='maxPages'
    )
    max_depth: int = Field(
        default=3,
        ge=1,
        le=5,
        alias='maxDepth'
    )
    follow_linkedin: bool = Field(default=True, alias='followLinkedIn')
    follow_twitter: bool = Field(default=True, alias='followTwitter')
    follow_facebook: bool = Field(default=False, alias='followFacebook')
    exclusion_patterns: list[str] = Field(
        default_factory=list,
        alias='exclusionPatterns'
    )


class CreateCompanyRequest(CamelCaseModel):
    """Request schema for creating a company."""

    company_name: str = Field(
        ...,
        min_length=1,
        max_length=200,
        alias='companyName'
    )
    website_url: HttpUrl = Field(..., alias='websiteUrl')
    industry: str | None = Field(
        default=None,
        max_length=100
    )
    config: CompanyConfig | None = None

    @field_validator('website_url', mode='before')
    @classmethod
    def normalize_url(cls, v: Any) -> Any:
        """Ensure URL is properly formatted."""
        if isinstance(v, str) and not v.startswith(('http://', 'https://')):
            return f'https://{v}'
        return v


# Response Schemas

class CreateCompanyResponse(CamelCaseModel):
    """Response schema for company creation."""

    company_id: str = Field(..., alias='companyId')
    status: str
    created_at: datetime = Field(..., alias='createdAt')


class CompanyListItem(CamelCaseModel):
    """Company item in list responses."""

    id: str
    company_name: str = Field(..., alias='companyName')
    website_url: str = Field(..., alias='websiteUrl')
    status: CompanyStatus
    total_tokens_used: int = Field(..., alias='totalTokensUsed')
    estimated_cost: float = Field(..., alias='estimatedCost')
    created_at: datetime = Field(..., alias='createdAt')
    completed_at: datetime | None = Field(default=None, alias='completedAt')


class CompanyDetail(CamelCaseModel):
    """Detailed company information."""

    id: str
    company_name: str = Field(..., alias='companyName')
    website_url: str = Field(..., alias='websiteUrl')
    industry: str | None = None
    analysis_mode: AnalysisMode = Field(..., alias='analysisMode')
    status: CompanyStatus
    total_tokens_used: int = Field(..., alias='totalTokensUsed')
    estimated_cost: float = Field(..., alias='estimatedCost')
    created_at: datetime = Field(..., alias='createdAt')
    completed_at: datetime | None = Field(default=None, alias='completedAt')


class AnalysisSummary(CamelCaseModel):
    """Analysis summary for company detail response."""

    id: str
    version_number: int = Field(..., alias='versionNumber')
    executive_summary: str | None = Field(default=None, alias='executiveSummary')
    full_analysis: dict[str, Any] | None = Field(default=None, alias='fullAnalysis')
    created_at: datetime = Field(..., alias='createdAt')


class CompanyDetailResponse(CamelCaseModel):
    """Complete company detail response."""

    company: CompanyDetail
    analysis: AnalysisSummary | None = None
    entity_count: int = Field(..., alias='entityCount')
    page_count: int = Field(..., alias='pageCount')


class ProgressResponse(CamelCaseModel):
    """Real-time progress response."""

    company_id: str = Field(..., alias='companyId')
    status: CompanyStatus
    phase: ProcessingPhase
    pages_crawled: int = Field(..., alias='pagesCrawled')
    pages_total: int = Field(..., alias='pagesTotal')
    entities_extracted: int = Field(..., alias='entitiesExtracted')
    tokens_used: int = Field(..., alias='tokensUsed')
    time_elapsed: int = Field(..., alias='timeElapsed')
    estimated_time_remaining: int | None = Field(
        default=None,
        alias='estimatedTimeRemaining'
    )
    current_activity: str | None = Field(default=None, alias='currentActivity')


class PauseResponse(CamelCaseModel):
    """Response for pause operation."""

    status: str
    checkpoint_saved: bool = Field(..., alias='checkpointSaved')
    paused_at: datetime = Field(..., alias='pausedAt')


class ResumeFromData(CamelCaseModel):
    """Data about where processing resumed from."""

    pages_crawled: int = Field(..., alias='pagesCrawled')
    entities_extracted: int = Field(..., alias='entitiesExtracted')
    phase: ProcessingPhase


class ResumeResponse(CamelCaseModel):
    """Response for resume operation."""

    status: str
    resumed_from: ResumeFromData = Field(..., alias='resumedFrom')


class RescanResponse(CamelCaseModel):
    """Response for rescan operation."""

    new_analysis_id: str = Field(..., alias='newAnalysisId')
    version_number: int = Field(..., alias='versionNumber')
    status: str


class DeletedRecords(CamelCaseModel):
    """Count of deleted records."""

    pages: int
    entities: int
    analyses: int


class DeleteResponse(CamelCaseModel):
    """Response for delete operation."""

    deleted: bool
    deleted_records: DeletedRecords = Field(..., alias='deletedRecords')


# Batch upload schemas

class BatchCompanyResult(CamelCaseModel):
    """Result for a single company in batch upload."""

    company_name: str = Field(..., alias='companyName')
    company_id: str | None = Field(default=None, alias='companyId')
    error: str | None = None


class BatchUploadResponse(CamelCaseModel):
    """Response for batch upload."""

    total_count: int = Field(..., alias='totalCount')
    successful: int
    failed: int
    companies: list[BatchCompanyResult]
