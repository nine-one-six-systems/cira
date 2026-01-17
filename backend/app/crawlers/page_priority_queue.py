"""Page priority queue for URL prioritization during crawling."""

import hashlib
import heapq
import logging
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse, urljoin, parse_qs

logger = logging.getLogger(__name__)


# Page type priorities (lower number = higher priority)
PAGE_TYPE_PRIORITY = {
    'about': 1,
    'team': 2,
    'product': 3,
    'service': 4,
    'contact': 5,
    'careers': 6,
    'pricing': 7,
    'blog': 8,
    'news': 9,
    'other': 10,
}

# URL patterns for page type detection
PAGE_TYPE_PATTERNS = {
    'about': [
        r'/about[-_]?us',
        r'/about/?$',
        r'/company/?$',
        r'/who[-_]?we[-_]?are',
        r'/our[-_]?story',
    ],
    'team': [
        r'/team/?',
        r'/people/?',
        r'/leadership/?',
        r'/management/?',
        r'/our[-_]?team/?',
        r'/founders/?',
        r'/executives/?',
    ],
    'product': [
        r'/products?/?',
        r'/solutions?/?',
        r'/platform/?',
        r'/features?/?',
        r'/offerings?/?',
    ],
    'service': [
        r'/services?/?',
        r'/what[-_]?we[-_]?do/?',
        r'/capabilities/?',
        r'/consulting/?',
    ],
    'contact': [
        r'/contact[-_]?us/?',
        r'/contact/?$',
        r'/get[-_]?in[-_]?touch/?',
        r'/reach[-_]?us/?',
        r'/locations?/?',
    ],
    'careers': [
        r'/careers?/?',
        r'/jobs?/?',
        r'/join[-_]?us/?',
        r'/hiring/?',
        r'/opportunities/?',
        r'/work[-_]?with[-_]?us/?',
    ],
    'pricing': [
        r'/pricing/?',
        r'/plans?/?',
        r'/packages?/?',
        r'/cost/?',
    ],
    'blog': [
        r'/blog/?',
        r'/articles?/?',
        r'/insights?/?',
        r'/resources?/?',
    ],
    'news': [
        r'/news/?',
        r'/press/?',
        r'/media/?',
        r'/announcements?/?',
    ],
}


@dataclass(order=True)
class QueuedURL:
    """
    A URL in the priority queue.

    Ordering is by (priority, depth, insertion_order) to ensure:
    - Higher priority pages (lower number) come first
    - At same priority, shallower pages come first (BFS)
    - At same priority and depth, earlier discovered comes first
    """

    priority: int = field(compare=True)
    depth: int = field(compare=True)
    insertion_order: int = field(compare=True)
    url: str = field(compare=False)
    page_type: str = field(compare=False, default='other')
    parent_url: str | None = field(compare=False, default=None)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'priority': self.priority,
            'depth': self.depth,
            'insertion_order': self.insertion_order,
            'url': self.url,
            'page_type': self.page_type,
            'parent_url': self.parent_url,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'QueuedURL':
        """Create from dictionary."""
        return cls(
            priority=data.get('priority', 10),
            depth=data.get('depth', 0),
            insertion_order=data.get('insertion_order', 0),
            url=data.get('url', ''),
            page_type=data.get('page_type', 'other'),
            parent_url=data.get('parent_url'),
        )


