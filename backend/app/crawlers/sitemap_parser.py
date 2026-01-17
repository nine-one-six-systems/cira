"""Sitemap parser for efficient URL discovery."""

import gzip
import logging
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from typing import Any
from urllib.parse import urljoin, urlparse
from xml.etree import ElementTree

import requests
from requests.exceptions import RequestException, Timeout

from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


# XML namespaces for sitemap parsing
SITEMAP_NS = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


@dataclass
class SitemapURL:
    """A URL entry from a sitemap."""

    url: str
    lastmod: datetime | None = None
    changefreq: str | None = None
    priority: float | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'url': self.url,
            'lastmod': self.lastmod.isoformat() if self.lastmod else None,
            'changefreq': self.changefreq,
            'priority': self.priority,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'SitemapURL':
        """Create from dictionary."""
        lastmod = None
        if data.get('lastmod'):
            try:
                lastmod = datetime.fromisoformat(data['lastmod'])
            except ValueError:
                pass
        return cls(
            url=data.get('url', ''),
            lastmod=lastmod,
            changefreq=data.get('changefreq'),
            priority=data.get('priority'),
        )


@dataclass
class SitemapResult:
    """Result of parsing sitemaps for a domain."""

    domain: str
    urls: list[SitemapURL] = field(default_factory=list)
    sitemap_urls: list[str] = field(default_factory=list)  # Sitemaps found
    errors: list[str] = field(default_factory=list)
    fetch_time: float = 0.0

    @property
    def url_count(self) -> int:
        """Get total URL count."""
        return len(self.urls)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'domain': self.domain,
            'urls': [u.to_dict() for u in self.urls],
            'sitemap_urls': self.sitemap_urls,
            'errors': self.errors,
            'fetch_time': self.fetch_time,
        }


