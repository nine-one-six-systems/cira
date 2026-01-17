"""Main crawl worker implementation."""

import hashlib
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from app.crawlers.browser_manager import PageContent, SimpleFetcher
from app.crawlers.external_links import ExternalLinkDetector, ExternalLink
from app.crawlers.page_classifier import PageClassifier
from app.crawlers.page_priority_queue import PagePriorityQueue, QueuedURL
from app.crawlers.pdf_extractor import PDFExtractor
from app.crawlers.rate_limiter import RateLimiter
from app.crawlers.robots_parser import RobotsParser

logger = logging.getLogger(__name__)


@dataclass
class CrawlConfig:
    """Configuration for a crawl session."""

    # Limits
    max_pages: int = 50
    max_time_seconds: int = 300  # 5 minutes
    max_depth: int = 3

    # Crawl behavior
    respect_robots: bool = True
    follow_external: bool = False

    # External link following config
    follow_linkedin: bool = False
    follow_twitter: bool = False
    follow_facebook: bool = False

    # Checkpointing
    checkpoint_interval_pages: int = 10
    checkpoint_interval_seconds: int = 120  # 2 minutes

    # Rate limiting
    requests_per_second: float = 1.0


@dataclass
class CrawledPage:
    """Result of crawling a single page."""

    url: str
    final_url: str | None = None
    status_code: int | None = None
    html: str = ''
    text: str = ''
    title: str = ''
    content_hash: str = ''
    page_type: str = 'other'
    is_external: bool = False
    is_pdf: bool = False
    links_found: list[str] = field(default_factory=list)
    external_links: list[ExternalLink] = field(default_factory=list)
    error: str | None = None
    crawl_time: float = 0.0

    @property
    def is_success(self) -> bool:
        """Check if page was crawled successfully."""
        return self.error is None and (
            self.status_code is None or 200 <= self.status_code < 400
        )


@dataclass
class CrawlProgress:
    """Current progress of a crawl session."""

    pages_crawled: int = 0
    pages_queued: int = 0
    pages_skipped: int = 0
    duplicates_found: int = 0
    errors_count: int = 0
    external_links_found: int = 0
    current_url: str = ''
    current_activity: str = ''
    started_at: datetime | None = None
    last_checkpoint_at: datetime | None = None
    elapsed_seconds: float = 0.0


@dataclass
class CrawlCheckpoint:
    """Checkpoint data for pause/resume."""

    visited_urls: set[str]
    content_hashes: set[str]
    queue_state: list[dict[str, Any]]
    progress: dict[str, Any]
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'visited_urls': list(self.visited_urls),
            'content_hashes': list(self.content_hashes),
            'queue_state': self.queue_state,
            'progress': self.progress,
            'timestamp': self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'CrawlCheckpoint':
        """Create from dictionary."""
        return cls(
            visited_urls=set(data.get('visited_urls', [])),
            content_hashes=set(data.get('content_hashes', [])),
            queue_state=data.get('queue_state', []),
            progress=data.get('progress', {}),
            timestamp=data.get('timestamp', ''),
        )


@dataclass
class CrawlResult:
    """Result of a complete crawl session."""

    pages: list[CrawledPage]
    progress: CrawlProgress
    checkpoint: CrawlCheckpoint | None = None
    stopped_reason: str = 'completed'  # 'completed', 'max_pages', 'max_time', 'paused', 'error'

    @property
    def is_complete(self) -> bool:
        """Check if crawl completed successfully."""
        return self.stopped_reason == 'completed'


