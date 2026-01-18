"""Batch job model for batch queue management."""

from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import String, Integer, Float, DateTime, Enum, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.company import Company

from app import db
from app.models.enums import BatchStatus


def utcnow() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


def generate_uuid() -> str:
    """Generate a UUID string for primary keys."""
    return str(uuid.uuid4())


class BatchJob(db.Model):
    """
    Batch job model representing a batch of companies to analyze.

    This model tracks batch-level progress, enables fair scheduling between
    multiple concurrent batches, and supports batch-wide operations like
    cancellation.
    """

    __tablename__ = 'batch_jobs'

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)

    # Batch identification
    name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Status tracking
    status: Mapped[BatchStatus] = mapped_column(
        Enum(BatchStatus), default=BatchStatus.PENDING, index=True
    )

    # Counts for progress tracking
    total_companies: Mapped[int] = mapped_column(Integer, default=0)
    pending_companies: Mapped[int] = mapped_column(Integer, default=0)
    processing_companies: Mapped[int] = mapped_column(Integer, default=0)
    completed_companies: Mapped[int] = mapped_column(Integer, default=0)
    failed_companies: Mapped[int] = mapped_column(Integer, default=0)

    # Token usage aggregation
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)

    # Priority for fair scheduling (lower = higher priority, default = 100)
    priority: Mapped[int] = mapped_column(Integer, default=100, index=True)

    # Configuration (shared across all companies in batch)
    config: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Concurrency limit for this batch (how many companies can run simultaneously)
    max_concurrent: Mapped[int] = mapped_column(Integer, default=3)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, onupdate=utcnow
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Error message if batch fails
    error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Relationships
    companies: Mapped[list['Company']] = relationship(
        'Company', back_populates='batch'
    )

    __table_args__ = (
        Index('ix_batch_jobs_status_priority', 'status', 'priority'),
        Index('ix_batch_jobs_status_created', 'status', 'created_at'),
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'totalCompanies': self.total_companies,
            'pendingCompanies': self.pending_companies,
            'processingCompanies': self.processing_companies,
            'completedCompanies': self.completed_companies,
            'failedCompanies': self.failed_companies,
            'totalTokensUsed': self.total_tokens_used,
            'estimatedCost': self.estimated_cost,
            'priority': self.priority,
            'maxConcurrent': self.max_concurrent,
            'progress': self.progress_percentage,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'startedAt': self.started_at.isoformat() if self.started_at else None,
            'completedAt': self.completed_at.isoformat() if self.completed_at else None,
        }

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_companies == 0:
            return 0.0
        return round(
            ((self.completed_companies + self.failed_companies) / self.total_companies) * 100,
            2
        )

    @property
    def is_active(self) -> bool:
        """Check if batch is still active (processing or pending)."""
        return self.status in (BatchStatus.PENDING, BatchStatus.PROCESSING)

    @property
    def is_finished(self) -> bool:
        """Check if batch has finished (completed, cancelled, or all done)."""
        return self.status in (BatchStatus.COMPLETED, BatchStatus.CANCELLED)

    def update_counts(self) -> None:
        """
        Update company counts based on actual company statuses.

        This should be called when company statuses change to keep
        batch counts in sync.
        """
        from app.models.company import Company
        from app.models.enums import CompanyStatus

        companies = Company.query.filter_by(batch_id=self.id).all()

        self.total_companies = len(companies)
        self.pending_companies = sum(1 for c in companies if c.status == CompanyStatus.PENDING)
        self.processing_companies = sum(1 for c in companies if c.status == CompanyStatus.IN_PROGRESS)
        self.completed_companies = sum(1 for c in companies if c.status == CompanyStatus.COMPLETED)
        self.failed_companies = sum(1 for c in companies if c.status == CompanyStatus.FAILED)

        # Update batch status based on company states
        if self.status in (BatchStatus.CANCELLED, BatchStatus.PAUSED):
            pass  # Don't change cancelled or paused status
        elif self.pending_companies == 0 and self.processing_companies == 0:
            self.status = BatchStatus.COMPLETED
            self.completed_at = utcnow()
        elif self.processing_companies > 0 or self.completed_companies > 0:
            self.status = BatchStatus.PROCESSING
            if not self.started_at:
                self.started_at = utcnow()

    def aggregate_tokens(self) -> None:
        """Aggregate token usage from all companies in batch."""
        from app.models.company import Company

        companies = Company.query.filter_by(batch_id=self.id).all()
        self.total_tokens_used = sum(c.total_tokens_used for c in companies)
        self.estimated_cost = sum(c.estimated_cost for c in companies)
