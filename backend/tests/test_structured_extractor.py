"""Tests for the Structured Data Extractor (Task 5.3 & 5.4)."""

import pytest


class TestEmailExtraction:
    """Test email extraction."""

    def test_extract_simple_email(self):
        """Test extracting a simple email address."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Contact us at info@acmecorp.com for more information."
        emails = extractor.extract_emails(text)

        assert len(emails) == 1
        assert emails[0].normalized_value == "info@acmecorp.com"

    def test_extract_multiple_emails(self):
        """Test extracting multiple email addresses."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Email john@company.com or support@company.io for help."
        emails = extractor.extract_emails(text)

        assert len(emails) == 2
        values = [e.normalized_value for e in emails]
        assert "john@company.com" in values
        assert "support@company.io" in values

    def test_extract_obfuscated_email(self):
        """Test extracting obfuscated email (user [at] domain [dot] com)."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Contact us at info [at] company [dot] com"
        emails = extractor.extract_emails(text)

        assert len(emails) == 1
        assert emails[0].normalized_value == "info@company.com"
        assert emails[0].confidence < 0.95  # Lower confidence for obfuscated

    def test_reject_invalid_email(self):
        """Test that invalid emails are rejected."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Invalid: user@ or @domain.com or just text"
        emails = extractor.extract_emails(text)

        assert len(emails) == 0

    def test_reject_example_domain(self):
        """Test that example.com domains are rejected."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Example: user@test.com and fake@domain.com"
        emails = extractor.extract_emails(text)

        # Should reject these placeholder domains
        values = [e.normalized_value for e in emails]
        assert "user@test.com" not in values
        assert "fake@domain.com" not in values

    def test_email_deduplication(self):
        """Test that duplicate emails are deduplicated."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Contact info@company.com or INFO@COMPANY.COM"
        emails = extractor.extract_emails(text)

        assert len(emails) == 1  # Should be deduplicated

    def test_email_context(self):
        """Test that email context is extracted."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "For sales inquiries, email sales@acme.org today."
        emails = extractor.extract_emails(text)

        assert len(emails) == 1
        assert 'sales' in emails[0].context.lower()


class TestPhoneExtraction:
    """Test phone number extraction."""

    def test_extract_us_phone_standard(self):
        """Test extracting standard US phone number."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Call us at (555) 123-4567 for support."
        phones = extractor.extract_phones(text)

        assert len(phones) == 1
        assert phones[0].normalized_value == "+15551234567"

    def test_extract_us_phone_dashes(self):
        """Test extracting US phone with dashes."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Phone: 555-123-4567"
        phones = extractor.extract_phones(text)

        assert len(phones) == 1
        assert phones[0].normalized_value == "+15551234567"

    def test_extract_us_phone_dots(self):
        """Test extracting US phone with dots."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Call 555.123.4567"
        phones = extractor.extract_phones(text)

        assert len(phones) == 1
        assert phones[0].normalized_value == "+15551234567"

    def test_extract_international_phone(self):
        """Test extracting international phone number."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "International: +1-555-123-4567"
        phones = extractor.extract_phones(text)

        assert len(phones) == 1
        assert "555" in phones[0].normalized_value

    def test_phone_deduplication(self):
        """Test phone number deduplication."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Call (555) 123-4567 or 555-123-4567"
        phones = extractor.extract_phones(text)

        assert len(phones) == 1  # Should be deduplicated

    def test_phone_context(self):
        """Test phone context extraction."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "For sales, call (555) 123-4567 now."
        phones = extractor.extract_phones(text)

        assert len(phones) == 1
        assert 'sales' in phones[0].context.lower()


class TestAddressExtraction:
    """Test address extraction."""

    def test_extract_us_street_address(self):
        """Test extracting US street address."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Our office is at 123 Main Street, Suite 100"
        addresses = extractor.extract_addresses(text)

        assert len(addresses) >= 1
        assert any('Main Street' in a.value for a in addresses)

    def test_extract_address_with_city_state_zip(self):
        """Test extracting address with city, state, ZIP."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Located in San Francisco, CA 94102"
        addresses = extractor.extract_addresses(text)

        assert len(addresses) >= 1

    def test_address_context(self):
        """Test address context extraction."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Headquarters: 456 Tech Boulevard, San Francisco"
        addresses = extractor.extract_addresses(text)

        if addresses:
            assert 'Tech Boulevard' in addresses[0].value or 'Headquarters' in addresses[0].context


