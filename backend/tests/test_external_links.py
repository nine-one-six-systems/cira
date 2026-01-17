"""Tests for external link detection."""

import pytest

from app.crawlers.external_links import (
    ExternalLink,
    ExternalLinkDetector,
    PLATFORM_DOMAINS,
    external_link_detector,
)


class TestExternalLink:
    """Tests for ExternalLink dataclass."""

    def test_basic_creation(self):
        """Test creating an ExternalLink."""
        link = ExternalLink(
            url='https://linkedin.com/company/example',
            platform='linkedin',
            link_type='company',
            handle='example',
            found_on_url='https://example.com/about',
        )

        assert link.url == 'https://linkedin.com/company/example'
        assert link.platform == 'linkedin'
        assert link.link_type == 'company'
        assert link.handle == 'example'
        assert link.found_on_url == 'https://example.com/about'

    def test_to_dict(self):
        """Test ExternalLink to_dict method."""
        link = ExternalLink(
            url='https://twitter.com/example',
            platform='twitter',
            link_type='company',
            handle='example',
        )

        result = link.to_dict()

        assert result['url'] == 'https://twitter.com/example'
        assert result['platform'] == 'twitter'
        assert result['link_type'] == 'company'
        assert result['handle'] == 'example'
        assert result['found_on_url'] is None

    def test_optional_fields(self):
        """Test ExternalLink with optional fields."""
        link = ExternalLink(
            url='https://facebook.com/example',
            platform='facebook',
            link_type='page',
        )

        assert link.handle is None
        assert link.found_on_url is None


class TestPlatformDomains:
    """Tests for PLATFORM_DOMAINS constant."""

    def test_linkedin_domains(self):
        """Test LinkedIn domains."""
        assert 'linkedin.com' in PLATFORM_DOMAINS['linkedin']
        assert 'www.linkedin.com' in PLATFORM_DOMAINS['linkedin']

    def test_twitter_domains(self):
        """Test Twitter/X domains."""
        assert 'twitter.com' in PLATFORM_DOMAINS['twitter']
        assert 'x.com' in PLATFORM_DOMAINS['twitter']

    def test_facebook_domains(self):
        """Test Facebook domains."""
        assert 'facebook.com' in PLATFORM_DOMAINS['facebook']
        assert 'fb.com' in PLATFORM_DOMAINS['facebook']

    def test_all_platforms_present(self):
        """Test all expected platforms are defined."""
        expected_platforms = [
            'linkedin', 'twitter', 'facebook', 'instagram', 'youtube', 'github'
        ]
        for platform in expected_platforms:
            assert platform in PLATFORM_DOMAINS


class TestExternalLinkDetectorLinkedIn:
    """Tests for LinkedIn link detection."""

    @pytest.fixture
    def detector(self):
        """Create an ExternalLinkDetector instance."""
        return ExternalLinkDetector()

    def test_linkedin_company_link(self, detector):
        """Test LinkedIn company page detection."""
        html = '<a href="https://linkedin.com/company/acme-corp">LinkedIn</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'linkedin'
        assert links[0].link_type == 'company'
        assert links[0].handle == 'acme-corp'

    def test_linkedin_person_link(self, detector):
        """Test LinkedIn personal profile detection."""
        html = '<a href="https://linkedin.com/in/john-doe">John Doe</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'linkedin'
        assert links[0].link_type == 'person'
        assert links[0].handle == 'john-doe'

    def test_linkedin_showcase_link(self, detector):
        """Test LinkedIn showcase page detection."""
        html = '<a href="https://linkedin.com/showcase/product-showcase">Showcase</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'linkedin'
        assert links[0].link_type == 'page'

    def test_linkedin_www_domain(self, detector):
        """Test LinkedIn with www subdomain."""
        html = '<a href="https://www.linkedin.com/company/example">LinkedIn</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'linkedin'


class TestExternalLinkDetectorTwitter:
    """Tests for Twitter/X link detection."""

    @pytest.fixture
    def detector(self):
        """Create an ExternalLinkDetector instance."""
        return ExternalLinkDetector()

    def test_twitter_profile(self, detector):
        """Test Twitter profile detection."""
        html = '<a href="https://twitter.com/acmecorp">Twitter</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'twitter'
        assert links[0].handle == 'acmecorp'

    def test_x_domain(self, detector):
        """Test X.com domain detection."""
        html = '<a href="https://x.com/example">X</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'twitter'

    def test_twitter_with_query_params(self, detector):
        """Test Twitter URL with query parameters."""
        html = '<a href="https://twitter.com/acme?ref=website">Twitter</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].handle == 'acme'


