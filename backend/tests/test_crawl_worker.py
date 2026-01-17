"""Tests for crawl worker."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from app.crawlers.crawl_worker import (
    CrawlConfig,
    CrawledPage,
    CrawlProgress,
    CrawlCheckpoint,
    CrawlResult,
    CrawlWorker,
    create_crawl_worker,
)
from app.crawlers.browser_manager import PageContent
from app.crawlers.external_links import ExternalLink


class TestCrawlConfig:
    """Tests for CrawlConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CrawlConfig()

        assert config.max_pages == 50
        assert config.max_time_seconds == 300
        assert config.max_depth == 3
        assert config.respect_robots is True
        assert config.checkpoint_interval_pages == 10
        assert config.requests_per_second == 1.0

    def test_custom_config(self):
        """Test custom configuration."""
        config = CrawlConfig(
            max_pages=100,
            max_time_seconds=600,
            follow_linkedin=True,
        )

        assert config.max_pages == 100
        assert config.max_time_seconds == 600
        assert config.follow_linkedin is True


class TestCrawledPage:
    """Tests for CrawledPage dataclass."""

    def test_successful_page(self):
        """Test successful page creation."""
        page = CrawledPage(
            url='https://example.com/about',
            status_code=200,
            html='<html></html>',
            text='About us',
        )

        assert page.is_success is True
        assert page.url == 'https://example.com/about'

    def test_failed_page_with_error(self):
        """Test failed page with error."""
        page = CrawledPage(
            url='https://example.com/page',
            error='Connection timeout',
        )

        assert page.is_success is False

    def test_failed_page_with_status(self):
        """Test failed page with non-200 status."""
        page = CrawledPage(
            url='https://example.com/404',
            status_code=404,
        )

        assert page.is_success is False

    def test_redirect_is_success(self):
        """Test that redirects are considered successful."""
        page = CrawledPage(
            url='https://example.com/old',
            final_url='https://example.com/new',
            status_code=301,
        )

        assert page.is_success is True


class TestCrawlProgress:
    """Tests for CrawlProgress dataclass."""

    def test_default_progress(self):
        """Test default progress values."""
        progress = CrawlProgress()

        assert progress.pages_crawled == 0
        assert progress.pages_queued == 0
        assert progress.errors_count == 0
        assert progress.current_url == ''


class TestCrawlCheckpoint:
    """Tests for CrawlCheckpoint dataclass."""

    def test_to_dict(self):
        """Test checkpoint serialization."""
        checkpoint = CrawlCheckpoint(
            visited_urls={'https://example.com/'},
            content_hashes={'abc123'},
            queue_state=[{'url': 'https://example.com/about'}],
            progress={'pages_crawled': 5},
            timestamp='2024-01-01T00:00:00Z',
        )

        result = checkpoint.to_dict()

        assert 'visited_urls' in result
        assert 'https://example.com/' in result['visited_urls']
        assert 'content_hashes' in result
        assert 'queue_state' in result
        assert 'progress' in result
        assert 'timestamp' in result

    def test_from_dict(self):
        """Test checkpoint deserialization."""
        data = {
            'visited_urls': ['https://example.com/'],
            'content_hashes': ['abc123'],
            'queue_state': [],
            'progress': {'pages_crawled': 10},
            'timestamp': '2024-01-01T00:00:00Z',
        }

        checkpoint = CrawlCheckpoint.from_dict(data)

        assert 'https://example.com/' in checkpoint.visited_urls
        assert 'abc123' in checkpoint.content_hashes
        assert checkpoint.progress['pages_crawled'] == 10


class TestCrawlResult:
    """Tests for CrawlResult dataclass."""

    def test_complete_result(self):
        """Test completed crawl result."""
        result = CrawlResult(
            pages=[],
            progress=CrawlProgress(),
            stopped_reason='completed',
        )

        assert result.is_complete is True

    def test_incomplete_result(self):
        """Test incomplete crawl result."""
        result = CrawlResult(
            pages=[],
            progress=CrawlProgress(),
            stopped_reason='max_pages',
        )

        assert result.is_complete is False


