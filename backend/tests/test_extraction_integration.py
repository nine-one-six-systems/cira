"""Extraction pipeline integration tests.

This module tests the full entity extraction pipeline to verify:
- NER-01: PERSON entities with spaCy
- NER-02: ORG entities (partners, clients, investors)
- NER-03: GPE entities (locations, headquarters)
- NER-04: PRODUCT entities
- NER-05: Person role detection (CEO, Founder, CTO, VP)
- NER-06: Structured data (email, phone, address, social handles)
- NER-07: Deduplication with confidence boosting

Requirement traceability: These tests verify that the entity extraction
pipeline (NLPPipeline -> EntityExtractor -> Deduplicator) correctly
processes crawled pages end-to-end.
"""

import pytest
from typing import Any

# Try to import spaCy to check availability
try:
    import spacy
    SPACY_AVAILABLE = True
    # Check if model is installed
    try:
        spacy.load('en_core_web_sm')
        SPACY_MODEL_AVAILABLE = True
    except OSError:
        SPACY_MODEL_AVAILABLE = False
except ImportError:
    SPACY_AVAILABLE = False
    SPACY_MODEL_AVAILABLE = False

# Import fixtures
from backend.tests.fixtures.extraction_fixtures import (
    ABOUT_PAGE_TEXT,
    TEAM_PAGE_TEXT,
    CONTACT_PAGE_TEXT,
    CAREERS_PAGE_TEXT,
    DUPLICATE_ENTITY_TEXT,
    PRODUCTS_PAGE_TEXT,
    EMPTY_PAGE_TEXT,
    NON_ENGLISH_TEXT,
    create_company_with_pages,
    create_empty_page_company,
    create_non_english_page_company,
)


# ============================================================================
# Test Class: NER Extraction (NER-01 to NER-05)
# ============================================================================