class SitemapParser:
    """
    Sitemap parser for efficient URL discovery.

    Features:
    - Detects sitemap at domain root (/sitemap.xml)
    - Supports sitemap index files with multiple sitemaps
    - Handles gzipped sitemaps
    - Extracts URLs with lastmod dates
    - Caches results in Redis
    - Falls back gracefully if no sitemap
    """

    USER_AGENT = 'CIRA Bot/1.0'
    FETCH_TIMEOUT = 30  # seconds
    MAX_SITEMAPS = 50  # Maximum sitemap files to process
    MAX_URLS = 10000  # Maximum URLs to extract
    CACHE_TTL = 86400  # 24 hours

    def __init__(self, redis_svc=None):
        """
        Initialize sitemap parser.

        Args:
            redis_svc: Redis service for caching (optional)
        """
        self._redis = redis_svc or redis_service
        self._session = requests.Session()
        self._session.headers['User-Agent'] = self.USER_AGENT

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc or url

    def _get_base_url(self, url: str) -> str:
        """Get base URL (scheme + netloc)."""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _get_sitemap_url(self, url: str) -> str:
        """Get default sitemap URL for a domain."""
        base = self._get_base_url(url)
        return urljoin(base, '/sitemap.xml')

    def _get_cache_key(self, domain: str) -> str:
        """Generate cache key for a domain."""
        return f"sitemap:{domain}"

    def get_urls(
        self,
        url: str,
        max_urls: int | None = None,
        force_refresh: bool = False
    ) -> SitemapResult:
        """
        Get URLs from sitemap(s) for a URL.

        Args:
            url: Base URL to find sitemaps for
            max_urls: Maximum URLs to return (default: 10000)
            force_refresh: If True, bypass cache

        Returns:
            SitemapResult with discovered URLs
        """
        domain = self._get_domain(url)
        max_urls = max_urls or self.MAX_URLS

        # Check cache
        if not force_refresh and self._redis.is_available:
            cache_key = self._get_cache_key(domain)
            cached = self._redis.cache_get(cache_key)
            if cached:
                logger.debug(f"Sitemap cache hit for {domain}")
                result = SitemapResult(
                    domain=cached['domain'],
                    urls=[SitemapURL.from_dict(u) for u in cached.get('urls', [])],
                    sitemap_urls=cached.get('sitemap_urls', []),
                    errors=cached.get('errors', []),
                    fetch_time=cached.get('fetch_time', 0.0),
                )
                return result

        # Fetch fresh
        result = self._discover_sitemaps(url, max_urls)

        # Cache result
        if self._redis.is_available:
            cache_key = self._get_cache_key(domain)
            self._redis.cache_set(cache_key, result.to_dict(), expiry=self.CACHE_TTL)

        return result

    def _discover_sitemaps(self, url: str, max_urls: int) -> SitemapResult:
        """
        Discover and parse sitemaps for a URL.

        Args:
            url: Base URL
            max_urls: Maximum URLs to extract

        Returns:
            SitemapResult with discovered URLs
        """
        import time
        start_time = time.time()

        domain = self._get_domain(url)
        result = SitemapResult(domain=domain)

        # Try default sitemap location
        sitemap_url = self._get_sitemap_url(url)
        sitemaps_to_process = [sitemap_url]
        processed_sitemaps = set()

        while sitemaps_to_process and len(processed_sitemaps) < self.MAX_SITEMAPS:
            current_sitemap = sitemaps_to_process.pop(0)

            if current_sitemap in processed_sitemaps:
                continue

            processed_sitemaps.add(current_sitemap)

            try:
                content = self._fetch_sitemap(current_sitemap)
                if content is None:
                    continue

                result.sitemap_urls.append(current_sitemap)

                # Parse the sitemap
                sitemap_type, data = self._parse_sitemap(content)

                if sitemap_type == 'index':
                    # Add child sitemaps to process
                    for child_url in data:
                        if child_url not in processed_sitemaps:
                            sitemaps_to_process.append(child_url)
                elif sitemap_type == 'urlset':
                    # Add URLs to result
                    for sitemap_url_obj in data:
                        if len(result.urls) >= max_urls:
                            logger.info(
                                f"Reached max URL limit ({max_urls}) for {domain}"
                            )
                            break
                        result.urls.append(sitemap_url_obj)

                if len(result.urls) >= max_urls:
                    break

            except Exception as e:
                error_msg = f"Error processing {current_sitemap}: {e}"
                logger.warning(error_msg)
                result.errors.append(error_msg)

        result.fetch_time = time.time() - start_time

        logger.info(
            f"Sitemap discovery for {domain}: "
            f"{len(result.urls)} URLs from {len(result.sitemap_urls)} sitemaps "
            f"in {result.fetch_time:.2f}s"
        )

        return result

    def _fetch_sitemap(self, url: str) -> bytes | None:
        """
        Fetch sitemap content, handling gzip.

        Args:
            url: Sitemap URL

        Returns:
            Raw content bytes, or None if fetch failed
        """
        try:
            response = self._session.get(
                url,
                timeout=self.FETCH_TIMEOUT,
                allow_redirects=True
            )

            if response.status_code == 404:
                logger.debug(f"Sitemap not found: {url}")
                return None

            if response.status_code != 200:
                logger.warning(f"Sitemap fetch failed: {url} (status {response.status_code})")
                return None

            content = response.content

            # Handle gzipped content
            if url.endswith('.gz') or response.headers.get('Content-Encoding') == 'gzip':
                try:
                    content = gzip.decompress(content)
                except gzip.BadGzipFile:
                    # Try as-is if not actually gzipped
                    pass

            return content

        except Timeout:
            logger.warning(f"Sitemap fetch timeout: {url}")
            return None

        except RequestException as e:
            logger.warning(f"Sitemap fetch error: {url} - {e}")
            return None

    def _parse_sitemap(
        self,
        content: bytes
    ) -> tuple[str, list[str] | list[SitemapURL]]:
        """
        Parse sitemap XML content.

        Args:
            content: Raw XML bytes

        Returns:
            Tuple of (type, data) where:
            - type is 'index' or 'urlset'
            - data is list of sitemap URLs or SitemapURL objects
        """
        try:
            # Parse XML
            root = ElementTree.fromstring(content)

            # Remove namespace for easier parsing
            tag = root.tag.split('}')[-1] if '}' in root.tag else root.tag

            if tag == 'sitemapindex':
                # Sitemap index - extract child sitemap URLs
                sitemaps = []
                for sitemap in root.findall('.//sm:sitemap', SITEMAP_NS):
                    loc = sitemap.find('sm:loc', SITEMAP_NS)
                    if loc is not None and loc.text:
                        sitemaps.append(loc.text.strip())

                # Try without namespace too
                for sitemap in root.findall('.//sitemap'):
                    loc = sitemap.find('loc')
                    if loc is not None and loc.text:
                        url = loc.text.strip()
                        if url not in sitemaps:
                            sitemaps.append(url)

                return 'index', sitemaps

            elif tag == 'urlset':
                # URL set - extract URLs
                urls = []

                # Try with namespace
                for url_elem in root.findall('.//sm:url', SITEMAP_NS):
                    url_obj = self._parse_url_element(url_elem, with_ns=True)
                    if url_obj:
                        urls.append(url_obj)

                # Try without namespace
                for url_elem in root.findall('.//url'):
                    url_obj = self._parse_url_element(url_elem, with_ns=False)
                    if url_obj and url_obj.url not in [u.url for u in urls]:
                        urls.append(url_obj)

                return 'urlset', urls

            else:
                logger.warning(f"Unknown sitemap type: {tag}")
                return 'unknown', []

        except ElementTree.ParseError as e:
            logger.warning(f"Failed to parse sitemap XML: {e}")
            return 'error', []

    def _parse_url_element(
        self,
        url_elem: ElementTree.Element,
        with_ns: bool
    ) -> SitemapURL | None:
        """
        Parse a URL element from sitemap.

        Args:
            url_elem: XML element containing URL data
            with_ns: Whether to use namespace for child elements

        Returns:
            SitemapURL object or None if invalid
        """
        ns = SITEMAP_NS if with_ns else {}
        prefix = 'sm:' if with_ns else ''

        loc = url_elem.find(f'{prefix}loc', ns)
        if loc is None or not loc.text:
            return None

        url = loc.text.strip()
        result = SitemapURL(url=url)

        # Parse lastmod
        lastmod = url_elem.find(f'{prefix}lastmod', ns)
        if lastmod is not None and lastmod.text:
            result.lastmod = self._parse_date(lastmod.text.strip())

        # Parse changefreq
        changefreq = url_elem.find(f'{prefix}changefreq', ns)
        if changefreq is not None and changefreq.text:
            result.changefreq = changefreq.text.strip()

        # Parse priority
        priority = url_elem.find(f'{prefix}priority', ns)
        if priority is not None and priority.text:
            try:
                result.priority = float(priority.text.strip())
            except ValueError:
                pass

        return result

    def _parse_date(self, date_str: str) -> datetime | None:
        """
        Parse date string from sitemap.

        Supports multiple formats: YYYY-MM-DD, ISO 8601, etc.
        """
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S%z',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S',
        ]

        # Clean up timezone format
        date_str = date_str.replace('+00:00', 'Z')

        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

        # Try ISO format as last resort
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            return None

    def clear_cache(self, domain: str | None = None) -> None:
        """
        Clear sitemap cache.

        Args:
            domain: Specific domain to clear, or None for all
        """
        if domain and self._redis.is_available:
            cache_key = self._get_cache_key(domain)
            self._redis.cache_delete(cache_key)
            logger.debug(f"Cleared sitemap cache for {domain}")


# Global instance
sitemap_parser = SitemapParser()