class TestSocialHandleExtraction:
    """Test social media handle extraction."""

    def test_extract_twitter_handle(self):
        """Test extracting Twitter handle."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Follow us on Twitter: @acmecompany"
        handles = extractor.extract_social_handles(text)

        assert any(h.extra_data.get('platform') == 'twitter' for h in handles)
        assert any('acmecompany' in h.normalized_value.lower() for h in handles)

    def test_extract_twitter_url(self):
        """Test extracting Twitter URL."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Twitter: https://twitter.com/acmecompany"
        handles = extractor.extract_social_handles(text)

        assert any(h.extra_data.get('platform') == 'twitter' for h in handles)

    def test_extract_linkedin_company(self):
        """Test extracting LinkedIn company URL."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "LinkedIn: https://linkedin.com/company/acme-corp"
        handles = extractor.extract_social_handles(text)

        assert any(h.extra_data.get('platform') == 'linkedin' for h in handles)
        assert any('acme' in h.normalized_value.lower() for h in handles)

    def test_extract_linkedin_person(self):
        """Test extracting LinkedIn personal URL."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "LinkedIn: https://linkedin.com/in/johnsmith"
        handles = extractor.extract_social_handles(text)

        assert any(h.extra_data.get('platform') == 'linkedin' for h in handles)
        assert any('johnsmith' in h.normalized_value.lower() for h in handles)

    def test_extract_facebook_url(self):
        """Test extracting Facebook URL."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "Facebook: https://facebook.com/acmecorp"
        handles = extractor.extract_social_handles(text)

        assert any(h.extra_data.get('platform') == 'facebook' for h in handles)

    def test_extract_github_url(self):
        """Test extracting GitHub URL."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "GitHub: https://github.com/acme-corp"
        handles = extractor.extract_social_handles(text)

        assert any(h.extra_data.get('platform') == 'github' for h in handles)

    def test_filter_generic_handles(self):
        """Test that generic handles are filtered out."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        text = "https://twitter.com/share and https://twitter.com/login"
        handles = extractor.extract_social_handles(text)

        # 'share' and 'login' should be filtered out
        values = [h.normalized_value.lower() for h in handles]
        assert 'share' not in values
        assert 'login' not in values


class TestTechStackExtraction:
    """Test tech stack extraction."""

    def test_extract_languages_disabled_by_default(self):
        """Test that tech stack is disabled by default."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=False)
        text = "We use Python and JavaScript."
        result = extractor.extract_tech_stack(text)

        # When not enabled, extract_all won't call extract_tech_stack
        assert result == []  # Direct call should still work but return empty

    def test_extract_python(self):
        """Test extracting Python language."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=True)
        text = "Our backend is built with Python."
        tech = extractor.extract_tech_stack(text)

        assert any(t.normalized_value == 'python' for t in tech)
        assert any(t.extra_data.get('category') == 'languages' for t in tech)

    def test_extract_javascript(self):
        """Test extracting JavaScript language."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=True)
        text = "Frontend uses JavaScript and TypeScript."
        tech = extractor.extract_tech_stack(text)

        assert any(t.normalized_value == 'javascript' for t in tech)
        assert any(t.normalized_value == 'typescript' for t in tech)

    def test_extract_react_framework(self):
        """Test extracting React framework."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=True)
        text = "Our UI is built with React and Next.js"
        tech = extractor.extract_tech_stack(text)

        assert any(t.normalized_value == 'react' for t in tech)
        assert any(t.normalized_value == 'nextjs' for t in tech)

    def test_extract_database(self):
        """Test extracting database technology."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=True)
        text = "We use PostgreSQL and Redis for caching."
        tech = extractor.extract_tech_stack(text)

        assert any(t.normalized_value == 'postgresql' for t in tech)
        assert any(t.normalized_value == 'redis' for t in tech)
        assert any(t.extra_data.get('category') == 'databases' for t in tech)

    def test_extract_cloud_provider(self):
        """Test extracting cloud provider."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=True)
        text = "Deployed on AWS with Kubernetes."
        tech = extractor.extract_tech_stack(text)

        assert any(t.normalized_value == 'aws' for t in tech)
        assert any(t.normalized_value == 'kubernetes' for t in tech)

    def test_extract_docker(self):
        """Test extracting Docker."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=True)
        text = "All services run in Docker containers."
        tech = extractor.extract_tech_stack(text)

        assert any(t.normalized_value == 'docker' for t in tech)

    def test_tech_stack_confidence_increases_with_mentions(self):
        """Test that confidence increases with multiple mentions."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=True)
        text = "We use Python. Python is great. Python Python Python."
        tech = extractor.extract_tech_stack(text)

        python_tech = [t for t in tech if t.normalized_value == 'python']
        assert len(python_tech) == 1
        assert python_tech[0].confidence > 0.7  # Boosted by multiple mentions
        assert python_tech[0].extra_data.get('mentions', 0) >= 3

    def test_tech_stack_deduplication(self):
        """Test that tech stack entries are deduplicated."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=True)
        text = "Python, PYTHON, python are all the same."
        tech = extractor.extract_tech_stack(text)

        python_count = sum(1 for t in tech if t.normalized_value == 'python')
        assert python_count == 1  # Should only appear once


