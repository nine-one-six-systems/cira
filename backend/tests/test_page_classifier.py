"""Tests for page classifier."""

import pytest

from app.crawlers.page_classifier import (
    PageClassifier,
    PageClassification,
    PAGE_TYPES,
    page_classifier,
)


class TestPageClassification:
    """Tests for PageClassification dataclass."""

    def test_basic_creation(self):
        """Test creating a PageClassification."""
        classification = PageClassification(
            page_type='about',
            confidence=0.9,
            match_source='url',
            matched_patterns=['/about/?$'],
        )

        assert classification.page_type == 'about'
        assert classification.confidence == 0.9
        assert classification.match_source == 'url'
        assert len(classification.matched_patterns) == 1


class TestPageTypesConstant:
    """Tests for PAGE_TYPES constant."""

    def test_all_types_present(self):
        """Test that all expected page types are defined."""
        expected_types = [
            'about', 'team', 'product', 'service', 'contact',
            'careers', 'pricing', 'blog', 'news', 'other'
        ]
        for ptype in expected_types:
            assert ptype in PAGE_TYPES


class TestPageClassifierURLPatterns:
    """Tests for URL-based classification."""

    @pytest.fixture
    def classifier(self):
        """Create a PageClassifier instance."""
        return PageClassifier()

    # About pages
    @pytest.mark.parametrize('url,expected_type', [
        ('https://example.com/about', 'about'),
        ('https://example.com/about/', 'about'),
        ('https://example.com/about-us', 'about'),
        ('https://example.com/about_us/', 'about'),
        ('https://example.com/company', 'about'),
        ('https://example.com/who-we-are', 'about'),
        ('https://example.com/our-story', 'about'),
        ('https://example.com/mission', 'about'),
        ('https://example.com/vision', 'about'),
        ('https://example.com/values', 'about'),
        ('https://example.com/history', 'about'),
    ])
    def test_about_pages(self, classifier, url, expected_type):
        """Test about page URL patterns."""
        result = classifier.classify(url)
        assert result.page_type == expected_type
        assert result.match_source == 'url'

    # Team pages
    @pytest.mark.parametrize('url,expected_type', [
        ('https://example.com/team', 'team'),
        ('https://example.com/team/', 'team'),
        ('https://example.com/our-team', 'team'),
        ('https://example.com/people', 'team'),
        ('https://example.com/leadership', 'team'),
        ('https://example.com/management', 'team'),
        ('https://example.com/founders', 'team'),
        ('https://example.com/executives', 'team'),
        ('https://example.com/board', 'team'),
        ('https://example.com/advisors', 'team'),
        ('https://example.com/team/john-doe', 'team'),
    ])
    def test_team_pages(self, classifier, url, expected_type):
        """Test team page URL patterns."""
        result = classifier.classify(url)
        assert result.page_type == expected_type

    # Product pages
    @pytest.mark.parametrize('url,expected_type', [
        ('https://example.com/products', 'product'),
        ('https://example.com/product', 'product'),
        ('https://example.com/solutions', 'product'),
        ('https://example.com/platform', 'product'),
        ('https://example.com/features', 'product'),
        ('https://example.com/offerings', 'product'),
        ('https://example.com/tools', 'product'),
        ('https://example.com/software', 'product'),
        ('https://example.com/products/enterprise', 'product'),
    ])
    def test_product_pages(self, classifier, url, expected_type):
        """Test product page URL patterns."""
        result = classifier.classify(url)
        assert result.page_type == expected_type

    # Service pages
    @pytest.mark.parametrize('url,expected_type', [
        ('https://example.com/services', 'service'),
        ('https://example.com/service', 'service'),
        ('https://example.com/what-we-do', 'service'),
        ('https://example.com/capabilities', 'service'),
        ('https://example.com/consulting', 'service'),
        ('https://example.com/expertise', 'service'),
        ('https://example.com/services/development', 'service'),
    ])
    def test_service_pages(self, classifier, url, expected_type):
        """Test service page URL patterns."""
        result = classifier.classify(url)
        assert result.page_type == expected_type

    # Contact pages
    @pytest.mark.parametrize('url,expected_type', [
        ('https://example.com/contact', 'contact'),
        ('https://example.com/contact/', 'contact'),
        ('https://example.com/contact-us', 'contact'),
        ('https://example.com/get-in-touch', 'contact'),
        ('https://example.com/reach-us', 'contact'),
        ('https://example.com/locations', 'contact'),
        ('https://example.com/offices', 'contact'),
        ('https://example.com/support', 'contact'),
    ])
    def test_contact_pages(self, classifier, url, expected_type):
        """Test contact page URL patterns."""
        result = classifier.classify(url)
        assert result.page_type == expected_type

    # Careers pages
    @pytest.mark.parametrize('url,expected_type', [
        ('https://example.com/careers', 'careers'),
        ('https://example.com/career', 'careers'),
        ('https://example.com/jobs', 'careers'),
        ('https://example.com/job', 'careers'),
        ('https://example.com/join-us', 'careers'),
        ('https://example.com/hiring', 'careers'),
        ('https://example.com/opportunities', 'careers'),
        ('https://example.com/work-with-us', 'careers'),
        ('https://example.com/openings', 'careers'),
        ('https://example.com/careers/engineering', 'careers'),
    ])
    def test_careers_pages(self, classifier, url, expected_type):
        """Test careers page URL patterns."""
        result = classifier.classify(url)
        assert result.page_type == expected_type

    # Pricing pages
    @pytest.mark.parametrize('url,expected_type', [
        ('https://example.com/pricing', 'pricing'),
        ('https://example.com/pricing/', 'pricing'),
        ('https://example.com/plans', 'pricing'),
        ('https://example.com/packages', 'pricing'),
        ('https://example.com/cost', 'pricing'),
        ('https://example.com/subscription', 'pricing'),
    ])
    def test_pricing_pages(self, classifier, url, expected_type):
        """Test pricing page URL patterns."""
        result = classifier.classify(url)
        assert result.page_type == expected_type

    # Blog pages
    @pytest.mark.parametrize('url,expected_type', [
        ('https://example.com/blog', 'blog'),
        ('https://example.com/blog/', 'blog'),
        ('https://example.com/articles', 'blog'),
        ('https://example.com/insights', 'blog'),
        ('https://example.com/resources', 'blog'),
        ('https://example.com/learn', 'blog'),
        ('https://example.com/blog/my-post', 'blog'),
    ])
    def test_blog_pages(self, classifier, url, expected_type):
        """Test blog page URL patterns."""
        result = classifier.classify(url)
        assert result.page_type == expected_type

    # News pages
    @pytest.mark.parametrize('url,expected_type', [
        ('https://example.com/news', 'news'),
        ('https://example.com/news/', 'news'),
        ('https://example.com/press', 'news'),
        ('https://example.com/press-releases', 'news'),
        ('https://example.com/media', 'news'),
        ('https://example.com/announcements', 'news'),
        ('https://example.com/newsroom', 'news'),
        ('https://example.com/news/2024-funding', 'news'),
    ])
    def test_news_pages(self, classifier, url, expected_type):
        """Test news page URL patterns."""
        result = classifier.classify(url)
        assert result.page_type == expected_type

    def test_unknown_page_returns_other(self, classifier):
        """Test that unknown URLs return 'other' type."""
        result = classifier.classify('https://example.com/random-page-xyz')
        assert result.page_type == 'other'
        assert result.match_source == 'default'

    def test_home_page_returns_other(self, classifier):
        """Test that home page returns 'other' type."""
        result = classifier.classify('https://example.com/')
        assert result.page_type == 'other'


