"""Configuration Pydantic schemas."""

from pydantic import Field

from app.models.enums import AnalysisMode
from app.schemas.base import CamelCaseModel


class DefaultConfig(CamelCaseModel):
    """Default analysis configuration."""

    analysis_mode: AnalysisMode = Field(..., alias='analysisMode')
    time_limit_minutes: int = Field(..., alias='timeLimitMinutes')
    max_pages: int = Field(..., alias='maxPages')
    max_depth: int = Field(..., alias='maxDepth')


class ModeConfig(CamelCaseModel):
    """Configuration for a specific analysis mode."""

    max_pages: int = Field(..., alias='maxPages')
    max_depth: int = Field(..., alias='maxDepth')
    follow_external: bool = Field(..., alias='followExternal')


class AppConfigResponse(CamelCaseModel):
    """Application configuration response."""

    defaults: DefaultConfig
    quick_mode: ModeConfig = Field(..., alias='quickMode')
    thorough_mode: ModeConfig = Field(..., alias='thoroughMode')


class UpdateConfigRequest(CamelCaseModel):
    """Request for updating configuration."""

    defaults: DefaultConfig | None = None