class CrawlWorker:
    """
    Main crawl worker implementation.

    Features:
    - Fetches URLs from priority queue
    - Respects rate limits and robots.txt
    - Extracts links, adds to queue
    - Stores HTML and text
    - Content hash for duplicate detection (FR-CRL-004)
    - Stops on time/page limit (FR-CRL-009, FR-CRL-010)
    - Updates checkpoint every 10 pages/2 min
    """

    def __init__(
        self,
        config: CrawlConfig | None = None,
        fetcher: SimpleFetcher | None = None,
        robots_parser: RobotsParser | None = None,
        rate_limiter: RateLimiter | None = None,
        page_classifier: PageClassifier | None = None,
        external_link_detector: ExternalLinkDetector | None = None,
        pdf_extractor: PDFExtractor | None = None,
    ):
        """
        Initialize crawl worker.

        Args:
            config: Crawl configuration
            fetcher: Page fetcher (SimpleFetcher or browser-based)
            robots_parser: Robots.txt parser
            rate_limiter: Rate limiter
            page_classifier: Page type classifier
            external_link_detector: External link detector
            pdf_extractor: PDF extractor
        """
        self.config = config or CrawlConfig()

        # Use provided dependencies or create defaults
        self._fetcher = fetcher or SimpleFetcher()
        self._robots = robots_parser or RobotsParser()
        self._rate_limiter = rate_limiter or RateLimiter()
        self._classifier = page_classifier or PageClassifier()
        self._link_detector = external_link_detector or ExternalLinkDetector()
        self._pdf_extractor = pdf_extractor or PDFExtractor()

        # Crawl state
        self._queue: PagePriorityQueue | None = None
        self._visited_urls: set[str] = set()
        self._content_hashes: set[str] = set()
        self._pages: list[CrawledPage] = []
        self._progress: CrawlProgress = CrawlProgress()

        # Control flags
        self._stop_requested = False
        self._pause_requested = False

        # Callbacks
        self._on_progress: Callable[[CrawlProgress], None] | None = None
        self._on_checkpoint: Callable[[CrawlCheckpoint], None] | None = None
        self._on_page: Callable[[CrawledPage], None] | None = None

    def set_callbacks(
        self,
        on_progress: Callable[[CrawlProgress], None] | None = None,
        on_checkpoint: Callable[[CrawlCheckpoint], None] | None = None,
        on_page: Callable[[CrawledPage], None] | None = None,
    ) -> None:
        """Set callback functions for progress updates."""
        self._on_progress = on_progress
        self._on_checkpoint = on_checkpoint
        self._on_page = on_page

    def crawl(
        self,
        start_url: str,
        checkpoint: CrawlCheckpoint | None = None,
    ) -> CrawlResult:
        """
        Start crawling from the given URL.

        Args:
            start_url: Starting URL for the crawl
            checkpoint: Optional checkpoint to resume from

        Returns:
            CrawlResult with all crawled pages and progress
        """
        # Initialize state
        self._initialize_crawl(start_url, checkpoint)

        # Main crawl loop
        stopped_reason = self._crawl_loop()

        # Create final checkpoint
        final_checkpoint = self._create_checkpoint()

        return CrawlResult(
            pages=self._pages,
            progress=self._progress,
            checkpoint=final_checkpoint,
            stopped_reason=stopped_reason,
        )

    def stop(self) -> None:
        """Request graceful stop of the crawl."""
        self._stop_requested = True

    def pause(self) -> None:
        """Request pause of the crawl (can be resumed)."""
        self._pause_requested = True

    def _initialize_crawl(
        self,
        start_url: str,
        checkpoint: CrawlCheckpoint | None = None,
    ) -> None:
        """Initialize crawl state from scratch or checkpoint."""
        # Reset control flags
        self._stop_requested = False
        self._pause_requested = False

        # Normalize start URL
        normalized_url = self._normalize_url(start_url) or start_url

        if checkpoint:
            # Resume from checkpoint
            self._visited_urls = checkpoint.visited_urls.copy()
            self._content_hashes = checkpoint.content_hashes.copy()
            progress_data = checkpoint.progress.copy()
            # Convert started_at string to datetime if needed
            if 'started_at' in progress_data and isinstance(progress_data['started_at'], str):
                progress_data['started_at'] = datetime.fromisoformat(progress_data['started_at'].replace('Z', '+00:00'))
            self._progress = CrawlProgress(**progress_data)

            # Create queue with base URL and restore state
            self._queue = PagePriorityQueue(
                base_url=normalized_url,
                max_depth=self.config.max_depth,
            )
            state = checkpoint.queue_state
            if isinstance(state, dict):
                self._queue.restore_state(
                    visited_urls=set(state.get('visited_urls', [])),
                    seen_urls=set(state.get('seen_urls', [])),
                    content_hashes=set(state.get('content_hashes', [])),
                    queued_urls=state.get('queued_urls'),
                )
            logger.info(
                f"Resuming crawl from checkpoint: "
                f"{len(self._visited_urls)} visited, "
                f"{self._queue.pending_count} queued"
            )
        else:
            # Fresh start
            self._visited_urls = set()
            self._content_hashes = set()
            self._pages = []
            self._progress = CrawlProgress(
                started_at=datetime.now(timezone.utc),
                last_checkpoint_at=datetime.now(timezone.utc),
            )
            self._queue = PagePriorityQueue(
                base_url=normalized_url,
                max_depth=self.config.max_depth,
            )

            # Add start URL to queue
            self._queue.add_url(normalized_url, depth=0)

        # Initialize rate limiter with config
        self._rate_limiter.set_default_rate(self.config.requests_per_second)

    def _crawl_loop(self) -> str:
        """Main crawl loop. Returns reason for stopping."""
        pages_since_checkpoint = 0
        last_checkpoint_time = time.time()

        while True:
            # Check stop conditions
            if self._stop_requested:
                return 'stopped'

            if self._pause_requested:
                return 'paused'

            if self._progress.pages_crawled >= self.config.max_pages:
                logger.info(f"Reached max pages limit: {self.config.max_pages}")
                return 'max_pages'

            elapsed = time.time() - (
                self._progress.started_at.timestamp()
                if self._progress.started_at
                else time.time()
            )
            if elapsed >= self.config.max_time_seconds:
                logger.info(f"Reached max time limit: {self.config.max_time_seconds}s")
                return 'max_time'

            # Get next URL from queue
            next_url = self._queue.pop()
            if not next_url:
                logger.info("Queue exhausted - crawl complete")
                return 'completed'

            # Update progress
            self._progress.current_url = next_url.url
            self._progress.current_activity = 'Crawling'
            self._progress.pages_queued = self._queue.pending_count
            self._progress.elapsed_seconds = elapsed
            self._emit_progress()

            # Check if already visited
            if next_url.url in self._visited_urls:
                self._progress.pages_skipped += 1
                continue

            # Crawl the page
            page = self._crawl_page(next_url)

            if page:
                self._pages.append(page)
                self._progress.pages_crawled += 1

                if not page.is_success:
                    self._progress.errors_count += 1

                if page.external_links:
                    self._progress.external_links_found += len(page.external_links)

                # Call page callback
                if self._on_page:
                    self._on_page(page)

            # Mark as visited
            self._visited_urls.add(next_url.url)

            # Checkpoint if needed
            pages_since_checkpoint += 1
            time_since_checkpoint = time.time() - last_checkpoint_time

            if (
                pages_since_checkpoint >= self.config.checkpoint_interval_pages or
                time_since_checkpoint >= self.config.checkpoint_interval_seconds
            ):
                self._emit_checkpoint()
                pages_since_checkpoint = 0
                last_checkpoint_time = time.time()

    def _crawl_page(self, queued_url: QueuedURL) -> CrawledPage | None:
        """Crawl a single page."""
        url = queued_url.url
        depth = queued_url.depth

        # Check robots.txt
        if self.config.respect_robots and not self._robots.is_allowed(url):
            logger.debug(f"Blocked by robots.txt: {url}")
            return CrawledPage(
                url=url,
                error='Blocked by robots.txt',
            )

        # Wait for rate limit
        self._rate_limiter.acquire(url)

        start_time = time.time()

        try:
            # Check if it's a PDF
            if self._pdf_extractor.is_pdf_url(url):
                return self._crawl_pdf(url, depth)

            # Fetch the page
            content = self._fetcher.fetch_page(url)
            crawl_time = time.time() - start_time

            if not content.is_success:
                return CrawledPage(
                    url=url,
                    final_url=content.final_url,
                    status_code=content.status_code,
                    error=content.error or f'HTTP {content.status_code}',
                    crawl_time=crawl_time,
                )

            # Extract content
            html = content.html
            text = content.text
            title = self._extract_title(html)

            # Compute content hash
            content_hash = self._compute_hash(text)

            # Check for duplicate content
            if content_hash in self._content_hashes:
                self._progress.duplicates_found += 1
                logger.debug(f"Duplicate content detected: {url}")
                return CrawledPage(
                    url=url,
                    final_url=content.final_url,
                    status_code=content.status_code,
                    content_hash=content_hash,
                    error='Duplicate content',
                    crawl_time=crawl_time,
                )

            self._content_hashes.add(content_hash)

            # Classify page type
            page_type = self._classifier.classify_url_only(url)

            # Extract links
            links = self._extract_links(html, url)

            # Detect external social links
            external_links = self._link_detector.detect_links(html, url)

            # Add discovered links to queue
            self._add_links_to_queue(links, url, depth + 1)

            # Handle external links
            if external_links and self.config.follow_external:
                self._handle_external_links(external_links, depth + 1)

            return CrawledPage(
                url=url,
                final_url=content.final_url,
                status_code=content.status_code,
                html=html,
                text=text,
                title=title,
                content_hash=content_hash,
                page_type=page_type,
                is_external=False,
                is_pdf=False,
                links_found=links,
                external_links=external_links,
                crawl_time=crawl_time,
            )

        except Exception as e:
            logger.warning(f"Error crawling {url}: {e}")
            return CrawledPage(
                url=url,
                error=str(e),
                crawl_time=time.time() - start_time,
            )

    def _crawl_pdf(self, url: str, depth: int) -> CrawledPage:
        """Crawl and extract text from a PDF."""
        start_time = time.time()

        try:
            result = self._pdf_extractor.extract_from_url(url)
            crawl_time = time.time() - start_time

            if result.error:
                return CrawledPage(
                    url=url,
                    is_pdf=True,
                    error=result.error,
                    crawl_time=crawl_time,
                )

            # Compute content hash
            content_hash = self._compute_hash(result.text)

            if content_hash in self._content_hashes:
                self._progress.duplicates_found += 1
                return CrawledPage(
                    url=url,
                    is_pdf=True,
                    content_hash=content_hash,
                    error='Duplicate content',
                    crawl_time=crawl_time,
                )

            self._content_hashes.add(content_hash)

            return CrawledPage(
                url=url,
                text=result.text,
                title=result.metadata.get('title', ''),
                content_hash=content_hash,
                page_type='other',
                is_pdf=True,
                crawl_time=crawl_time,
            )

        except Exception as e:
            logger.warning(f"Error extracting PDF {url}: {e}")
            return CrawledPage(
                url=url,
                is_pdf=True,
                error=str(e),
                crawl_time=time.time() - start_time,
            )

    def _extract_title(self, html: str) -> str:
        """Extract page title from HTML."""
        try:
            soup = BeautifulSoup(html, 'lxml')
            title_tag = soup.find('title')
            if title_tag:
                return title_tag.get_text().strip()
        except Exception:
            pass
        return ''

    def _extract_links(self, html: str, base_url: str) -> list[str]:
        """Extract all links from HTML."""
        links = []
        try:
            soup = BeautifulSoup(html, 'lxml')
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                absolute_url = self._resolve_url(href, base_url)
                if absolute_url:
                    links.append(absolute_url)
        except Exception as e:
            logger.warning(f"Error extracting links: {e}")

        return links

    def _resolve_url(self, href: str, base_url: str) -> str | None:
        """Resolve relative URL to absolute."""
        if not href:
            return None

        # Skip non-HTTP URLs
        if href.startswith(('javascript:', 'mailto:', 'tel:', '#', 'data:')):
            return None

        # Make absolute
        try:
            absolute = urljoin(base_url, href)
            normalized = self._normalize_url(absolute)
            return normalized
        except Exception:
            return None

    def _normalize_url(self, url: str) -> str | None:
        """Normalize URL for comparison and deduplication."""
        if not url:
            return None

        try:
            parsed = urlparse(url)

            # Only HTTP(S) URLs
            if parsed.scheme not in ('http', 'https'):
                return None

            # Normalize host
            host = parsed.netloc.lower()
            if not host:
                return None

            # Remove default ports
            if ':80' in host and parsed.scheme == 'http':
                host = host.replace(':80', '')
            if ':443' in host and parsed.scheme == 'https':
                host = host.replace(':443', '')

            # Normalize path
            path = parsed.path or '/'

            # Remove trailing slash for non-root paths
            if len(path) > 1 and path.endswith('/'):
                path = path.rstrip('/')

            # Remove fragments
            # Keep query string as-is

            return f"{parsed.scheme}://{host}{path}"
            if parsed.query:
                return f"{parsed.scheme}://{host}{path}?{parsed.query}"
            return f"{parsed.scheme}://{host}{path}"

        except Exception:
            return None

    def _add_links_to_queue(
        self,
        links: list[str],
        source_url: str,
        depth: int,
    ) -> None:
        """Add discovered links to the crawl queue."""
        source_domain = urlparse(source_url).netloc.lower()

        for link in links:
            # Check if same domain
            link_domain = urlparse(link).netloc.lower()
            if link_domain != source_domain:
                continue

            # Check if already visited
            if link in self._visited_urls:
                continue

            # Add to queue
            self._queue.add_url(link, depth=depth)

    def _handle_external_links(
        self,
        links: list[ExternalLink],
        depth: int,
    ) -> None:
        """Handle discovered external social links."""
        follow_config = {
            'followLinkedIn': self.config.follow_linkedin,
            'followTwitter': self.config.follow_twitter,
            'followFacebook': self.config.follow_facebook,
        }

        for link in links:
            if self._link_detector.should_follow(link.url, follow_config):
                self._queue.add_url(link.url, depth=depth)

    def _compute_hash(self, content: str) -> str:
        """Compute content hash for duplicate detection."""
        # Normalize content before hashing
        normalized = re.sub(r'\s+', ' ', content.strip().lower())
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()[:16]

    def _create_checkpoint(self) -> CrawlCheckpoint:
        """Create a checkpoint of current crawl state."""
        # Get queue state which includes visited_urls, seen_urls, content_hashes
        queue_state = self._queue.get_state() if self._queue else {}

        return CrawlCheckpoint(
            visited_urls=self._visited_urls.copy(),
            content_hashes=self._content_hashes.copy(),
            queue_state=queue_state,
            progress={
                'pages_crawled': self._progress.pages_crawled,
                'pages_queued': self._progress.pages_queued,
                'pages_skipped': self._progress.pages_skipped,
                'duplicates_found': self._progress.duplicates_found,
                'errors_count': self._progress.errors_count,
                'external_links_found': self._progress.external_links_found,
                'started_at': self._progress.started_at.isoformat() if self._progress.started_at else None,
            },
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def _emit_progress(self) -> None:
        """Emit progress update via callback."""
        if self._on_progress:
            self._on_progress(self._progress)

    def _emit_checkpoint(self) -> None:
        """Emit checkpoint via callback."""
        checkpoint = self._create_checkpoint()
        self._progress.last_checkpoint_at = datetime.now(timezone.utc)

        if self._on_checkpoint:
            self._on_checkpoint(checkpoint)

        logger.debug(
            f"Checkpoint: {self._progress.pages_crawled} pages, "
            f"{self._queue.pending_count if self._queue else 0} queued"
        )


# Global instance (optional, typically instantiated per crawl session)
def create_crawl_worker(config: CrawlConfig | None = None) -> CrawlWorker:
    """Factory function to create a crawl worker."""
    return CrawlWorker(config=config)