class TestPageClassifierContentPatterns:
    """Tests for content-based classification."""

    @pytest.fixture
    def classifier(self):
        """Create a PageClassifier instance."""
        return PageClassifier()

    def test_about_content(self, classifier):
        """Test about page content patterns."""
        content = """
        Our Mission is to provide the best software solutions.
        Our Vision is to be the industry leader.
        Founded in 2015, we have been serving customers worldwide.
        Who we are: A team of dedicated professionals.
        """
        # Use a generic URL so content determines the type
        result = classifier.classify('https://example.com/page', content)
        assert result.page_type == 'about'

    def test_team_content(self, classifier):
        """Test team page content patterns."""
        content = """
        Our Team consists of talented individuals.
        Leadership Team: John Smith - CEO, Jane Doe - CTO
        Executive Team drives our company forward.
        Board of Directors oversees our strategy.
        """
        result = classifier.classify('https://example.com/page', content)
        assert result.page_type == 'team'

    def test_careers_content(self, classifier):
        """Test careers page content patterns."""
        content = """
        Job Openings - We're hiring!
        Open Positions in Engineering, Sales, and Marketing.
        Join Our Team and make an impact.
        Career Opportunities await you.
        """
        result = classifier.classify('https://example.com/page', content)
        assert result.page_type == 'careers'

    def test_contact_content(self, classifier):
        """Test contact page content patterns."""
        content = """
        Contact Us for more information.
        Get in touch with our team.
        Send us a message and we'll respond within 24 hours.
        """
        result = classifier.classify('https://example.com/page', content)
        assert result.page_type == 'contact'

    def test_pricing_content(self, classifier):
        """Test pricing page content patterns."""
        content = """
        Pricing Plans to fit your needs.
        Monthly plan: $49/month
        Annual plan: $499/year - Save 15%!
        Start your free trial today.
        """
        result = classifier.classify('https://example.com/page', content)
        assert result.page_type == 'pricing'

    def test_news_content(self, classifier):
        """Test news page content patterns."""
        content = """
        Press Release: Company Announces New Product
        News & Events - Latest updates
        In the news: CEO interviewed by Tech Magazine
        """
        result = classifier.classify('https://example.com/page', content)
        assert result.page_type == 'news'


