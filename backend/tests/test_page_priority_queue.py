"""Tests for page priority queue."""

import pytest

from app.crawlers.page_priority_queue import (
    PagePriorityQueue,
    QueuedURL,
    PAGE_TYPE_PRIORITY,
)


class TestQueuedURL:
    """Tests for QueuedURL dataclass."""

    def test_ordering_by_priority(self):
        """Test that URLs are ordered by priority first."""
        url1 = QueuedURL(priority=1, depth=0, insertion_order=0, url='https://example.com/about')
        url2 = QueuedURL(priority=5, depth=0, insertion_order=0, url='https://example.com/contact')

        assert url1 < url2  # Lower priority number = higher priority

    def test_ordering_by_depth(self):
        """Test that URLs at same priority are ordered by depth."""
        url1 = QueuedURL(priority=1, depth=1, insertion_order=0, url='https://example.com/a')
        url2 = QueuedURL(priority=1, depth=2, insertion_order=0, url='https://example.com/b')

        assert url1 < url2  # Shallower depth = higher priority

    def test_ordering_by_insertion_order(self):
        """Test that URLs at same priority and depth are ordered by insertion."""
        url1 = QueuedURL(priority=1, depth=1, insertion_order=0, url='https://example.com/a')
        url2 = QueuedURL(priority=1, depth=1, insertion_order=1, url='https://example.com/b')

        assert url1 < url2  # Earlier insertion = higher priority

    def test_to_dict(self):
        """Test conversion to dictionary."""
        url = QueuedURL(
            priority=1,
            depth=2,
            insertion_order=5,
            url='https://example.com/about',
            page_type='about',
            parent_url='https://example.com/',
        )
        data = url.to_dict()

        assert data['priority'] == 1
        assert data['depth'] == 2
        assert data['url'] == 'https://example.com/about'
        assert data['page_type'] == 'about'

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'priority': 2,
            'depth': 1,
            'insertion_order': 3,
            'url': 'https://example.com/team',
            'page_type': 'team',
        }
        url = QueuedURL.from_dict(data)

        assert url.priority == 2
        assert url.url == 'https://example.com/team'
        assert url.page_type == 'team'


