"""Tests for Redis service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from redis.exceptions import ConnectionError, TimeoutError, RedisError

from app.services.redis_service import RedisService, redis_service


class TestRedisServiceInitialization:
    """Tests for Redis service initialization."""

    def test_service_init_without_url(self):
        """Test service initialization without URL."""
        service = RedisService()
        assert service._redis_url is None
        assert service._client is None

    def test_service_init_with_url(self):
        """Test service initialization with URL parameter."""
        service = RedisService(redis_url='redis://localhost:6379/0')
        assert service._redis_url == 'redis://localhost:6379/0'

    def test_service_init_app(self, app):
        """Test service initialization with Flask app."""
        service = RedisService()
        # Service will try to connect but may fail without Redis running
        with patch.object(service, '_setup_connection'):
            service.init_app(app)
            assert service._redis_url is not None

    def test_service_is_available_when_no_client(self):
        """Test is_available returns False when client is None."""
        service = RedisService()
        assert service.is_available is False


class TestRedisServiceHealthCheck:
    """Tests for Redis health check functionality."""

    def test_health_check_without_client(self):
        """Test health check when client is not initialized."""
        service = RedisService()
        result = service.health_check()
        assert result['status'] == 'unavailable'
        assert result['connected'] is False
        assert result['error'] == 'Redis client not initialized'

    def test_health_check_with_connection(self):
        """Test health check with mocked connection."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.ping.return_value = True
        service._client = mock_client

        result = service.health_check()
        assert result['status'] == 'healthy'
        assert result['connected'] is True
        assert result['latency_ms'] is not None

    def test_health_check_connection_error(self):
        """Test health check when connection fails."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")
        service._client = mock_client

        result = service.health_check()
        assert result['status'] == 'unhealthy'
        assert result['connected'] is False
        assert 'Connection refused' in result['error']

    def test_health_check_timeout_error(self):
        """Test health check when connection times out."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.ping.side_effect = TimeoutError("Timeout")
        service._client = mock_client

        result = service.health_check()
        assert result['status'] == 'unhealthy'
        assert result['connected'] is False

    def test_health_check_redis_error(self):
        """Test health check with generic Redis error."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.ping.side_effect = RedisError("Generic error")
        service._client = mock_client

        result = service.health_check()
        assert result['status'] == 'degraded'
        assert result['connected'] is False


class TestRedisServiceKeyNamespace:
    """Tests for key namespace functionality."""

    def test_make_key_single_part(self):
        """Test making a key with single part."""
        service = RedisService()
        key = service._make_key('test')
        assert key == 'cira:test'

    def test_make_key_multiple_parts(self):
        """Test making a key with multiple parts."""
        service = RedisService()
        key = service._make_key('job', '123', 'status')
        assert key == 'cira:job:123:status'


class TestRedisServiceCacheOperations:
    """Tests for cache get/set/delete operations."""

    def test_cache_get_without_client(self):
        """Test cache get returns None when no client."""
        service = RedisService()
        result = service.cache_get('test_key')
        assert result is None

    def test_cache_set_without_client(self):
        """Test cache set returns False when no client."""
        service = RedisService()
        result = service.cache_set('test_key', {'data': 'value'})
        assert result is False

    def test_cache_delete_without_client(self):
        """Test cache delete returns False when no client."""
        service = RedisService()
        result = service.cache_delete('test_key')
        assert result is False

    def test_cache_get_success(self):
        """Test successful cache get."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.get.return_value = b'{"data": "value"}'
        service._client = mock_client

        result = service.cache_get('test_key')
        assert result == {'data': 'value'}
        mock_client.get.assert_called_once_with('cira:cache:test_key')

    def test_cache_get_not_found(self):
        """Test cache get when key doesn't exist."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.get.return_value = None
        service._client = mock_client

        result = service.cache_get('nonexistent')
        assert result is None

    def test_cache_set_success(self):
        """Test successful cache set."""
        service = RedisService()
        mock_client = MagicMock()
        service._client = mock_client

        result = service.cache_set('test_key', {'data': 'value'})
        assert result is True
        mock_client.setex.assert_called_once()

    def test_cache_set_with_custom_expiry(self):
        """Test cache set with custom expiry."""
        service = RedisService()
        mock_client = MagicMock()
        service._client = mock_client

        service.cache_set('test_key', {'data': 'value'}, expiry=300)
        mock_client.setex.assert_called_with(
            'cira:cache:test_key',
            300,
            '{"data": "value"}'
        )

    def test_cache_delete_success(self):
        """Test successful cache delete."""
        service = RedisService()
        mock_client = MagicMock()
        service._client = mock_client

        result = service.cache_delete('test_key')
        assert result is True
        mock_client.delete.assert_called_once_with('cira:cache:test_key')


class TestRedisServiceJobStatus:
    """Tests for job status operations."""

    def test_get_job_status_without_client(self):
        """Test get job status returns None when no client."""
        service = RedisService()
        result = service.get_job_status('company-123')
        assert result is None

    def test_set_job_status_without_client(self):
        """Test set job status returns False when no client."""
        service = RedisService()
        result = service.set_job_status('company-123', {'status': 'pending'})
        assert result is False

    def test_get_job_status_success(self):
        """Test successful get job status."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.get.return_value = b'{"status": "in_progress", "phase": "crawling"}'
        service._client = mock_client

        result = service.get_job_status('company-123')
        assert result == {'status': 'in_progress', 'phase': 'crawling'}
        mock_client.get.assert_called_once_with('cira:job:company-123:status')

    def test_set_job_status_success(self):
        """Test successful set job status."""
        service = RedisService()
        mock_client = MagicMock()
        service._client = mock_client

        result = service.set_job_status('company-123', {'status': 'in_progress'})
        assert result is True
        mock_client.setex.assert_called_once()

    def test_delete_job_status_success(self):
        """Test successful delete job status."""
        service = RedisService()
        mock_client = MagicMock()
        service._client = mock_client

        result = service.delete_job_status('company-123')
        assert result is True
        mock_client.delete.assert_called_once_with('cira:job:company-123:status')