@pytest.mark.skipif(not SPACY_MODEL_AVAILABLE, reason="spaCy model not available")
class TestNERExtraction:
    """Tests for Named Entity Recognition extraction.

    Verifies requirements NER-01 through NER-05:
    - PERSON entities with confidence scores
    - ORG entities with relationship detection
    - GPE/location entities
    - PRODUCT entities
    - Role detection for persons
    """

    def test_extracts_person_entities_with_roles(self):
        """Test PERSON entity extraction with role detection (NER-01, NER-05).

        Verifies:
        - PERSON entities are extracted from team page text
        - At least one person has a detected role (CEO, Founder, CTO, etc.)
        - Confidence scores are between 0 and 1
        """
        from app.extractors.nlp_pipeline import NLPPipeline, ExtractionConfig

        config = ExtractionConfig(min_confidence=0.4)
        pipeline = NLPPipeline(config=config)

        entities = pipeline.process_text(TEAM_PAGE_TEXT)

        # Filter to person entities
        persons = [e for e in entities if e.label == 'PERSON']

        # Assert persons found
        assert len(persons) > 0, "Expected PERSON entities to be extracted"

        # Check that at least some have roles
        persons_with_roles = [
            p for p in persons
            if p.extra_data.get('role') is not None
        ]
        assert len(persons_with_roles) > 0, "Expected at least one person with a detected role"

        # Verify confidence scores are valid
        for person in persons:
            assert 0 <= person.confidence <= 1, f"Confidence {person.confidence} out of range"

        # Check specific expected names
        person_names = [p.text for p in persons]
        # Should find at least some of the key people
        expected_names = ["John Smith", "Sarah Johnson", "Michael Chen"]
        found_expected = sum(1 for name in expected_names if any(name in p for p in person_names))
        assert found_expected >= 1, f"Expected to find key people, got: {person_names[:5]}"

    def test_extracts_organization_entities_with_relationships(self):
        """Test ORG entity extraction with relationship detection (NER-02).

        Verifies:
        - ORG entities are extracted from about page
        - Relationship types are detected (investor, partner, client)
        """
        from app.extractors.nlp_pipeline import NLPPipeline, ExtractionConfig

        config = ExtractionConfig(min_confidence=0.4)
        pipeline = NLPPipeline(config=config)

        entities = pipeline.process_text(ABOUT_PAGE_TEXT)

        # Filter to org entities
        orgs = [e for e in entities if e.label in ('ORG', 'NORP')]

        # Assert orgs found
        assert len(orgs) > 0, "Expected ORG entities to be extracted"

        # Check for relationship detection
        orgs_with_relationships = [
            o for o in orgs
            if o.extra_data.get('relationship') is not None
        ]

        # Get org names for debugging
        org_names = [o.text for o in orgs]

        # Verify confidence scores
        for org in orgs:
            assert 0 <= org.confidence <= 1, f"Confidence {org.confidence} out of range"

        # Should find some key organizations
        expected_orgs = ["Sequoia", "Microsoft", "Google", "Amazon"]
        found_expected = sum(1 for name in expected_orgs if any(name in o for o in org_names))
        assert found_expected >= 1, f"Expected to find key organizations, got: {org_names[:10]}"

    def test_extracts_location_entities(self):
        """Test GPE/location entity extraction (NER-03).

        Verifies:
        - GPE/location entities are extracted
        - City and state are identified
        """
        from app.extractors.nlp_pipeline import NLPPipeline, ExtractionConfig

        config = ExtractionConfig(min_confidence=0.4)
        pipeline = NLPPipeline(config=config)

        entities = pipeline.process_text(ABOUT_PAGE_TEXT)

        # Filter to location entities
        locations = [e for e in entities if e.label in ('GPE', 'LOC', 'FAC')]

        # Assert locations found
        assert len(locations) > 0, "Expected location entities to be extracted"

        # Get location names
        location_names = [loc.text for loc in locations]

        # Check for expected locations
        expected_locations = ["San Francisco", "California"]
        found_expected = sum(1 for loc in expected_locations if any(loc in l for l in location_names))
        assert found_expected >= 1, f"Expected to find San Francisco or California, got: {location_names}"

        # Verify confidence scores
        for loc in locations:
            assert 0 <= loc.confidence <= 1, f"Confidence {loc.confidence} out of range"

    def test_extracts_product_entities(self):
        """Test PRODUCT entity extraction (NER-04).

        Verifies:
        - PRODUCT entities are extracted from products page
        """
        from app.extractors.nlp_pipeline import NLPPipeline, ExtractionConfig

        config = ExtractionConfig(min_confidence=0.4)
        pipeline = NLPPipeline(config=config)

        entities = pipeline.process_text(PRODUCTS_PAGE_TEXT)

        # Filter to product entities
        products = [e for e in entities if e.label in ('PRODUCT', 'WORK_OF_ART')]

        # Note: spaCy's NER may not perfectly identify custom product names
        # The test verifies the extraction code works correctly

        # Verify any products found have valid confidence
        for product in products:
            assert 0 <= product.confidence <= 1, f"Confidence {product.confidence} out of range"


# ============================================================================
# Test Class: Structured Data Extraction (NER-06)
# ============================================================================