class TestExtractAll:
    """Test extract_all function."""

    def test_extract_all_combines_results(self):
        """Test that extract_all combines all extractors."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=True)
        text = """
        Contact: info@company.com
        Phone: (555) 123-4567
        Address: 123 Main Street, San Francisco, CA 94102
        Twitter: @companyhandle
        Built with Python and React.
        """
        result = extractor.extract_all(text)

        # Should have multiple entity types
        types = {e.entity_type for e in result}
        assert 'email' in types
        assert 'phone' in types
        assert 'social_handle' in types
        assert 'tech_stack' in types

    def test_extract_all_without_tech_stack(self):
        """Test extract_all with tech stack disabled."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor(enable_tech_stack=False)
        text = "Email: test@company.org and we use Python"
        result = extractor.extract_all(text)

        # Should have email but not tech_stack
        types = {e.entity_type for e in result}
        assert 'email' in types
        assert 'tech_stack' not in types


class TestStructuredEntity:
    """Test StructuredEntity dataclass."""

    def test_entity_to_dict(self):
        """Test converting entity to dictionary."""
        from app.extractors.structured_extractor import StructuredEntity

        entity = StructuredEntity(
            entity_type='email',
            value='TEST@company.com',
            normalized_value='test@company.com',
            confidence=0.95,
            context='Contact at TEST@company.com',
            extra_data={'platform': 'email'}
        )

        result = entity.to_dict()

        assert result['type'] == 'email'
        assert result['value'] == 'TEST@company.com'
        assert result['normalized'] == 'test@company.com'
        assert result['confidence'] == 0.95

    def test_entity_default_normalized(self):
        """Test that normalized defaults to value."""
        from app.extractors.structured_extractor import StructuredEntity

        entity = StructuredEntity(
            entity_type='phone',
            value='(555) 123-4567',
            confidence=0.9,
            context='Call us'
        )

        result = entity.to_dict()
        assert result['normalized'] == '(555) 123-4567'


class TestGlobalExtractor:
    """Test global extractor instance."""

    def test_global_extractor_exists(self):
        """Test that global extractor is available."""
        from app.extractors.structured_extractor import structured_extractor

        assert structured_extractor is not None

    def test_global_extractor_type(self):
        """Test global extractor type."""
        from app.extractors.structured_extractor import (
            structured_extractor,
            StructuredDataExtractor
        )

        assert isinstance(structured_extractor, StructuredDataExtractor)

    def test_global_extractor_tech_stack_disabled(self):
        """Test that global extractor has tech stack disabled by default."""
        from app.extractors.structured_extractor import structured_extractor

        assert structured_extractor.enable_tech_stack is False
