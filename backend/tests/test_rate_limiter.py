"""Tests for rate limiter service."""

import asyncio
import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from app.crawlers.rate_limiter import (
    DomainBucket,
    RateLimiter,
    RateLimitedContext,
    rate_limiter,
)


class TestDomainBucket:
    """Tests for DomainBucket class."""

    def test_initial_state(self):
        """Test bucket starts with full tokens."""
        bucket = DomainBucket(domain='example.com')
        assert bucket.tokens == 1.0
        assert bucket.max_tokens == 1.0
        assert bucket.refill_rate == 1.0

    def test_acquire_token(self):
        """Test acquiring a token."""
        bucket = DomainBucket(domain='example.com', tokens=1.0)
        assert bucket.acquire() is True
        assert bucket.tokens == 0.0

    def test_acquire_no_tokens(self):
        """Test acquiring when no tokens available."""
        bucket = DomainBucket(domain='example.com', tokens=0.0)
        bucket.last_refill = time.time()  # Prevent refill
        assert bucket.acquire() is False

    def test_refill_over_time(self):
        """Test tokens refill over time."""
        bucket = DomainBucket(
            domain='example.com',
            tokens=0.0,
            max_tokens=10.0,  # Allow up to 10 tokens
            refill_rate=10.0  # 10 tokens per second
        )
        bucket.last_refill = time.time() - 0.5  # 0.5 seconds ago
        bucket.refill()
        # Should have gained ~5 tokens (0.5s * 10/s)
        assert 4.5 <= bucket.tokens <= 5.5

    def test_refill_max_cap(self):
        """Test tokens don't exceed max."""
        bucket = DomainBucket(
            domain='example.com',
            tokens=0.0,
            max_tokens=2.0,
            refill_rate=10.0
        )
        bucket.last_refill = time.time() - 1.0  # 1 second ago
        bucket.refill()
        assert bucket.tokens == 2.0  # Capped at max

    def test_can_acquire(self):
        """Test checking if can acquire."""
        bucket = DomainBucket(domain='example.com', tokens=1.0)
        assert bucket.can_acquire() is True

        bucket.tokens = 0.0
        bucket.last_refill = time.time()
        assert bucket.can_acquire() is False

    def test_wait_time_with_tokens(self):
        """Test wait time when tokens available."""
        bucket = DomainBucket(domain='example.com', tokens=1.0)
        assert bucket.wait_time() == 0.0

    def test_wait_time_no_tokens(self):
        """Test wait time when no tokens."""
        bucket = DomainBucket(
            domain='example.com',
            tokens=0.0,
            refill_rate=2.0  # 2 tokens per second
        )
        bucket.last_refill = time.time()
        wait = bucket.wait_time()
        # Need 1 token at 2 tokens/sec = 0.5s wait
        assert 0.4 <= wait <= 0.6

    def test_crawl_delay_effective(self):
        """Test crawl delay affects effective delay."""
        bucket = DomainBucket(
            domain='example.com',
            refill_rate=1.0,  # 1 token/sec = 1s base delay
            crawl_delay=3.0  # robots.txt specifies 3s
        )
        assert bucket.get_effective_delay() == 3.0

    def test_crawl_delay_ignored_if_lower(self):
        """Test crawl delay ignored if lower than base rate."""
        bucket = DomainBucket(
            domain='example.com',
            refill_rate=0.5,  # 0.5 token/sec = 2s base delay
            crawl_delay=1.0  # robots.txt specifies 1s
        )
        # Should use base delay of 2s since it's higher
        assert bucket.get_effective_delay() == 2.0

    def test_time_since_last_request(self):
        """Test tracking time since last request."""
        bucket = DomainBucket(domain='example.com')

        # Never made request
        assert bucket.time_since_last_request() == float('inf')

        # Make a request
        bucket.last_request = time.time() - 1.0
        elapsed = bucket.time_since_last_request()
        assert 0.9 <= elapsed <= 1.2


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis service."""
        mock = MagicMock()
        mock.is_available = True
        return mock

    @pytest.fixture
    def mock_robots(self):
        """Create mock robots parser."""
        mock = MagicMock()
        mock.get_crawl_delay.return_value = None
        return mock

    @pytest.fixture
    def limiter(self, mock_redis, mock_robots):
        """Create rate limiter with mocks."""
        return RateLimiter(
            default_rate=10.0,  # Fast for tests
            redis_svc=mock_redis,
            robots_svc=mock_robots
        )

    def test_get_domain(self, limiter):
        """Test domain extraction."""
        assert limiter._get_domain('https://example.com/page') == 'example.com'
        assert limiter._get_domain('http://sub.example.com:8080/') == 'sub.example.com:8080'

    def test_acquire_first_request(self, limiter):
        """Test first request is allowed immediately."""
        url = 'https://example.com/page1'
        assert limiter.acquire(url, blocking=False) is True
        limiter.release(url)

    def test_acquire_rate_limited(self, limiter):
        """Test subsequent requests are rate limited."""
        url = 'https://example.com/page'

        # First request - should succeed
        assert limiter.acquire(url, blocking=False) is True
        # Don't release yet - domain should be locked

        # Second request should fail (domain locked)
        assert limiter.acquire(url, blocking=False) is False

        # Release first
        limiter.release(url)

        # Now second should work (with high rate, tokens refill fast)
        time.sleep(0.15)  # Wait for tokens to refill at 10/sec
        assert limiter.acquire(url, blocking=False) is True
        limiter.release(url)

    def test_acquire_blocking(self, limiter):
        """Test blocking acquire waits for permission."""
        url = 'https://example.com/page'

        # Acquire in another thread
        acquired = []

        def acquire_in_thread():
            time.sleep(0.1)  # Small delay
            result = limiter.acquire(url, blocking=True, timeout=2.0)
            acquired.append(result)

        # First acquire
        assert limiter.acquire(url, blocking=False) is True

        # Start thread that will wait
        thread = threading.Thread(target=acquire_in_thread)
        thread.start()

        # Release after a short delay
        time.sleep(0.05)
        limiter.release(url)

        thread.join(timeout=3.0)
        assert len(acquired) == 1
        assert acquired[0] is True

    def test_acquire_timeout(self):
        """Test acquire times out."""
        # Use slow rate limiter
        limiter = RateLimiter(default_rate=0.1)  # 0.1 req/sec = 10s between
        url = 'https://example.com/page'

        # Acquire first
        assert limiter.acquire(url, blocking=False) is True

        # Second with short timeout should fail
        start = time.time()
        result = limiter.acquire(url, blocking=True, timeout=0.2)
        elapsed = time.time() - start

        assert result is False
        assert elapsed >= 0.15  # Should have waited close to timeout

        limiter.release(url)

    def test_different_domains_not_limited(self, limiter):
        """Test different domains are independent."""
        url1 = 'https://example.com/page'
        url2 = 'https://other.com/page'

        # Both should succeed immediately
        assert limiter.acquire(url1, blocking=False) is True
        assert limiter.acquire(url2, blocking=False) is True

        limiter.release(url1)
        limiter.release(url2)

    def test_can_request(self, limiter):
        """Test can_request check."""
        url = 'https://example.com/page'
        assert limiter.can_request(url) is True

        limiter.acquire(url, blocking=False)
        assert limiter.can_request(url) is False  # Domain locked

        limiter.release(url)
        time.sleep(0.15)
        assert limiter.can_request(url) is True

    def test_wait_time_for(self, limiter):
        """Test wait time calculation."""
        url = 'https://example.com/page'
        assert limiter.wait_time_for(url) == 0.0  # Has tokens

        # Use up token
        limiter.acquire(url, blocking=False)
        limiter.release(url)

        wait = limiter.wait_time_for(url)
        assert wait > 0.0  # Should need to wait

    def test_set_crawl_delay(self, limiter):
        """Test setting crawl delay."""
        url = 'https://example.com/page'
        limiter.set_crawl_delay(url, 5.0)

        bucket = limiter._get_bucket('example.com')
        assert bucket.crawl_delay == 5.0

    def test_configure_domain(self, limiter):
        """Test configuring domain rate."""
        url = 'https://example.com/page'
        limiter.configure_domain(url, rate=0.5, burst=3.0)

        bucket = limiter._get_bucket('example.com')
        assert bucket.refill_rate == 0.5
        assert bucket.max_tokens == 3.0

    def test_apply_robots_delay(self, mock_redis, mock_robots):
        """Test applying crawl-delay from robots.txt."""
        mock_robots.get_crawl_delay.return_value = 2.5
        limiter = RateLimiter(redis_svc=mock_redis, robots_svc=mock_robots)

        url = 'https://example.com/page'
        limiter.apply_robots_delay(url)

        bucket = limiter._get_bucket('example.com')
        assert bucket.crawl_delay == 2.5

    def test_apply_robots_delay_none(self, limiter, mock_robots):
        """Test when robots.txt has no crawl-delay."""
        mock_robots.get_crawl_delay.return_value = None

        url = 'https://example.com/page'
        limiter.apply_robots_delay(url)

        bucket = limiter._get_bucket('example.com')
        assert bucket.crawl_delay is None

    def test_get_stats(self, limiter):
        """Test getting stats."""
        url = 'https://example.com/page'
        limiter.acquire(url, blocking=False)
        limiter.release(url)

        stats = limiter.get_stats()
        assert 'example.com' in stats
        assert 'tokens' in stats['example.com']
        assert 'refill_rate' in stats['example.com']

    def test_reset_domain(self, limiter):
        """Test resetting a domain."""
        url = 'https://example.com/page'
        limiter.acquire(url, blocking=False)
        limiter.release(url)

        limiter.reset_domain(url)

        # Bucket should be recreated fresh
        bucket = limiter._get_bucket('example.com')
        assert bucket.tokens == limiter._default_burst

    def test_reset_all(self, limiter):
        """Test resetting all state."""
        limiter.acquire('https://example.com/page', blocking=False)
        limiter.release('https://example.com/page')
        limiter.acquire('https://other.com/page', blocking=False)
        limiter.release('https://other.com/page')

        limiter.reset_all()

        assert len(limiter._buckets) == 0
        assert len(limiter._domain_locks) == 0

    def test_release_not_held(self, limiter):
        """Test release when lock not held doesn't crash."""
        url = 'https://example.com/page'
        # Release without acquire should not raise
        limiter.release(url)


