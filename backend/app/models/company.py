"""Company and related models."""

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import String, Text, Integer, Float, DateTime, Enum, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db
from app.models.enums import (
    CompanyStatus,
    CrawlStatus,
    ProcessingPhase,
    AnalysisMode,
    PageType,
    EntityType,
    ApiCallType,
)


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    """Generate a UUID string for primary keys."""
    return str(uuid.uuid4())


class Company(db.Model):
    """Company model representing a company to analyze."""

    __tablename__ = 'companies'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    website_url: Mapped[str] = mapped_column(String(500), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Analysis configuration
    analysis_mode: Mapped[AnalysisMode] = mapped_column(
        Enum(AnalysisMode), default=AnalysisMode.THOROUGH
    )
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Status and tracking
    status: Mapped[CompanyStatus] = mapped_column(
        Enum(CompanyStatus), default=CompanyStatus.PENDING, index=True
    )
    processing_phase: Mapped[ProcessingPhase] = mapped_column(
        Enum(ProcessingPhase), default=ProcessingPhase.QUEUED
    )

    # Token usage tracking
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Pause tracking
    total_paused_duration_ms: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    crawl_sessions: Mapped[list['CrawlSession']] = relationship(
        'CrawlSession', back_populates='company', cascade='all, delete-orphan'
    )
    pages: Mapped[list['Page']] = relationship(
        'Page', back_populates='company', cascade='all, delete-orphan'
    )
    entities: Mapped[list['Entity']] = relationship(
        'Entity', back_populates='company', cascade='all, delete-orphan'
    )
    analyses: Mapped[list['Analysis']] = relationship(
        'Analysis', back_populates='company', cascade='all, delete-orphan'
    )
    token_usages: Mapped[list['TokenUsage']] = relationship(
        'TokenUsage', back_populates='company', cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_companies_status_created', 'status', 'created_at'),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'companyName': self.company_name,
            'websiteUrl': self.website_url,
            'industry': self.industry,
            'analysisMode': self.analysis_mode.value,
            'status': self.status.value,
            'totalTokensUsed': self.total_tokens_used,
            'estimatedCost': self.estimated_cost,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
        }


class CrawlSession(db.Model):
    """Crawl session model tracking a single crawl execution."""

    __tablename__ = 'crawl_sessions'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True
    )

    # Crawl stats
    pages_crawled: Mapped[int] = mapped_column(Integer, default=0)
    pages_queued: Mapped[int] = mapped_column(Integer, default=0)
    crawl_depth_reached: Mapped[int] = mapped_column(Integer, default=0)
    external_links_followed: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    status: Mapped[CrawlStatus] = mapped_column(
        Enum(CrawlStatus), default=CrawlStatus.ACTIVE, index=True
    )

    # Checkpoint data for pause/resume
    checkpoint_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )

    # Relationships
    company: Mapped['Company'] = relationship('Company', back_populates='crawl_sessions')

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'companyId': self.company_id,
            'pagesCrawled': self.pages_crawled,
            'pagesQueued': self.pages_queued,
            'crawlDepthReached': self.crawl_depth_reached,
            'externalLinksFollowed': self.external_links_followed,
            'status': self.status.value,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
        }


class Page(db.Model):
    """Page model representing a crawled web page."""

    __tablename__ = 'pages'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True
    )

    # Page info
    url: Mapped[str] = mapped_column(String(2000), nullable=False)
    page_type: Mapped[PageType] = mapped_column(Enum(PageType), default=PageType.OTHER)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Content
    raw_html: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    crawled_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    is_external: Mapped[bool] = mapped_column(default=False)

    # Relationships
    company: Mapped['Company'] = relationship('Company', back_populates='pages')

    __table_args__ = (
        Index('ix_pages_company_type', 'company_id', 'page_type'),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'url': self.url,
            'pageType': self.page_type.value,
            'crawledAt': self.crawled_at.isoformat() if self.crawled_at else None,
            'isExternal': self.is_external,
        }


class Entity(db.Model):
    """Entity model representing an extracted entity."""

    __tablename__ = 'entities'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True
    )

    # Entity info
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), nullable=False)
    entity_value: Mapped[str] = mapped_column(String(500), nullable=False)
    context_snippet: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)

    # Additional data (for person roles, org relationships, etc.)
    extra_data: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    company: Mapped['Company'] = relationship('Company', back_populates='entities')

    __table_args__ = (
        Index('ix_entities_company_type', 'company_id', 'entity_type'),
        Index('ix_entities_confidence', 'confidence_score'),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'entityType': self.entity_type.value,
            'entityValue': self.entity_value,
            'contextSnippet': self.context_snippet,
            'sourceUrl': self.source_url,
            'confidenceScore': self.confidence_score,
        }


class Analysis(db.Model):
    """Analysis model representing a completed analysis."""

    __tablename__ = 'analyses'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True
    )

    # Version tracking (max 3 versions per company)
    version_number: Mapped[int] = mapped_column(Integer, default=1)

    # Analysis content
    executive_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_analysis: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    raw_insights: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Token breakdown
    token_breakdown: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    company: Mapped['Company'] = relationship('Company', back_populates='analyses')

    __table_args__ = (
        Index('ix_analyses_company_version', 'company_id', 'version_number'),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'versionNumber': self.version_number,
            'executiveSummary': self.executive_summary,
            'fullAnalysis': self.full_analysis,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
        }


class TokenUsage(db.Model):
    """Token usage model for tracking API call costs."""

    __tablename__ = 'token_usages'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    company_id: Mapped[str] = mapped_column(
        String(36), ForeignKey('companies.id', ondelete='CASCADE'), nullable=False, index=True
    )

    # API call info
    api_call_type: Mapped[ApiCallType] = mapped_column(Enum(ApiCallType), nullable=False)
    section: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Token counts
    input_tokens: Mapped[int] = mapped_column(Integer, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0)

    # Timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    # Relationships
    company: Mapped['Company'] = relationship('Company', back_populates='token_usages')

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'callType': self.api_call_type.value,
            'section': self.section,
            'inputTokens': self.input_tokens,
            'outputTokens': self.output_tokens,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
        }