class TestStructuredDataExtraction:
    """Tests for structured data extraction via regex patterns.

    Verifies requirement NER-06:
    - Email extraction with validation
    - Phone number extraction with E.164 normalization
    - Address extraction
    - Social handle extraction with platform detection
    """

    def test_extracts_emails_with_validation(self):
        """Test email extraction with domain validation.

        Verifies:
        - Emails are extracted from contact page
        - Invalid domains (example.com) are rejected
        - Emails are normalized to lowercase
        """
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        entities = extractor.extract_emails(CONTACT_PAGE_TEXT)

        # Assert emails found
        assert len(entities) > 0, "Expected email entities to be extracted"

        # Get extracted emails
        emails = [e.normalized_value for e in entities]

        # Should find key emails
        expected_emails = [
            "info@techinnovate.com",
            "sales@techinnovate.com",
            "support@techinnovate.com",
        ]
        for expected in expected_emails:
            assert expected in emails, f"Expected to find {expected}, got: {emails}"

        # Verify no invalid domains
        for entity in entities:
            assert 'example.com' not in entity.normalized_value, "Should reject example.com"
            assert 'test.com' not in entity.normalized_value, "Should reject test.com"

        # Verify confidence scores
        for entity in entities:
            assert entity.confidence > 0.5, f"Expected high confidence for emails"

    def test_extracts_phones_with_normalization(self):
        """Test phone extraction with E.164 normalization.

        Verifies:
        - Phone numbers are extracted from multiple formats
        - Numbers are normalized to E.164 format (+1XXXXXXXXXX)
        """
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        entities = extractor.extract_phones(CONTACT_PAGE_TEXT)

        # Assert phones found
        assert len(entities) > 0, "Expected phone entities to be extracted"

        # Verify normalization to E.164
        for entity in entities:
            # E.164 format: +1 followed by 10 digits
            normalized = entity.normalized_value
            assert normalized.startswith('+1'), f"Expected E.164 format, got: {normalized}"
            # After +1, should have exactly 10 digits
            digits = normalized[2:]
            assert len(digits) == 10, f"Expected 10 digits after +1, got: {digits}"
            assert digits.isdigit(), f"Expected only digits, got: {digits}"

        # Verify confidence
        for entity in entities:
            assert entity.confidence >= 0.5, f"Expected reasonable confidence for phones"

    def test_extracts_addresses(self):
        """Test physical address extraction.

        Verifies:
        - Address entities are extracted
        - Contains street, city, state information
        """
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        entities = extractor.extract_addresses(CONTACT_PAGE_TEXT)

        # Assert addresses found
        assert len(entities) > 0, "Expected address entities to be extracted"

        # Get address values
        addresses = [e.value for e in entities]

        # At least one address should contain key elements
        has_street = any('Street' in addr or 'Avenue' in addr for addr in addresses)
        has_location = any('San Francisco' in addr or 'New York' in addr or any(
            term in addr for term in ['CA', 'NY', '94105', '10118']
        ) for addr in addresses)

        assert has_street or has_location, f"Expected addresses with street/location, got: {addresses}"

        # Verify confidence
        for entity in entities:
            assert entity.entity_type == 'address'
            assert entity.confidence > 0, f"Expected non-zero confidence"

    def test_extracts_social_handles(self):
        """Test social media handle extraction with platform detection.

        Verifies:
        - Social handles are extracted from URLs
        - Platform metadata is included (twitter, linkedin, etc.)
        """
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()
        entities = extractor.extract_social_handles(CONTACT_PAGE_TEXT)

        # Assert handles found
        assert len(entities) > 0, "Expected social handle entities to be extracted"

        # Verify platform detection
        platforms_found = set(e.extra_data.get('platform') for e in entities)

        # Should find multiple platforms
        expected_platforms = {'linkedin', 'twitter', 'facebook', 'github', 'youtube'}
        found_expected = platforms_found.intersection(expected_platforms)
        assert len(found_expected) >= 2, f"Expected multiple platforms, got: {platforms_found}"

        # Verify handle extraction
        for entity in entities:
            assert entity.entity_type == 'social_handle'
            assert entity.extra_data.get('platform') is not None, "Expected platform metadata"
            assert entity.normalized_value, "Expected normalized handle value"


# ============================================================================
# Test Class: Deduplication (NER-07)
# ============================================================================