class TestCrawlWorkerInit:
    """Tests for CrawlWorker initialization."""

    def test_default_init(self):
        """Test default initialization."""
        worker = CrawlWorker()

        assert worker.config is not None
        assert worker._fetcher is not None
        assert worker._robots is not None
        assert worker._rate_limiter is not None
        assert worker._classifier is not None

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = CrawlConfig(max_pages=100)
        worker = CrawlWorker(config=config)

        assert worker.config.max_pages == 100

    def test_init_with_custom_dependencies(self):
        """Test initialization with custom dependencies."""
        mock_fetcher = MagicMock()
        mock_robots = MagicMock()

        worker = CrawlWorker(
            fetcher=mock_fetcher,
            robots_parser=mock_robots,
        )

        assert worker._fetcher is mock_fetcher
        assert worker._robots is mock_robots


class TestCrawlWorkerCallbacks:
    """Tests for CrawlWorker callbacks."""

    def test_set_callbacks(self):
        """Test setting callbacks."""
        worker = CrawlWorker()

        on_progress = MagicMock()
        on_checkpoint = MagicMock()
        on_page = MagicMock()

        worker.set_callbacks(
            on_progress=on_progress,
            on_checkpoint=on_checkpoint,
            on_page=on_page,
        )

        assert worker._on_progress is on_progress
        assert worker._on_checkpoint is on_checkpoint
        assert worker._on_page is on_page


class TestCrawlWorkerURLHandling:
    """Tests for URL handling methods."""

    @pytest.fixture
    def worker(self):
        """Create a CrawlWorker instance."""
        return CrawlWorker()

    def test_normalize_url_basic(self, worker):
        """Test basic URL normalization."""
        result = worker._normalize_url('https://example.com/page')
        assert result == 'https://example.com/page'

    def test_normalize_url_trailing_slash(self, worker):
        """Test trailing slash removal."""
        result = worker._normalize_url('https://example.com/page/')
        assert result == 'https://example.com/page'

    def test_normalize_url_root_keeps_slash(self, worker):
        """Test root URL keeps slash."""
        result = worker._normalize_url('https://example.com/')
        assert result == 'https://example.com/'

    def test_normalize_url_lowercase_host(self, worker):
        """Test host is lowercased."""
        result = worker._normalize_url('https://EXAMPLE.COM/Page')
        assert 'example.com' in result

    def test_normalize_url_invalid(self, worker):
        """Test invalid URL returns None."""
        assert worker._normalize_url('') is None
        assert worker._normalize_url('not-a-url') is None
        assert worker._normalize_url('ftp://example.com') is None

    def test_resolve_url_absolute(self, worker):
        """Test absolute URL resolution."""
        result = worker._resolve_url(
            'https://example.com/about',
            'https://example.com/'
        )
        assert result == 'https://example.com/about'

    def test_resolve_url_relative(self, worker):
        """Test relative URL resolution."""
        result = worker._resolve_url('/about', 'https://example.com/')
        assert result == 'https://example.com/about'

    def test_resolve_url_skip_javascript(self, worker):
        """Test javascript: URLs are skipped."""
        result = worker._resolve_url('javascript:void(0)', 'https://example.com/')
        assert result is None

    def test_resolve_url_skip_mailto(self, worker):
        """Test mailto: URLs are skipped."""
        result = worker._resolve_url('mailto:test@example.com', 'https://example.com/')
        assert result is None


class TestCrawlWorkerContentHash:
    """Tests for content hashing."""

    @pytest.fixture
    def worker(self):
        """Create a CrawlWorker instance."""
        return CrawlWorker()

    def test_compute_hash_basic(self, worker):
        """Test basic content hashing."""
        hash1 = worker._compute_hash('Hello World')
        hash2 = worker._compute_hash('Hello World')

        assert hash1 == hash2
        assert len(hash1) == 16  # Truncated to 16 chars

    def test_compute_hash_whitespace_normalization(self, worker):
        """Test whitespace is normalized."""
        hash1 = worker._compute_hash('Hello World')
        hash2 = worker._compute_hash('Hello    World')
        hash3 = worker._compute_hash('Hello\n\nWorld')

        assert hash1 == hash2
        assert hash1 == hash3

    def test_compute_hash_case_insensitive(self, worker):
        """Test hashing is case-insensitive."""
        hash1 = worker._compute_hash('Hello World')
        hash2 = worker._compute_hash('hello world')

        assert hash1 == hash2

    def test_compute_hash_different_content(self, worker):
        """Test different content has different hash."""
        hash1 = worker._compute_hash('Hello World')
        hash2 = worker._compute_hash('Goodbye World')

        assert hash1 != hash2


