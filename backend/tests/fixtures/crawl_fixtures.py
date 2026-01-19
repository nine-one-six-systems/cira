"""Shared fixtures for crawl integration testing.

Provides mock HTML responses, sitemap, robots.txt, and factory functions
for creating mock fetchers that simulate a realistic company website.
"""

from dataclasses import dataclass
from typing import Callable
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

from app.crawlers.browser_manager import PageContent


# Base URL for mock website
BASE_URL = "https://example-company.com"


# =============================================================================
# Mock HTML Responses
# =============================================================================

mock_html_responses: dict[str, str] = {
    f"{BASE_URL}/": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Example Company - Innovative Solutions</title>
    <meta charset="UTF-8">
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About Us</a>
            <a href="/team">Our Team</a>
            <a href="/products">Products</a>
            <a href="/contact">Contact</a>
            <a href="/blog">Blog</a>
        </nav>
    </header>
    <main>
        <h1>Welcome to Example Company</h1>
        <p>We are a leading provider of innovative solutions that help businesses
        transform their operations and achieve unprecedented growth. Our team of
        experts combines cutting-edge technology with deep industry knowledge to
        deliver results that exceed expectations.</p>
        <p>Founded in 2015, we have helped over 500 companies streamline their
        processes and increase productivity. Our commitment to excellence and
        customer satisfaction has made us a trusted partner for businesses
        worldwide.</p>
        <section class="social">
            <h3>Follow Us</h3>
            <a href="https://linkedin.com/company/example-company">LinkedIn</a>
            <a href="https://twitter.com/examplecompany">Twitter</a>
        </section>
    </main>
    <footer>
        <p>&copy; 2024 Example Company. All rights reserved.</p>
    </footer>
</body>
</html>""",

    f"{BASE_URL}/about": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>About Us - Example Company</title>
    <meta charset="UTF-8">
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About Us</a>
            <a href="/team">Our Team</a>
            <a href="/products">Products</a>
            <a href="/contact">Contact</a>
        </nav>
    </header>
    <main>
        <h1>About Example Company</h1>
        <p>Our mission is to empower businesses through innovative technology
        solutions. We believe that every company, regardless of size, deserves
        access to world-class tools and expertise that can help them succeed
        in today's competitive landscape.</p>
        <p>Our vision is to become the global leader in business transformation,
        helping millions of organizations unlock their full potential. We are
        committed to continuous innovation and excellence in everything we do.</p>
        <section class="values">
            <h2>Our Values</h2>
            <ul>
                <li>Innovation - We constantly push boundaries</li>
                <li>Integrity - We do what's right</li>
                <li>Excellence - We strive for the best</li>
                <li>Collaboration - We succeed together</li>
            </ul>
        </section>
        <a href="https://linkedin.com/company/example-company">Connect on LinkedIn</a>
    </main>
</body>
</html>""",

    f"{BASE_URL}/team": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Our Team - Example Company</title>
    <meta charset="UTF-8">
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About Us</a>
            <a href="/team">Our Team</a>
            <a href="/products">Products</a>
        </nav>
    </header>
    <main>
        <h1>Leadership Team</h1>
        <p>Our leadership team brings together decades of experience in
        technology, business strategy, and innovation. Together, they guide
        our company toward achieving its mission of empowering businesses
        worldwide.</p>
        <section class="executives">
            <article class="team-member">
                <h3>Jane Smith</h3>
                <p class="title">CEO & Co-Founder</p>
                <p>Jane has over 20 years of experience in technology leadership.
                Before founding Example Company, she served as VP of Engineering
                at a Fortune 500 company.</p>
            </article>
            <article class="team-member">
                <h3>John Doe</h3>
                <p class="title">CTO & Co-Founder</p>
                <p>John is a visionary technologist with expertise in AI and
                cloud computing. He holds several patents and has led teams
                at some of the world's most innovative companies.</p>
            </article>
            <article class="team-member">
                <h3>Emily Chen</h3>
                <p class="title">CFO</p>
                <p>Emily brings financial expertise and strategic insight to
                our leadership team. She previously served as CFO at multiple
                successful startups.</p>
            </article>
        </section>
        <a href="/team/advisors">Meet Our Advisors</a>
        <a href="https://linkedin.com/in/janesmith">Jane's LinkedIn</a>
    </main>
</body>
</html>""",

    f"{BASE_URL}/products": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Products - Example Company</title>
    <meta charset="UTF-8">
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About Us</a>
            <a href="/products">Products</a>
            <a href="/pricing">Pricing</a>
        </nav>
    </header>
    <main>
        <h1>Our Products</h1>
        <p>We offer a comprehensive suite of products designed to help
        businesses streamline operations, improve efficiency, and drive
        growth. Our solutions are built on cutting-edge technology and
        backed by world-class support.</p>
        <section class="product-list">
            <article class="product">
                <h2>Enterprise Platform</h2>
                <p>Our flagship product for large organizations. Includes
                advanced analytics, workflow automation, and seamless
                integration with existing systems.</p>
                <a href="/products/enterprise">Learn More</a>
            </article>
            <article class="product">
                <h2>Small Business Suite</h2>
                <p>Tailored for small and medium businesses. Get powerful
                features without the complexity. Easy to set up and use.</p>
                <a href="/products/smb">Learn More</a>
            </article>
            <article class="product">
                <h2>Analytics Dashboard</h2>
                <p>Real-time insights into your business performance. Make
                data-driven decisions with confidence.</p>
                <a href="/products/analytics">Learn More</a>
            </article>
        </section>
        <a href="https://facebook.com/examplecompany">Follow us on Facebook</a>
    </main>
</body>
</html>""",

    f"{BASE_URL}/contact": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Contact Us - Example Company</title>
    <meta charset="UTF-8">
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/about">About Us</a>
            <a href="/contact">Contact</a>
        </nav>
    </header>
    <main>
        <h1>Contact Us</h1>
        <p>We'd love to hear from you! Whether you have questions about our
        products, need support, or want to explore partnership opportunities,
        our team is here to help.</p>
        <section class="contact-info">
            <h2>Get in Touch</h2>
            <p>Email: info@example-company.com</p>
            <p>Phone: +1 (555) 123-4567</p>
            <p>Address: 123 Innovation Way, Tech City, TC 12345</p>
        </section>
        <section class="social-links">
            <h2>Follow Us</h2>
            <a href="https://linkedin.com/company/example-company">LinkedIn</a>
            <a href="https://twitter.com/examplecompany">Twitter</a>
            <a href="https://facebook.com/examplecompany">Facebook</a>
        </section>
    </main>
</body>
</html>""",

    f"{BASE_URL}/blog": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Blog - Example Company</title>
    <meta charset="UTF-8">
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/blog">Blog</a>
        </nav>
    </header>
    <main>
        <h1>Latest Posts</h1>
        <p>Stay up to date with the latest news, insights, and best practices
        from our team of experts. We share valuable content about technology,
        business transformation, and industry trends.</p>
        <article class="post">
            <h2><a href="/blog/post-1">The Future of Business Technology</a></h2>
            <p>Published on January 15, 2024</p>
            <p>Explore the emerging trends that will shape how businesses
            operate in the coming years...</p>
        </article>
        <article class="post">
            <h2><a href="/blog/post-2">5 Tips for Digital Transformation</a></h2>
            <p>Published on January 10, 2024</p>
            <p>Learn the key strategies for successfully transforming your
            business operations...</p>
        </article>
    </main>
</body>
</html>""",

    f"{BASE_URL}/admin": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Admin - Example Company</title>
</head>
<body>
    <h1>Admin Panel</h1>
    <p>This page should not be crawled (blocked by robots.txt)</p>
</body>
</html>""",

    f"{BASE_URL}/pricing": """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Pricing - Example Company</title>
    <meta charset="UTF-8">
</head>
<body>
    <header>
        <nav>
            <a href="/">Home</a>
            <a href="/products">Products</a>
            <a href="/pricing">Pricing</a>
        </nav>
    </header>
    <main>
        <h1>Pricing Plans</h1>
        <p>Choose the plan that's right for your business. All plans include
        our core features, dedicated support, and regular updates.</p>
        <section class="pricing-tiers">
            <div class="tier">
                <h2>Starter</h2>
                <p class="price">$49/month</p>
                <p>Perfect for small teams getting started.</p>
            </div>
            <div class="tier">
                <h2>Professional</h2>
                <p class="price">$149/month</p>
                <p>For growing businesses with advanced needs.</p>
            </div>
            <div class="tier">
                <h2>Enterprise</h2>
                <p class="price">Contact Us</p>
                <p>Custom solutions for large organizations.</p>
            </div>
        </section>
    </main>
</body>
</html>""",
}


# Additional pages for depth testing (page1 -> page2 -> page3 -> page4)
mock_html_responses[f"{BASE_URL}/page1"] = """<!DOCTYPE html>
<html lang="en">
<head><title>Page 1</title></head>
<body>
    <h1>Page 1</h1>
    <p>This is page 1, which links to page 2. It contains enough content
    to ensure proper text extraction and content hash generation.</p>
    <a href="/page2">Go to Page 2</a>
</body>
</html>"""

mock_html_responses[f"{BASE_URL}/page2"] = """<!DOCTYPE html>
<html lang="en">
<head><title>Page 2</title></head>
<body>
    <h1>Page 2</h1>
    <p>This is page 2, which links to page 3. It contains enough content
    to ensure proper text extraction and content hash generation.</p>
    <a href="/page3">Go to Page 3</a>
</body>
</html>"""

mock_html_responses[f"{BASE_URL}/page3"] = """<!DOCTYPE html>
<html lang="en">
<head><title>Page 3</title></head>
<body>
    <h1>Page 3</h1>
    <p>This is page 3, which links to page 4. It contains enough content
    to ensure proper text extraction and content hash generation.</p>
    <a href="/page4">Go to Page 4</a>
</body>
</html>"""

mock_html_responses[f"{BASE_URL}/page4"] = """<!DOCTYPE html>
<html lang="en">
<head><title>Page 4</title></head>
<body>
    <h1>Page 4</h1>
    <p>This is page 4, the deepest page. It contains enough content
    to ensure proper text extraction and content hash generation.</p>
</body>
</html>"""


# Duplicate content page (for testing content hash deduplication)
mock_html_responses[f"{BASE_URL}/about-duplicate"] = mock_html_responses[f"{BASE_URL}/about"]


# =============================================================================
# Mock Sitemap Response
# =============================================================================

mock_sitemap_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{BASE_URL}/</loc>
        <lastmod>2024-01-15</lastmod>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>{BASE_URL}/about</loc>
        <lastmod>2024-01-10</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>{BASE_URL}/team</loc>
        <lastmod>2024-01-08</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.8</priority>
    </url>
    <url>
        <loc>{BASE_URL}/products</loc>
        <lastmod>2024-01-12</lastmod>
        <changefreq>weekly</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>{BASE_URL}/contact</loc>
        <lastmod>2024-01-05</lastmod>
        <changefreq>monthly</changefreq>
        <priority>0.7</priority>
    </url>
</urlset>"""


# Extended sitemap with 10 URLs (for max_pages limit testing)
mock_sitemap_extended = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url><loc>{BASE_URL}/</loc></url>
    <url><loc>{BASE_URL}/about</loc></url>
    <url><loc>{BASE_URL}/team</loc></url>
    <url><loc>{BASE_URL}/products</loc></url>
    <url><loc>{BASE_URL}/contact</loc></url>
    <url><loc>{BASE_URL}/pricing</loc></url>
    <url><loc>{BASE_URL}/blog</loc></url>
    <url><loc>{BASE_URL}/blog/post-1</loc></url>
    <url><loc>{BASE_URL}/blog/post-2</loc></url>
    <url><loc>{BASE_URL}/blog/post-3</loc></url>
</urlset>"""


# =============================================================================
# Mock Robots.txt Response
# =============================================================================

mock_robots_response = f"""User-agent: *
Allow: /
Disallow: /admin
Disallow: /private
Crawl-delay: 1

Sitemap: {BASE_URL}/sitemap.xml
"""


# Permissive robots.txt (allows all)
mock_robots_allow_all = """User-agent: *
Allow: /
"""


# =============================================================================
# Mock External Links
# =============================================================================

mock_external_links = {
    "linkedin": [
        "https://linkedin.com/company/example-company",
        "https://linkedin.com/in/janesmith",
    ],
    "twitter": [
        "https://twitter.com/examplecompany",
    ],
    "facebook": [
        "https://facebook.com/examplecompany",
    ],
}


# =============================================================================
# Factory Functions
# =============================================================================

def create_mock_fetcher(
    responses: dict[str, str] | None = None,
    default_status: int = 200,
) -> MagicMock:
    """
    Create a mock SimpleFetcher that returns appropriate HTML based on URL.

    Args:
        responses: Optional dict mapping URLs to HTML content.
                  Defaults to mock_html_responses.
        default_status: HTTP status code for successful responses.

    Returns:
        MagicMock configured to return PageContent objects.
    """
    responses = responses or mock_html_responses
    mock_fetcher = MagicMock()

    def fetch_page(url: str) -> PageContent:
        """Fetch page implementation for mock."""
        from bs4 import BeautifulSoup

        # Normalize URL (remove trailing slash for non-root paths)
        normalized = url.rstrip('/') if url != f"{BASE_URL}/" else url

        # Check if URL exists in responses
        if normalized in responses:
            html = responses[normalized]
            soup = BeautifulSoup(html, 'lxml')

            # Remove script/style for text extraction
            for element in soup(['script', 'style', 'noscript']):
                element.decompose()

            text = soup.get_text(separator=' ', strip=True)
            title = soup.title.string if soup.title else ''

            return PageContent(
                url=url,
                html=html,
                text=text,
                title=title,
                status_code=default_status,
                final_url=url,
                error=None,
            )

        # URL not found
        return PageContent(
            url=url,
            html='',
            text='',
            title='',
            status_code=404,
            final_url=url,
            error='Not Found',
        )

    mock_fetcher.fetch_page = MagicMock(side_effect=fetch_page)
    return mock_fetcher


def create_mock_robots_parser(
    robots_content: str | None = None,
    disallowed_paths: list[str] | None = None,
) -> MagicMock:
    """
    Create a mock RobotsParser.

    Args:
        robots_content: Optional robots.txt content (not used directly).
        disallowed_paths: List of paths that should be disallowed.
                         Defaults to ['/admin', '/private'].

    Returns:
        MagicMock configured for robots.txt checking.
    """
    disallowed = disallowed_paths or ['/admin', '/private']
    mock_parser = MagicMock()

    def is_allowed(url: str) -> bool:
        """Check if URL is allowed by robots.txt."""
        parsed = urlparse(url)
        path = parsed.path

        for disallowed_path in disallowed:
            if path.startswith(disallowed_path):
                return False
        return True

    mock_parser.is_allowed = MagicMock(side_effect=is_allowed)
    mock_parser.get_crawl_delay = MagicMock(return_value=None)
    mock_parser.get_sitemaps = MagicMock(return_value=[f"{BASE_URL}/sitemap.xml"])
    mock_parser.get_rules = MagicMock(return_value=MagicMock(
        is_allowed=is_allowed,
        disallowed_paths=disallowed,
        crawl_delay=None,
        sitemaps=[f"{BASE_URL}/sitemap.xml"],
    ))

    return mock_parser


def create_mock_sitemap_parser(
    sitemap_urls: list[str] | None = None,
) -> MagicMock:
    """
    Create a mock SitemapParser.

    Args:
        sitemap_urls: List of URLs to return from sitemap.
                     Defaults to standard test URLs.

    Returns:
        MagicMock configured for sitemap parsing.
    """
    from app.crawlers.sitemap_parser import SitemapResult, SitemapURL

    urls = sitemap_urls or [
        f"{BASE_URL}/",
        f"{BASE_URL}/about",
        f"{BASE_URL}/team",
        f"{BASE_URL}/products",
        f"{BASE_URL}/contact",
    ]

    mock_parser = MagicMock()

    def get_urls(url: str, max_urls: int | None = None, force_refresh: bool = False):
        """Get URLs from sitemap."""
        sitemap_url_objects = [
            SitemapURL(url=u, lastmod=None, changefreq=None, priority=None)
            for u in urls
        ]
        return SitemapResult(
            domain=urlparse(url).netloc,
            urls=sitemap_url_objects,
            sitemap_urls=[f"{BASE_URL}/sitemap.xml"],
            errors=[],
            fetch_time=0.1,
        )

    mock_parser.get_urls = MagicMock(side_effect=get_urls)
    return mock_parser


def create_mock_rate_limiter() -> MagicMock:
    """
    Create a mock RateLimiter that doesn't actually delay.

    Returns:
        MagicMock that immediately returns for acquire calls.
    """
    mock_limiter = MagicMock()
    mock_limiter.acquire = MagicMock(return_value=True)
    mock_limiter.release = MagicMock()
    mock_limiter.set_default_rate = MagicMock()
    mock_limiter.can_request = MagicMock(return_value=True)
    mock_limiter.wait_time_for = MagicMock(return_value=0.0)
    return mock_limiter


def create_mock_http_responses() -> dict[str, tuple[int, str]]:
    """
    Create dict mapping URLs to (status_code, content) for httpx/requests mocking.

    Returns:
        Dict mapping URLs to (status, content) tuples.
    """
    responses = {}

    # Add sitemap.xml
    responses[f"{BASE_URL}/sitemap.xml"] = (200, mock_sitemap_response)

    # Add robots.txt
    responses[f"{BASE_URL}/robots.txt"] = (200, mock_robots_response)

    # Add all HTML pages
    for url, html in mock_html_responses.items():
        responses[url] = (200, html)

    return responses


@dataclass
class MockCrawlEnvironment:
    """Container for all mock objects needed for crawl testing."""

    fetcher: MagicMock
    robots_parser: MagicMock
    sitemap_parser: MagicMock
    rate_limiter: MagicMock
    http_responses: dict[str, tuple[int, str]]


def create_mock_crawl_environment(
    html_responses: dict[str, str] | None = None,
    disallowed_paths: list[str] | None = None,
    sitemap_urls: list[str] | None = None,
) -> MockCrawlEnvironment:
    """
    Create a complete mock environment for crawl integration testing.

    Args:
        html_responses: Custom HTML responses to use.
        disallowed_paths: Custom disallowed paths for robots.txt.
        sitemap_urls: Custom sitemap URLs.

    Returns:
        MockCrawlEnvironment with all configured mocks.
    """
    return MockCrawlEnvironment(
        fetcher=create_mock_fetcher(html_responses),
        robots_parser=create_mock_robots_parser(disallowed_paths=disallowed_paths),
        sitemap_parser=create_mock_sitemap_parser(sitemap_urls),
        rate_limiter=create_mock_rate_limiter(),
        http_responses=create_mock_http_responses(),
    )


# =============================================================================
# Pytest Fixtures (for import into test files)
# =============================================================================

def pytest_crawl_fixtures():
    """
    Return dict of pytest fixture definitions.

    Usage in test file:
        from backend.tests.fixtures.crawl_fixtures import pytest_crawl_fixtures
        fixtures = pytest_crawl_fixtures()
    """
    import pytest

    @pytest.fixture
    def mock_fetcher():
        """Pytest fixture for mock fetcher."""
        return create_mock_fetcher()

    @pytest.fixture
    def mock_robots():
        """Pytest fixture for mock robots parser."""
        return create_mock_robots_parser()

    @pytest.fixture
    def mock_sitemap():
        """Pytest fixture for mock sitemap parser."""
        return create_mock_sitemap_parser()

    @pytest.fixture
    def mock_rate_limiter():
        """Pytest fixture for mock rate limiter."""
        return create_mock_rate_limiter()

    @pytest.fixture
    def crawl_environment():
        """Pytest fixture for complete crawl environment."""
        return create_mock_crawl_environment()

    return {
        'mock_fetcher': mock_fetcher,
        'mock_robots': mock_robots,
        'mock_sitemap': mock_sitemap,
        'mock_rate_limiter': mock_rate_limiter,
        'crawl_environment': crawl_environment,
    }