class TestRateLimiterAsync:
    """Tests for async rate limiter methods."""

    @pytest.fixture
    def limiter(self):
        """Create rate limiter for async tests."""
        return RateLimiter(default_rate=10.0)

    @pytest.mark.asyncio
    async def test_acquire_async(self, limiter):
        """Test async acquire."""
        url = 'https://example.com/page'
        result = await limiter.acquire_async(url, timeout=1.0)
        assert result is True
        limiter.release(url)

    @pytest.mark.asyncio
    async def test_acquire_async_multiple(self, limiter):
        """Test multiple async acquires."""
        url = 'https://example.com/page'

        # First acquire
        result1 = await limiter.acquire_async(url, timeout=1.0)
        assert result1 is True

        # Second should wait (but succeed with high rate)
        async def delayed_release():
            await asyncio.sleep(0.05)
            limiter.release(url)

        task = asyncio.create_task(delayed_release())
        result2 = await limiter.acquire_async(url, timeout=1.0)
        assert result2 is True

        await task
        limiter.release(url)

    @pytest.mark.asyncio
    async def test_acquire_async_timeout(self):
        """Test async acquire timeout."""
        limiter = RateLimiter(default_rate=0.1)  # Slow rate
        url = 'https://example.com/page'

        # First acquire
        result1 = await limiter.acquire_async(url, timeout=1.0)
        assert result1 is True

        # Second should timeout
        result2 = await limiter.acquire_async(url, timeout=0.1)
        assert result2 is False

        limiter.release(url)


