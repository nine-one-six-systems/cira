"""Pydantic schemas package."""

from app.schemas.base import (
    ApiError,
    ApiErrorResponse,
    ApiResponse,
    CamelCaseModel,
    PaginatedResponse,
    PaginationMeta,
)
from app.schemas.company import (
    AnalysisSummary,
    BatchCompanyResult,
    BatchUploadResponse,
    CompanyConfig,
    CompanyDetail,
    CompanyDetailResponse,
    CompanyListItem,
    CreateCompanyRequest,
    CreateCompanyResponse,
    DeletedRecords,
    DeleteResponse,
    PauseResponse,
    ProgressResponse,
    RescanResponse,
    ResumeFromData,
    ResumeResponse,
)
from app.schemas.config import (
    AppConfigResponse,
    DefaultConfig,
    ModeConfig,
    UpdateConfigRequest,
)
from app.schemas.entity import EntityItem, EntityQueryParams
from app.schemas.health import HealthResponse
from app.schemas.page import PageItem, PageQueryParams
from app.schemas.token import TokenUsageItem, TokenUsageResponse
from app.schemas.version import (
    CompareQueryParams,
    CompareVersionsResponse,
    VersionChange,
    VersionChanges,
    VersionItem,
)

__all__ = [
    # Base
    'ApiError',
    'ApiErrorResponse',
    'ApiResponse',
    'CamelCaseModel',
    'PaginatedResponse',
    'PaginationMeta',
    # Company
    'AnalysisSummary',
    'BatchCompanyResult',
    'BatchUploadResponse',
    'CompanyConfig',
    'CompanyDetail',
    'CompanyDetailResponse',
    'CompanyListItem',
    'CreateCompanyRequest',
    'CreateCompanyResponse',
    'DeletedRecords',
    'DeleteResponse',
    'PauseResponse',
    'ProgressResponse',
    'RescanResponse',
    'ResumeFromData',
    'ResumeResponse',
    # Config
    'AppConfigResponse',
    'DefaultConfig',
    'ModeConfig',
    'UpdateConfigRequest',
    # Entity
    'EntityItem',
    'EntityQueryParams',
    # Health
    'HealthResponse',
    # Page
    'PageItem',
    'PageQueryParams',
    # Token
    'TokenUsageItem',
    'TokenUsageResponse',
    # Version
    'CompareQueryParams',
    'CompareVersionsResponse',
    'VersionChange',
    'VersionChanges',
    'VersionItem',
]