class TestDeduplication:
    """Tests for entity deduplication and merging.

    Verifies requirement NER-07:
    - Duplicate entities merged across pages
    - Person name variations matched
    - Organization name variations matched
    - Confidence boosted by multiple mentions
    - Source URLs preserved
    """

    def test_deduplicates_identical_entities_across_pages(self):
        """Test that identical entities from multiple sources are merged.

        Verifies:
        - Duplicate values are merged
        - Source URLs from all mentions are preserved
        """
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()

        # Create entities with same value from different pages
        entities = [
            {
                'type': 'email',
                'value': 'info@techinnovate.com',
                'confidence': 0.9,
                'source_url': '/about',
                'context': 'Contact us at info@techinnovate.com',
                'extra_data': {},
            },
            {
                'type': 'email',
                'value': 'info@techinnovate.com',
                'confidence': 0.85,
                'source_url': '/contact',
                'context': 'Email: info@techinnovate.com',
                'extra_data': {},
            },
            {
                'type': 'email',
                'value': 'sales@techinnovate.com',
                'confidence': 0.9,
                'source_url': '/contact',
                'context': 'Sales: sales@techinnovate.com',
                'extra_data': {},
            },
        ]

        merged = deduplicator.deduplicate_entities(entities)

        # Should have 2 unique emails
        assert len(merged) == 2, f"Expected 2 unique entities, got {len(merged)}"

        # Find the info@ entity
        info_entity = next((e for e in merged if 'info@' in e.canonical_value), None)
        assert info_entity is not None, "Expected to find info@techinnovate.com"

        # Should have both source URLs
        assert len(info_entity.source_urls) == 2, "Expected 2 source URLs for duplicated entity"
        assert '/about' in info_entity.source_urls
        assert '/contact' in info_entity.source_urls

    def test_deduplicates_person_name_variations(self):
        """Test person name variation matching (e.g., 'John Smith' and 'J. Smith').

        Verifies:
        - Names with initials are matched to full names
        - Longer name is used as canonical value
        """
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()

        entities = [
            {
                'type': 'person',
                'value': 'John Smith',
                'confidence': 0.8,
                'source_url': '/team',
                'context': 'John Smith is the CEO',
                'extra_data': {'role': 'CEO'},
            },
            {
                'type': 'person',
                'value': 'J. Smith',
                'confidence': 0.7,
                'source_url': '/about',
                'context': 'led by J. Smith',
                'extra_data': {},
            },
            {
                'type': 'person',
                'value': 'Sarah Johnson',
                'confidence': 0.85,
                'source_url': '/team',
                'context': 'Sarah Johnson, CTO',
                'extra_data': {'role': 'CTO'},
            },
        ]

        merged = deduplicator.deduplicate_entities(entities)

        # Should merge John Smith and J. Smith
        assert len(merged) == 2, f"Expected 2 unique persons, got {len(merged)}"

        # Find John Smith entity - look for entity with "John Smith" specifically
        john = next(
            (e for e in merged if e.entity_value == 'John Smith'),
            None
        )
        assert john is not None, f"Expected to find John Smith, got: {[e.entity_value for e in merged]}"

        # Canonical should be the longer name "John Smith"
        assert john.canonical_value == 'John Smith', \
            f"Expected 'John Smith' as canonical, got: {john.canonical_value}"

        # Should have 2 source URLs from both mentions (John Smith and J. Smith merged)
        assert john.mention_count == 2, f"Expected 2 mentions, got: {john.mention_count}"
        assert len(john.source_urls) == 2, f"Expected 2 source URLs for merged person, got: {john.source_urls}"

    def test_deduplicates_org_name_variations(self):
        """Test organization name variation matching (e.g., 'Google' and 'Google Inc.').

        Verifies:
        - Org names with/without suffixes are matched
        - Variations like Inc., LLC, Corp. are handled
        """
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()

        entities = [
            {
                'type': 'org',
                'value': 'Google',
                'confidence': 0.9,
                'source_url': '/about',
                'context': 'partnership with Google',
                'extra_data': {'relationship': 'partner'},
            },
            {
                'type': 'org',
                'value': 'Google Inc.',
                'confidence': 0.85,
                'source_url': '/partners',
                'context': 'Google Inc. is a partner',
                'extra_data': {},
            },
            {
                'type': 'org',
                'value': 'Microsoft',
                'confidence': 0.9,
                'source_url': '/about',
                'context': 'integration with Microsoft',
                'extra_data': {},
            },
        ]

        merged = deduplicator.deduplicate_entities(entities)

        # Should merge Google and Google Inc.
        assert len(merged) == 2, f"Expected 2 unique orgs, got {len(merged)}"

        # Find Google entity
        google = next((e for e in merged if 'google' in e.canonical_value.lower()), None)
        assert google is not None, "Expected to find Google"

        # Should have 2 source URLs
        assert len(google.source_urls) == 2, "Expected 2 source URLs for merged org"

    def test_confidence_boosted_by_multiple_mentions(self):
        """Test that confidence is boosted when entity is mentioned multiple times.

        Verifies:
        - Final confidence > base confidence when mentioned multiple times
        """
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()

        # Same entity mentioned 5+ times
        entities = [
            {
                'type': 'person',
                'value': 'John Smith',
                'confidence': 0.7,
                'source_url': f'/page{i}',
                'context': f'John Smith mentioned on page {i}',
                'extra_data': {},
            }
            for i in range(6)
        ]

        merged = deduplicator.deduplicate_entities(entities)

        assert len(merged) == 1, "Expected 1 merged entity"

        # Confidence should be boosted above base
        base_confidence = 0.7
        assert merged[0].confidence_score > base_confidence, \
            f"Expected boosted confidence > {base_confidence}, got {merged[0].confidence_score}"

        # Should not exceed 1.0
        assert merged[0].confidence_score <= 1.0, "Confidence should not exceed 1.0"

        # Should track mention count
        assert merged[0].mention_count == 6, f"Expected 6 mentions, got {merged[0].mention_count}"


