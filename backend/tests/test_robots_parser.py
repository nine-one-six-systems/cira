"""Tests for robots.txt parser."""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from app.crawlers.robots_parser import RobotsParser, RobotsRules


class TestRobotsRules:
    """Tests for RobotsRules dataclass."""

    def test_default_allows_all(self):
        """Empty rules should allow all paths."""
        rules = RobotsRules(domain='example.com')
        assert rules.is_allowed('/') is True
        assert rules.is_allowed('/about') is True
        assert rules.is_allowed('/team/leadership') is True

    def test_not_found_allows_all(self):
        """Missing robots.txt should allow all paths."""
        rules = RobotsRules(domain='example.com', found=False)
        assert rules.is_allowed('/') is True
        assert rules.is_allowed('/admin') is True
        assert rules.is_allowed('/private/data') is True

    def test_disallow_single_path(self):
        """Single disallow rule should block matching path."""
        rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/admin']
        )
        assert rules.is_allowed('/') is True
        assert rules.is_allowed('/admin') is False
        assert rules.is_allowed('/admin/') is False
        assert rules.is_allowed('/admin/users') is False
        assert rules.is_allowed('/about') is True

    def test_disallow_multiple_paths(self):
        """Multiple disallow rules should block all matching paths."""
        rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/admin', '/private', '/api']
        )
        assert rules.is_allowed('/admin') is False
        assert rules.is_allowed('/private') is False
        assert rules.is_allowed('/api') is False
        assert rules.is_allowed('/api/v1') is False
        assert rules.is_allowed('/about') is True
        assert rules.is_allowed('/team') is True

    def test_disallow_root(self):
        """Disallow / should block everything."""
        rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/']
        )
        assert rules.is_allowed('/') is False
        assert rules.is_allowed('/about') is False
        assert rules.is_allowed('/team') is False

    def test_allow_overrides_disallow(self):
        """Allow with longer match should override disallow."""
        rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/admin'],
            allowed_paths=['/admin/public']
        )
        assert rules.is_allowed('/admin') is False
        assert rules.is_allowed('/admin/users') is False
        assert rules.is_allowed('/admin/public') is True
        assert rules.is_allowed('/admin/public/stats') is True

    def test_disallow_overrides_allow_with_longer_match(self):
        """Disallow with longer match should override allow."""
        rules = RobotsRules(
            domain='example.com',
            allowed_paths=['/api'],
            disallowed_paths=['/api/internal']
        )
        assert rules.is_allowed('/api') is True
        assert rules.is_allowed('/api/v1') is True
        assert rules.is_allowed('/api/internal') is False
        assert rules.is_allowed('/api/internal/stats') is False

    def test_wildcard_pattern(self):
        """Wildcard * should match any characters."""
        rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/private/*.pdf']
        )
        assert rules.is_allowed('/private/doc.pdf') is False
        assert rules.is_allowed('/private/report.pdf') is False
        assert rules.is_allowed('/private/doc.html') is True
        assert rules.is_allowed('/public/doc.pdf') is True

    def test_end_anchor_pattern(self):
        """Pattern ending with $ should match exact end."""
        rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/*.php$']
        )
        assert rules.is_allowed('/index.php') is False
        assert rules.is_allowed('/admin/login.php') is False
        assert rules.is_allowed('/index.php?id=1') is True  # Has query string
        assert rules.is_allowed('/index.html') is True

    def test_complex_wildcard_pattern(self):
        """Complex patterns with multiple wildcards."""
        rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/*/admin/*']
        )
        assert rules.is_allowed('/site/admin/users') is False
        assert rules.is_allowed('/app/admin/settings') is False
        assert rules.is_allowed('/admin/users') is True  # Doesn't match prefix
        assert rules.is_allowed('/site/public') is True

    def test_empty_path_normalized(self):
        """Empty path should be treated as /."""
        rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/']
        )
        assert rules.is_allowed('') is False
        assert rules.is_allowed('/') is False

    def test_path_without_leading_slash(self):
        """Path without leading slash should be normalized."""
        rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/admin']
        )
        assert rules.is_allowed('admin') is False
        assert rules.is_allowed('admin/users') is False

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        original = RobotsRules(
            domain='example.com',
            allowed_paths=['/public', '/api'],
            disallowed_paths=['/admin', '/private'],
            crawl_delay=2.5,
            sitemaps=['https://example.com/sitemap.xml'],
            fetch_time=1234567890.0,
            found=True
        )

        data = original.to_dict()
        restored = RobotsRules.from_dict(data)

        assert restored.domain == original.domain
        assert restored.allowed_paths == original.allowed_paths
        assert restored.disallowed_paths == original.disallowed_paths
        assert restored.crawl_delay == original.crawl_delay
        assert restored.sitemaps == original.sitemaps
        assert restored.fetch_time == original.fetch_time
        assert restored.found == original.found

    def test_from_dict_with_missing_fields(self):
        """from_dict should handle missing fields gracefully."""
        data = {'domain': 'example.com'}
        rules = RobotsRules.from_dict(data)

        assert rules.domain == 'example.com'
        assert rules.allowed_paths == []
        assert rules.disallowed_paths == []
        assert rules.crawl_delay is None
        assert rules.sitemaps == []
        assert rules.fetch_time == 0.0
        assert rules.found is True


class TestRobotsParser:
    """Tests for RobotsParser class."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis service."""
        mock = MagicMock()
        mock.is_available = True
        mock.cache_get.return_value = None
        mock.cache_set.return_value = True
        mock.cache_delete.return_value = True
        return mock

    @pytest.fixture
    def parser(self, mock_redis):
        """Create a parser with mock Redis."""
        return RobotsParser(redis_svc=mock_redis)

    def test_get_domain(self, parser):
        """Test domain extraction from URL."""
        assert parser._get_domain('https://example.com/page') == 'example.com'
        assert parser._get_domain('http://sub.example.com:8080/') == 'sub.example.com:8080'
        assert parser._get_domain('https://example.com') == 'example.com'

    def test_get_robots_url(self, parser):
        """Test robots.txt URL generation."""
        url = parser._get_robots_url('https://example.com/about/team')
        assert url == 'https://example.com/robots.txt'

        url = parser._get_robots_url('http://sub.example.com:8080/page')
        assert url == 'http://sub.example.com:8080/robots.txt'

    @patch('app.crawlers.robots_parser.requests.get')
    def test_fetch_robots_success(self, mock_get, parser):
        """Test successful robots.txt fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
User-agent: *
Disallow: /admin
Allow: /admin/public
Crawl-delay: 2
Sitemap: https://example.com/sitemap.xml
"""
        mock_get.return_value = mock_response

        rules = parser._fetch_robots('https://example.com/page')

        assert rules.domain == 'example.com'
        assert rules.found is True
        assert '/admin' in rules.disallowed_paths
        assert '/admin/public' in rules.allowed_paths
        assert rules.crawl_delay == 2.0
        assert 'https://example.com/sitemap.xml' in rules.sitemaps

    @patch('app.crawlers.robots_parser.requests.get')
    def test_fetch_robots_not_found(self, mock_get, parser):
        """Test handling of missing robots.txt (404)."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        rules = parser._fetch_robots('https://example.com/')

        assert rules.domain == 'example.com'
        assert rules.found is False
        assert rules.is_allowed('/admin') is True  # Allow all when not found

    @patch('app.crawlers.robots_parser.requests.get')
    def test_fetch_robots_server_error(self, mock_get, parser):
        """Test handling of server errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        rules = parser._fetch_robots('https://example.com/')

        assert rules.found is False  # Treat as not found on errors

    @patch('app.crawlers.robots_parser.requests.get')
    def test_fetch_robots_timeout(self, mock_get, parser):
        """Test handling of timeout."""
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout('Connection timed out')

        rules = parser._fetch_robots('https://example.com/')

        assert rules.found is False

    @patch('app.crawlers.robots_parser.requests.get')
    def test_fetch_robots_connection_error(self, mock_get, parser):
        """Test handling of connection errors."""
        mock_get.side_effect = requests.ConnectionError('Failed to connect')

        rules = parser._fetch_robots('https://example.com/')

        assert rules.found is False

    def test_parse_robots_basic(self, parser):
        """Test basic robots.txt parsing."""
        content = """
User-agent: *
Disallow: /private
Disallow: /admin
Allow: /admin/public
Crawl-delay: 1.5
"""
        rules = parser._parse_robots('example.com', content)

        assert rules.domain == 'example.com'
        assert '/private' in rules.disallowed_paths
        assert '/admin' in rules.disallowed_paths
        assert '/admin/public' in rules.allowed_paths
        assert rules.crawl_delay == 1.5

    def test_parse_robots_cira_specific(self, parser):
        """Test CIRA-specific user-agent rules."""
        content = """
User-agent: *
Disallow: /

User-agent: CIRA Bot
Disallow: /private
Allow: /
"""
        rules = parser._parse_robots('example.com', content)

        # Should use CIRA-specific rules, not wildcard
        assert '/private' in rules.disallowed_paths
        assert '/' in rules.allowed_paths
        # Should NOT use wildcard's disallow /
        assert rules.disallowed_paths == ['/private']

    def test_parse_robots_comments(self, parser):
        """Test that comments are ignored."""
        content = """
# This is a comment
User-agent: *
Disallow: /admin  # Inline comment
# Another comment
Disallow: /private
"""
        rules = parser._parse_robots('example.com', content)

        assert '/admin' in rules.disallowed_paths
        assert '/private' in rules.disallowed_paths

    def test_parse_robots_multiple_sitemaps(self, parser):
        """Test parsing multiple sitemaps."""
        content = """
User-agent: *
Disallow:

Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap-news.xml
Sitemap: https://example.com/sitemap-images.xml
"""
        rules = parser._parse_robots('example.com', content)

        assert len(rules.sitemaps) == 3
        assert 'https://example.com/sitemap.xml' in rules.sitemaps
        assert 'https://example.com/sitemap-news.xml' in rules.sitemaps
        assert 'https://example.com/sitemap-images.xml' in rules.sitemaps

    def test_parse_robots_malformed_lines(self, parser):
        """Test handling of malformed lines."""
        content = """
User-agent: *
Disallow: /admin
This is not a valid directive
Disallow /missing-colon
: empty directive
Disallow: /private
"""
        rules = parser._parse_robots('example.com', content)

        # Should still parse valid directives
        assert '/admin' in rules.disallowed_paths
        assert '/private' in rules.disallowed_paths

    def test_parse_robots_empty_disallow(self, parser):
        """Test empty Disallow (allows all)."""
        content = """
User-agent: *
Disallow:
"""
        rules = parser._parse_robots('example.com', content)

        assert rules.disallowed_paths == []
        assert rules.is_allowed('/anything') is True

    def test_parse_robots_invalid_crawl_delay(self, parser):
        """Test handling of invalid crawl-delay."""
        content = """
User-agent: *
Crawl-delay: not-a-number
Disallow: /admin
"""
        rules = parser._parse_robots('example.com', content)

        assert rules.crawl_delay is None
        assert '/admin' in rules.disallowed_paths

    @patch('app.crawlers.robots_parser.requests.get')
    def test_caching_memory(self, mock_get, parser, mock_redis):
        """Test memory caching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin"
        mock_get.return_value = mock_response

        # First call should fetch
        rules1 = parser.get_rules('https://example.com/')
        assert mock_get.call_count == 1

        # Second call should use memory cache
        rules2 = parser.get_rules('https://example.com/')
        assert mock_get.call_count == 1  # No additional fetch

        assert rules1.disallowed_paths == rules2.disallowed_paths

    @patch('app.crawlers.robots_parser.requests.get')
    def test_caching_redis(self, mock_get, parser, mock_redis):
        """Test Redis caching."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin"
        mock_get.return_value = mock_response

        # Fetch once
        parser.get_rules('https://example.com/')

        # Verify Redis cache_set was called
        assert mock_redis.cache_set.called
        cache_key = mock_redis.cache_set.call_args[0][0]
        assert 'robots:example.com' == cache_key

    @patch('app.crawlers.robots_parser.requests.get')
    def test_caching_redis_hit(self, mock_get, mock_redis):
        """Test cache hit from Redis."""
        # Set up Redis to return cached rules
        cached_rules = {
            'domain': 'example.com',
            'disallowed_paths': ['/cached'],
            'allowed_paths': [],
            'crawl_delay': None,
            'sitemaps': [],
            'fetch_time': time.time(),
            'found': True
        }
        mock_redis.cache_get.return_value = cached_rules

        parser = RobotsParser(redis_svc=mock_redis)
        rules = parser.get_rules('https://example.com/')

        # Should not fetch - used cached
        assert mock_get.call_count == 0
        assert '/cached' in rules.disallowed_paths

    @patch('app.crawlers.robots_parser.requests.get')
    def test_force_refresh(self, mock_get, parser):
        """Test force_refresh bypasses cache."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin"
        mock_get.return_value = mock_response

        # First call
        parser.get_rules('https://example.com/')
        assert mock_get.call_count == 1

        # Second call with force_refresh
        parser.get_rules('https://example.com/', force_refresh=True)
        assert mock_get.call_count == 2

    @patch('app.crawlers.robots_parser.requests.get')
    def test_is_allowed(self, mock_get, parser):
        """Test is_allowed convenience method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin"
        mock_get.return_value = mock_response

        assert parser.is_allowed('https://example.com/about') is True
        assert parser.is_allowed('https://example.com/admin') is False
        assert parser.is_allowed('https://example.com/admin/users') is False

    @patch('app.crawlers.robots_parser.requests.get')
    def test_is_allowed_with_query_string(self, mock_get, parser):
        """Test is_allowed with query strings."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /search"
        mock_get.return_value = mock_response

        assert parser.is_allowed('https://example.com/search?q=test') is False
        assert parser.is_allowed('https://example.com/about?ref=home') is True

    @patch('app.crawlers.robots_parser.requests.get')
    def test_get_crawl_delay(self, mock_get, parser):
        """Test get_crawl_delay method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nCrawl-delay: 3.5\nDisallow: /admin"
        mock_get.return_value = mock_response

        delay = parser.get_crawl_delay('https://example.com/')
        assert delay == 3.5

    @patch('app.crawlers.robots_parser.requests.get')
    def test_get_crawl_delay_not_set(self, mock_get, parser):
        """Test get_crawl_delay when not specified."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin"
        mock_get.return_value = mock_response

        delay = parser.get_crawl_delay('https://example.com/')
        assert delay is None

    @patch('app.crawlers.robots_parser.requests.get')
    def test_get_sitemaps(self, mock_get, parser):
        """Test get_sitemaps method."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
User-agent: *
Disallow:

Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap-products.xml
"""
        mock_get.return_value = mock_response

        sitemaps = parser.get_sitemaps('https://example.com/')
        assert len(sitemaps) == 2
        assert 'https://example.com/sitemap.xml' in sitemaps
        assert 'https://example.com/sitemap-products.xml' in sitemaps

    def test_clear_cache_specific_domain(self, parser, mock_redis):
        """Test clearing cache for specific domain."""
        # Pre-populate memory cache
        parser._memory_cache['example.com'] = RobotsRules(domain='example.com')
        parser._memory_cache['other.com'] = RobotsRules(domain='other.com')

        parser.clear_cache('example.com')

        assert 'example.com' not in parser._memory_cache
        assert 'other.com' in parser._memory_cache
        assert mock_redis.cache_delete.called

    def test_clear_cache_all(self, parser, mock_redis):
        """Test clearing all cache."""
        # Pre-populate memory cache
        parser._memory_cache['example.com'] = RobotsRules(domain='example.com')
        parser._memory_cache['other.com'] = RobotsRules(domain='other.com')

        parser.clear_cache()

        assert len(parser._memory_cache) == 0

    @patch('app.crawlers.robots_parser.requests.get')
    def test_cache_expiry(self, mock_get, mock_redis):
        """Test that expired cache entries are refreshed."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "User-agent: *\nDisallow: /admin"
        mock_get.return_value = mock_response

        parser = RobotsParser(redis_svc=mock_redis)

        # Manually add expired cache entry
        expired_rules = RobotsRules(
            domain='example.com',
            disallowed_paths=['/old'],
            fetch_time=time.time() - 100000  # Very old
        )
        parser._memory_cache['example.com'] = expired_rules

        # Should fetch new rules
        rules = parser.get_rules('https://example.com/')
        assert mock_get.call_count == 1
        assert '/admin' in rules.disallowed_paths
        assert '/old' not in rules.disallowed_paths


class TestRobotsParserIntegration:
    """Integration tests for robots parser with real-world scenarios."""

    @pytest.fixture
    def parser(self):
        """Create parser with disabled caching for tests."""
        mock_redis = MagicMock()
        mock_redis.is_available = False
        return RobotsParser(redis_svc=mock_redis)

    def test_real_world_robots_google(self, parser):
        """Test parsing a Google-style robots.txt."""
        content = """
User-agent: *
Disallow: /search
Disallow: /sdch
Disallow: /groups
Allow: /search/about
Allow: /groups/static

User-agent: Googlebot
Allow: /

Sitemap: https://www.google.com/sitemap.xml
"""
        rules = parser._parse_robots('google.com', content)

        # For wildcard user agent (CIRA Bot falls back to this)
        assert '/search' in rules.disallowed_paths
        assert '/search/about' in rules.allowed_paths
        assert rules.is_allowed('/search') is False
        assert rules.is_allowed('/search/about') is True
        assert rules.is_allowed('/about') is True

    def test_real_world_robots_comprehensive(self, parser):
        """Test parsing a comprehensive robots.txt."""
        content = """
# Comments at top
User-agent: *
Crawl-delay: 10
Disallow: /cgi-bin/
Disallow: /tmp/
Disallow: /~joe/
Disallow: /*.pdf$
Disallow: /*?*
Allow: /public/
Allow: /*.html$

# CIRA gets special access
User-agent: CIRA Bot
Crawl-delay: 1
Disallow: /private/
Allow: /

Sitemap: https://example.com/sitemap.xml
Sitemap: https://example.com/sitemap-images.xml
"""
        rules = parser._parse_robots('example.com', content)

        # Should use CIRA-specific rules
        assert rules.crawl_delay == 1.0
        assert '/private/' in rules.disallowed_paths
        assert '/' in rules.allowed_paths

        # Should have sitemaps
        assert len(rules.sitemaps) == 2

    def test_real_world_empty_robots(self, parser):
        """Test parsing an empty robots.txt (allows all)."""
        content = ""
        rules = parser._parse_robots('example.com', content)

        assert rules.disallowed_paths == []
        assert rules.is_allowed('/anything') is True

    def test_real_world_disallow_all(self, parser):
        """Test parsing robots.txt that disallows all."""
        content = """
User-agent: *
Disallow: /
"""
        rules = parser._parse_robots('example.com', content)

        assert rules.is_allowed('/') is False
        assert rules.is_allowed('/about') is False
        assert rules.is_allowed('/team') is False