class TestPagePriorityQueue:
    """Tests for PagePriorityQueue class."""

    @pytest.fixture
    def queue(self):
        """Create a basic queue."""
        return PagePriorityQueue(
            base_url='https://example.com',
            max_depth=3,
        )

    def test_normalize_url(self, queue):
        """Test URL normalization."""
        # Removes trailing slash
        assert queue.normalize_url('https://example.com/about/') == 'https://example.com/about'

        # Keeps root slash
        assert queue.normalize_url('https://example.com/') == 'https://example.com/'

        # Lowercases domain
        assert queue.normalize_url('https://Example.COM/About') == 'https://example.com/About'

        # Removes tracking parameters
        url = 'https://example.com/page?utm_source=test&id=123'
        normalized = queue.normalize_url(url)
        assert 'utm_source' not in normalized
        assert 'id=123' in normalized

    def test_is_same_domain(self, queue):
        """Test same domain check."""
        assert queue.is_same_domain('https://example.com/page') is True
        assert queue.is_same_domain('https://example.com/deep/path') is True
        assert queue.is_same_domain('https://other.com/page') is False
        assert queue.is_same_domain('https://sub.example.com/page') is False

    def test_classify_page_type(self, queue):
        """Test page type classification."""
        assert queue.classify_page_type('https://example.com/about') == 'about'
        assert queue.classify_page_type('https://example.com/about-us') == 'about'
        assert queue.classify_page_type('https://example.com/team') == 'team'
        assert queue.classify_page_type('https://example.com/our-team') == 'team'
        assert queue.classify_page_type('https://example.com/products') == 'product'
        assert queue.classify_page_type('https://example.com/services') == 'service'
        assert queue.classify_page_type('https://example.com/contact') == 'contact'
        assert queue.classify_page_type('https://example.com/careers') == 'careers'
        assert queue.classify_page_type('https://example.com/pricing') == 'pricing'
        assert queue.classify_page_type('https://example.com/blog') == 'blog'
        assert queue.classify_page_type('https://example.com/news') == 'news'
        assert queue.classify_page_type('https://example.com/random') == 'other'

    def test_add_url_basic(self, queue):
        """Test adding a URL."""
        result = queue.add_url('https://example.com/about')

        assert result is True
        assert queue.seen_count == 1
        assert len(queue) == 1

    def test_add_url_duplicate(self, queue):
        """Test that duplicates are rejected."""
        queue.add_url('https://example.com/about')
        result = queue.add_url('https://example.com/about')

        assert result is False
        assert queue.seen_count == 1

    def test_add_url_normalized_duplicate(self, queue):
        """Test that normalized duplicates are rejected."""
        queue.add_url('https://example.com/about')
        result = queue.add_url('https://example.com/about/')

        assert result is False
        assert queue.seen_count == 1

    def test_add_url_different_domain(self, queue):
        """Test that different domains are rejected."""
        result = queue.add_url('https://other.com/page')

        assert result is False
        assert queue.seen_count == 0

    def test_add_url_max_depth(self, queue):
        """Test max depth enforcement."""
        result = queue.add_url('https://example.com/page', depth=4)

        assert result is False  # Exceeds max_depth of 3

    def test_add_url_with_exclusion(self):
        """Test URL exclusion patterns."""
        queue = PagePriorityQueue(
            base_url='https://example.com',
            exclusion_patterns=[r'/admin', r'\.pdf$'],
        )

        assert queue.add_url('https://example.com/admin') is False
        assert queue.add_url('https://example.com/doc.pdf') is False
        assert queue.add_url('https://example.com/about') is True

    def test_add_urls(self, queue):
        """Test adding multiple URLs."""
        urls = [
            'https://example.com/about',
            'https://example.com/team',
            'https://other.com/page',  # Different domain
        ]
        added = queue.add_urls(urls)

        assert added == 2

    def test_pop_priority_order(self, queue):
        """Test that pop returns URLs in priority order."""
        queue.add_url('https://example.com/blog')      # Priority 8
        queue.add_url('https://example.com/about')     # Priority 1
        queue.add_url('https://example.com/contact')   # Priority 5

        url1 = queue.pop()
        url2 = queue.pop()
        url3 = queue.pop()

        assert url1.page_type == 'about'   # Highest priority (1)
        assert url2.page_type == 'contact' # Medium priority (5)
        assert url3.page_type == 'blog'    # Lowest priority (8)

    def test_pop_depth_order(self, queue):
        """Test that same-priority URLs are ordered by depth (BFS)."""
        queue.add_url('https://example.com/deep/about', depth=2)
        queue.add_url('https://example.com/about', depth=1)

        url1 = queue.pop()
        url2 = queue.pop()

        assert url1.depth == 1  # Shallower first
        assert url2.depth == 2

    def test_pop_empty_queue(self, queue):
        """Test pop on empty queue."""
        result = queue.pop()
        assert result is None

    def test_peek(self, queue):
        """Test peeking without removal."""
        queue.add_url('https://example.com/about')

        url1 = queue.peek()
        url2 = queue.peek()
        url3 = queue.pop()

        assert url1.url == url2.url == url3.url

    def test_mark_visited(self, queue):
        """Test marking URLs as visited."""
        queue.add_url('https://example.com/about')
        url = queue.pop()
        queue.mark_visited(url.url)

        assert queue.is_visited('https://example.com/about') is True
        assert queue.visited_count == 1

    def test_mark_visited_with_hash(self, queue):
        """Test marking visited with content hash."""
        queue.add_url('https://example.com/about')
        url = queue.pop()
        queue.mark_visited(url.url, content_hash='abc123')

        assert queue.is_duplicate_content('abc123') is True
        assert queue.is_duplicate_content('different') is False

    def test_content_hash_tracking(self, queue):
        """Test content hash for duplicate detection."""
        content = 'Hello World'
        hash1 = queue.compute_content_hash(content)
        hash2 = queue.compute_content_hash(content)
        hash3 = queue.compute_content_hash('Different')

        assert hash1 == hash2
        assert hash1 != hash3

        # Add hash
        assert queue.add_content_hash(hash1) is True
        assert queue.add_content_hash(hash1) is False  # Duplicate
        assert queue.is_duplicate_content(hash1) is True

    def test_len_excludes_visited(self, queue):
        """Test that len excludes visited URLs."""
        queue.add_url('https://example.com/about')
        queue.add_url('https://example.com/team')

        assert len(queue) == 2

        url = queue.pop()
        queue.mark_visited(url.url)

        assert len(queue) == 1

    def test_bool(self, queue):
        """Test boolean evaluation."""
        assert bool(queue) is False

        queue.add_url('https://example.com/about')
        assert bool(queue) is True

    def test_get_visited_urls(self, queue):
        """Test getting visited URLs."""
        queue.add_url('https://example.com/about')
        url = queue.pop()
        queue.mark_visited(url.url)

        visited = queue.get_visited_urls()
        assert len(visited) == 1
        assert queue.normalize_url('https://example.com/about') in visited

    def test_restore_state(self, queue):
        """Test restoring queue state."""
        queue.add_url('https://example.com/about')
        queue.add_url('https://example.com/team')
        url = queue.pop()
        queue.mark_visited(url.url, content_hash='hash1')

        # Get state
        state = queue.get_state()

        # Create new queue and restore
        new_queue = PagePriorityQueue(
            base_url='https://example.com',
            max_depth=3,
        )
        new_queue.restore_state(
            visited_urls=set(state['visited_urls']),
            seen_urls=set(state['seen_urls']),
            content_hashes=set(state['content_hashes']),
            queued_urls=state['queued_urls'],
        )

        assert new_queue.visited_count == queue.visited_count
        assert new_queue.seen_count == queue.seen_count
        assert len(new_queue) == len(queue)

    def test_get_stats(self, queue):
        """Test getting queue statistics."""
        queue.add_url('https://example.com/about')
        queue.add_url('https://example.com/blog')
        url = queue.pop()
        queue.mark_visited(url.url)

        stats = queue.get_stats()

        assert stats['pending_count'] == 1
        assert stats['visited_count'] == 1
        assert stats['seen_count'] == 2
        assert stats['max_depth'] == 3
        assert 'by_page_type' in stats


