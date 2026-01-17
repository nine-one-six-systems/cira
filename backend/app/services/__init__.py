"""Business logic services package."""

from app.services.redis_service import redis_service, RedisService

__all__ = [
    'redis_service',
    'RedisService',
]


# Lazy imports to avoid circular dependencies
def get_job_service():
    """Get the job service instance (lazy load to avoid circular imports)."""
    from app.services.job_service import job_service
    return job_service


def get_job_service_class():
    """Get the JobService class (lazy load to avoid circular imports)."""
    from app.services.job_service import JobService
    return JobService


def get_progress_service():
    """Get the progress service instance (lazy load to avoid circular imports)."""
    from app.services.progress_service import progress_service
    return progress_service


def get_progress_service_class():
    """Get the ProgressService class (lazy load to avoid circular imports)."""
    from app.services.progress_service import ProgressService
    return ProgressService


def get_checkpoint_service():
    """Get the checkpoint service instance (lazy load to avoid circular imports)."""
    from app.services.checkpoint_service import checkpoint_service
    return checkpoint_service


def get_checkpoint_service_class():
    """Get the CheckpointService class (lazy load to avoid circular imports)."""
    from app.services.checkpoint_service import CheckpointService
    return CheckpointService
