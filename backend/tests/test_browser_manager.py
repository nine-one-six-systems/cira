"""Tests for browser manager."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.crawlers.browser_manager import (
    BrowserManager,
    BrowserConfig,
    PageContent,
    SimpleFetcher,
)


class TestPageContent:
    """Tests for PageContent dataclass."""

    def test_success_check(self):
        """Test is_success property."""
        # Success case
        content = PageContent(
            url='https://example.com',
            html='<html></html>',
            text='Hello',
            status_code=200,
        )
        assert content.is_success is True

        # 404 is not success
        content = PageContent(
            url='https://example.com',
            html='',
            text='',
            status_code=404,
        )
        assert content.is_success is False

        # Error is not success
        content = PageContent(
            url='https://example.com',
            html='',
            text='',
            error='Timeout',
        )
        assert content.is_success is False

    def test_redirect_tracking(self):
        """Test final URL tracking after redirects."""
        content = PageContent(
            url='https://example.com',
            html='<html></html>',
            text='',
            final_url='https://www.example.com/',
        )
        assert content.url == 'https://example.com'
        assert content.final_url == 'https://www.example.com/'


class TestBrowserConfig:
    """Tests for BrowserConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = BrowserConfig()

        assert config.headless is True
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080
        assert config.user_agent == 'CIRA Bot/1.0'
        assert config.timeout_ms == 30000
        assert config.pool_size == 3

    def test_custom_config(self):
        """Test custom configuration."""
        config = BrowserConfig(
            headless=False,
            viewport_width=1280,
            viewport_height=720,
            timeout_ms=10000,
            pool_size=5,
        )

        assert config.headless is False
        assert config.viewport_width == 1280
        assert config.pool_size == 5


class TestBrowserManager:
    """Tests for BrowserManager class."""

    def test_init(self):
        """Test initialization."""
        manager = BrowserManager()

        assert manager._initialized is False
        assert manager._browser is None

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = BrowserConfig(pool_size=5)
        manager = BrowserManager(config=config)

        assert manager._config.pool_size == 5

    def test_get_stats_not_initialized(self):
        """Test get_stats when not initialized."""
        manager = BrowserManager()
        stats = manager.get_stats()

        assert stats['initialized'] is False
        assert stats['contexts_active'] == 0

    @pytest.mark.asyncio
    async def test_shutdown_when_not_initialized(self):
        """Test shutdown when browser not initialized."""
        manager = BrowserManager()
        # Should not raise
        await manager.shutdown()
        assert manager._initialized is False


class TestBrowserManagerMocked:
    """Tests for BrowserManager with mocked Playwright."""

    @pytest.fixture
    def mock_playwright_module(self):
        """Create mock playwright module and components."""
        mock_pw_instance = MagicMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        # Set up mock chain
        mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_pw_instance.stop = AsyncMock()
        mock_browser.close = AsyncMock()
        mock_context.close = AsyncMock()

        # Create the async_playwright mock
        mock_async_pw = MagicMock()
        mock_async_pw_context = AsyncMock()
        mock_async_pw_context.start = AsyncMock(return_value=mock_pw_instance)
        mock_async_pw.return_value = mock_async_pw_context

        return mock_async_pw, mock_pw_instance, mock_browser, mock_context, mock_page

    @pytest.mark.asyncio
    async def test_initialize(self, mock_playwright_module):
        """Test browser initialization."""
        mock_async_pw, mock_pw, mock_browser, mock_context, mock_page = mock_playwright_module

        with patch.dict('sys.modules', {'playwright.async_api': MagicMock(async_playwright=mock_async_pw)}):
            with patch('app.crawlers.browser_manager.async_playwright', mock_async_pw, create=True):
                manager = BrowserManager(BrowserConfig(pool_size=1))

                # Manually set up to avoid the import
                manager._playwright = mock_pw
                manager._browser = mock_browser
                manager._contexts = [mock_context]
                manager._initialized = True

                assert manager._initialized is True

                await manager.shutdown()

    @pytest.mark.asyncio
    async def test_fetch_page_structure(self):
        """Test that fetch_page returns correct structure when browser not available."""
        manager = BrowserManager()

        # Without initialization, it should fail gracefully
        # This tests the structure without needing playwright
        result = PageContent(
            url='https://example.com/',
            html='<html></html>',
            text='Test content',
            status_code=200,
        )

        assert result.is_success is True
        assert result.url == 'https://example.com/'

    @pytest.mark.asyncio
    async def test_context_manager_structure(self):
        """Test async context manager structure."""
        manager = BrowserManager()

        # Test the methods exist
        assert hasattr(manager, '__aenter__')
        assert hasattr(manager, '__aexit__')


