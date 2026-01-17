"""Health check Pydantic schemas."""

from typing import Literal

from app.schemas.base import CamelCaseModel


class HealthResponse(CamelCaseModel):
    """Health check response."""

    status: Literal['healthy', 'degraded']
    version: str
    database: Literal['connected', 'disconnected']
    redis: Literal['connected', 'disconnected']