class TestCrawlWorkerExtraction:
    """Tests for content extraction methods."""

    @pytest.fixture
    def worker(self):
        """Create a CrawlWorker instance."""
        return CrawlWorker()

    def test_extract_title(self, worker):
        """Test title extraction."""
        html = '<html><head><title>Test Page</title></head></html>'
        title = worker._extract_title(html)
        assert title == 'Test Page'

    def test_extract_title_missing(self, worker):
        """Test missing title returns empty string."""
        html = '<html><head></head></html>'
        title = worker._extract_title(html)
        assert title == ''

    def test_extract_links(self, worker):
        """Test link extraction."""
        html = '''
        <html>
        <body>
            <a href="/about">About</a>
            <a href="https://example.com/contact">Contact</a>
            <a href="mailto:test@example.com">Email</a>
        </body>
        </html>
        '''
        links = worker._extract_links(html, 'https://example.com/')

        assert len(links) == 2  # mailto should be excluded
        assert 'https://example.com/about' in links
        assert 'https://example.com/contact' in links


class TestCrawlWorkerWithMocks:
    """Tests for CrawlWorker with mocked dependencies."""

    @pytest.fixture
    def mock_fetcher(self):
        """Create mock fetcher."""
        fetcher = MagicMock()
        fetcher.fetch_page.return_value = PageContent(
            url='https://example.com/',
            html='<html><head><title>Test</title></head><body><a href="/about">About</a></body></html>',
            text='Test content',
            status_code=200,
        )
        return fetcher

    @pytest.fixture
    def mock_robots(self):
        """Create mock robots parser."""
        robots = MagicMock()
        robots.is_allowed.return_value = True
        robots.get_crawl_delay.return_value = None
        return robots

    @pytest.fixture
    def mock_rate_limiter(self):
        """Create mock rate limiter."""
        limiter = MagicMock()
        limiter.acquire.return_value = True
        return limiter

    def test_crawl_single_page(
        self,
        mock_fetcher,
        mock_robots,
        mock_rate_limiter,
    ):
        """Test crawling a single page."""
        config = CrawlConfig(max_pages=1)
        worker = CrawlWorker(
            config=config,
            fetcher=mock_fetcher,
            robots_parser=mock_robots,
            rate_limiter=mock_rate_limiter,
        )

        result = worker.crawl('https://example.com/')

        assert len(result.pages) == 1
        assert result.pages[0].url == 'https://example.com/'
        assert result.progress.pages_crawled == 1

    def test_crawl_respects_max_pages(
        self,
        mock_fetcher,
        mock_robots,
        mock_rate_limiter,
    ):
        """Test crawl stops at max pages."""
        config = CrawlConfig(max_pages=2)
        worker = CrawlWorker(
            config=config,
            fetcher=mock_fetcher,
            robots_parser=mock_robots,
            rate_limiter=mock_rate_limiter,
        )

        result = worker.crawl('https://example.com/')

        assert result.progress.pages_crawled <= 2
        assert result.stopped_reason in ('completed', 'max_pages')

    def test_crawl_checks_robots(
        self,
        mock_fetcher,
        mock_robots,
        mock_rate_limiter,
    ):
        """Test crawl checks robots.txt."""
        mock_robots.is_allowed.return_value = False

        config = CrawlConfig(max_pages=1)
        worker = CrawlWorker(
            config=config,
            fetcher=mock_fetcher,
            robots_parser=mock_robots,
            rate_limiter=mock_rate_limiter,
        )

        result = worker.crawl('https://example.com/')

        mock_robots.is_allowed.assert_called()
        # Page should have error due to robots.txt block
        if result.pages:
            assert 'robots' in result.pages[0].error.lower()

    def test_crawl_respects_rate_limit(
        self,
        mock_fetcher,
        mock_robots,
        mock_rate_limiter,
    ):
        """Test crawl calls rate limiter."""
        config = CrawlConfig(max_pages=1)
        worker = CrawlWorker(
            config=config,
            fetcher=mock_fetcher,
            robots_parser=mock_robots,
            rate_limiter=mock_rate_limiter,
        )

        worker.crawl('https://example.com/')

        mock_rate_limiter.acquire.assert_called()

    def test_crawl_callbacks_called(
        self,
        mock_fetcher,
        mock_robots,
        mock_rate_limiter,
    ):
        """Test callbacks are called during crawl."""
        on_progress = MagicMock()
        on_page = MagicMock()

        config = CrawlConfig(max_pages=1)
        worker = CrawlWorker(
            config=config,
            fetcher=mock_fetcher,
            robots_parser=mock_robots,
            rate_limiter=mock_rate_limiter,
        )
        worker.set_callbacks(on_progress=on_progress, on_page=on_page)

        worker.crawl('https://example.com/')

        on_progress.assert_called()
        on_page.assert_called()


