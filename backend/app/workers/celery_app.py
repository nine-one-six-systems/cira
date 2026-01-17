"""Celery application configuration."""

import logging
from celery import Celery
from kombu import Queue

logger = logging.getLogger(__name__)

# Create Celery app instance
celery_app = Celery('cira')

# Default configuration - will be overridden by init_celery
celery_app.conf.update(
    broker_url='redis://localhost:6379/1',
    result_backend='redis://localhost:6379/1',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
)


def init_celery(app) -> Celery:
    """
    Initialize Celery with Flask app configuration.

    Args:
        app: Flask application instance

    Returns:
        Configured Celery application instance
    """
    # Update Celery config from Flask app config
    celery_app.conf.update(
        broker_url=app.config.get('CELERY_BROKER_URL', 'redis://localhost:6379/1'),
        result_backend=app.config.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1'),
    )

    # Configure task queues for different job types
    celery_app.conf.task_queues = (
        Queue('default', routing_key='default'),
        Queue('crawl', routing_key='crawl.#'),
        Queue('extract', routing_key='extract.#'),
        Queue('analyze', routing_key='analyze.#'),
    )

    # Default queue
    celery_app.conf.task_default_queue = 'default'
    celery_app.conf.task_default_routing_key = 'default'

    # Task routes - map task names to queues
    celery_app.conf.task_routes = {
        'app.workers.tasks.crawl_company': {'queue': 'crawl'},
        'app.workers.tasks.crawl_page': {'queue': 'crawl'},
        'app.workers.tasks.extract_entities': {'queue': 'extract'},
        'app.workers.tasks.analyze_content': {'queue': 'analyze'},
        'app.workers.tasks.generate_summary': {'queue': 'analyze'},
    }

    # Task retry configuration with exponential backoff
    celery_app.conf.task_annotations = {
        '*': {
            'rate_limit': '10/s',
            'max_retries': 3,
            'default_retry_delay': 10,
            'retry_backoff': True,
            'retry_backoff_max': 600,  # Max 10 minutes
            'retry_jitter': True,
        }
    }

    # Result expiration (24 hours)
    celery_app.conf.result_expires = 86400

    # Concurrency settings
    celery_app.conf.worker_concurrency = 4

    # Heartbeat settings for worker health
    celery_app.conf.broker_heartbeat = 10
    celery_app.conf.broker_heartbeat_checkrate = 2

    # Task time limits
    celery_app.conf.task_soft_time_limit = 3600  # 1 hour soft limit
    celery_app.conf.task_time_limit = 3900  # 1 hour 5 min hard limit

    # Make Celery tasks inherit Flask app context
    class ContextTask(celery_app.Task):
        """Task base class that provides Flask app context."""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app.Task = ContextTask

    logger.info("Celery initialized with Flask app context")
    return celery_app


def get_celery_app():
    """Get the Celery application instance."""
    return celery_app