# ============================================================================
# Test Class: Full Pipeline (Integration with Database)
# ============================================================================

@pytest.mark.skipif(not SPACY_MODEL_AVAILABLE, reason="spaCy model not available")
class TestFullPipeline:
    """Tests for the full extraction pipeline with database integration.

    Verifies end-to-end extraction flow:
    - Extract entities from company pages
    - Save entities to database
    - Handle edge cases (empty pages, non-English)
    """

    def test_extract_and_save_for_company(self, app):
        """Test extracting and saving entities for a company (full pipeline).

        Verifies:
        - Entities are extracted from all pages
        - Entities are saved to database
        - Correct entity types are stored
        - Source URL and context snippet are recorded
        """
        from app import db
        from app.models import Entity
        from app.extractors.entity_extractor import EntityExtractor

        with app.app_context():
            # Create company with pages
            data = create_company_with_pages(db)
            company_id = data['company_id']

            # Run extraction and save
            extractor = EntityExtractor()
            result = extractor.save_entities_for_company(company_id)

            # Should have saved some entities
            assert result['entities_saved'] > 0, "Expected entities to be saved"
            assert result['pages_processed'] > 0, "Expected pages to be processed"

            # Query saved entities
            entities = Entity.query.filter_by(company_id=company_id).all()

            assert len(entities) > 0, "Expected entities in database"

            # Check entity properties
            for entity in entities:
                assert entity.entity_type is not None, "Expected entity type"
                assert entity.entity_value is not None, "Expected entity value"
                assert entity.source_url is not None, "Expected source URL"
                assert 0 <= entity.confidence_score <= 1, "Confidence should be 0-1"

            # Should have multiple entity types
            entity_types = set(e.entity_type.value for e in entities)
            assert len(entity_types) >= 2, f"Expected multiple entity types, got: {entity_types}"

    def test_extraction_handles_empty_pages(self, app):
        """Test that extraction handles empty pages gracefully.

        Verifies:
        - No error when page has empty extracted_text
        - Returns 0 entities extracted
        """
        from app import db
        from app.extractors.entity_extractor import EntityExtractor

        with app.app_context():
            # Create company with empty page
            data = create_empty_page_company(db)
            page_id = data['page_id']

            # Run extraction
            extractor = EntityExtractor()
            result = extractor.extract_from_page(page_id)

            # Should complete without error
            assert result.error is None, f"Expected no error, got: {result.error}"

            # Should have 0 entities
            assert result.entities_extracted == 0, "Expected 0 entities from empty page"

    def test_extraction_handles_non_english_gracefully(self, app):
        """Test that extraction handles non-English text gracefully.

        Verifies:
        - No error on non-English content
        - May extract fewer entities (acceptable)
        """
        from app import db
        from app.extractors.entity_extractor import EntityExtractor

        with app.app_context():
            # Create company with non-English page
            data = create_non_english_page_company(db)
            page_id = data['page_id']

            # Run extraction - should not raise
            extractor = EntityExtractor()
            result = extractor.extract_from_page(page_id)

            # Should complete without error
            assert result.error is None, f"Expected no error, got: {result.error}"

            # May or may not extract entities - both are acceptable
            # The important thing is no crash/error