class TestPagePriorityQueuePriorities:
    """Tests for page type priorities."""

    def test_priority_order(self):
        """Test that priority values follow expected order."""
        # About should be highest priority
        assert PAGE_TYPE_PRIORITY['about'] < PAGE_TYPE_PRIORITY['team']
        assert PAGE_TYPE_PRIORITY['team'] < PAGE_TYPE_PRIORITY['product']
        assert PAGE_TYPE_PRIORITY['product'] < PAGE_TYPE_PRIORITY['service']
        assert PAGE_TYPE_PRIORITY['service'] < PAGE_TYPE_PRIORITY['contact']
        assert PAGE_TYPE_PRIORITY['contact'] < PAGE_TYPE_PRIORITY['careers']
        assert PAGE_TYPE_PRIORITY['careers'] < PAGE_TYPE_PRIORITY['pricing']
        assert PAGE_TYPE_PRIORITY['pricing'] < PAGE_TYPE_PRIORITY['blog']
        assert PAGE_TYPE_PRIORITY['blog'] < PAGE_TYPE_PRIORITY['news']
        assert PAGE_TYPE_PRIORITY['news'] < PAGE_TYPE_PRIORITY['other']

    def test_key_pages_prioritized(self):
        """Test that key pages come before blog/news."""
        queue = PagePriorityQueue(
            base_url='https://example.com',
            max_depth=3,
        )

        # Add in reverse priority order
        queue.add_url('https://example.com/news')
        queue.add_url('https://example.com/blog')
        queue.add_url('https://example.com/careers')
        queue.add_url('https://example.com/contact')
        queue.add_url('https://example.com/services')
        queue.add_url('https://example.com/products')
        queue.add_url('https://example.com/team')
        queue.add_url('https://example.com/about')

        # Pop should return in priority order
        order = []
        while queue:
            url = queue.pop()
            order.append(url.page_type)

        assert order[0] == 'about'
        assert order[1] == 'team'
        assert order[-1] == 'news'


class TestPagePriorityQueueBFS:
    """Tests for BFS behavior within priority levels."""

    def test_bfs_within_same_priority(self):
        """Test BFS order within same priority level."""
        queue = PagePriorityQueue(
            base_url='https://example.com',
            max_depth=5,
        )

        # Add 'other' type pages at different depths
        queue.add_url('https://example.com/page1', depth=0)
        queue.add_url('https://example.com/page2', depth=0)
        queue.add_url('https://example.com/sub/page3', depth=1)
        queue.add_url('https://example.com/sub/page4', depth=1)
        queue.add_url('https://example.com/deep/sub/page5', depth=2)

        # All are 'other' type, so should come out in depth order
        depths = []
        while queue:
            url = queue.pop()
            depths.append(url.depth)

        # Should be in ascending depth order (BFS)
        assert depths == sorted(depths)

    def test_insertion_order_preserved(self):
        """Test that insertion order is preserved at same priority/depth."""
        queue = PagePriorityQueue(
            base_url='https://example.com',
            max_depth=3,
        )

        # Add pages at same depth
        queue.add_url('https://example.com/a', depth=1)
        queue.add_url('https://example.com/b', depth=1)
        queue.add_url('https://example.com/c', depth=1)

        urls = []
        while queue:
            url = queue.pop()
            urls.append(url.url)

        # Should preserve insertion order
        assert 'a' in urls[0]
        assert 'b' in urls[1]
        assert 'c' in urls[2]
