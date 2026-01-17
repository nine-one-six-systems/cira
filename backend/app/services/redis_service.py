"""Redis service for caching, sessions, and progress tracking."""

import json
import logging
from typing import Any

import redis
from redis.exceptions import ConnectionError, RedisError, TimeoutError

logger = logging.getLogger(__name__)


class RedisService:
    """
    Redis service providing caching, progress state, and distributed locking.

    Features:
    - Connection pooling for efficient connection management
    - Namespace prefixing for key isolation
    - Graceful error handling for Redis unavailability
    - Health check endpoint integration
    """

    NAMESPACE = "cira"
    DEFAULT_EXPIRY = 3600  # 1 hour default TTL
    PROGRESS_EXPIRY = 86400  # 24 hours for progress data
    LOCK_EXPIRY = 60  # 1 minute for distributed locks

    def __init__(self, redis_url: str | None = None, pool_size: int = 10):
        """
        Initialize Redis service.

        Args:
            redis_url: Redis connection URL (e.g., 'redis://localhost:6379/0')
            pool_size: Maximum number of connections in the pool
        """
        self._redis_url = redis_url
        self._pool_size = pool_size
        self._client: redis.Redis | None = None
        self._pool: redis.ConnectionPool | None = None

    def init_app(self, app: Any) -> None:
        """
        Initialize Redis service with Flask app.

        Args:
            app: Flask application instance
        """
        redis_url = app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        self._redis_url = redis_url
        self._setup_connection()
        logger.info(f"Redis service initialized with URL: {redis_url}")

    def _setup_connection(self) -> None:
        """Set up Redis connection pool and client."""
        if not self._redis_url:
            logger.warning("Redis URL not configured, service will be unavailable")
            return

        try:
            self._pool = redis.ConnectionPool.from_url(
                self._redis_url,
                max_connections=self._pool_size,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True
            )
            self._client = redis.Redis(connection_pool=self._pool)
            # Test connection
            self._client.ping()
            logger.info("Redis connection established successfully")
        except (ConnectionError, RedisError) as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self._client = None

    @property
    def client(self) -> redis.Redis | None:
        """Get Redis client instance."""
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if Redis is available and responding."""
        if not self._client:
            return False
        try:
            self._client.ping()
            return True
        except (ConnectionError, TimeoutError, RedisError):
            return False

    def health_check(self) -> dict[str, Any]:
        """
        Perform health check and return status.

        Returns:
            Health status dictionary with status, latency, and any errors
        """
        result = {
            "status": "unavailable",
            "connected": False,
            "latency_ms": None,
            "error": None
        }

        if not self._client:
            result["error"] = "Redis client not initialized"
            return result

        try:
            import time
            start = time.time()
            self._client.ping()
            latency = (time.time() - start) * 1000

            result["status"] = "healthy"
            result["connected"] = True
            result["latency_ms"] = round(latency, 2)
        except (ConnectionError, TimeoutError) as e:
            result["status"] = "unhealthy"
            result["error"] = str(e)
        except RedisError as e:
            result["status"] = "degraded"
            result["error"] = str(e)

        return result

    def _make_key(self, *parts: str) -> str:
        """
        Create a namespaced key.

        Args:
            *parts: Key parts to join

        Returns:
            Namespaced key string
        """
        return f"{self.NAMESPACE}:{':'.join(parts)}"

    # ==================== Cache Operations ====================

    def cache_get(self, key: str) -> Any | None:
        """
        Get value from cache.

        Args:
            key: Cache key (without namespace)

        Returns:
            Cached value or None if not found/error
        """
        if not self._client:
            return None

        try:
            full_key = self._make_key("cache", key)
            value = self._client.get(full_key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Cache get error for key '{key}': {e}")
            return None

    def cache_set(
        self,
        key: str,
        value: Any,
        expiry: int | None = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key (without namespace)
            value: Value to cache (must be JSON serializable)
            expiry: TTL in seconds (default: 1 hour)

        Returns:
            True if successful, False otherwise
        """
        if not self._client:
            return False

        try:
            full_key = self._make_key("cache", key)
            serialized = json.dumps(value)
            self._client.setex(
                full_key,
                expiry or self.DEFAULT_EXPIRY,
                serialized
            )
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.warning(f"Cache set error for key '{key}': {e}")
            return False

    def cache_delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key (without namespace)

        Returns:
            True if deleted, False otherwise
        """
        if not self._client:
            return False

        try:
            full_key = self._make_key("cache", key)
            self._client.delete(full_key)
            return True
        except RedisError as e:
            logger.warning(f"Cache delete error for key '{key}': {e}")
            return False

    # ==================== Job Status Operations ====================

    def get_job_status(self, company_id: str) -> dict[str, Any] | None:
        """
        Get job status from Redis.

        Args:
            company_id: Company UUID

        Returns:
            Job status dictionary or None
        """
        if not self._client:
            return None

        try:
            key = self._make_key("job", company_id, "status")
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Get job status error for '{company_id}': {e}")
            return None

    def set_job_status(
        self,
        company_id: str,
        status: dict[str, Any],
        expiry: int | None = None
    ) -> bool:
        """
        Set job status in Redis.

        Args:
            company_id: Company UUID
            status: Status dictionary
            expiry: TTL in seconds (default: 24 hours)

        Returns:
            True if successful
        """
        if not self._client:
            return False

        try:
            key = self._make_key("job", company_id, "status")
            serialized = json.dumps(status)
            self._client.setex(
                key,
                expiry or self.PROGRESS_EXPIRY,
                serialized
            )
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.warning(f"Set job status error for '{company_id}': {e}")
            return False

    def delete_job_status(self, company_id: str) -> bool:
        """Delete job status from Redis."""
        if not self._client:
            return False

        try:
            key = self._make_key("job", company_id, "status")
            self._client.delete(key)
            return True
        except RedisError as e:
            logger.warning(f"Delete job status error for '{company_id}': {e}")
            return False

    # ==================== Progress Operations ====================

    def get_progress(self, company_id: str) -> dict[str, Any] | None:
        """
        Get job progress for UI polling.

        Args:
            company_id: Company UUID

        Returns:
            Progress dictionary or None
        """
        if not self._client:
            return None

        try:
            key = self._make_key("job", company_id, "progress")
            value = self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except (RedisError, json.JSONDecodeError) as e:
            logger.warning(f"Get progress error for '{company_id}': {e}")
            return None

    def set_progress(
        self,
        company_id: str,
        progress: dict[str, Any],
        expiry: int | None = None
    ) -> bool:
        """
        Set job progress for UI polling.

        Args:
            company_id: Company UUID
            progress: Progress dictionary
            expiry: TTL in seconds (default: 24 hours)

        Returns:
            True if successful
        """
        if not self._client:
            return False

        try:
            key = self._make_key("job", company_id, "progress")
            serialized = json.dumps(progress)
            self._client.setex(
                key,
                expiry or self.PROGRESS_EXPIRY,
                serialized
            )
            return True
        except (RedisError, TypeError, ValueError) as e:
            logger.warning(f"Set progress error for '{company_id}': {e}")
            return False

    def set_activity(self, company_id: str, activity: str) -> bool:
        """
        Set current activity description.

        Args:
            company_id: Company UUID
            activity: Current activity description

        Returns:
            True if successful
        """
        if not self._client:
            return False

        try:
            key = self._make_key("job", company_id, "activity")
            self._client.setex(key, self.PROGRESS_EXPIRY, activity)
            return True
        except RedisError as e:
            logger.warning(f"Set activity error for '{company_id}': {e}")
            return False

    def get_activity(self, company_id: str) -> str | None:
        """Get current activity description."""
        if not self._client:
            return None

        try:
            key = self._make_key("job", company_id, "activity")
            value = self._client.get(key)
            return value.decode('utf-8') if value else None
        except RedisError as e:
            logger.warning(f"Get activity error for '{company_id}': {e}")
            return None

    # ==================== Distributed Locking ====================

    def acquire_lock(
        self,
        company_id: str,
        worker_id: str,
        expiry: int | None = None
    ) -> bool:
        """
        Acquire distributed lock for a job.

        Args:
            company_id: Company UUID
            worker_id: Identifier for the worker acquiring the lock
            expiry: Lock expiry in seconds (default: 60 seconds)

        Returns:
            True if lock acquired, False if already locked
        """
        if not self._client:
            return False

        try:
            key = self._make_key("job", company_id, "lock")
            # SET NX ensures only one worker can acquire the lock
            acquired = self._client.set(
                key,
                worker_id,
                nx=True,
                ex=expiry or self.LOCK_EXPIRY
            )
            if acquired:
                logger.debug(f"Lock acquired for job {company_id} by {worker_id}")
            return bool(acquired)
        except RedisError as e:
            logger.warning(f"Acquire lock error for '{company_id}': {e}")
            return False

    def release_lock(self, company_id: str, worker_id: str) -> bool:
        """
        Release distributed lock for a job.

        Only releases if the lock is held by the same worker.

        Args:
            company_id: Company UUID
            worker_id: Identifier for the worker releasing the lock

        Returns:
            True if lock released, False otherwise
        """
        if not self._client:
            return False

        try:
            key = self._make_key("job", company_id, "lock")
            # Use Lua script for atomic check-and-delete
            script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
            result = self._client.eval(script, 1, key, worker_id)
            if result:
                logger.debug(f"Lock released for job {company_id} by {worker_id}")
            return bool(result)
        except RedisError as e:
            logger.warning(f"Release lock error for '{company_id}': {e}")
            return False

    def extend_lock(
        self,
        company_id: str,
        worker_id: str,
        expiry: int | None = None
    ) -> bool:
        """
        Extend lock expiry time.

        Args:
            company_id: Company UUID
            worker_id: Identifier for the worker holding the lock
            expiry: New expiry in seconds

        Returns:
            True if extended, False if not holding lock
        """
        if not self._client:
            return False

        try:
            key = self._make_key("job", company_id, "lock")
            # Use Lua script for atomic check-and-expire
            script = """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("expire", KEYS[1], ARGV[2])
            else
                return 0
            end
            """
            result = self._client.eval(
                script, 1, key, worker_id, str(expiry or self.LOCK_EXPIRY)
            )
            return bool(result)
        except RedisError as e:
            logger.warning(f"Extend lock error for '{company_id}': {e}")
            return False

    def get_lock_holder(self, company_id: str) -> str | None:
        """Get the worker ID holding the lock."""
        if not self._client:
            return None

        try:
            key = self._make_key("job", company_id, "lock")
            value = self._client.get(key)
            return value.decode('utf-8') if value else None
        except RedisError as e:
            logger.warning(f"Get lock holder error for '{company_id}': {e}")
            return None

    # ==================== Cleanup Operations ====================

    def cleanup_job(self, company_id: str) -> bool:
        """
        Clean up all Redis keys for a job.

        Args:
            company_id: Company UUID

        Returns:
            True if cleaned up
        """
        if not self._client:
            return False

        try:
            pattern = self._make_key("job", company_id, "*")
            keys = list(self._client.scan_iter(pattern))
            if keys:
                self._client.delete(*keys)
                logger.debug(f"Cleaned up {len(keys)} keys for job {company_id}")
            return True
        except RedisError as e:
            logger.warning(f"Cleanup error for '{company_id}': {e}")
            return False

    def cleanup_stale_jobs(self, max_age_seconds: int = 3600) -> list[str]:
        """
        Find and cleanup stale job keys.

        Args:
            max_age_seconds: Maximum age for job keys

        Returns:
            List of cleaned up company IDs
        """
        if not self._client:
            return []

        # Note: This is a simplified implementation
        # In production, you'd track job timestamps
        cleaned = []
        try:
            pattern = self._make_key("job", "*", "status")
            for key in self._client.scan_iter(pattern):
                ttl = self._client.ttl(key)
                # If TTL is -1 (no expiry) or expired, clean up
                if ttl == -1:
                    # Extract company_id from key
                    parts = key.decode('utf-8').split(':')
                    if len(parts) >= 3:
                        company_id = parts[2]
                        self.cleanup_job(company_id)
                        cleaned.append(company_id)
        except RedisError as e:
            logger.warning(f"Stale job cleanup error: {e}")

        return cleaned


# Global instance (initialized via init_app)
redis_service = RedisService()