class TestRedisServiceProgress:
    """Tests for progress tracking operations."""

    def test_get_progress_without_client(self):
        """Test get progress returns None when no client."""
        service = RedisService()
        result = service.get_progress('company-123')
        assert result is None

    def test_set_progress_without_client(self):
        """Test set progress returns False when no client."""
        service = RedisService()
        result = service.set_progress('company-123', {'percentage': 50})
        assert result is False

    def test_get_progress_success(self):
        """Test successful get progress."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.get.return_value = b'{"percentage": 75, "pages_crawled": 30}'
        service._client = mock_client

        result = service.get_progress('company-123')
        assert result == {'percentage': 75, 'pages_crawled': 30}
        mock_client.get.assert_called_once_with('cira:job:company-123:progress')

    def test_set_progress_success(self):
        """Test successful set progress."""
        service = RedisService()
        mock_client = MagicMock()
        service._client = mock_client

        result = service.set_progress('company-123', {'percentage': 50})
        assert result is True

    def test_set_activity_success(self):
        """Test successful set activity."""
        service = RedisService()
        mock_client = MagicMock()
        service._client = mock_client

        result = service.set_activity('company-123', 'Crawling page 15...')
        assert result is True
        mock_client.setex.assert_called_once()

    def test_get_activity_success(self):
        """Test successful get activity."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.get.return_value = b'Analyzing entities...'
        service._client = mock_client

        result = service.get_activity('company-123')
        assert result == 'Analyzing entities...'