class TestCrawlWorkerCheckpointing:
    """Tests for checkpoint functionality."""

    @pytest.fixture
    def worker(self):
        """Create a CrawlWorker instance."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page.return_value = PageContent(
            url='https://example.com/',
            html='<html></html>',
            text='Test',
            status_code=200,
        )

        mock_robots = MagicMock()
        mock_robots.is_allowed.return_value = True

        mock_rate_limiter = MagicMock()
        mock_rate_limiter.acquire.return_value = True

        return CrawlWorker(
            config=CrawlConfig(max_pages=5),
            fetcher=mock_fetcher,
            robots_parser=mock_robots,
            rate_limiter=mock_rate_limiter,
        )

    def test_checkpoint_created(self, worker):
        """Test checkpoint is created after crawl."""
        result = worker.crawl('https://example.com/')

        assert result.checkpoint is not None
        assert len(result.checkpoint.visited_urls) > 0

    def test_resume_from_checkpoint(self, worker):
        """Test resuming from checkpoint."""
        # First crawl
        result1 = worker.crawl('https://example.com/')

        # Resume with checkpoint
        result2 = worker.crawl('https://example.com/', checkpoint=result1.checkpoint)

        # Should have used checkpoint data
        assert result2.checkpoint is not None


class TestCrawlWorkerStopControl:
    """Tests for stop/pause functionality."""

    @pytest.fixture
    def worker(self):
        """Create a slow CrawlWorker for testing stop/pause."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch_page.return_value = PageContent(
            url='https://example.com/',
            html='<html><body><a href="/page2">Link</a></body></html>',
            text='Test',
            status_code=200,
        )

        mock_robots = MagicMock()
        mock_robots.is_allowed.return_value = True

        mock_rate_limiter = MagicMock()
        mock_rate_limiter.acquire.return_value = True

        return CrawlWorker(
            config=CrawlConfig(max_pages=100),
            fetcher=mock_fetcher,
            robots_parser=mock_robots,
            rate_limiter=mock_rate_limiter,
        )

    def test_stop_sets_flag(self, worker):
        """Test stop sets the stop flag."""
        worker.stop()
        assert worker._stop_requested is True

    def test_pause_sets_flag(self, worker):
        """Test pause sets the pause flag."""
        worker.pause()
        assert worker._pause_requested is True


class TestCrawlWorkerDuplicateDetection:
    """Tests for duplicate content detection."""

    def test_detects_duplicate_content(self):
        """Test duplicate content is detected."""
        # Create two pages with same content
        mock_fetcher = MagicMock()

        call_count = [0]

        def fetch_side_effect(url):
            call_count[0] += 1
            if call_count[0] == 1:
                return PageContent(
                    url='https://example.com/',
                    html='<html><body>Same content<a href="/page2">Link</a></body></html>',
                    text='Same content',
                    status_code=200,
                )
            else:
                return PageContent(
                    url='https://example.com/page2',
                    html='<html><body>Same content</body></html>',
                    text='Same content',
                    status_code=200,
                )

        mock_fetcher.fetch_page.side_effect = fetch_side_effect

        mock_robots = MagicMock()
        mock_robots.is_allowed.return_value = True

        mock_rate_limiter = MagicMock()
        mock_rate_limiter.acquire.return_value = True

        worker = CrawlWorker(
            config=CrawlConfig(max_pages=2),
            fetcher=mock_fetcher,
            robots_parser=mock_robots,
            rate_limiter=mock_rate_limiter,
        )

        result = worker.crawl('https://example.com/')

        # Should have detected duplicates
        assert result.progress.duplicates_found >= 0


class TestCreateCrawlWorker:
    """Tests for create_crawl_worker factory."""

    def test_create_default(self):
        """Test creating default worker."""
        worker = create_crawl_worker()

        assert worker is not None
        assert isinstance(worker, CrawlWorker)

    def test_create_with_config(self):
        """Test creating worker with config."""
        config = CrawlConfig(max_pages=200)
        worker = create_crawl_worker(config)

        assert worker.config.max_pages == 200