class TestRateLimitedContext:
    """Tests for RateLimitedContext context manager."""

    @pytest.fixture
    def limiter(self):
        """Create rate limiter."""
        return RateLimiter(default_rate=10.0)

    def test_sync_context_manager(self, limiter):
        """Test sync context manager."""
        url = 'https://example.com/page'

        with RateLimitedContext(limiter, url):
            # Should be able to use the limiter
            assert limiter._get_domain_lock('example.com').locked()

        # Lock should be released
        assert not limiter._get_domain_lock('example.com').locked()

    def test_sync_context_manager_timeout(self):
        """Test sync context manager timeout."""
        limiter = RateLimiter(default_rate=0.1)
        url = 'https://example.com/page'

        # Hold the lock
        limiter.acquire(url, blocking=False)

        with pytest.raises(TimeoutError):
            with RateLimitedContext(limiter, url, timeout=0.1):
                pass

        limiter.release(url)

    @pytest.mark.asyncio
    async def test_async_context_manager(self, limiter):
        """Test async context manager."""
        url = 'https://example.com/page'

        async with RateLimitedContext(limiter, url):
            # Should be in the context
            assert limiter._get_domain_lock('example.com').locked()

        # Lock should be released
        assert not limiter._get_domain_lock('example.com').locked()

    @pytest.mark.asyncio
    async def test_async_context_manager_timeout(self):
        """Test async context manager timeout."""
        limiter = RateLimiter(default_rate=0.1)
        url = 'https://example.com/page'

        # Hold the lock
        await limiter.acquire_async(url, timeout=1.0)

        with pytest.raises(TimeoutError):
            async with RateLimitedContext(limiter, url, timeout=0.1):
                pass

        limiter.release(url)


