"""Web crawling engine package."""

from app.crawlers.robots_parser import RobotsParser, robots_parser
from app.crawlers.rate_limiter import RateLimiter, rate_limiter, RateLimitedContext
from app.crawlers.sitemap_parser import SitemapParser, sitemap_parser
from app.crawlers.page_priority_queue import PagePriorityQueue, QueuedURL
from app.crawlers.browser_manager import (
    BrowserManager,
    BrowserConfig,
    PageContent,
    SimpleFetcher,
    browser_manager,
    simple_fetcher,
)

__all__ = [
    # robots.txt
    'RobotsParser',
    'robots_parser',
    # Rate limiting
    'RateLimiter',
    'rate_limiter',
    'RateLimitedContext',
    # Sitemap parsing
    'SitemapParser',
    'sitemap_parser',
    # Page priority queue
    'PagePriorityQueue',
    'QueuedURL',
    # Browser management
    'BrowserManager',
    'BrowserConfig',
    'PageContent',
    'SimpleFetcher',
    'browser_manager',
    'simple_fetcher',
]


# Lazy imports to avoid circular dependencies
def get_rate_limiter():
    """Get the rate limiter instance (lazy load)."""
    from app.crawlers.rate_limiter import rate_limiter
    return rate_limiter


def get_rate_limiter_class():
    """Get the RateLimiter class (lazy load)."""
    from app.crawlers.rate_limiter import RateLimiter
    return RateLimiter


def get_sitemap_parser():
    """Get the sitemap parser instance (lazy load)."""
    from app.crawlers.sitemap_parser import sitemap_parser
    return sitemap_parser


def get_sitemap_parser_class():
    """Get the SitemapParser class (lazy load)."""
    from app.crawlers.sitemap_parser import SitemapParser
    return SitemapParser


def get_page_priority_queue():
    """Get the PagePriorityQueue class (lazy load)."""
    from app.crawlers.page_priority_queue import PagePriorityQueue
    return PagePriorityQueue


def get_browser_manager():
    """Get the browser manager instance (lazy load)."""
    from app.crawlers.browser_manager import browser_manager
    return browser_manager


def get_browser_manager_class():
    """Get the BrowserManager class (lazy load)."""
    from app.crawlers.browser_manager import BrowserManager
    return BrowserManager