class TestExternalLinkDetectorFacebook:
    """Tests for Facebook link detection."""

    @pytest.fixture
    def detector(self):
        """Create an ExternalLinkDetector instance."""
        return ExternalLinkDetector()

    def test_facebook_page(self, detector):
        """Test Facebook page detection."""
        html = '<a href="https://facebook.com/acmecorp">Facebook</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'facebook'
        assert links[0].link_type == 'page'

    def test_fb_shorthand(self, detector):
        """Test fb.com shorthand domain."""
        html = '<a href="https://fb.com/example">FB</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'facebook'


class TestExternalLinkDetectorOtherPlatforms:
    """Tests for other platform detection."""

    @pytest.fixture
    def detector(self):
        """Create an ExternalLinkDetector instance."""
        return ExternalLinkDetector()

    def test_instagram_link(self, detector):
        """Test Instagram link detection."""
        html = '<a href="https://instagram.com/acmecorp">Instagram</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'instagram'

    def test_youtube_channel(self, detector):
        """Test YouTube channel detection."""
        html = '<a href="https://youtube.com/c/AcmeCorp">YouTube</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'youtube'
        assert links[0].link_type == 'channel'

    def test_youtube_user(self, detector):
        """Test YouTube user page detection."""
        html = '<a href="https://youtube.com/user/acmecorp">YouTube</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'youtube'

    def test_youtube_at_handle(self, detector):
        """Test YouTube @handle format."""
        html = '<a href="https://youtube.com/@AcmeCorp">YouTube</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'youtube'

    def test_github_org(self, detector):
        """Test GitHub organization detection."""
        html = '<a href="https://github.com/acme-corp">GitHub</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'github'
        assert links[0].link_type == 'organization'


class TestExternalLinkDetectorFiltering:
    """Tests for link filtering."""

    @pytest.fixture
    def detector(self):
        """Create an ExternalLinkDetector instance."""
        return ExternalLinkDetector()

    def test_filters_generic_handles(self, detector):
        """Test that generic handles are filtered out."""
        html = '''
        <a href="https://twitter.com/share">Share</a>
        <a href="https://facebook.com/login">Login</a>
        '''
        links = detector.detect_links(html, 'https://example.com/')

        # These should be filtered because 'share' and 'login' are in IGNORE_HANDLES
        assert len(links) == 0

    def test_filters_javascript_links(self, detector):
        """Test that javascript: links are filtered."""
        html = '<a href="javascript:void(0)">Click</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 0

    def test_filters_mailto_links(self, detector):
        """Test that mailto: links are filtered."""
        html = '<a href="mailto:test@example.com">Email</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 0

    def test_deduplicates_links(self, detector):
        """Test that duplicate links are removed."""
        html = '''
        <a href="https://linkedin.com/company/acme">LinkedIn</a>
        <a href="https://linkedin.com/company/acme">LinkedIn Again</a>
        '''
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1


class TestExternalLinkDetectorURLHandling:
    """Tests for URL handling and normalization."""

    @pytest.fixture
    def detector(self):
        """Create an ExternalLinkDetector instance."""
        return ExternalLinkDetector()

    def test_protocol_relative_url(self, detector):
        """Test protocol-relative URLs."""
        html = '<a href="//linkedin.com/company/acme">LinkedIn</a>'
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].url.startswith('https://')

    def test_non_social_links_ignored(self, detector):
        """Test that non-social links are ignored."""
        html = '''
        <a href="https://example.com/page">Internal</a>
        <a href="https://google.com">Google</a>
        <a href="https://amazon.com">Amazon</a>
        '''
        links = detector.detect_links(html, 'https://example.com/')

        assert len(links) == 0


