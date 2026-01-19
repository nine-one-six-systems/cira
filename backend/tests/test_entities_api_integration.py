"""API Integration tests for Entity endpoints.

These tests verify the GET /companies/:id/entities endpoint,
including filtering, pagination, and response format.

Requirements verified:
- API-10: GET /companies/:id/entities returns extracted entities
- NER-01-07: Entity extraction results accessible via API
"""

import pytest
from app import db
from app.models.company import Company, Entity
from app.models.enums import EntityType


class TestListEntities:
    """Tests for listing entities - API-10 requirement."""

    def test_list_entities_returns_empty_for_new_company(self, client, app):
        """
        API-10: GET /companies/:id/entities returns empty list for company with no entities.
        Response must have: data=[], meta.total=0
        """
        with app.app_context():
            company = Company(
                company_name='Empty Entity Corp',
                website_url='https://empty-entity.com'
            )
            db.session.add(company)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['data'] == []
        assert data['meta']['total'] == 0

    def test_list_entities_returns_entities(self, client, app):
        """
        API-10: GET /companies/:id/entities returns all entities for a company.
        Each entity must have: id, entityType, entityValue, confidenceScore, sourceUrl
        """
        with app.app_context():
            company = Company(
                company_name='Entity Corp',
                website_url='https://entity-corp.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 5 entities of mixed types
            entity_data = [
                (EntityType.PERSON, 'John Smith', 0.9),
                (EntityType.ORGANIZATION, 'Acme Inc', 0.85),
                (EntityType.EMAIL, 'contact@example.com', 0.95),
                (EntityType.PHONE, '555-123-4567', 0.8),
                (EntityType.LOCATION, 'San Francisco, CA', 0.75),
            ]
            for etype, evalue, confidence in entity_data:
                entity = Entity(
                    company_id=company.id,
                    entity_type=etype,
                    entity_value=evalue,
                    confidence_score=confidence,
                    source_url='https://entity-corp.com/about'
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities')

        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 5

        # Verify each entity has required fields
        for entity in data['data']:
            assert 'id' in entity
            assert 'entityType' in entity
            assert 'entityValue' in entity
            assert 'confidenceScore' in entity
            assert 'sourceUrl' in entity

    def test_list_entities_orders_by_confidence_descending(self, client, app):
        """
        API-10: Entities are ordered by confidence score descending.
        Entities with scores 0.5, 0.9, 0.7 should return in order 0.9, 0.7, 0.5
        """
        with app.app_context():
            company = Company(
                company_name='Sorted Corp',
                website_url='https://sorted-corp.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add entities with specific confidence scores
            for confidence in [0.5, 0.9, 0.7]:
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person with {confidence} confidence',
                    confidence_score=confidence
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities')

        assert response.status_code == 200
        data = response.get_json()
        entities = data['data']

        assert len(entities) == 3
        assert entities[0]['confidenceScore'] == 0.9
        assert entities[1]['confidenceScore'] == 0.7
        assert entities[2]['confidenceScore'] == 0.5

    def test_list_entities_filters_by_type(self, client, app):
        """
        API-10: Type filter returns only entities of specified type.
        """
        with app.app_context():
            company = Company(
                company_name='Type Filter Corp',
                website_url='https://type-filter.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add entities: 2 person, 2 org, 2 email
            for i in range(2):
                db.session.add(Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}',
                    confidence_score=0.8
                ))
                db.session.add(Entity(
                    company_id=company.id,
                    entity_type=EntityType.ORGANIZATION,
                    entity_value=f'Org {i}',
                    confidence_score=0.8
                ))
                db.session.add(Entity(
                    company_id=company.id,
                    entity_type=EntityType.EMAIL,
                    entity_value=f'email{i}@example.com',
                    confidence_score=0.8
                ))

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities?type=person')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 2
        for entity in data['data']:
            assert entity['entityType'] == 'person'

    def test_list_entities_filters_by_min_confidence(self, client, app):
        """
        API-10: minConfidence filter excludes low-confidence entities.
        Entities with confidence 0.3, 0.5, 0.7, 0.9 filtered by minConfidence=0.6
        should return only 0.7 and 0.9
        """
        with app.app_context():
            company = Company(
                company_name='Confidence Filter Corp',
                website_url='https://confidence-filter.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add entities with various confidence scores
            for confidence in [0.3, 0.5, 0.7, 0.9]:
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person with {confidence}',
                    confidence_score=confidence
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities?minConfidence=0.6')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 2

        # Verify only high-confidence entities returned (ordered desc)
        assert data['data'][0]['confidenceScore'] == 0.9
        assert data['data'][1]['confidenceScore'] == 0.7

    def test_list_entities_combined_filters(self, client, app):
        """
        API-10: Multiple filters can be combined.
        Filter by type=person AND minConfidence=0.5 should return
        only high-confidence person entities.
        """
        with app.app_context():
            company = Company(
                company_name='Combined Filter Corp',
                website_url='https://combined-filter.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add mixed entities with various types and confidences
            # Persons: 0.3, 0.6, 0.8
            for conf in [0.3, 0.6, 0.8]:
                db.session.add(Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {conf}',
                    confidence_score=conf
                ))
            # Orgs: 0.4, 0.7, 0.9
            for conf in [0.4, 0.7, 0.9]:
                db.session.add(Entity(
                    company_id=company.id,
                    entity_type=EntityType.ORGANIZATION,
                    entity_value=f'Org {conf}',
                    confidence_score=conf
                ))

            db.session.commit()
            company_id = company.id

        response = client.get(
            f'/api/v1/companies/{company_id}/entities?type=person&minConfidence=0.5'
        )

        assert response.status_code == 200
        data = response.get_json()

        # Should only return persons with confidence >= 0.5 (0.6 and 0.8)
        assert len(data['data']) == 2
        for entity in data['data']:
            assert entity['entityType'] == 'person'
            assert entity['confidenceScore'] >= 0.5


class TestEntitiesPagination:
    """Tests for entity pagination."""

    def test_list_entities_default_pagination(self, client, app):
        """
        API-10: Default pagination returns up to 50 entities.
        With 60 entities: len(data)=50, meta.total=60, meta.page=1, meta.totalPages=2
        """
        with app.app_context():
            company = Company(
                company_name='Paginated Corp',
                website_url='https://paginated-corp.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 60 entities
            for i in range(60):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i:02d}',
                    confidence_score=0.5 + (i * 0.005)  # Varied confidence
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 50
        assert data['meta']['total'] == 60
        assert data['meta']['page'] == 1
        assert data['meta']['totalPages'] == 2

    def test_list_entities_custom_page_size(self, client, app):
        """
        API-10: Custom pageSize parameter is respected.
        With 30 entities and pageSize=10: len(data)=10, meta.totalPages=3
        """
        with app.app_context():
            company = Company(
                company_name='Custom Page Corp',
                website_url='https://custom-page.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 30 entities
            for i in range(30):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i:02d}',
                    confidence_score=0.8
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities?pageSize=10')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 10
        assert data['meta']['pageSize'] == 10
        assert data['meta']['totalPages'] == 3

    def test_list_entities_page_navigation(self, client, app):
        """
        API-10: Page navigation returns correct data slices.
        With 25 entities and pageSize=10:
        - Page 1: 10 entities
        - Page 2: 10 entities
        - Page 3: 5 entities
        """
        with app.app_context():
            company = Company(
                company_name='Navigation Corp',
                website_url='https://navigation-corp.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 25 entities with descending confidence for predictable order
            for i in range(25):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i:02d}',
                    confidence_score=1.0 - (i * 0.01)
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        # Page 1
        response = client.get(f'/api/v1/companies/{company_id}/entities?page=1&pageSize=10')
        data = response.get_json()
        assert len(data['data']) == 10
        assert data['meta']['page'] == 1

        # Page 2
        response = client.get(f'/api/v1/companies/{company_id}/entities?page=2&pageSize=10')
        data = response.get_json()
        assert len(data['data']) == 10
        assert data['meta']['page'] == 2

        # Page 3
        response = client.get(f'/api/v1/companies/{company_id}/entities?page=3&pageSize=10')
        data = response.get_json()
        assert len(data['data']) == 5
        assert data['meta']['page'] == 3

    def test_list_entities_page_size_capped_at_100(self, client, app):
        """
        API-10: Page size is capped at 100.
        Request pageSize=200 should return max 100 entities.
        """
        with app.app_context():
            company = Company(
                company_name='Capped Corp',
                website_url='https://capped-corp.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add 150 entities
            for i in range(150):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i:03d}',
                    confidence_score=0.8
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities?pageSize=200')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) <= 100
        assert data['meta']['pageSize'] <= 100


class TestEntitiesErrorHandling:
    """Tests for entity endpoint error handling."""

    def test_list_entities_company_not_found(self, client):
        """
        API-10: Non-existent company returns 404 with NOT_FOUND code.
        """
        response = client.get('/api/v1/companies/00000000-0000-0000-0000-000000000000/entities')

        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert data['error']['code'] == 'NOT_FOUND'

    def test_list_entities_invalid_type_ignored(self, client, app):
        """
        API-10: Invalid entity type filter is silently ignored.
        With invalid type, returns all entities.
        """
        with app.app_context():
            company = Company(
                company_name='Invalid Type Corp',
                website_url='https://invalid-type.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add entities
            for i in range(5):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}',
                    confidence_score=0.8
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities?type=invalid_type')

        assert response.status_code == 200
        data = response.get_json()
        # Invalid type should be ignored, returning all entities
        assert len(data['data']) == 5

    def test_list_entities_invalid_page_number_clamped(self, client, app):
        """
        API-10: Invalid page numbers are clamped to valid range.
        page=0 or page=-1 should be clamped to page=1
        """
        with app.app_context():
            company = Company(
                company_name='Clamped Page Corp',
                website_url='https://clamped-page.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add some entities
            for i in range(5):
                entity = Entity(
                    company_id=company.id,
                    entity_type=EntityType.PERSON,
                    entity_value=f'Person {i}',
                    confidence_score=0.8
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        # Test page=0
        response = client.get(f'/api/v1/companies/{company_id}/entities?page=0')
        assert response.status_code == 200
        data = response.get_json()
        assert data['meta']['page'] == 1

        # Test page=-1
        response = client.get(f'/api/v1/companies/{company_id}/entities?page=-1')
        assert response.status_code == 200
        data = response.get_json()
        assert data['meta']['page'] == 1


class TestEntityResponseFormat:
    """Tests for entity response format validation."""

    def test_entity_response_includes_context_snippet(self, client, app):
        """
        API-10: Entity response includes contextSnippet field.
        """
        with app.app_context():
            company = Company(
                company_name='Context Corp',
                website_url='https://context-corp.com'
            )
            db.session.add(company)
            db.session.flush()

            entity = Entity(
                company_id=company.id,
                entity_type=EntityType.PERSON,
                entity_value='John Smith',
                context_snippet='John Smith is the CEO of Context Corp',
                confidence_score=0.9
            )
            db.session.add(entity)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert 'contextSnippet' in data['data'][0]
        assert data['data'][0]['contextSnippet'] == 'John Smith is the CEO of Context Corp'

    def test_entity_response_includes_source_url(self, client, app):
        """
        API-10: Entity response includes sourceUrl field.
        """
        with app.app_context():
            company = Company(
                company_name='Source Corp',
                website_url='https://source-corp.com'
            )
            db.session.add(company)
            db.session.flush()

            entity = Entity(
                company_id=company.id,
                entity_type=EntityType.PERSON,
                entity_value='Jane Doe',
                source_url='https://source-corp.com/team',
                confidence_score=0.85
            )
            db.session.add(entity)
            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == 1
        assert 'sourceUrl' in data['data'][0]
        assert data['data'][0]['sourceUrl'] == 'https://source-corp.com/team'

    def test_entity_types_serialized_correctly(self, client, app):
        """
        API-10: Entity types are serialized as lowercase strings.
        """
        with app.app_context():
            company = Company(
                company_name='All Types Corp',
                website_url='https://all-types.com'
            )
            db.session.add(company)
            db.session.flush()

            # Add entities with various types
            entity_types = [
                EntityType.PERSON,
                EntityType.ORGANIZATION,
                EntityType.LOCATION,
                EntityType.EMAIL,
                EntityType.PHONE,
                EntityType.DATE,
                EntityType.MONEY,
                EntityType.ADDRESS,
                EntityType.SOCIAL_HANDLE,
                EntityType.TECH_STACK,
                EntityType.PRODUCT,
            ]
            for etype in entity_types:
                entity = Entity(
                    company_id=company.id,
                    entity_type=etype,
                    entity_value=f'Test {etype.value}',
                    confidence_score=0.8
                )
                db.session.add(entity)

            db.session.commit()
            company_id = company.id

        response = client.get(f'/api/v1/companies/{company_id}/entities')

        assert response.status_code == 200
        data = response.get_json()
        assert len(data['data']) == len(entity_types)

        # Verify all entity types are lowercase strings
        entity_type_values = {e['entityType'] for e in data['data']}
        expected_values = {
            'person', 'org', 'location', 'email', 'phone',
            'date', 'money', 'address', 'social_handle', 'tech_stack', 'product'
        }
        assert entity_type_values == expected_values

        # Verify all values are lowercase strings
        for entity in data['data']:
            assert isinstance(entity['entityType'], str)
            assert entity['entityType'].islower() or '_' in entity['entityType']
