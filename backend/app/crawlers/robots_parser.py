"""robots.txt parser with caching support."""

import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import requests
from requests.exceptions import RequestException, Timeout

from app.services.redis_service import redis_service

logger = logging.getLogger(__name__)


@dataclass
class RobotsRules:
    """Parsed robots.txt rules for a domain."""

    domain: str
    allowed_paths: list[str] = field(default_factory=list)
    disallowed_paths: list[str] = field(default_factory=list)
    crawl_delay: float | None = None
    sitemaps: list[str] = field(default_factory=list)
    fetch_time: float = 0.0
    found: bool = True

    def is_allowed(self, path: str) -> bool:
        """
        Check if a path is allowed to be crawled.

        Uses longest match rule: if both Allow and Disallow match,
        the one with the longer path takes precedence.

        Args:
            path: URL path to check (e.g., '/about', '/team/leadership')

        Returns:
            True if the path is allowed, False otherwise
        """
        # Normalize path
        if not path:
            path = '/'
        if not path.startswith('/'):
            path = '/' + path

        # Default is allowed if no robots.txt found
        if not self.found:
            return True

        # If no rules at all, allow everything
        if not self.disallowed_paths and not self.allowed_paths:
            return True

        # Find best matching rule (longest match)
        best_match_length = -1
        is_allowed = True  # Default to allowed

        # Check disallowed paths
        for pattern in self.disallowed_paths:
            if self._matches(path, pattern):
                match_length = len(pattern)
                if match_length > best_match_length:
                    best_match_length = match_length
                    is_allowed = False

        # Check allowed paths (can override disallow with longer match)
        for pattern in self.allowed_paths:
            if self._matches(path, pattern):
                match_length = len(pattern)
                if match_length > best_match_length:
                    best_match_length = match_length
                    is_allowed = True

        return is_allowed

    def _matches(self, path: str, pattern: str) -> bool:
        """
        Check if a path matches a robots.txt pattern.

        Supports wildcards (*) and end-of-string anchor ($).

        Args:
            path: URL path to check
            pattern: robots.txt pattern

        Returns:
            True if the path matches the pattern
        """
        # Handle empty pattern (matches nothing)
        if not pattern:
            return False

        # Check for end anchor
        has_end_anchor = pattern.endswith('$')
        if has_end_anchor:
            pattern = pattern[:-1]  # Remove $ for processing

        # Build regex by processing character by character
        # We need to escape everything except * which becomes .*
        parts = []
        i = 0
        while i < len(pattern):
            char = pattern[i]
            if char == '*':
                parts.append('.*')
            else:
                # Escape all regex special characters
                parts.append(re.escape(char))
            i += 1

        regex_pattern = '^' + ''.join(parts)
        if has_end_anchor:
            regex_pattern += '$'

        try:
            return bool(re.match(regex_pattern, path))
        except re.error:
            # If regex fails, fall back to simple prefix match
            clean_pattern = pattern.rstrip('*')
            return path.startswith(clean_pattern)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'domain': self.domain,
            'allowed_paths': self.allowed_paths,
            'disallowed_paths': self.disallowed_paths,
            'crawl_delay': self.crawl_delay,
            'sitemaps': self.sitemaps,
            'fetch_time': self.fetch_time,
            'found': self.found,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'RobotsRules':
        """Create from dictionary."""
        return cls(
            domain=data.get('domain', ''),
            allowed_paths=data.get('allowed_paths', []),
            disallowed_paths=data.get('disallowed_paths', []),
            crawl_delay=data.get('crawl_delay'),
            sitemaps=data.get('sitemaps', []),
            fetch_time=data.get('fetch_time', 0.0),
            found=data.get('found', True),
        )