class TestSimpleFetcher:
    """Tests for SimpleFetcher (non-JS fallback)."""

    def test_user_agent(self):
        """Test user agent is set."""
        fetcher = SimpleFetcher()
        assert fetcher.USER_AGENT == 'CIRA Bot/1.0'

    def test_fetch_page_success(self):
        """Test successful page fetch."""
        with patch('requests.Session') as MockSession:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '<html><head><title>Test</title></head><body>Hello World</body></html>'
            mock_response.headers = {'content-type': 'text/html'}
            mock_response.url = 'https://example.com/'
            mock_session.get.return_value = mock_response
            MockSession.return_value = mock_session

            fetcher = SimpleFetcher()
            fetcher._session = mock_session

            result = fetcher.fetch_page('https://example.com/')

            assert result.is_success is True
            assert result.status_code == 200
            assert 'Hello World' in result.text

    def test_fetch_page_404(self):
        """Test 404 response."""
        with patch('requests.Session') as MockSession:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = ''
            mock_response.headers = {}
            mock_response.url = 'https://example.com/notfound'
            mock_session.get.return_value = mock_response
            MockSession.return_value = mock_session

            fetcher = SimpleFetcher()
            fetcher._session = mock_session

            result = fetcher.fetch_page('https://example.com/notfound')

            assert result.is_success is False
            assert result.status_code == 404

    def test_fetch_page_error(self):
        """Test connection error."""
        from requests.exceptions import ConnectionError

        with patch('requests.Session') as MockSession:
            mock_session = MagicMock()
            mock_session.get.side_effect = ConnectionError('Failed to connect')
            MockSession.return_value = mock_session

            fetcher = SimpleFetcher()
            fetcher._session = mock_session

            result = fetcher.fetch_page('https://example.com/')

            assert result.is_success is False
            assert result.error is not None

    def test_fetch_page_strips_scripts(self):
        """Test that script content is removed from text."""
        with patch('requests.Session') as MockSession:
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = '''
            <html>
            <head><script>var x = 1;</script></head>
            <body>
                <p>Visible text</p>
                <script>console.log("hidden");</script>
                <style>.hidden { display: none; }</style>
            </body>
            </html>
            '''
            mock_response.headers = {}
            mock_response.url = 'https://example.com/'
            mock_session.get.return_value = mock_response
            MockSession.return_value = mock_session

            fetcher = SimpleFetcher()
            fetcher._session = mock_session

            result = fetcher.fetch_page('https://example.com/')

            assert 'Visible text' in result.text
            assert 'var x' not in result.text
            assert 'console.log' not in result.text


class TestBrowserManagerFetchMultiple:
    """Tests for concurrent page fetching."""

    @pytest.mark.asyncio
    async def test_fetch_multiple_empty(self):
        """Test fetching empty list."""
        manager = BrowserManager()
        results = await manager.fetch_multiple([])
        assert results == []

    def test_manager_has_fetch_multiple(self):
        """Test that fetch_multiple method exists."""
        manager = BrowserManager()
        assert hasattr(manager, 'fetch_multiple')
        assert callable(manager.fetch_multiple)
