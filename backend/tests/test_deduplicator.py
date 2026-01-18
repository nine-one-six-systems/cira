"""Tests for the Entity Deduplicator (Task 5.5)."""

import pytest


class TestEntityDeduplicatorBasics:
    """Test deduplicator initialization and basic operations."""

    def test_deduplicator_initializes(self):
        """Test that deduplicator initializes without error."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        assert deduplicator is not None

    def test_deduplicate_empty_list(self):
        """Test deduplicating empty list."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        result = deduplicator.deduplicate_entities([])

        assert result == []

    def test_deduplicate_single_entity(self):
        """Test deduplicating single entity."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [{
            'type': 'person',
            'value': 'John Smith',
            'confidence': 0.9,
            'source_url': 'https://example.com/about',
            'context': 'John Smith is the CEO',
            'extra_data': {'role': 'CEO'}
        }]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1
        assert result[0].entity_value == 'John Smith'


class TestExactDeduplication:
    """Test exact matching deduplication (emails, phones)."""

    def test_deduplicate_identical_emails(self):
        """Test deduplicating identical emails."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.9,
                'source_url': 'https://example.com/contact',
                'context': 'Contact us at info@company.com'
            },
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.8,
                'source_url': 'https://example.com/about',
                'context': 'Email info@company.com'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1
        # Should keep highest confidence
        assert result[0].confidence_score >= 0.9
        # Should have both source URLs
        assert len(result[0].source_urls) == 2

    def test_deduplicate_case_insensitive_emails(self):
        """Test deduplicating case-insensitive emails."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'email',
                'value': 'INFO@company.com',
                'confidence': 0.9,
                'source_url': 'https://example.com/1',
                'context': 'Context 1'
            },
            {
                'type': 'email',
                'value': 'info@COMPANY.com',
                'confidence': 0.8,
                'source_url': 'https://example.com/2',
                'context': 'Context 2'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1

    def test_deduplicate_phones(self):
        """Test deduplicating phone numbers."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'phone',
                'value': '(555) 123-4567',
                'confidence': 0.9,
                'source_url': 'https://example.com/contact',
                'context': 'Call us'
            },
            {
                'type': 'phone',
                'value': '555-123-4567',
                'confidence': 0.85,
                'source_url': 'https://example.com/about',
                'context': 'Phone number'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1


class TestPersonDeduplication:
    """Test person entity deduplication with fuzzy matching."""

    def test_deduplicate_identical_names(self):
        """Test deduplicating identical person names."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'person',
                'value': 'John Smith',
                'confidence': 0.9,
                'source_url': 'https://example.com/team',
                'context': 'John Smith is the CEO',
                'extra_data': {'role': 'CEO'}
            },
            {
                'type': 'person',
                'value': 'John Smith',
                'confidence': 0.8,
                'source_url': 'https://example.com/about',
                'context': 'Meet John Smith',
                'extra_data': {'role': 'Founder'}
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1
        # Should merge roles
        roles = result[0].extra_data.get('roles', [])
        assert 'CEO' in roles
        assert 'Founder' in roles

    def test_deduplicate_name_variations(self):
        """Test deduplicating name variations (J. Smith vs John Smith)."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'person',
                'value': 'John Smith',
                'confidence': 0.9,
                'source_url': 'https://example.com/team',
                'context': 'John Smith'
            },
            {
                'type': 'person',
                'value': 'J. Smith',
                'confidence': 0.8,
                'source_url': 'https://example.com/about',
                'context': 'J. Smith said'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        # Should merge these as the same person
        assert len(result) == 1
        # Should use longer name as canonical
        assert result[0].entity_value == 'John Smith'

    def test_different_people_not_merged(self):
        """Test that different people are not merged."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'person',
                'value': 'John Smith',
                'confidence': 0.9,
                'source_url': 'https://example.com/team',
                'context': 'John Smith'
            },
            {
                'type': 'person',
                'value': 'Jane Doe',
                'confidence': 0.8,
                'source_url': 'https://example.com/about',
                'context': 'Jane Doe'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 2


class TestOrganizationDeduplication:
    """Test organization entity deduplication."""

    def test_deduplicate_identical_orgs(self):
        """Test deduplicating identical organizations."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'org',
                'value': 'Google',
                'confidence': 0.9,
                'source_url': 'https://example.com/partners',
                'context': 'Partner Google',
                'extra_data': {'relationship': 'partner'}
            },
            {
                'type': 'org',
                'value': 'Google',
                'confidence': 0.8,
                'source_url': 'https://example.com/about',
                'context': 'Like Google',
                'extra_data': {}
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1
        # Should merge relationships
        relationships = result[0].extra_data.get('relationships', [])
        assert 'partner' in relationships

    def test_deduplicate_org_with_suffixes(self):
        """Test deduplicating orgs with different suffixes (Google vs Google Inc)."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'org',
                'value': 'Google Inc.',
                'confidence': 0.9,
                'source_url': 'https://example.com/1',
                'context': 'Google Inc.'
            },
            {
                'type': 'org',
                'value': 'Google',
                'confidence': 0.8,
                'source_url': 'https://example.com/2',
                'context': 'Google'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        # Should merge as same org
        assert len(result) == 1
        # Should use longer name as canonical
        assert result[0].entity_value == 'Google Inc.'

    def test_different_orgs_not_merged(self):
        """Test that different organizations are not merged."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'org',
                'value': 'Google',
                'confidence': 0.9,
                'source_url': 'https://example.com/1',
                'context': 'Google'
            },
            {
                'type': 'org',
                'value': 'Microsoft',
                'confidence': 0.8,
                'source_url': 'https://example.com/2',
                'context': 'Microsoft'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 2


class TestConfidenceHandling:
    """Test confidence score handling during deduplication."""

    def test_highest_confidence_retained(self):
        """Test that highest confidence is retained."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.6,
                'source_url': 'https://example.com/1',
                'context': 'Context 1'
            },
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.9,
                'source_url': 'https://example.com/2',
                'context': 'Context 2'
            },
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.7,
                'source_url': 'https://example.com/3',
                'context': 'Context 3'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1
        # Confidence should be at least 0.9 (highest) + boost from multiple mentions
        assert result[0].confidence_score >= 0.9

    def test_confidence_boosted_by_mentions(self):
        """Test that confidence is boosted by multiple mentions."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'person',
                'value': 'John Smith',
                'confidence': 0.7,
                'source_url': f'https://example.com/{i}',
                'context': 'John Smith'
            }
            for i in range(5)
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1
        # Should be boosted above base confidence
        assert result[0].confidence_score > 0.7
        assert result[0].mention_count == 5


