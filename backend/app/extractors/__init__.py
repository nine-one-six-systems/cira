"""Entity extraction module for NLP-based entity recognition and pattern extraction."""

from app.extractors.nlp_pipeline import NLPPipeline, nlp_pipeline
from app.extractors.entity_extractor import EntityExtractor, entity_extractor
from app.extractors.structured_extractor import StructuredDataExtractor, structured_extractor
from app.extractors.deduplicator import EntityDeduplicator, deduplicator

__all__ = [
    'NLPPipeline',
    'nlp_pipeline',
    'EntityExtractor',
    'entity_extractor',
    'StructuredDataExtractor',
    'structured_extractor',
    'EntityDeduplicator',
    'deduplicator',
]