class TestRateLimiterConcurrency:
    """Tests for concurrent rate limiting."""

    def test_concurrent_different_domains(self):
        """Test concurrent requests to different domains."""
        limiter = RateLimiter(default_rate=10.0)
        results = []
        errors = []

        def make_request(url, index):
            try:
                if limiter.acquire(url, blocking=True, timeout=2.0):
                    time.sleep(0.01)  # Simulate request
                    results.append((index, url))
                    limiter.release(url)
                else:
                    errors.append((index, 'timeout'))
            except Exception as e:
                errors.append((index, str(e)))

        threads = []
        for i in range(10):
            url = f'https://domain{i % 5}.com/page'  # 5 different domains
            t = threading.Thread(target=make_request, args=(url, i))
            threads.append(t)
            t.start()

        for t in threads:
            t.join(timeout=5.0)

        assert len(errors) == 0
        assert len(results) == 10

    def test_concurrent_same_domain(self):
        """Test concurrent requests to same domain are serialized."""
        limiter = RateLimiter(default_rate=100.0)  # Fast refill
        url = 'https://example.com/page'
        order = []
        lock = threading.Lock()

        def make_request(index):
            if limiter.acquire(url, blocking=True, timeout=5.0):
                with lock:
                    order.append(f'start-{index}')
                time.sleep(0.02)  # Simulate request
                with lock:
                    order.append(f'end-{index}')
                limiter.release(url)

        threads = []
        for i in range(5):
            t = threading.Thread(target=make_request, args=(i,))
            threads.append(t)

        # Start all threads nearly simultaneously
        for t in threads:
            t.start()

        for t in threads:
            t.join(timeout=10.0)

        # Verify requests are serialized (each end comes before next start)
        # The pattern should be: start-X, end-X, start-Y, end-Y, ...
        assert len(order) == 10

        # Check that no two requests overlap
        in_progress = 0
        max_concurrent = 0
        for event in order:
            if event.startswith('start'):
                in_progress += 1
                max_concurrent = max(max_concurrent, in_progress)
            else:
                in_progress -= 1

        assert max_concurrent == 1  # Only one at a time


class TestRateLimiterRobotsTxtIntegration:
    """Tests for rate limiter integration with robots.txt."""

    def test_respects_crawl_delay(self):
        """Test that crawl-delay from robots.txt is respected."""
        mock_robots = MagicMock()
        mock_robots.get_crawl_delay.return_value = 0.5  # 0.5 second delay

        limiter = RateLimiter(
            default_rate=10.0,  # 10/sec = 0.1s between requests
            robots_svc=mock_robots
        )
        url = 'https://example.com/page'

        # Apply robots delay
        limiter.apply_robots_delay(url)

        # First request
        limiter.acquire(url, blocking=False)
        limiter.release(url)

        bucket = limiter._get_bucket('example.com')
        assert bucket.get_effective_delay() == 0.5  # Should use robots.txt delay