class TestRedisServiceDistributedLocking:
    """Tests for distributed locking operations."""

    def test_acquire_lock_without_client(self):
        """Test acquire lock returns False when no client."""
        service = RedisService()
        result = service.acquire_lock('company-123', 'worker-1')
        assert result is False

    def test_release_lock_without_client(self):
        """Test release lock returns False when no client."""
        service = RedisService()
        result = service.release_lock('company-123', 'worker-1')
        assert result is False

    def test_acquire_lock_success(self):
        """Test successful lock acquisition."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.set.return_value = True
        service._client = mock_client

        result = service.acquire_lock('company-123', 'worker-1')
        assert result is True
        mock_client.set.assert_called_once()
        call_kwargs = mock_client.set.call_args[1]
        assert call_kwargs['nx'] is True  # Ensure SET NX is used

    def test_acquire_lock_already_locked(self):
        """Test lock acquisition when already locked."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.set.return_value = None  # NX returns None if key exists
        service._client = mock_client

        result = service.acquire_lock('company-123', 'worker-1')
        assert result is False

    def test_release_lock_success(self):
        """Test successful lock release."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.eval.return_value = 1
        service._client = mock_client

        result = service.release_lock('company-123', 'worker-1')
        assert result is True

    def test_release_lock_not_held(self):
        """Test release lock when not holding the lock."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.eval.return_value = 0
        service._client = mock_client

        result = service.release_lock('company-123', 'worker-1')
        assert result is False

    def test_extend_lock_success(self):
        """Test successful lock extension."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.eval.return_value = 1
        service._client = mock_client

        result = service.extend_lock('company-123', 'worker-1', expiry=120)
        assert result is True

    def test_extend_lock_without_client(self):
        """Test extend lock returns False when no client."""
        service = RedisService()
        result = service.extend_lock('company-123', 'worker-1')
        assert result is False

    def test_get_lock_holder_success(self):
        """Test getting lock holder."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.get.return_value = b'worker-1'
        service._client = mock_client

        result = service.get_lock_holder('company-123')
        assert result == 'worker-1'

    def test_get_lock_holder_not_locked(self):
        """Test getting lock holder when not locked."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.get.return_value = None
        service._client = mock_client

        result = service.get_lock_holder('company-123')
        assert result is None


class TestRedisServiceCleanup:
    """Tests for cleanup operations."""

    def test_cleanup_job_without_client(self):
        """Test cleanup job returns False when no client."""
        service = RedisService()
        result = service.cleanup_job('company-123')
        assert result is False

    def test_cleanup_job_success(self):
        """Test successful job cleanup."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = [
            b'cira:job:company-123:status',
            b'cira:job:company-123:progress',
            b'cira:job:company-123:activity'
        ]
        service._client = mock_client

        result = service.cleanup_job('company-123')
        assert result is True
        mock_client.delete.assert_called_once()

    def test_cleanup_job_no_keys(self):
        """Test job cleanup when no keys exist."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.scan_iter.return_value = []
        service._client = mock_client

        result = service.cleanup_job('company-123')
        assert result is True
        mock_client.delete.assert_not_called()


class TestRedisServiceGracefulDegradation:
    """Tests for graceful degradation when Redis is unavailable."""

    def test_cache_operations_fail_gracefully(self):
        """Test cache operations fail gracefully on Redis error."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.get.side_effect = RedisError("Connection lost")
        mock_client.setex.side_effect = RedisError("Connection lost")
        mock_client.delete.side_effect = RedisError("Connection lost")
        service._client = mock_client

        # All operations should return None/False instead of raising
        assert service.cache_get('key') is None
        assert service.cache_set('key', 'value') is False
        assert service.cache_delete('key') is False

    def test_job_operations_fail_gracefully(self):
        """Test job operations fail gracefully on Redis error."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.get.side_effect = RedisError("Connection lost")
        mock_client.setex.side_effect = RedisError("Connection lost")
        service._client = mock_client

        # All operations should return None/False instead of raising
        assert service.get_job_status('company-123') is None
        assert service.set_job_status('company-123', {}) is False
        assert service.get_progress('company-123') is None
        assert service.set_progress('company-123', {}) is False

    def test_lock_operations_fail_gracefully(self):
        """Test lock operations fail gracefully on Redis error."""
        service = RedisService()
        mock_client = MagicMock()
        mock_client.set.side_effect = RedisError("Connection lost")
        mock_client.eval.side_effect = RedisError("Connection lost")
        service._client = mock_client

        # All operations should return False instead of raising
        assert service.acquire_lock('company-123', 'worker-1') is False
        assert service.release_lock('company-123', 'worker-1') is False
        assert service.extend_lock('company-123', 'worker-1') is False


class TestGlobalRedisService:
    """Tests for global redis_service instance."""

    def test_global_service_exists(self):
        """Test that global service instance exists."""
        from app.services import redis_service
        assert redis_service is not None
        assert isinstance(redis_service, RedisService)


class TestRedisServiceIntegrationWithHealthEndpoint:
    """Tests for Redis service integration with health endpoint."""

    def test_health_endpoint_uses_redis_service(self, client):
        """Test that health endpoint properly uses redis service."""
        response = client.get('/api/v1/health')
        assert response.status_code == 200
        data = response.get_json()
        assert 'redis' in data['data']
        # Redis won't be connected in test, so it should be disconnected
        assert data['data']['redis'] in ['connected', 'disconnected']
