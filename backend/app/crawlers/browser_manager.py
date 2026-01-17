"""Playwright browser manager for JavaScript-rendered content."""

import asyncio
import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    """Content fetched from a page."""

    url: str
    html: str
    text: str
    title: str = ''
    status_code: int = 200
    content_type: str = ''
    final_url: str = ''  # After redirects
    error: str | None = None
    load_time_ms: float = 0.0

    @property
    def is_success(self) -> bool:
        """Check if page fetch was successful."""
        return self.error is None and 200 <= self.status_code < 400


@dataclass
class BrowserConfig:
    """Configuration for browser manager."""

    headless: bool = True
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = 'CIRA Bot/1.0'
    timeout_ms: int = 30000  # 30 seconds
    wait_for_load: str = 'networkidle'  # or 'domcontentloaded' or 'load'
    javascript_enabled: bool = True
    ignore_https_errors: bool = True
    pool_size: int = 3  # Number of browser contexts


class BrowserManager:
    """
    Playwright browser manager for JavaScript rendering.

    Features:
    - Headless browser mode
    - 30-second timeout per page
    - Viewport: 1920x1080
    - User-Agent: "CIRA Bot/1.0"
    - Browser pool for concurrency
    - Graceful cleanup on shutdown
    - Memory-efficient operation
    """

    def __init__(self, config: BrowserConfig | None = None):
        """
        Initialize browser manager.

        Args:
            config: Browser configuration
        """
        self._config = config or BrowserConfig()
        self._browser = None
        self._playwright = None
        self._contexts: list = []
        self._context_pool: asyncio.Queue | None = None
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize Playwright browser."""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            try:
                from playwright.async_api import async_playwright

                logger.info("Initializing Playwright browser...")

                self._playwright = await async_playwright().start()

                # Launch browser
                self._browser = await self._playwright.chromium.launch(
                    headless=self._config.headless,
                )

                # Create context pool
                self._context_pool = asyncio.Queue()
                for _ in range(self._config.pool_size):
                    context = await self._create_context()
                    self._contexts.append(context)
                    await self._context_pool.put(context)

                self._initialized = True
                logger.info(
                    f"Playwright initialized with {self._config.pool_size} contexts"
                )

            except ImportError:
                logger.error(
                    "Playwright not installed. Run: pip install playwright && "
                    "playwright install chromium"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Playwright: {e}")
                await self.shutdown()
                raise

    async def _create_context(self):
        """Create a new browser context."""
        return await self._browser.new_context(
            viewport={
                'width': self._config.viewport_width,
                'height': self._config.viewport_height,
            },
            user_agent=self._config.user_agent,
            java_script_enabled=self._config.javascript_enabled,
            ignore_https_errors=self._config.ignore_https_errors,
        )

    async def shutdown(self) -> None:
        """Shutdown browser and release resources."""
        logger.info("Shutting down Playwright browser...")

        # Close all contexts
        for context in self._contexts:
            try:
                await context.close()
            except Exception as e:
                logger.warning(f"Error closing context: {e}")

        self._contexts.clear()

        # Close browser
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            self._browser = None

        # Stop playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.warning(f"Error stopping playwright: {e}")
            self._playwright = None

        self._initialized = False
        self._context_pool = None

        logger.info("Playwright browser shutdown complete")

    @asynccontextmanager
    async def get_context(self):
        """
        Get a browser context from the pool.

        Usage:
            async with browser_manager.get_context() as context:
                page = await context.new_page()
                ...
        """
        if not self._initialized:
            await self.initialize()

        context = await self._context_pool.get()
        try:
            yield context
        finally:
            await self._context_pool.put(context)

    async def fetch_page(self, url: str) -> PageContent:
        """
        Fetch a page with JavaScript rendering.

        Args:
            url: URL to fetch

        Returns:
            PageContent with HTML, text, and metadata
        """
        import time
        start_time = time.time()

        if not self._initialized:
            await self.initialize()

        result = PageContent(
            url=url,
            html='',
            text='',
            final_url=url,
        )

        page = None
        try:
            async with self.get_context() as context:
                page = await context.new_page()

                # Set timeout
                page.set_default_timeout(self._config.timeout_ms)

                # Navigate to page
                response = await page.goto(
                    url,
                    wait_until=self._config.wait_for_load,
                    timeout=self._config.timeout_ms,
                )

                if response:
                    result.status_code = response.status
                    result.content_type = response.headers.get('content-type', '')
                    result.final_url = response.url

                # Wait for content to stabilize
                await self._wait_for_content(page)

                # Get HTML content
                result.html = await page.content()

                # Get text content
                result.text = await page.evaluate('''
                    () => {
                        // Remove script and style elements
                        const scripts = document.querySelectorAll('script, style, noscript');
                        scripts.forEach(el => el.remove());

                        // Get text content
                        return document.body ? document.body.innerText : '';
                    }
                ''')

                # Get title
                result.title = await page.title()

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Error fetching {url}: {error_msg}")
            result.error = error_msg

            # Check for specific error types
            if 'timeout' in error_msg.lower():
                result.status_code = 408  # Request Timeout
            elif 'net::' in error_msg.lower():
                result.status_code = 0  # Network error

        finally:
            if page:
                try:
                    await page.close()
                except Exception:
                    pass

        result.load_time_ms = (time.time() - start_time) * 1000

        logger.debug(
            f"Fetched {url}: status={result.status_code}, "
            f"html_len={len(result.html)}, time={result.load_time_ms:.0f}ms"
        )

        return result

    async def _wait_for_content(self, page) -> None:
        """
        Wait for dynamic content to load.

        Uses heuristics to detect when content has stabilized.
        """
        try:
            # Wait a bit for any dynamic content
            await asyncio.sleep(0.5)

            # Wait for any pending network requests
            await page.wait_for_load_state('networkidle', timeout=5000)

        except Exception:
            # Timeout is OK - content may have loaded
            pass

    async def fetch_multiple(
        self,
        urls: list[str],
        concurrency: int | None = None
    ) -> list[PageContent]:
        """
        Fetch multiple pages concurrently.

        Args:
            urls: List of URLs to fetch
            concurrency: Max concurrent fetches (default: pool_size)

        Returns:
            List of PageContent objects in same order as input
        """
        if not urls:
            return []

        concurrency = concurrency or self._config.pool_size

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)

        async def fetch_with_semaphore(url: str) -> PageContent:
            async with semaphore:
                return await self.fetch_page(url)

        # Fetch all pages
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to PageContent with errors
        final_results = []
        for url, result in zip(urls, results):
            if isinstance(result, Exception):
                final_results.append(PageContent(
                    url=url,
                    html='',
                    text='',
                    error=str(result),
                ))
            else:
                final_results.append(result)

        return final_results

    def fetch_page_sync(self, url: str) -> PageContent:
        """
        Synchronous wrapper for fetch_page.

        Args:
            url: URL to fetch

        Returns:
            PageContent with HTML, text, and metadata
        """
        return asyncio.run(self.fetch_page(url))

    def get_stats(self) -> dict[str, Any]:
        """Get browser manager statistics."""
        return {
            'initialized': self._initialized,
            'config': {
                'headless': self._config.headless,
                'viewport': f"{self._config.viewport_width}x{self._config.viewport_height}",
                'timeout_ms': self._config.timeout_ms,
                'pool_size': self._config.pool_size,
            },
            'contexts_active': len(self._contexts),
        }

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        return False


class SimpleFetcher:
    """
    Simple HTTP fetcher for non-JS pages.

    Falls back to this when Playwright is unavailable or unnecessary.
    """

    USER_AGENT = 'CIRA Bot/1.0'
    TIMEOUT = 30

    def __init__(self):
        """Initialize simple fetcher."""
        import requests
        self._session = requests.Session()
        self._session.headers['User-Agent'] = self.USER_AGENT

    def fetch_page(self, url: str) -> PageContent:
        """
        Fetch a page using requests (no JS rendering).

        Args:
            url: URL to fetch

        Returns:
            PageContent with HTML and basic text extraction
        """
        import time
        from bs4 import BeautifulSoup
        from requests.exceptions import RequestException

        start_time = time.time()

        result = PageContent(
            url=url,
            html='',
            text='',
            final_url=url,
        )

        try:
            response = self._session.get(
                url,
                timeout=self.TIMEOUT,
                allow_redirects=True,
            )

            result.status_code = response.status_code
            result.content_type = response.headers.get('content-type', '')
            result.final_url = response.url

            if response.status_code == 200:
                result.html = response.text

                # Extract text using BeautifulSoup
                soup = BeautifulSoup(result.html, 'lxml')

                # Remove script and style elements
                for element in soup(['script', 'style', 'noscript']):
                    element.decompose()

                result.text = soup.get_text(separator=' ', strip=True)
                result.title = soup.title.string if soup.title else ''

        except RequestException as e:
            result.error = str(e)
            logger.warning(f"Simple fetch error for {url}: {e}")

        result.load_time_ms = (time.time() - start_time) * 1000
        return result


# Global instances
browser_manager = BrowserManager()
simple_fetcher = SimpleFetcher()
