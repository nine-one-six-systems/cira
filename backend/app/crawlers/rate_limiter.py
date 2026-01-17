"""Rate limiter service for polite web crawling."""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse

from app.crawlers.robots_parser import robots_parser
from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


@dataclass
class DomainBucket:
    """Token bucket for rate limiting a single domain."""

    domain: str
    tokens: float = 1.0  # Current tokens
    max_tokens: float = 1.0  # Maximum burst capacity
    refill_rate: float = 1.0  # Tokens per second (1 = 1 request/sec)
    last_refill: float = field(default_factory=time.time)
    crawl_delay: float | None = None  # From robots.txt
    last_request: float = 0.0  # Timestamp of last request

    def get_effective_delay(self) -> float:
        """Get effective delay considering crawl-delay and refill rate."""
        base_delay = 1.0 / self.refill_rate  # Time between requests at base rate
        if self.crawl_delay is not None and self.crawl_delay > base_delay:
            return self.crawl_delay
        return base_delay

    def refill(self) -> None:
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now

    def can_acquire(self) -> bool:
        """Check if a token can be acquired without blocking."""
        self.refill()
        return self.tokens >= 1.0

    def acquire(self) -> bool:
        """
        Try to acquire a token (non-blocking).

        Returns:
            True if token acquired, False if no tokens available
        """
        self.refill()
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            self.last_request = time.time()
            return True
        return False

    def wait_time(self) -> float:
        """Calculate time to wait before a token is available."""
        self.refill()
        if self.tokens >= 1.0:
            return 0.0
        # Calculate time needed to get 1 token
        tokens_needed = 1.0 - self.tokens
        wait = tokens_needed / self.refill_rate
        return max(wait, 0.0)

    def time_since_last_request(self) -> float:
        """Get time since last request to this domain."""
        if self.last_request == 0.0:
            return float('inf')  # Never made a request
        return time.time() - self.last_request