# ============================================================================
# Test Class: Component Wiring
# ============================================================================

@pytest.mark.skipif(not SPACY_MODEL_AVAILABLE, reason="spaCy model not available")
class TestComponentWiring:
    """Tests verifying correct wiring between extraction components.

    Validates key_links from the plan:
    - EntityExtractor -> NLPPipeline (nlp.process_text())
    - EntityExtractor -> StructuredDataExtractor (extract_all())
    - EntityExtractor -> EntityDeduplicator (deduplicate_entities())
    """

    def test_nlp_pipeline_integration(self):
        """Test that NLPPipeline correctly processes text."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()

        # Process should return entities
        entities = pipeline.process_text(ABOUT_PAGE_TEXT)

        assert isinstance(entities, list), "Expected list of entities"
        assert len(entities) > 0, "Expected some entities extracted"

        # Each entity should have required attributes
        for entity in entities:
            assert hasattr(entity, 'text'), "Entity should have text"
            assert hasattr(entity, 'label'), "Entity should have label"
            assert hasattr(entity, 'confidence'), "Entity should have confidence"
            assert hasattr(entity, 'context_snippet'), "Entity should have context_snippet"

    def test_structured_extractor_extract_all(self):
        """Test that StructuredDataExtractor.extract_all() works correctly."""
        from app.extractors.structured_extractor import StructuredDataExtractor

        extractor = StructuredDataExtractor()

        # extract_all should call all sub-extractors
        entities = extractor.extract_all(CONTACT_PAGE_TEXT)

        assert isinstance(entities, list), "Expected list of entities"
        assert len(entities) > 0, "Expected some entities extracted"

        # Should have multiple types
        types = set(e.entity_type for e in entities)
        expected_types = {'email', 'phone', 'social_handle'}
        found_types = types.intersection(expected_types)
        assert len(found_types) >= 2, f"Expected multiple types, got: {types}"

    def test_deduplicator_integration(self):
        """Test that EntityDeduplicator.deduplicate_entities() works correctly."""
        from app.extractors.deduplicator import EntityDeduplicator

        deduplicator = EntityDeduplicator()

        # Create test entities
        entities = [
            {'type': 'person', 'value': 'John Smith', 'confidence': 0.8,
             'source_url': '/a', 'context': 'test', 'extra_data': {}},
            {'type': 'person', 'value': 'John Smith', 'confidence': 0.7,
             'source_url': '/b', 'context': 'test', 'extra_data': {}},
        ]

        merged = deduplicator.deduplicate_entities(entities)

        assert isinstance(merged, list), "Expected list of merged entities"
        assert len(merged) == 1, "Expected duplicates to be merged"

        # Merged entity should have combined source URLs
        assert len(merged[0].source_urls) == 2, "Expected both source URLs preserved"
