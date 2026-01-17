"""External link detection and handling for social media profiles."""

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ExternalLink:
    """Detected external link with metadata."""

    url: str
    platform: str  # 'linkedin', 'twitter', 'facebook', 'other'
    link_type: str  # 'company', 'person', 'page', 'unknown'
    handle: str | None = None  # e.g., '@company' or 'company-name'
    found_on_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'url': self.url,
            'platform': self.platform,
            'link_type': self.link_type,
            'handle': self.handle,
            'found_on_url': self.found_on_url,
        }


# Platform detection patterns
PLATFORM_PATTERNS = {
    'linkedin': [
        # Company pages
        re.compile(r'linkedin\.com/company/([a-zA-Z0-9_-]+)', re.I),
        # Personal profiles
        re.compile(r'linkedin\.com/in/([a-zA-Z0-9_-]+)', re.I),
        # Showcase pages
        re.compile(r'linkedin\.com/showcase/([a-zA-Z0-9_-]+)', re.I),
    ],
    'twitter': [
        # Twitter/X profiles (handles)
        re.compile(r'(?:twitter|x)\.com/([a-zA-Z0-9_]+)(?:/|$|\?)', re.I),
    ],
    'facebook': [
        # Facebook pages
        re.compile(r'facebook\.com/([a-zA-Z0-9.]+)(?:/|$|\?)', re.I),
        # FB shorthand
        re.compile(r'fb\.com/([a-zA-Z0-9.]+)(?:/|$|\?)', re.I),
    ],
    'instagram': [
        re.compile(r'instagram\.com/([a-zA-Z0-9._]+)(?:/|$|\?)', re.I),
    ],
    'youtube': [
        re.compile(r'youtube\.com/(?:c/|channel/|user/|@)([a-zA-Z0-9_-]+)', re.I),
    ],
    'github': [
        re.compile(r'github\.com/([a-zA-Z0-9_-]+)(?:/|$|\?)', re.I),
    ],
}

# Domains by platform
PLATFORM_DOMAINS = {
    'linkedin': ['linkedin.com', 'www.linkedin.com'],
    'twitter': ['twitter.com', 'www.twitter.com', 'x.com', 'www.x.com'],
    'facebook': ['facebook.com', 'www.facebook.com', 'fb.com', 'www.fb.com'],
    'instagram': ['instagram.com', 'www.instagram.com'],
    'youtube': ['youtube.com', 'www.youtube.com'],
    'github': ['github.com', 'www.github.com'],
}

# Handles/pages to ignore (generic, not company-specific)
IGNORE_HANDLES = {
    'share', 'sharer', 'intent', 'login', 'signup', 'help', 'settings',
    'about', 'privacy', 'terms', 'policy', 'legal', 'support', 'contact',
    'home', 'search', 'explore', 'feed', 'notifications', 'messages',
}