class TestPageClassifierCombined:
    """Tests for combined URL and content classification."""

    @pytest.fixture
    def classifier(self):
        """Create a PageClassifier instance."""
        return PageClassifier()

    def test_url_and_content_agree(self, classifier):
        """Test when URL and content patterns agree."""
        content = "Our Team is composed of industry experts."
        result = classifier.classify('https://example.com/team', content)

        assert result.page_type == 'team'
        assert result.match_source == 'combined'
        assert result.confidence > 0.7  # Combined confidence from both sources

    def test_url_stronger_than_content(self, classifier):
        """Test when URL pattern is stronger."""
        content = "Some generic content about the page"
        result = classifier.classify('https://example.com/about', content)

        assert result.page_type == 'about'
        assert result.match_source == 'url'

    def test_content_only_when_url_not_matched(self, classifier):
        """Test content classification when URL doesn't match."""
        content = "Job Openings - We're hiring talented engineers!"
        result = classifier.classify('https://example.com/page', content)

        assert result.page_type == 'careers'
        assert result.match_source == 'content'


class TestPageClassifierMethods:
    """Tests for additional PageClassifier methods."""

    @pytest.fixture
    def classifier(self):
        """Create a PageClassifier instance."""
        return PageClassifier()

    def test_classify_url_only(self, classifier):
        """Test classify_url_only method."""
        result = classifier.classify_url_only('https://example.com/about')
        assert result == 'about'

        result = classifier.classify_url_only('https://example.com/unknown')
        assert result == 'other'

    def test_get_all_patterns(self, classifier):
        """Test get_all_patterns method."""
        patterns = classifier.get_all_patterns()

        assert 'url_patterns' in patterns
        assert 'content_patterns' in patterns

        # Check URL patterns
        assert 'about' in patterns['url_patterns']
        assert 'team' in patterns['url_patterns']
        assert len(patterns['url_patterns']['about']) > 0

        # Check content patterns
        assert 'about' in patterns['content_patterns']
        assert 'careers' in patterns['content_patterns']


class TestGlobalInstance:
    """Tests for global page_classifier instance."""

    def test_global_instance_exists(self):
        """Test that global instance exists and works."""
        assert page_classifier is not None
        assert isinstance(page_classifier, PageClassifier)

    def test_global_instance_works(self):
        """Test that global instance can classify pages."""
        result = page_classifier.classify('https://example.com/careers')
        assert result.page_type == 'careers'


class TestConfidenceScoring:
    """Tests for confidence scoring."""

    @pytest.fixture
    def classifier(self):
        """Create a PageClassifier instance."""
        return PageClassifier()

    def test_exact_match_high_confidence(self, classifier):
        """Test that exact URL matches have high confidence."""
        result = classifier.classify('https://example.com/about')
        assert result.confidence >= 0.9

    def test_subpage_lower_confidence(self, classifier):
        """Test that subpages have somewhat lower confidence."""
        # Team page
        main = classifier.classify('https://example.com/team')
        sub = classifier.classify('https://example.com/team/john-doe')

        assert main.confidence > sub.confidence

    def test_confidence_range(self, classifier):
        """Test that confidence is always in valid range."""
        urls = [
            'https://example.com/about',
            'https://example.com/team/leadership',
            'https://example.com/products',
            'https://example.com/random',
        ]

        for url in urls:
            result = classifier.classify(url)
            assert 0.0 <= result.confidence <= 1.0


class TestCaseInsensitivity:
    """Tests for case-insensitive matching."""

    @pytest.fixture
    def classifier(self):
        """Create a PageClassifier instance."""
        return PageClassifier()

    def test_uppercase_path(self, classifier):
        """Test uppercase URL paths are matched."""
        result = classifier.classify('https://example.com/ABOUT')
        assert result.page_type == 'about'

    def test_mixed_case_path(self, classifier):
        """Test mixed case URL paths are matched."""
        result = classifier.classify('https://example.com/About-Us')
        assert result.page_type == 'about'

    def test_mixed_case_content(self, classifier):
        """Test mixed case content is matched."""
        content = "OUR MISSION is to help businesses grow."
        result = classifier.classify('https://example.com/page', content)
        assert result.page_type == 'about'