class TestExternalLinkDetectorMethods:
    """Tests for ExternalLinkDetector utility methods."""

    @pytest.fixture
    def detector(self):
        """Create an ExternalLinkDetector instance."""
        return ExternalLinkDetector()

    def test_is_social_link(self, detector):
        """Test is_social_link method."""
        assert detector.is_social_link('https://linkedin.com/company/test')
        assert detector.is_social_link('https://twitter.com/test')
        assert detector.is_social_link('https://facebook.com/test')
        assert not detector.is_social_link('https://google.com')
        assert not detector.is_social_link('https://example.com')

    def test_get_platform(self, detector):
        """Test get_platform method."""
        assert detector.get_platform('https://linkedin.com/company/test') == 'linkedin'
        assert detector.get_platform('https://twitter.com/test') == 'twitter'
        assert detector.get_platform('https://x.com/test') == 'twitter'
        assert detector.get_platform('https://facebook.com/test') == 'facebook'
        assert detector.get_platform('https://google.com') is None

    def test_detect_links_from_urls(self, detector):
        """Test detect_links_from_urls method."""
        urls = [
            'https://linkedin.com/company/acme',
            'https://twitter.com/acme',
            'https://google.com/search',
            'https://facebook.com/acme',
        ]

        links = detector.detect_links_from_urls(urls, 'https://example.com/')

        assert len(links) == 3
        platforms = {link.platform for link in links}
        assert 'linkedin' in platforms
        assert 'twitter' in platforms
        assert 'facebook' in platforms


class TestShouldFollow:
    """Tests for should_follow method."""

    @pytest.fixture
    def detector(self):
        """Create an ExternalLinkDetector instance."""
        return ExternalLinkDetector()

    def test_follow_linkedin_enabled(self, detector):
        """Test following LinkedIn when enabled."""
        config = {'followLinkedIn': True, 'followTwitter': False}
        url = 'https://linkedin.com/company/acme'

        assert detector.should_follow(url, config)

    def test_follow_linkedin_disabled(self, detector):
        """Test not following LinkedIn when disabled."""
        config = {'followLinkedIn': False, 'followTwitter': True}
        url = 'https://linkedin.com/company/acme'

        assert not detector.should_follow(url, config)

    def test_follow_twitter_enabled(self, detector):
        """Test following Twitter when enabled."""
        config = {'followLinkedIn': False, 'followTwitter': True}
        url = 'https://twitter.com/acme'

        assert detector.should_follow(url, config)

    def test_follow_facebook_enabled(self, detector):
        """Test following Facebook when enabled."""
        config = {'followFacebook': True}
        url = 'https://facebook.com/acme'

        assert detector.should_follow(url, config)

    def test_no_config(self, detector):
        """Test with no config."""
        url = 'https://linkedin.com/company/acme'

        assert not detector.should_follow(url, None)

    def test_unknown_platform(self, detector):
        """Test with unknown platform."""
        config = {'followLinkedIn': True}
        url = 'https://instagram.com/acme'

        assert not detector.should_follow(url, config)


class TestFilterCompanyLinks:
    """Tests for filter_company_links method."""

    @pytest.fixture
    def detector(self):
        """Create an ExternalLinkDetector instance."""
        return ExternalLinkDetector()

    def test_filters_person_links(self, detector):
        """Test that person links are filtered out."""
        links = [
            ExternalLink(
                url='https://linkedin.com/company/acme',
                platform='linkedin',
                link_type='company',
            ),
            ExternalLink(
                url='https://linkedin.com/in/john-doe',
                platform='linkedin',
                link_type='person',
            ),
        ]

        filtered = detector.filter_company_links(links)

        assert len(filtered) == 1
        assert filtered[0].link_type == 'company'

    def test_keeps_company_types(self, detector):
        """Test that company types are kept."""
        links = [
            ExternalLink(
                url='https://linkedin.com/company/acme',
                platform='linkedin',
                link_type='company',
            ),
            ExternalLink(
                url='https://facebook.com/acme',
                platform='facebook',
                link_type='page',
            ),
            ExternalLink(
                url='https://github.com/acme',
                platform='github',
                link_type='organization',
            ),
            ExternalLink(
                url='https://youtube.com/c/acme',
                platform='youtube',
                link_type='channel',
            ),
        ]

        filtered = detector.filter_company_links(links)

        assert len(filtered) == 4


class TestGlobalInstance:
    """Tests for global external_link_detector instance."""

    def test_global_instance_exists(self):
        """Test that global instance exists."""
        assert external_link_detector is not None
        assert isinstance(external_link_detector, ExternalLinkDetector)

    def test_global_instance_works(self):
        """Test that global instance can detect links."""
        html = '<a href="https://linkedin.com/company/test">LinkedIn</a>'
        links = external_link_detector.detect_links(html, 'https://example.com/')

        assert len(links) == 1
        assert links[0].platform == 'linkedin'
