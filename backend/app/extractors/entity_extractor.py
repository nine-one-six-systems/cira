"""Named Entity Extraction Worker.

Task 5.2: Named Entity Extraction Worker
- Extract: company names, locations, people with roles, products, organizations, dates, money
- Store with confidence scores and context snippets
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING

from app.extractors.nlp_pipeline import NLPPipeline, ExtractedEntity, ExtractionConfig, nlp_pipeline

if TYPE_CHECKING:
    from app.models import Company, Page, Entity
    from app.models.enums import EntityType

logger = logging.getLogger(__name__)


@dataclass
class ExtractionResult:
    """Result of entity extraction for a page."""
    page_id: str
    url: str
    entities_extracted: int
    entities: list[dict[str, Any]] = field(default_factory=list)
    processing_time_ms: float = 0.0
    error: str | None = None


@dataclass
class BatchExtractionResult:
    """Result of entity extraction for a company."""
    company_id: str
    pages_processed: int
    total_entities: int
    entities_by_type: dict[str, int] = field(default_factory=dict)
    page_results: list[ExtractionResult] = field(default_factory=list)
    processing_time_ms: float = 0.0


class EntityExtractor:
    """
    Named Entity Extraction Worker.

    This class extracts entities from crawled pages using spaCy NLP:
    - Company name variations (FR-NER-001)
    - Locations - headquarters, offices (FR-NER-002)
    - People names with roles (FR-NER-003)
    - Product and service names (FR-NER-004)
    - Organization mentions - partners, clients, investors (FR-NER-005)
    - Dates - founded, milestones (FR-NER-006)
    - Monetary values - revenue, funding (FR-NER-007)

    Entities are stored with:
    - Confidence scores based on spaCy's scoring
    - Context snippets (50 chars before/after)
    - Source URL for traceability
    """

    # Map spaCy labels to our EntityType enum values
    SPACY_TO_ENTITY_TYPE = {
        'PERSON': 'person',
        'ORG': 'org',
        'NORP': 'org',
        'GPE': 'location',
        'LOC': 'location',
        'FAC': 'location',
        'PRODUCT': 'product',
        'WORK_OF_ART': 'product',
        'DATE': 'date',
        'TIME': 'date',
        'EVENT': 'date',
        'MONEY': 'money',
        'PERCENT': 'money',
    }

    def __init__(
        self,
        nlp: NLPPipeline | None = None,
        config: ExtractionConfig | None = None
    ):
        """
        Initialize the entity extractor.

        Args:
            nlp: Optional NLP pipeline instance
            config: Optional extraction configuration
        """
        self.nlp = nlp or nlp_pipeline
        self.config = config or ExtractionConfig()

    def _get_db(self):
        """Get db instance lazily to avoid circular import."""
        from app import db
        return db

    def _get_models(self):
        """Get model classes lazily to avoid circular import."""
        from app.models import Company, Page, Entity
        return Company, Page, Entity

    def _get_entity_type_enum(self):
        """Get EntityType enum lazily."""
        from app.models.enums import EntityType
        return EntityType

    def extract_from_page(
        self,
        page_id: str,
        text: str | None = None
    ) -> ExtractionResult:
        """
        Extract entities from a single page.

        Args:
            page_id: UUID of the page
            text: Optional text content (if not provided, loads from DB)

        Returns:
            ExtractionResult with extracted entities
        """
        start_time = datetime.utcnow()
        db = self._get_db()
        _, Page, _ = self._get_models()

        page = db.session.get(Page, page_id)
        if not page:
            return ExtractionResult(
                page_id=page_id,
                url='',
                entities_extracted=0,
                error=f"Page {page_id} not found"
            )

        # Get text content
        content = text or page.extracted_text or ''
        if not content.strip():
            return ExtractionResult(
                page_id=page_id,
                url=page.url,
                entities_extracted=0
            )

        # Extract entities using NLP pipeline
        extracted = self.nlp.process_text(content)

        # Convert to entity dicts
        entities = []
        for ent in extracted:
            entity_type = self.SPACY_TO_ENTITY_TYPE.get(ent.label)
            if entity_type:
                entities.append({
                    'text': ent.text,
                    'type': entity_type,
                    'confidence': ent.confidence,
                    'context': ent.context_snippet,
                    'extra_data': ent.extra_data,
                    'source_url': page.url,
                })

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return ExtractionResult(
            page_id=page_id,
            url=page.url,
            entities_extracted=len(entities),
            entities=entities,
            processing_time_ms=processing_time
        )

    def extract_for_company(
        self,
        company_id: str,
        progress_callback: callable | None = None
    ) -> BatchExtractionResult:
        """
        Extract entities from all pages of a company.

        Args:
            company_id: UUID of the company
            progress_callback: Optional callback for progress updates

        Returns:
            BatchExtractionResult with all extracted entities
        """
        start_time = datetime.utcnow()
        db = self._get_db()
        Company, Page, Entity = self._get_models()
        EntityType = self._get_entity_type_enum()

        company = db.session.get(Company, company_id)
        if not company:
            return BatchExtractionResult(
                company_id=company_id,
                pages_processed=0,
                total_entities=0
            )

        # Get all pages with content
        pages = Page.query.filter_by(company_id=company_id).filter(
            Page.extracted_text.isnot(None),
            Page.extracted_text != ''
        ).all()

        if not pages:
            return BatchExtractionResult(
                company_id=company_id,
                pages_processed=0,
                total_entities=0
            )

        # Extract from all pages
        page_results = []
        all_entities = []
        entities_by_type: dict[str, int] = {}

        for i, page in enumerate(pages):
            result = self.extract_from_page(page.id, page.extracted_text)
            page_results.append(result)

            # Collect entities
            for entity_dict in result.entities:
                all_entities.append({
                    **entity_dict,
                    'page_id': page.id,
                })
                entity_type = entity_dict['type']
                entities_by_type[entity_type] = entities_by_type.get(entity_type, 0) + 1

            # Progress callback
            if progress_callback:
                progress_callback({
                    'pages_processed': i + 1,
                    'total_pages': len(pages),
                    'entities_extracted': len(all_entities),
                })

        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return BatchExtractionResult(
            company_id=company_id,
            pages_processed=len(pages),
            total_entities=len(all_entities),
            entities_by_type=entities_by_type,
            page_results=page_results,
            processing_time_ms=processing_time
        )

    def save_entities_for_company(
        self,
        company_id: str,
        progress_callback: callable | None = None
    ) -> dict[str, Any]:
        """
        Extract and save entities for a company to the database.

        Args:
            company_id: UUID of the company
            progress_callback: Optional callback for progress updates

        Returns:
            Dictionary with extraction summary
        """
        db = self._get_db()
        Company, Page, Entity = self._get_models()
        EntityType = self._get_entity_type_enum()

        # First extract all entities
        result = self.extract_for_company(company_id, progress_callback)

        if result.total_entities == 0:
            return {
                'company_id': company_id,
                'entities_saved': 0,
                'pages_processed': result.pages_processed,
                'message': 'No entities extracted'
            }

        # Collect all entities from all pages
        entities_to_save = []
        for page_result in result.page_results:
            for entity_dict in page_result.entities:
                entities_to_save.append({
                    'company_id': company_id,
                    'entity_type': entity_dict['type'],
                    'entity_value': entity_dict['text'],
                    'context_snippet': entity_dict.get('context'),
                    'source_url': entity_dict.get('source_url'),
                    'confidence_score': entity_dict.get('confidence', 0.0),
                    'extra_data': entity_dict.get('extra_data'),
                })

        # Save to database
        saved_count = 0
        for entity_data in entities_to_save:
            try:
                # Map string type to enum
                entity_type_str = entity_data['entity_type']
                entity_type = EntityType(entity_type_str)

                entity = Entity(
                    company_id=entity_data['company_id'],
                    entity_type=entity_type,
                    entity_value=entity_data['entity_value'],
                    context_snippet=entity_data.get('context_snippet'),
                    source_url=entity_data.get('source_url'),
                    confidence_score=entity_data.get('confidence_score', 0.0),
                    extra_data=entity_data.get('extra_data'),
                )
                db.session.add(entity)
                saved_count += 1
            except Exception as e:
                logger.warning(f"Failed to save entity: {e}")

        db.session.commit()

        return {
            'company_id': company_id,
            'entities_saved': saved_count,
            'pages_processed': result.pages_processed,
            'entities_by_type': result.entities_by_type,
            'processing_time_ms': result.processing_time_ms,
        }

    def get_extraction_stats(self, company_id: str) -> dict[str, Any]:
        """
        Get extraction statistics for a company.

        Args:
            company_id: UUID of the company

        Returns:
            Dictionary with extraction statistics
        """
        db = self._get_db()
        Company, Page, Entity = self._get_models()

        company = db.session.get(Company, company_id)
        if not company:
            return {'error': f'Company {company_id} not found'}

        # Count entities by type
        from sqlalchemy import func
        type_counts = db.session.query(
            Entity.entity_type,
            func.count(Entity.id)
        ).filter_by(company_id=company_id).group_by(Entity.entity_type).all()

        entities_by_type = {str(t.value): c for t, c in type_counts}

        # Get average confidence
        avg_confidence = db.session.query(
            func.avg(Entity.confidence_score)
        ).filter_by(company_id=company_id).scalar() or 0.0

        # Count pages with entities
        pages_with_entities = db.session.query(
            func.count(func.distinct(Entity.source_url))
        ).filter_by(company_id=company_id).scalar() or 0

        return {
            'company_id': company_id,
            'total_entities': sum(entities_by_type.values()),
            'entities_by_type': entities_by_type,
            'average_confidence': round(avg_confidence, 3),
            'pages_with_entities': pages_with_entities,
        }


# Global extractor instance
entity_extractor = EntityExtractor()