class TestSourceUrlHandling:
    """Test source URL preservation."""

    def test_all_source_urls_preserved(self):
        """Test that all source URLs are preserved."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.9,
                'source_url': 'https://example.com/page1',
                'context': 'Context 1'
            },
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.8,
                'source_url': 'https://example.com/page2',
                'context': 'Context 2'
            },
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.7,
                'source_url': 'https://example.com/page3',
                'context': 'Context 3'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1
        assert len(result[0].source_urls) == 3
        assert 'https://example.com/page1' in result[0].source_urls
        assert 'https://example.com/page2' in result[0].source_urls
        assert 'https://example.com/page3' in result[0].source_urls

    def test_duplicate_source_urls_deduplicated(self):
        """Test that duplicate source URLs are deduplicated."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.9,
                'source_url': 'https://example.com/page1',
                'context': 'Context 1'
            },
            {
                'type': 'email',
                'value': 'info@company.com',
                'confidence': 0.8,
                'source_url': 'https://example.com/page1',  # Same URL
                'context': 'Context 2'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1
        assert len(result[0].source_urls) == 1


class TestContextHandling:
    """Test context preservation."""

    def test_contexts_preserved(self):
        """Test that contexts are preserved."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'person',
                'value': 'John Smith',
                'confidence': 0.9,
                'source_url': 'https://example.com/1',
                'context': 'CEO John Smith leads'
            },
            {
                'type': 'person',
                'value': 'John Smith',
                'confidence': 0.8,
                'source_url': 'https://example.com/2',
                'context': 'John Smith, founder'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        assert len(result) == 1
        assert len(result[0].contexts) >= 1


class TestMergedEntity:
    """Test MergedEntity dataclass."""

    def test_merged_entity_to_dict(self):
        """Test converting merged entity to dictionary."""
        from app.extractors.deduplicator import MergedEntity

        entity = MergedEntity(
            entity_type='person',
            entity_value='John Smith',
            canonical_value='john smith',
            confidence_score=0.95,
            source_urls=['https://example.com/1', 'https://example.com/2'],
            contexts=['CEO John Smith', 'John Smith, founder'],
            mention_count=2,
            extra_data={'roles': ['CEO', 'Founder']}
        )

        result = entity.to_dict()

        assert result['type'] == 'person'
        assert result['value'] == 'John Smith'
        assert result['canonical'] == 'john smith'
        assert result['confidence'] == 0.95
        assert len(result['source_urls']) == 2
        assert result['mentions'] == 2

    def test_merged_entity_limits_contexts(self):
        """Test that to_dict limits contexts to 3."""
        from app.extractors.deduplicator import MergedEntity

        entity = MergedEntity(
            entity_type='email',
            entity_value='test@test.com',
            canonical_value='test@test.com',
            confidence_score=0.9,
            source_urls=['url1'],
            contexts=['c1', 'c2', 'c3', 'c4', 'c5'],
            mention_count=5,
            extra_data={}
        )

        result = entity.to_dict()
        assert len(result['contexts']) == 3


class TestTypeSeparation:
    """Test that different entity types are handled separately."""

    def test_different_types_not_merged(self):
        """Test that different entity types are not merged."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        entities = [
            {
                'type': 'person',
                'value': 'Apple',
                'confidence': 0.9,
                'source_url': 'https://example.com/1',
                'context': 'Apple the person'
            },
            {
                'type': 'org',
                'value': 'Apple',
                'confidence': 0.8,
                'source_url': 'https://example.com/2',
                'context': 'Apple the company'
            }
        ]
        result = deduplicator.deduplicate_entities(entities)

        # Different types should not be merged
        assert len(result) == 2