class RateLimiter:
    """
    Rate limiter for polite web crawling.

    Features:
    - Per-domain rate limiting (default 1 request/second)
    - Respects Crawl-delay from robots.txt if higher
    - Token bucket algorithm for burst handling
    - No parallel requests to same domain
    - Thread-safe operations
    """

    DEFAULT_RATE = 1.0  # 1 request per second
    DEFAULT_BURST = 1.0  # No burst (1 token max)

    def __init__(
        self,
        default_rate: float | None = None,
        default_burst: float | None = None,
        redis_svc=None,
        robots_svc=None
    ):
        """
        Initialize rate limiter.

        Args:
            default_rate: Default requests per second per domain
            default_burst: Maximum burst tokens (for occasional faster requests)
            redis_svc: Redis service for distributed rate limiting (optional)
            robots_svc: Robots parser for crawl-delay (optional)
        """
        self._default_rate = default_rate or self.DEFAULT_RATE
        self._default_burst = default_burst or self.DEFAULT_BURST
        self._redis = redis_svc or redis_service
        self._robots = robots_svc or robots_parser
        self._buckets: dict[str, DomainBucket] = {}
        self._lock = threading.Lock()
        self._domain_locks: dict[str, threading.Lock] = {}

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc or url

    def _get_bucket(self, domain: str) -> DomainBucket:
        """Get or create token bucket for a domain."""
        with self._lock:
            if domain not in self._buckets:
                # Create new bucket
                bucket = DomainBucket(
                    domain=domain,
                    tokens=self._default_burst,
                    max_tokens=self._default_burst,
                    refill_rate=self._default_rate
                )
                self._buckets[domain] = bucket
                # Create domain-specific lock
                self._domain_locks[domain] = threading.Lock()
            return self._buckets[domain]

    def _get_domain_lock(self, domain: str) -> threading.Lock:
        """Get lock for a specific domain."""
        with self._lock:
            if domain not in self._domain_locks:
                self._domain_locks[domain] = threading.Lock()
            return self._domain_locks[domain]

    def set_crawl_delay(self, url: str, delay: float | None) -> None:
        """
        Set crawl delay for a domain (usually from robots.txt).

        Args:
            url: URL to set delay for
            delay: Crawl delay in seconds, or None to clear
        """
        domain = self._get_domain(url)
        bucket = self._get_bucket(domain)
        bucket.crawl_delay = delay
        logger.debug(f"Set crawl-delay={delay}s for {domain}")

    def configure_domain(
        self,
        url: str,
        rate: float | None = None,
        burst: float | None = None
    ) -> None:
        """
        Configure rate limiting for a specific domain.

        Args:
            url: URL to configure
            rate: Requests per second
            burst: Maximum burst capacity
        """
        domain = self._get_domain(url)
        bucket = self._get_bucket(domain)

        if rate is not None:
            bucket.refill_rate = rate
        if burst is not None:
            bucket.max_tokens = burst
            bucket.tokens = min(bucket.tokens, burst)

        logger.debug(
            f"Configured rate limiting for {domain}: "
            f"rate={bucket.refill_rate}/s, burst={bucket.max_tokens}"
        )

    def can_request(self, url: str) -> bool:
        """
        Check if a request can be made to a URL without blocking.

        Args:
            url: URL to check

        Returns:
            True if request can be made immediately
        """
        domain = self._get_domain(url)
        bucket = self._get_bucket(domain)
        domain_lock = self._get_domain_lock(domain)

        # Check if domain lock is available
        if domain_lock.locked():
            return False

        return bucket.can_acquire()

    def wait_time_for(self, url: str) -> float:
        """
        Get time to wait before making a request to a URL.

        Args:
            url: URL to check

        Returns:
            Seconds to wait (0 if can request immediately)
        """
        domain = self._get_domain(url)
        bucket = self._get_bucket(domain)
        return bucket.wait_time()

    def acquire(self, url: str, blocking: bool = True, timeout: float = 30.0) -> bool:
        """
        Acquire permission to make a request to a URL.

        Args:
            url: URL to request
            blocking: If True, wait for permission; if False, return immediately
            timeout: Maximum time to wait in blocking mode

        Returns:
            True if permission acquired, False otherwise
        """
        domain = self._get_domain(url)
        bucket = self._get_bucket(domain)
        domain_lock = self._get_domain_lock(domain)

        start_time = time.time()

        while True:
            # Try to acquire domain lock (ensures no parallel requests)
            if not domain_lock.acquire(blocking=False):
                if not blocking:
                    return False
                if time.time() - start_time > timeout:
                    logger.warning(f"Timeout waiting for domain lock: {domain}")
                    return False
                time.sleep(0.01)  # Brief sleep before retry
                continue

            try:
                # Check token bucket
                if bucket.acquire():
                    logger.debug(f"Rate limiter: acquired permit for {domain}")
                    return True

                if not blocking:
                    domain_lock.release()
                    return False

                # Calculate wait time
                wait = bucket.wait_time()
                effective_delay = bucket.get_effective_delay()
                wait = max(wait, effective_delay - bucket.time_since_last_request())

                if time.time() - start_time + wait > timeout:
                    logger.warning(f"Timeout waiting for rate limit: {domain}")
                    domain_lock.release()
                    return False

                # Wait and retry
                domain_lock.release()
                time.sleep(min(wait, 0.1))  # Sleep in small increments

            except Exception:
                domain_lock.release()
                raise

    def release(self, url: str) -> None:
        """
        Release domain lock after completing a request.

        MUST be called after acquire() returns True.

        Args:
            url: URL that was requested
        """
        domain = self._get_domain(url)
        domain_lock = self._get_domain_lock(domain)

        try:
            domain_lock.release()
            logger.debug(f"Rate limiter: released permit for {domain}")
        except RuntimeError:
            # Lock wasn't held - this is OK, might be released twice
            pass

    async def acquire_async(
        self,
        url: str,
        timeout: float = 30.0
    ) -> bool:
        """
        Async version of acquire.

        Args:
            url: URL to request
            timeout: Maximum time to wait

        Returns:
            True if permission acquired
        """
        domain = self._get_domain(url)
        bucket = self._get_bucket(domain)
        domain_lock = self._get_domain_lock(domain)

        start_time = time.time()

        while True:
            # Try to acquire domain lock
            if not domain_lock.acquire(blocking=False):
                if time.time() - start_time > timeout:
                    return False
                await asyncio.sleep(0.01)
                continue

            try:
                # Check token bucket
                if bucket.acquire():
                    return True

                # Calculate wait time
                wait = bucket.wait_time()
                effective_delay = bucket.get_effective_delay()
                wait = max(wait, effective_delay - bucket.time_since_last_request())

                if time.time() - start_time + wait > timeout:
                    domain_lock.release()
                    return False

                # Wait and retry
                domain_lock.release()
                await asyncio.sleep(min(wait, 0.1))

            except Exception:
                domain_lock.release()
                raise

    def apply_robots_delay(self, url: str) -> None:
        """
        Check robots.txt and apply crawl-delay if specified.

        Args:
            url: URL to check robots.txt for
        """
        try:
            crawl_delay = self._robots.get_crawl_delay(url)
            if crawl_delay is not None:
                self.set_crawl_delay(url, crawl_delay)
        except Exception as e:
            logger.warning(f"Failed to get robots.txt crawl-delay: {e}")

    def get_stats(self) -> dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dictionary with stats per domain
        """
        stats = {}
        with self._lock:
            for domain, bucket in self._buckets.items():
                stats[domain] = {
                    'tokens': bucket.tokens,
                    'max_tokens': bucket.max_tokens,
                    'refill_rate': bucket.refill_rate,
                    'crawl_delay': bucket.crawl_delay,
                    'effective_delay': bucket.get_effective_delay(),
                    'last_request': bucket.last_request,
                    'time_since_last': bucket.time_since_last_request(),
                }
        return stats

    def reset_domain(self, url: str) -> None:
        """
        Reset rate limiting for a domain.

        Args:
            url: URL whose domain should be reset
        """
        domain = self._get_domain(url)
        with self._lock:
            if domain in self._buckets:
                del self._buckets[domain]
            if domain in self._domain_locks:
                del self._domain_locks[domain]
        logger.debug(f"Reset rate limiting for {domain}")

    def reset_all(self) -> None:
        """Reset all rate limiting state."""
        with self._lock:
            self._buckets.clear()
            self._domain_locks.clear()
        logger.debug("Reset all rate limiting state")


class RateLimitedContext:
    """
    Context manager for rate-limited requests.

    Usage:
        async with RateLimitedContext(rate_limiter, url):
            # Make request
            response = await fetch(url)
    """

    def __init__(
        self,
        rate_limiter: RateLimiter,
        url: str,
        timeout: float = 30.0
    ):
        self._limiter = rate_limiter
        self._url = url
        self._timeout = timeout
        self._acquired = False

    def __enter__(self):
        self._acquired = self._limiter.acquire(self._url, timeout=self._timeout)
        if not self._acquired:
            raise TimeoutError(f"Rate limit timeout for {self._url}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._acquired:
            self._limiter.release(self._url)
        return False

    async def __aenter__(self):
        self._acquired = await self._limiter.acquire_async(
            self._url,
            timeout=self._timeout
        )
        if not self._acquired:
            raise TimeoutError(f"Rate limit timeout for {self._url}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._acquired:
            self._limiter.release(self._url)
        return False


# Global instance
rate_limiter = RateLimiter()