class RobotsParser:
    """
    robots.txt parser with caching support.

    Features:
    - Parses robots.txt from domains
    - Caches rules for 24 hours
    - Respects Disallow directives
    - Honors Crawl-delay
    - Handles missing robots.txt gracefully
    - User-Agent specific rules (prefers CIRA Bot, falls back to *)
    """

    USER_AGENT = 'CIRA Bot'
    CACHE_TTL = 86400  # 24 hours
    FETCH_TIMEOUT = 10  # seconds

    def __init__(self, redis_svc=None):
        """
        Initialize robots parser.

        Args:
            redis_svc: Redis service instance for caching (optional)
        """
        self._redis = redis_svc or redis_service
        self._memory_cache: dict[str, RobotsRules] = {}

    def _get_cache_key(self, domain: str) -> str:
        """Generate cache key for a domain."""
        return f"robots:{domain}"

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc or url

    def _get_robots_url(self, url: str) -> str:
        """Get robots.txt URL for a given URL."""
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        return urljoin(base, '/robots.txt')

    def get_rules(self, url: str, force_refresh: bool = False) -> RobotsRules:
        """
        Get robots.txt rules for a URL.

        First checks cache (Redis then memory), fetches if not found.

        Args:
            url: URL to get rules for
            force_refresh: If True, bypass cache and fetch fresh

        Returns:
            RobotsRules object with parsed rules
        """
        domain = self._get_domain(url)

        if not force_refresh:
            # Check memory cache first
            if domain in self._memory_cache:
                rules = self._memory_cache[domain]
                # Check if still valid (within TTL)
                if time.time() - rules.fetch_time < self.CACHE_TTL:
                    logger.debug(f"robots.txt cache hit (memory) for {domain}")
                    return rules

            # Check Redis cache
            if self._redis.is_available:
                cache_key = self._get_cache_key(domain)
                cached = self._redis.cache_get(cache_key)
                if cached:
                    rules = RobotsRules.from_dict(cached)
                    # Store in memory cache too
                    self._memory_cache[domain] = rules
                    logger.debug(f"robots.txt cache hit (Redis) for {domain}")
                    return rules

        # Fetch fresh
        rules = self._fetch_robots(url)

        # Cache the rules
        self._cache_rules(domain, rules)

        return rules

    def _cache_rules(self, domain: str, rules: RobotsRules) -> None:
        """Cache rules in both memory and Redis."""
        # Memory cache
        self._memory_cache[domain] = rules

        # Redis cache
        if self._redis.is_available:
            cache_key = self._get_cache_key(domain)
            self._redis.cache_set(
                cache_key,
                rules.to_dict(),
                expiry=self.CACHE_TTL
            )
            logger.debug(f"Cached robots.txt rules for {domain}")

    def _fetch_robots(self, url: str) -> RobotsRules:
        """
        Fetch and parse robots.txt for a URL.

        Args:
            url: URL to fetch robots.txt for

        Returns:
            RobotsRules with parsed rules or default allow-all if not found
        """
        domain = self._get_domain(url)
        robots_url = self._get_robots_url(url)

        logger.debug(f"Fetching robots.txt from {robots_url}")

        try:
            response = requests.get(
                robots_url,
                timeout=self.FETCH_TIMEOUT,
                headers={'User-Agent': f'{self.USER_AGENT}/1.0'},
                allow_redirects=True
            )

            if response.status_code == 404:
                # No robots.txt - allow all
                logger.info(f"No robots.txt found for {domain} (404)")
                return RobotsRules(
                    domain=domain,
                    found=False,
                    fetch_time=time.time()
                )

            if response.status_code != 200:
                # Other error - assume allow all for safety
                logger.warning(
                    f"robots.txt fetch failed for {domain}: "
                    f"status {response.status_code}"
                )
                return RobotsRules(
                    domain=domain,
                    found=False,
                    fetch_time=time.time()
                )

            # Parse the content
            return self._parse_robots(domain, response.text)

        except Timeout:
            logger.warning(f"robots.txt fetch timeout for {domain}")
            return RobotsRules(domain=domain, found=False, fetch_time=time.time())

        except RequestException as e:
            logger.warning(f"robots.txt fetch error for {domain}: {e}")
            return RobotsRules(domain=domain, found=False, fetch_time=time.time())

    def _parse_robots(self, domain: str, content: str) -> RobotsRules:
        """
        Parse robots.txt content.

        Args:
            domain: The domain this robots.txt belongs to
            content: Raw robots.txt content

        Returns:
            RobotsRules with parsed rules
        """
        rules = RobotsRules(
            domain=domain,
            fetch_time=time.time(),
            found=True
        )

        current_user_agents: list[str] = []
        collecting_rules = False

        # Track rules for specific user agents
        ua_rules: dict[str, dict] = {
            '*': {'allow': [], 'disallow': [], 'crawl_delay': None},
            self.USER_AGENT.lower(): {'allow': [], 'disallow': [], 'crawl_delay': None},
        }

        for line in content.split('\n'):
            # Remove comments and whitespace
            line = line.split('#')[0].strip()
            if not line:
                continue

            # Parse directive
            if ':' not in line:
                continue

            directive, value = line.split(':', 1)
            directive = directive.strip().lower()
            value = value.strip()

            if directive == 'user-agent':
                # Start new user-agent block
                ua = value.lower()
                if ua in ('*', self.USER_AGENT.lower()):
                    current_user_agents = [ua]
                    collecting_rules = True
                else:
                    # Not our user agent or wildcard
                    current_user_agents = []
                    collecting_rules = False

            elif directive == 'disallow' and collecting_rules:
                for ua in current_user_agents:
                    if ua in ua_rules and value:
                        ua_rules[ua]['disallow'].append(value)

            elif directive == 'allow' and collecting_rules:
                for ua in current_user_agents:
                    if ua in ua_rules and value:
                        ua_rules[ua]['allow'].append(value)

            elif directive == 'crawl-delay' and collecting_rules:
                try:
                    delay = float(value)
                    for ua in current_user_agents:
                        if ua in ua_rules:
                            ua_rules[ua]['crawl_delay'] = delay
                except ValueError:
                    pass

            elif directive == 'sitemap':
                if value and value.startswith(('http://', 'https://')):
                    rules.sitemaps.append(value)

        # Prefer CIRA Bot specific rules, fall back to wildcard
        cira_key = self.USER_AGENT.lower()
        if ua_rules.get(cira_key, {}).get('disallow') or \
           ua_rules.get(cira_key, {}).get('allow') or \
           ua_rules.get(cira_key, {}).get('crawl_delay'):
            # Use CIRA-specific rules
            rules.disallowed_paths = ua_rules[cira_key]['disallow']
            rules.allowed_paths = ua_rules[cira_key]['allow']
            rules.crawl_delay = ua_rules[cira_key]['crawl_delay']
        else:
            # Fall back to wildcard rules
            rules.disallowed_paths = ua_rules['*']['disallow']
            rules.allowed_paths = ua_rules['*']['allow']
            rules.crawl_delay = ua_rules['*']['crawl_delay']

        logger.info(
            f"Parsed robots.txt for {domain}: "
            f"{len(rules.disallowed_paths)} disallow, "
            f"{len(rules.allowed_paths)} allow, "
            f"crawl-delay={rules.crawl_delay}, "
            f"{len(rules.sitemaps)} sitemaps"
        )

        return rules

    def is_allowed(self, url: str) -> bool:
        """
        Check if a URL is allowed to be crawled.

        Args:
            url: Full URL to check

        Returns:
            True if allowed, False if blocked by robots.txt
        """
        parsed = urlparse(url)
        path = parsed.path or '/'
        if parsed.query:
            path = f"{path}?{parsed.query}"

        rules = self.get_rules(url)
        allowed = rules.is_allowed(path)

        if not allowed:
            logger.debug(f"URL blocked by robots.txt: {url}")

        return allowed

    def get_crawl_delay(self, url: str) -> float | None:
        """
        Get Crawl-delay for a URL's domain.

        Args:
            url: URL to get delay for

        Returns:
            Crawl delay in seconds, or None if not specified
        """
        rules = self.get_rules(url)
        return rules.crawl_delay

    def get_sitemaps(self, url: str) -> list[str]:
        """
        Get sitemaps declared in robots.txt.

        Args:
            url: URL to get sitemaps for

        Returns:
            List of sitemap URLs
        """
        rules = self.get_rules(url)
        return rules.sitemaps

    def clear_cache(self, domain: str | None = None) -> None:
        """
        Clear cached robots.txt rules.

        Args:
            domain: Specific domain to clear, or None for all
        """
        if domain:
            # Clear specific domain
            if domain in self._memory_cache:
                del self._memory_cache[domain]
            if self._redis.is_available:
                cache_key = self._get_cache_key(domain)
                self._redis.cache_delete(cache_key)
            logger.debug(f"Cleared robots.txt cache for {domain}")
        else:
            # Clear all
            self._memory_cache.clear()
            logger.debug("Cleared all robots.txt cache (memory only)")


# Global instance
robots_parser = RobotsParser()
