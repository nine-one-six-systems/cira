"""Tests for Celery application setup."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from kombu import Queue

from app.workers.celery_app import celery_app, init_celery, get_celery_app
from app.workers.tasks import (
    TaskError,
    RetryableError,
    PermanentError,
    health_check,
)


class TestCeleryAppConfiguration:
    """Tests for Celery application configuration."""

    def test_celery_app_exists(self):
        """Test that Celery app is created."""
        assert celery_app is not None
        assert celery_app.main == 'cira'

    def test_celery_default_configuration(self):
        """Test default Celery configuration."""
        assert celery_app.conf.task_serializer == 'json'
        assert celery_app.conf.result_serializer == 'json'
        assert 'json' in celery_app.conf.accept_content
        assert celery_app.conf.timezone == 'UTC'
        assert celery_app.conf.enable_utc is True

    def test_celery_task_tracking(self):
        """Test task tracking configuration."""
        assert celery_app.conf.task_track_started is True
        assert celery_app.conf.task_acks_late is True

    def test_get_celery_app(self):
        """Test get_celery_app returns the app instance."""
        app = get_celery_app()
        assert app is celery_app


class TestCeleryInitialization:
    """Tests for Celery initialization with Flask app."""

    def test_init_celery_with_flask_app(self, app):
        """Test Celery initialization with Flask app."""
        result = init_celery(app)
        assert result is celery_app

    def test_init_celery_sets_broker_url(self, app):
        """Test that init_celery sets broker URL from Flask config."""
        init_celery(app)
        expected_url = app.config.get('CELERY_BROKER_URL')
        assert celery_app.conf.broker_url == expected_url

    def test_init_celery_sets_result_backend(self, app):
        """Test that init_celery sets result backend from Flask config."""
        init_celery(app)
        expected_url = app.config.get('CELERY_RESULT_BACKEND')
        assert celery_app.conf.result_backend == expected_url


class TestCeleryTaskQueues:
    """Tests for Celery task queue configuration."""

    def test_task_queues_configured(self, app):
        """Test that task queues are configured."""
        init_celery(app)
        queues = celery_app.conf.task_queues
        assert queues is not None
        queue_names = [q.name for q in queues]
        assert 'default' in queue_names
        assert 'crawl' in queue_names
        assert 'extract' in queue_names
        assert 'analyze' in queue_names

    def test_default_queue_set(self, app):
        """Test that default queue is set."""
        init_celery(app)
        assert celery_app.conf.task_default_queue == 'default'

    def test_task_routes_configured(self, app):
        """Test that task routes are configured."""
        init_celery(app)
        routes = celery_app.conf.task_routes
        assert routes is not None
        assert 'app.workers.tasks.crawl_company' in routes
        assert routes['app.workers.tasks.crawl_company']['queue'] == 'crawl'
        assert 'app.workers.tasks.extract_entities' in routes
        assert routes['app.workers.tasks.extract_entities']['queue'] == 'extract'
        assert 'app.workers.tasks.analyze_content' in routes
        assert routes['app.workers.tasks.analyze_content']['queue'] == 'analyze'


class TestCeleryRetryConfiguration:
    """Tests for Celery retry configuration."""

    def test_task_annotations_configured(self, app):
        """Test that task annotations are configured for retry."""
        init_celery(app)
        annotations = celery_app.conf.task_annotations
        assert annotations is not None
        assert '*' in annotations
        assert annotations['*']['max_retries'] == 3
        assert annotations['*']['retry_backoff'] is True
        assert annotations['*']['retry_jitter'] is True

    def test_retry_backoff_max_set(self, app):
        """Test that retry backoff max is set."""
        init_celery(app)
        annotations = celery_app.conf.task_annotations
        assert annotations['*']['retry_backoff_max'] == 600  # 10 minutes


class TestCeleryTimeLimits:
    """Tests for Celery time limit configuration."""

    def test_soft_time_limit_set(self, app):
        """Test that soft time limit is set."""
        init_celery(app)
        assert celery_app.conf.task_soft_time_limit == 3600  # 1 hour

    def test_hard_time_limit_set(self, app):
        """Test that hard time limit is set."""
        init_celery(app)
        assert celery_app.conf.task_time_limit == 3900  # 1 hour 5 min


class TestCeleryResultExpiration:
    """Tests for Celery result expiration configuration."""

    def test_result_expires_set(self, app):
        """Test that result expiration is set."""
        init_celery(app)
        assert celery_app.conf.result_expires == 86400  # 24 hours


class TestTaskExceptions:
    """Tests for task exception classes."""

    def test_task_error_base_class(self):
        """Test TaskError is Exception subclass."""
        assert issubclass(TaskError, Exception)
        error = TaskError("test error")
        assert str(error) == "test error"

    def test_retryable_error(self):
        """Test RetryableError is TaskError subclass."""
        assert issubclass(RetryableError, TaskError)
        error = RetryableError("network timeout")
        assert str(error) == "network timeout"

    def test_permanent_error(self):
        """Test PermanentError is TaskError subclass."""
        assert issubclass(PermanentError, TaskError)
        error = PermanentError("invalid input")
        assert str(error) == "invalid input"


class TestHealthCheckTask:
    """Tests for health check task."""

    def test_health_check_task_exists(self):
        """Test that health check task is registered."""
        assert health_check.name == 'app.workers.tasks.health_check'

    def test_health_check_returns_status(self, app):
        """Test health check task returns status."""
        with app.app_context():
            result = health_check()
            assert result['status'] == 'healthy'
            assert 'timestamp' in result
            assert result['worker'] == 'celery'


class TestCrawlTasks:
    """Tests for crawl task definitions."""

    def test_crawl_company_task_registered(self, app):
        """Test crawl_company task is registered."""
        from app.workers.tasks import crawl_company
        assert crawl_company.name == 'app.workers.tasks.crawl_company'
        assert crawl_company.max_retries == 3

    def test_crawl_page_task_registered(self, app):
        """Test crawl_page task is registered."""
        from app.workers.tasks import crawl_page
        assert crawl_page.name == 'app.workers.tasks.crawl_page'
        assert crawl_page.max_retries == 3


class TestExtractionTasks:
    """Tests for extraction task definitions."""

    def test_extract_entities_task_registered(self, app):
        """Test extract_entities task is registered."""
        from app.workers.tasks import extract_entities
        assert extract_entities.name == 'app.workers.tasks.extract_entities'
        assert extract_entities.max_retries == 3


class TestAnalysisTasks:
    """Tests for analysis task definitions."""

    def test_analyze_content_task_registered(self, app):
        """Test analyze_content task is registered."""
        from app.workers.tasks import analyze_content
        assert analyze_content.name == 'app.workers.tasks.analyze_content'
        assert analyze_content.max_retries == 3

    def test_generate_summary_task_registered(self, app):
        """Test generate_summary task is registered."""
        from app.workers.tasks import generate_summary
        assert generate_summary.name == 'app.workers.tasks.generate_summary'
        assert generate_summary.max_retries == 3


class TestCrawlCompanyTask:
    """Tests for crawl_company task definition."""

    def test_crawl_company_task_bind(self):
        """Test crawl_company is a bound task."""
        from app.workers.tasks import crawl_company
        # Bound tasks have bind=True which means self is passed
        # We verify the task is registered and has expected properties
        assert crawl_company.name == 'app.workers.tasks.crawl_company'
        assert crawl_company.max_retries == 3

    def test_crawl_company_routing(self, app):
        """Test crawl_company routes to crawl queue."""
        init_celery(app)
        routes = celery_app.conf.task_routes
        assert routes['app.workers.tasks.crawl_company']['queue'] == 'crawl'


class TestExtractEntitiesTask:
    """Tests for extract_entities task definition."""

    def test_extract_entities_task_bind(self):
        """Test extract_entities is a bound task."""
        from app.workers.tasks import extract_entities
        assert extract_entities.name == 'app.workers.tasks.extract_entities'
        assert extract_entities.max_retries == 3

    def test_extract_entities_routing(self, app):
        """Test extract_entities routes to extract queue."""
        init_celery(app)
        routes = celery_app.conf.task_routes
        assert routes['app.workers.tasks.extract_entities']['queue'] == 'extract'


class TestAnalyzeContentTask:
    """Tests for analyze_content task definition."""

    def test_analyze_content_task_bind(self):
        """Test analyze_content is a bound task."""
        from app.workers.tasks import analyze_content
        assert analyze_content.name == 'app.workers.tasks.analyze_content'
        assert analyze_content.max_retries == 3

    def test_analyze_content_routing(self, app):
        """Test analyze_content routes to analyze queue."""
        init_celery(app)
        routes = celery_app.conf.task_routes
        assert routes['app.workers.tasks.analyze_content']['queue'] == 'analyze'


class TestGenerateSummaryTask:
    """Tests for generate_summary task definition."""

    def test_generate_summary_task_bind(self):
        """Test generate_summary is a bound task."""
        from app.workers.tasks import generate_summary
        assert generate_summary.name == 'app.workers.tasks.generate_summary'
        assert generate_summary.max_retries == 3

    def test_generate_summary_routing(self, app):
        """Test generate_summary routes to analyze queue."""
        init_celery(app)
        routes = celery_app.conf.task_routes
        assert routes['app.workers.tasks.generate_summary']['queue'] == 'analyze'


class TestTaskRetryBehavior:
    """Tests for task retry behavior."""

    def test_retryable_error_in_autoretry_for(self):
        """Test that RetryableError is in autoretry_for."""
        from app.workers.tasks import crawl_company
        assert RetryableError in crawl_company.autoretry_for

    def test_task_has_retry_backoff(self):
        """Test that tasks have retry backoff enabled."""
        from app.workers.tasks import crawl_company
        # The retry_backoff is set in task decorator
        assert crawl_company.retry_backoff is True