class ExternalLinkDetector:
    """
    Detects and extracts external social media links.

    Features:
    - Detects LinkedIn company/person profiles (FR-EXT-001)
    - Detects Twitter/X company profiles (FR-EXT-002)
    - Detects Facebook business pages (FR-EXT-003)
    - Extracts handles for each platform
    - Filters out generic/non-company links
    """

    def __init__(self):
        """Initialize external link detector."""
        self._patterns = PLATFORM_PATTERNS
        self._domains = PLATFORM_DOMAINS
        self._ignore_handles = IGNORE_HANDLES

    def detect_links(
        self,
        html: str,
        source_url: str | None = None
    ) -> list[ExternalLink]:
        """
        Detect external links in HTML content.

        Args:
            html: HTML content to scan
            source_url: URL where the links were found

        Returns:
            List of ExternalLink objects
        """
        links = []
        seen_urls = set()

        # Find all href attributes
        href_pattern = re.compile(r'href=["\']([^"\']+)["\']', re.I)

        for match in href_pattern.finditer(html):
            url = match.group(1)

            # Normalize URL
            url = self._normalize_url(url, source_url)
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            # Check if it's a social media link
            link = self._detect_platform(url, source_url)
            if link:
                links.append(link)

        return links

    def detect_links_from_urls(
        self,
        urls: list[str],
        source_url: str | None = None
    ) -> list[ExternalLink]:
        """
        Detect social media links from a list of URLs.

        Args:
            urls: List of URLs to check
            source_url: URL where the links were found

        Returns:
            List of ExternalLink objects
        """
        links = []
        seen_urls = set()

        for url in urls:
            url = self._normalize_url(url, source_url)
            if not url or url in seen_urls:
                continue

            seen_urls.add(url)

            link = self._detect_platform(url, source_url)
            if link:
                links.append(link)

        return links

    def _normalize_url(
        self,
        url: str,
        base_url: str | None = None
    ) -> str | None:
        """Normalize a URL."""
        if not url:
            return None

        # Skip javascript: and mailto: links
        if url.startswith(('javascript:', 'mailto:', 'tel:', '#')):
            return None

        # Make absolute if relative
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            if base_url:
                parsed = urlparse(base_url)
                url = f"{parsed.scheme}://{parsed.netloc}{url}"
            else:
                return None

        # Ensure it has a scheme
        if not url.startswith(('http://', 'https://')):
            return None

        return url

    def _detect_platform(
        self,
        url: str,
        source_url: str | None
    ) -> ExternalLink | None:
        """Detect social media platform from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Find matching platform
        for platform, domains in self._domains.items():
            if domain in domains:
                return self._extract_link_info(url, platform, source_url)

        return None

    def _extract_link_info(
        self,
        url: str,
        platform: str,
        source_url: str | None
    ) -> ExternalLink | None:
        """Extract link information for a detected platform."""
        handle = None
        link_type = 'unknown'

        # Try to extract handle using platform patterns
        for pattern in self._patterns.get(platform, []):
            match = pattern.search(url)
            if match:
                handle = match.group(1)
                break

        # Filter out ignored handles
        if handle and handle.lower() in self._ignore_handles:
            return None

        # Determine link type
        if platform == 'linkedin':
            if '/company/' in url.lower():
                link_type = 'company'
            elif '/in/' in url.lower():
                link_type = 'person'
            elif '/showcase/' in url.lower():
                link_type = 'page'
        elif platform == 'twitter':
            link_type = 'company'  # Could be person, but assume company
        elif platform == 'facebook':
            link_type = 'page'
        elif platform == 'instagram':
            link_type = 'company'
        elif platform == 'youtube':
            link_type = 'channel'
        elif platform == 'github':
            link_type = 'organization'

        return ExternalLink(
            url=url,
            platform=platform,
            link_type=link_type,
            handle=handle,
            found_on_url=source_url,
        )

    def is_social_link(self, url: str) -> bool:
        """Check if a URL is a social media link."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for domains in self._domains.values():
            if domain in domains:
                return True

        return False

    def get_platform(self, url: str) -> str | None:
        """Get the platform name for a URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        for platform, domains in self._domains.items():
            if domain in domains:
                return platform

        return None

    def should_follow(
        self,
        url: str,
        follow_config: dict[str, bool] | None = None
    ) -> bool:
        """
        Check if a social link should be followed based on config.

        Args:
            url: URL to check
            follow_config: Dict with 'followLinkedIn', 'followTwitter', 'followFacebook'

        Returns:
            True if the link should be followed
        """
        if not follow_config:
            return False

        platform = self.get_platform(url)
        if not platform:
            return False

        # Map platforms to config keys
        config_keys = {
            'linkedin': 'followLinkedIn',
            'twitter': 'followTwitter',
            'facebook': 'followFacebook',
        }

        config_key = config_keys.get(platform)
        if config_key:
            return follow_config.get(config_key, False)

        return False

    def filter_company_links(
        self,
        links: list[ExternalLink]
    ) -> list[ExternalLink]:
        """Filter links to keep only company/organization pages."""
        return [
            link for link in links
            if link.link_type in ('company', 'page', 'organization', 'channel')
        ]


# Global instance
external_link_detector = ExternalLinkDetector()