class TestNormalization:
    """Test value normalization."""

    def test_normalize_email(self):
        """Test email normalization."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        normalized = deduplicator._normalize_value('INFO@COMPANY.COM', 'email')

        assert normalized == 'info@company.com'

    def test_normalize_phone(self):
        """Test phone normalization."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        normalized = deduplicator._normalize_value('(555) 123-4567', 'phone')

        assert normalized == '5551234567'

    def test_normalize_org_name(self):
        """Test organization name normalization."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        normalized = deduplicator._normalize_org_name('Google Inc.')

        assert 'google' in normalized
        assert 'inc' not in normalized


class TestNameMatching:
    """Test person name matching."""

    def test_names_match_exact(self):
        """Test exact name match."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        assert deduplicator._names_match('John Smith', 'John Smith')
        assert deduplicator._names_match('John Smith', 'john smith')

    def test_names_match_initial(self):
        """Test initial name match."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        assert deduplicator._names_match('J. Smith', 'John Smith')
        assert deduplicator._names_match('John Smith', 'J. Smith')

    def test_names_dont_match_different(self):
        """Test different names don't match."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        assert not deduplicator._names_match('John Smith', 'Jane Doe')
        assert not deduplicator._names_match('John Smith', 'John Doe')


class TestSimilarityRatio:
    """Test string similarity calculation."""

    def test_similarity_identical(self):
        """Test similarity of identical strings."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        similarity = deduplicator._similarity_ratio('hello', 'hello')

        assert similarity == 1.0

    def test_similarity_completely_different(self):
        """Test similarity of completely different strings."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        similarity = deduplicator._similarity_ratio('abc', 'xyz')

        assert similarity == 0.0

    def test_similarity_partial_match(self):
        """Test similarity of partially matching strings."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()
        similarity = deduplicator._similarity_ratio('google', 'googl')

        assert 0.8 < similarity < 1.0

    def test_similarity_empty_strings(self):
        """Test similarity with empty strings."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()

        assert deduplicator._similarity_ratio('', 'hello') == 0.0
        assert deduplicator._similarity_ratio('hello', '') == 0.0
        assert deduplicator._similarity_ratio('', '') == 0.0


class TestGlobalDeduplicator:
    """Test global deduplicator instance."""

    def test_global_deduplicator_exists(self):
        """Test that global deduplicator is available."""
        from app.extractors.deduplicator import deduplicator

        assert deduplicator is not None

    def test_global_deduplicator_type(self):
        """Test global deduplicator type."""
        from app.extractors.deduplicator import deduplicator, EntityDeduplicator

        assert isinstance(deduplicator, EntityDeduplicator)
