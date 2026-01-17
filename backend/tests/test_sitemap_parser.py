"""Tests for sitemap parser."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.crawlers.sitemap_parser import (
    SitemapParser,
    SitemapResult,
    SitemapURL,
    sitemap_parser,
)


class TestSitemapURL:
    """Tests for SitemapURL dataclass."""

    def test_basic_url(self):
        """Test basic URL creation."""
        url = SitemapURL(url='https://example.com/page')
        assert url.url == 'https://example.com/page'
        assert url.lastmod is None
        assert url.changefreq is None
        assert url.priority is None

    def test_url_with_metadata(self):
        """Test URL with all metadata."""
        now = datetime.now()
        url = SitemapURL(
            url='https://example.com/page',
            lastmod=now,
            changefreq='weekly',
            priority=0.8,
        )
        assert url.lastmod == now
        assert url.changefreq == 'weekly'
        assert url.priority == 0.8

    def test_to_dict(self):
        """Test conversion to dictionary."""
        now = datetime(2024, 1, 15, 10, 30, 0)
        url = SitemapURL(
            url='https://example.com/page',
            lastmod=now,
            changefreq='daily',
            priority=0.5,
        )
        data = url.to_dict()

        assert data['url'] == 'https://example.com/page'
        assert data['lastmod'] == '2024-01-15T10:30:00'
        assert data['changefreq'] == 'daily'
        assert data['priority'] == 0.5

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            'url': 'https://example.com/page',
            'lastmod': '2024-01-15T10:30:00',
            'changefreq': 'monthly',
            'priority': 0.3,
        }
        url = SitemapURL.from_dict(data)

        assert url.url == 'https://example.com/page'
        assert url.lastmod == datetime(2024, 1, 15, 10, 30, 0)
        assert url.changefreq == 'monthly'
        assert url.priority == 0.3

    def test_from_dict_missing_fields(self):
        """Test from_dict with missing fields."""
        data = {'url': 'https://example.com/page'}
        url = SitemapURL.from_dict(data)

        assert url.url == 'https://example.com/page'
        assert url.lastmod is None


class TestSitemapResult:
    """Tests for SitemapResult dataclass."""

    def test_empty_result(self):
        """Test empty result."""
        result = SitemapResult(domain='example.com')
        assert result.url_count == 0
        assert result.errors == []

    def test_with_urls(self):
        """Test result with URLs."""
        result = SitemapResult(
            domain='example.com',
            urls=[
                SitemapURL(url='https://example.com/page1'),
                SitemapURL(url='https://example.com/page2'),
            ],
        )
        assert result.url_count == 2

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = SitemapResult(
            domain='example.com',
            urls=[SitemapURL(url='https://example.com/page')],
            sitemap_urls=['https://example.com/sitemap.xml'],
            errors=['Error 1'],
            fetch_time=1.5,
        )
        data = result.to_dict()

        assert data['domain'] == 'example.com'
        assert len(data['urls']) == 1
        assert len(data['sitemap_urls']) == 1
        assert len(data['errors']) == 1


class TestSitemapParser:
    """Tests for SitemapParser class."""

    @pytest.fixture
    def mock_redis(self):
        """Create mock Redis service."""
        mock = MagicMock()
        mock.is_available = True
        mock.cache_get.return_value = None
        mock.cache_set.return_value = True
        return mock

    @pytest.fixture
    def parser(self, mock_redis):
        """Create parser with mock Redis."""
        return SitemapParser(redis_svc=mock_redis)

    def test_get_domain(self, parser):
        """Test domain extraction."""
        assert parser._get_domain('https://example.com/page') == 'example.com'
        assert parser._get_domain('http://sub.example.com:8080/') == 'sub.example.com:8080'

    def test_get_sitemap_url(self, parser):
        """Test sitemap URL generation."""
        url = parser._get_sitemap_url('https://example.com/about')
        assert url == 'https://example.com/sitemap.xml'

    def test_parse_date_formats(self, parser):
        """Test various date format parsing."""
        # YYYY-MM-DD
        date = parser._parse_date('2024-01-15')
        assert date == datetime(2024, 1, 15)

        # ISO 8601 with timezone
        date = parser._parse_date('2024-01-15T10:30:00Z')
        assert date is not None

        # ISO 8601 without timezone
        date = parser._parse_date('2024-01-15T10:30:00')
        assert date is not None

        # Invalid date
        date = parser._parse_date('not-a-date')
        assert date is None

    @patch.object(SitemapParser, '_fetch_sitemap')
    def test_parse_sitemap_urlset(self, mock_fetch, parser):
        """Test parsing a URL set sitemap."""
        sitemap_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/page1</loc>
    <lastmod>2024-01-15</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://example.com/page2</loc>
  </url>
</urlset>'''

        sitemap_type, data = parser._parse_sitemap(sitemap_xml)

        assert sitemap_type == 'urlset'
        assert len(data) == 2
        assert data[0].url == 'https://example.com/page1'
        assert data[0].priority == 0.8
        assert data[1].url == 'https://example.com/page2'

    @patch.object(SitemapParser, '_fetch_sitemap')
    def test_parse_sitemap_index(self, mock_fetch, parser):
        """Test parsing a sitemap index."""
        index_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://example.com/sitemap-1.xml</loc>
  </sitemap>
  <sitemap>
    <loc>https://example.com/sitemap-2.xml</loc>
  </sitemap>
</sitemapindex>'''

        sitemap_type, data = parser._parse_sitemap(index_xml)

        assert sitemap_type == 'index'
        assert len(data) == 2
        assert 'https://example.com/sitemap-1.xml' in data
        assert 'https://example.com/sitemap-2.xml' in data

    def test_parse_sitemap_invalid_xml(self, parser):
        """Test parsing invalid XML."""
        invalid_xml = b'not valid xml <>'

        sitemap_type, data = parser._parse_sitemap(invalid_xml)

        assert sitemap_type == 'error'
        assert data == []

    def test_parse_sitemap_no_namespace(self, parser):
        """Test parsing sitemap without namespace."""
        sitemap_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<urlset>
  <url>
    <loc>https://example.com/page1</loc>
  </url>
</urlset>'''

        sitemap_type, data = parser._parse_sitemap(sitemap_xml)

        assert sitemap_type == 'urlset'
        assert len(data) == 1

    @patch('app.crawlers.sitemap_parser.requests.Session.get')
    def test_fetch_sitemap_success(self, mock_get, parser):
        """Test successful sitemap fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<urlset></urlset>'
        mock_response.headers = {}
        mock_get.return_value = mock_response

        content = parser._fetch_sitemap('https://example.com/sitemap.xml')

        assert content == b'<urlset></urlset>'

    @patch('app.crawlers.sitemap_parser.requests.Session.get')
    def test_fetch_sitemap_not_found(self, mock_get, parser):
        """Test sitemap not found."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        content = parser._fetch_sitemap('https://example.com/sitemap.xml')

        assert content is None

    @patch('app.crawlers.sitemap_parser.requests.Session.get')
    def test_fetch_sitemap_gzipped(self, mock_get, parser):
        """Test gzipped sitemap handling."""
        import gzip

        original = b'<urlset></urlset>'
        compressed = gzip.compress(original)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = compressed
        mock_response.headers = {'Content-Encoding': 'gzip'}
        mock_get.return_value = mock_response

        content = parser._fetch_sitemap('https://example.com/sitemap.xml.gz')

        assert content == original

    @patch('app.crawlers.sitemap_parser.requests.Session.get')
    def test_fetch_sitemap_timeout(self, mock_get, parser):
        """Test sitemap fetch timeout."""
        from requests.exceptions import Timeout
        mock_get.side_effect = Timeout()

        content = parser._fetch_sitemap('https://example.com/sitemap.xml')

        assert content is None

    @patch.object(SitemapParser, '_fetch_sitemap')
    def test_get_urls_basic(self, mock_fetch, parser, mock_redis):
        """Test getting URLs from sitemap."""
        sitemap_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
  <url><loc>https://example.com/page2</loc></url>
</urlset>'''

        mock_fetch.return_value = sitemap_xml

        result = parser.get_urls('https://example.com/')

        assert result.domain == 'example.com'
        assert result.url_count == 2

    @patch.object(SitemapParser, '_fetch_sitemap')
    def test_get_urls_with_index(self, mock_fetch, parser, mock_redis):
        """Test getting URLs from sitemap index."""
        index_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
</sitemapindex>'''

        urlset_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/page1</loc></url>
</urlset>'''

        mock_fetch.side_effect = [index_xml, urlset_xml]

        result = parser.get_urls('https://example.com/')

        assert result.url_count == 1
        assert len(result.sitemap_urls) == 2

    @patch.object(SitemapParser, '_fetch_sitemap')
    def test_get_urls_max_urls(self, mock_fetch, parser, mock_redis):
        """Test max URLs limit."""
        urls = ''.join(
            f'<url><loc>https://example.com/page{i}</loc></url>'
            for i in range(100)
        )
        sitemap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>'''.encode()

        mock_fetch.return_value = sitemap_xml

        result = parser.get_urls('https://example.com/', max_urls=10)

        assert result.url_count == 10

    @patch.object(SitemapParser, '_fetch_sitemap')
    def test_get_urls_cache_hit(self, mock_fetch, parser, mock_redis):
        """Test cache hit."""
        mock_redis.cache_get.return_value = {
            'domain': 'example.com',
            'urls': [{'url': 'https://example.com/cached'}],
            'sitemap_urls': [],
            'errors': [],
            'fetch_time': 1.0,
        }

        result = parser.get_urls('https://example.com/')

        assert result.url_count == 1
        assert result.urls[0].url == 'https://example.com/cached'
        mock_fetch.assert_not_called()

    @patch.object(SitemapParser, '_fetch_sitemap')
    def test_get_urls_no_sitemap(self, mock_fetch, parser, mock_redis):
        """Test handling of missing sitemap."""
        mock_fetch.return_value = None

        result = parser.get_urls('https://example.com/')

        assert result.url_count == 0
        assert len(result.sitemap_urls) == 0

    def test_clear_cache(self, parser, mock_redis):
        """Test cache clearing."""
        parser.clear_cache('example.com')
        mock_redis.cache_delete.assert_called_once()


class TestSitemapParserIntegration:
    """Integration tests for sitemap parser."""

    @pytest.fixture
    def parser(self):
        """Create parser with disabled caching."""
        mock_redis = MagicMock()
        mock_redis.is_available = False
        return SitemapParser(redis_svc=mock_redis)

    def test_real_world_sitemap(self, parser):
        """Test parsing a comprehensive sitemap."""
        sitemap_xml = b'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9
        http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
  <url>
    <loc>https://example.com/</loc>
    <lastmod>2024-01-15T10:00:00+00:00</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://example.com/about</loc>
    <lastmod>2024-01-10</lastmod>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://example.com/contact</loc>
  </url>
</urlset>'''

        sitemap_type, data = parser._parse_sitemap(sitemap_xml)

        assert sitemap_type == 'urlset'
        assert len(data) == 3

        # Check first URL has all metadata
        assert data[0].url == 'https://example.com/'
        assert data[0].lastmod is not None
        assert data[0].changefreq == 'daily'
        assert data[0].priority == 1.0

        # Check second URL has partial metadata
        assert data[1].url == 'https://example.com/about'
        assert data[1].priority == 0.8

        # Check third URL has no metadata
        assert data[2].url == 'https://example.com/contact'
        assert data[2].lastmod is None