class PagePriorityQueue:
    """
    Priority queue for URL crawling.

    Features:
    - Prioritizes key page types (About, Team, Products, etc.)
    - Implements BFS within same priority level
    - URL normalization and deduplication
    - Configurable max depth
    - Content hash tracking for duplicate detection
    """

    def __init__(
        self,
        base_url: str,
        max_depth: int = 3,
        exclusion_patterns: list[str] | None = None
    ):
        """
        Initialize priority queue.

        Args:
            base_url: Base URL of the website being crawled
            max_depth: Maximum crawl depth from base URL
            exclusion_patterns: URL patterns to exclude
        """
        self._base_url = base_url
        self._base_domain = self._get_domain(base_url)
        self._max_depth = max_depth
        self._exclusion_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in (exclusion_patterns or [])
        ]

        # Priority queue (min-heap)
        self._queue: list[QueuedURL] = []
        self._insertion_counter = 0

        # Tracking sets
        self._seen_urls: set[str] = set()
        self._visited_urls: set[str] = set()
        self._content_hashes: set[str] = set()

        # Compile page type patterns
        self._page_type_patterns = {
            ptype: [re.compile(p, re.IGNORECASE) for p in patterns]
            for ptype, patterns in PAGE_TYPE_PATTERNS.items()
        }

    def _get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc

    def normalize_url(self, url: str) -> str:
        """
        Normalize a URL for consistent comparison.

        - Removes fragments (#...)
        - Removes trailing slashes from path (except root)
        - Lowercases scheme and domain
        - Sorts query parameters
        - Removes common tracking parameters
        """
        parsed = urlparse(url)

        # Lowercase scheme and domain
        scheme = parsed.scheme.lower() or 'https'
        domain = parsed.netloc.lower()

        # Normalize path
        path = parsed.path or '/'
        if path != '/' and path.endswith('/'):
            path = path.rstrip('/')

        # Sort and filter query parameters
        query_params = parse_qs(parsed.query, keep_blank_values=True)

        # Remove common tracking parameters
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'fbclid', 'gclid', 'ref', 'source', 'mc_cid', 'mc_eid',
        }
        filtered_params = {
            k: v for k, v in query_params.items()
            if k.lower() not in tracking_params
        }

        # Rebuild query string (sorted)
        if filtered_params:
            query = '&'.join(
                f"{k}={v[0]}"
                for k, v in sorted(filtered_params.items())
            )
            return f"{scheme}://{domain}{path}?{query}"

        return f"{scheme}://{domain}{path}"

    def is_same_domain(self, url: str) -> bool:
        """Check if URL is on the same domain as base."""
        return self._get_domain(url) == self._base_domain

    def is_excluded(self, url: str) -> bool:
        """Check if URL matches exclusion patterns."""
        for pattern in self._exclusion_patterns:
            if pattern.search(url):
                return True
        return False

    def classify_page_type(self, url: str) -> str:
        """
        Classify URL into page type based on path.

        Args:
            url: URL to classify

        Returns:
            Page type string (about, team, product, etc.)
        """
        parsed = urlparse(url)
        path = parsed.path.lower()

        for page_type, patterns in self._page_type_patterns.items():
            for pattern in patterns:
                if pattern.search(path):
                    return page_type

        return 'other'

    def get_priority(self, page_type: str) -> int:
        """Get priority number for a page type."""
        return PAGE_TYPE_PRIORITY.get(page_type, PAGE_TYPE_PRIORITY['other'])

    def add_url(
        self,
        url: str,
        depth: int = 0,
        parent_url: str | None = None
    ) -> bool:
        """
        Add a URL to the queue.

        Args:
            url: URL to add
            depth: Crawl depth from base URL
            parent_url: URL of the page this was found on

        Returns:
            True if added, False if already seen/excluded/out of scope
        """
        # Normalize URL
        normalized = self.normalize_url(url)

        # Check if already seen
        if normalized in self._seen_urls:
            return False

        # Check depth limit
        if depth > self._max_depth:
            logger.debug(f"URL exceeds max depth ({depth} > {self._max_depth}): {url}")
            return False

        # Check same domain
        if not self.is_same_domain(normalized):
            logger.debug(f"URL not on same domain: {url}")
            return False

        # Check exclusion patterns
        if self.is_excluded(normalized):
            logger.debug(f"URL matches exclusion pattern: {url}")
            return False

        # Mark as seen
        self._seen_urls.add(normalized)

        # Classify page type and get priority
        page_type = self.classify_page_type(normalized)
        priority = self.get_priority(page_type)

        # Create queue entry
        entry = QueuedURL(
            priority=priority,
            depth=depth,
            insertion_order=self._insertion_counter,
            url=normalized,
            page_type=page_type,
            parent_url=parent_url,
        )
        self._insertion_counter += 1

        # Add to heap
        heapq.heappush(self._queue, entry)

        logger.debug(
            f"Added to queue: {normalized} "
            f"(type={page_type}, priority={priority}, depth={depth})"
        )

        return True

    def add_urls(
        self,
        urls: list[str],
        depth: int = 0,
        parent_url: str | None = None
    ) -> int:
        """
        Add multiple URLs to the queue.

        Args:
            urls: List of URLs to add
            depth: Crawl depth
            parent_url: Parent URL

        Returns:
            Number of URLs added
        """
        added = 0
        for url in urls:
            if self.add_url(url, depth=depth, parent_url=parent_url):
                added += 1
        return added

    def pop(self) -> QueuedURL | None:
        """
        Get the next highest-priority URL.

        Returns:
            QueuedURL object or None if queue is empty
        """
        while self._queue:
            entry = heapq.heappop(self._queue)

            # Skip if already visited
            if entry.url in self._visited_urls:
                continue

            return entry

        return None

    def peek(self) -> QueuedURL | None:
        """
        Peek at the next URL without removing it.

        Returns:
            QueuedURL object or None if queue is empty
        """
        # Find first non-visited entry
        for entry in self._queue:
            if entry.url not in self._visited_urls:
                return entry
        return None

    def mark_visited(self, url: str, content_hash: str | None = None) -> None:
        """
        Mark a URL as visited.

        Args:
            url: URL that was visited
            content_hash: Optional hash of page content for duplicate detection
        """
        normalized = self.normalize_url(url)
        self._visited_urls.add(normalized)

        if content_hash:
            self._content_hashes.add(content_hash)

    def is_visited(self, url: str) -> bool:
        """Check if a URL has been visited."""
        normalized = self.normalize_url(url)
        return normalized in self._visited_urls

    def is_duplicate_content(self, content_hash: str) -> bool:
        """Check if content hash indicates duplicate page."""
        return content_hash in self._content_hashes

    def add_content_hash(self, content_hash: str) -> bool:
        """
        Add content hash for duplicate detection.

        Args:
            content_hash: Hash of page content

        Returns:
            True if new hash, False if duplicate
        """
        if content_hash in self._content_hashes:
            return False
        self._content_hashes.add(content_hash)
        return True

    @staticmethod
    def compute_content_hash(content: str | bytes) -> str:
        """
        Compute hash of page content.

        Args:
            content: Page content (str or bytes)

        Returns:
            SHA-256 hash string
        """
        if isinstance(content, str):
            content = content.encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def __len__(self) -> int:
        """Get number of URLs in queue (excluding visited)."""
        return sum(
            1 for entry in self._queue
            if entry.url not in self._visited_urls
        )

    def __bool__(self) -> bool:
        """Check if queue has any URLs to process."""
        return len(self) > 0

    @property
    def seen_count(self) -> int:
        """Get number of URLs seen (added to queue)."""
        return len(self._seen_urls)

    @property
    def visited_count(self) -> int:
        """Get number of URLs visited."""
        return len(self._visited_urls)

    @property
    def pending_count(self) -> int:
        """Get number of URLs pending (seen but not visited)."""
        return len(self._seen_urls) - len(self._visited_urls)

    def get_visited_urls(self) -> set[str]:
        """Get set of visited URLs."""
        return self._visited_urls.copy()

    def get_seen_urls(self) -> set[str]:
        """Get set of seen URLs."""
        return self._seen_urls.copy()

    def restore_state(
        self,
        visited_urls: set[str],
        seen_urls: set[str],
        content_hashes: set[str],
        queued_urls: list[dict[str, Any]] | None = None
    ) -> None:
        """
        Restore queue state from checkpoint.

        Args:
            visited_urls: Set of visited URLs
            seen_urls: Set of seen URLs
            content_hashes: Set of content hashes
            queued_urls: Optional list of queued URL dicts
        """
        self._visited_urls = set(visited_urls)
        self._seen_urls = set(seen_urls)
        self._content_hashes = set(content_hashes)

        if queued_urls:
            self._queue = []
            for entry_dict in queued_urls:
                entry = QueuedURL.from_dict(entry_dict)
                heapq.heappush(self._queue, entry)
                self._insertion_counter = max(
                    self._insertion_counter,
                    entry.insertion_order + 1
                )

        logger.info(
            f"Restored queue state: {len(self._visited_urls)} visited, "
            f"{len(self._queue)} queued"
        )

    def get_state(self) -> dict[str, Any]:
        """
        Get current queue state for checkpointing.

        Returns:
            Dictionary with queue state
        """
        return {
            'visited_urls': list(self._visited_urls),
            'seen_urls': list(self._seen_urls),
            'content_hashes': list(self._content_hashes),
            'queued_urls': [
                entry.to_dict() for entry in self._queue
                if entry.url not in self._visited_urls
            ],
            'insertion_counter': self._insertion_counter,
        }

    def get_stats(self) -> dict[str, Any]:
        """Get queue statistics."""
        # Count URLs by type in queue
        type_counts = {}
        for entry in self._queue:
            if entry.url not in self._visited_urls:
                type_counts[entry.page_type] = type_counts.get(entry.page_type, 0) + 1

        return {
            'pending_count': self.pending_count,
            'visited_count': self.visited_count,
            'seen_count': self.seen_count,
            'content_hashes': len(self._content_hashes),
            'max_depth': self._max_depth,
            'by_page_type': type_counts,
        }
