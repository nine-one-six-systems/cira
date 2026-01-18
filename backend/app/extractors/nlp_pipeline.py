"""spaCy NLP Pipeline for entity extraction.

This module provides the core NLP functionality using spaCy with the
en_core_web_lg model for Named Entity Recognition (NER).

Task 5.1: spaCy NLP Pipeline Setup
- spaCy with en_core_web_lg installed
- Custom pipeline for domain entities
- Optimized for batch processing
- Configurable confidence thresholds
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Generator

logger = logging.getLogger(__name__)

# Try to import spacy, but allow graceful degradation
try:
    import spacy
    from spacy.language import Language
    from spacy.tokens import Doc, Span
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    spacy = None
    Language = None
    Doc = None
    Span = None


@dataclass
class ExtractedEntity:
    """Represents an entity extracted by the NLP pipeline."""
    text: str
    label: str  # PERSON, ORG, GPE, DATE, MONEY, etc.
    start_char: int
    end_char: int
    confidence: float
    context_snippet: str
    extra_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'text': self.text,
            'label': self.label,
            'start_char': self.start_char,
            'end_char': self.end_char,
            'confidence': self.confidence,
            'context_snippet': self.context_snippet,
            'extra_data': self.extra_data,
        }


@dataclass
class ExtractionConfig:
    """Configuration for entity extraction."""
    min_confidence: float = 0.5
    max_context_length: int = 100
    enable_tech_stack: bool = False
    batch_size: int = 1000  # Tokens per batch


class NLPPipeline:
    """
    spaCy NLP Pipeline for Named Entity Recognition.

    This class provides:
    - Loading and managing the spaCy model (en_core_web_lg)
    - Extracting named entities (PERSON, ORG, GPE, DATE, MONEY, etc.)
    - Context snippet extraction
    - Batch processing optimization
    - Confidence scoring based on spaCy's scores

    Performance targets:
    - Process 1000+ tokens/second
    - Batch processing more efficient than single-document
    - Memory stable for large documents
    """

    # spaCy label to our EntityType mapping
    LABEL_MAPPING = {
        'PERSON': 'person',
        'ORG': 'org',
        'GPE': 'location',       # Geopolitical entities
        'LOC': 'location',       # Non-GPE locations
        'PRODUCT': 'product',
        'DATE': 'date',
        'TIME': 'date',          # Map TIME to date as well
        'MONEY': 'money',
        'PERCENT': 'money',      # Often related to funding/growth
        'NORP': 'org',           # Nationalities, religious, political groups
        'FAC': 'location',       # Buildings, airports, highways
        'EVENT': 'date',         # Named events
        'WORK_OF_ART': 'product',
        'LAW': 'org',            # Legal documents
        'LANGUAGE': 'other',     # Languages
        'QUANTITY': 'other',     # Measurements
        'ORDINAL': 'other',      # "first", "second"
        'CARDINAL': 'other',     # Numerals
    }

    # Role patterns for detecting person roles
    ROLE_PATTERNS = [
        # C-Suite
        (r'\b(CEO|Chief Executive Officer)\b', 'CEO'),
        (r'\b(CTO|Chief Technology Officer)\b', 'CTO'),
        (r'\b(CFO|Chief Financial Officer)\b', 'CFO'),
        (r'\b(COO|Chief Operating Officer)\b', 'COO'),
        (r'\b(CMO|Chief Marketing Officer)\b', 'CMO'),
        (r'\b(CIO|Chief Information Officer)\b', 'CIO'),
        (r'\b(CISO|Chief Information Security Officer)\b', 'CISO'),
        (r'\b(CPO|Chief Product Officer)\b', 'CPO'),
        (r'\b(CRO|Chief Revenue Officer)\b', 'CRO'),
        (r'\b(CLO|Chief Legal Officer)\b', 'CLO'),
        # Leadership
        (r'\b(Founder|Co-Founder|Co-founder|Cofounder)\b', 'Founder'),
        (r'\b(President)\b', 'President'),
        (r'\b(Chairman|Chair)\b', 'Chairman'),
        # VP/Director level
        (r'\b(VP|Vice President)\s+(of\s+)?(\w+)', 'VP'),
        (r'\b(Director)\s+(of\s+)?(\w+)', 'Director'),
        (r'\b(Senior Vice President|SVP)\b', 'SVP'),
        (r'\b(Executive Vice President|EVP)\b', 'EVP'),
        # Manager level
        (r'\b(Head)\s+(of\s+)?(\w+)', 'Head'),
        (r'\b(Manager)\s+(of\s+)?(\w+)', 'Manager'),
        (r'\b(Lead)\s+(\w+)', 'Lead'),
        # Individual contributor
        (r'\b(Engineer|Developer|Architect)\b', 'Engineer'),
        (r'\b(Designer)\b', 'Designer'),
        (r'\b(Analyst)\b', 'Analyst'),
    ]

    def __init__(self, config: ExtractionConfig | None = None):
        """
        Initialize the NLP pipeline.

        Args:
            config: Optional extraction configuration
        """
        self.config = config or ExtractionConfig()
        self._nlp = None
        self._is_initialized = False
        self._role_patterns = [
            (re.compile(pattern, re.IGNORECASE), role)
            for pattern, role in self.ROLE_PATTERNS
        ]

    @property
    def nlp(self):
        """Lazy load the spaCy model."""
        if self._nlp is None:
            self._load_model()
        return self._nlp

    @property
    def is_available(self) -> bool:
        """Check if spaCy is available."""
        return SPACY_AVAILABLE

    @property
    def is_initialized(self) -> bool:
        """Check if the model is loaded."""
        return self._is_initialized

    def _load_model(self) -> None:
        """Load the spaCy model."""
        if not SPACY_AVAILABLE:
            logger.warning("spaCy is not installed. NLP features will be limited.")
            return

        try:
            # Try to load the large model first
            self._nlp = spacy.load('en_core_web_lg')
            logger.info("Loaded spaCy model: en_core_web_lg")
        except OSError:
            try:
                # Fall back to smaller models
                self._nlp = spacy.load('en_core_web_md')
                logger.warning("en_core_web_lg not found, using en_core_web_md")
            except OSError:
                try:
                    self._nlp = spacy.load('en_core_web_sm')
                    logger.warning("en_core_web_md not found, using en_core_web_sm")
                except OSError:
                    logger.error("No spaCy English model found. Please install one with: "
                               "python -m spacy download en_core_web_lg")
                    return

        # Optimize pipeline - disable components we don't need
        # Keep: ner, tagger (for role detection)
        # Could disable: parser (dependency parsing) if not needed for role context

        self._is_initialized = True
        logger.info(f"NLP pipeline initialized with config: min_confidence={self.config.min_confidence}")

    def process_text(self, text: str) -> list[ExtractedEntity]:
        """
        Process a single text document and extract entities.

        Args:
            text: The text to process

        Returns:
            List of extracted entities
        """
        if not self.is_available or not text:
            return []

        doc = self.nlp(text)
        return self._extract_entities_from_doc(doc, text)

    def process_batch(self, texts: list[str]) -> list[list[ExtractedEntity]]:
        """
        Process a batch of texts efficiently.

        Args:
            texts: List of texts to process

        Returns:
            List of entity lists, one per input text
        """
        if not self.is_available or not texts:
            return [[] for _ in texts]

        results = []
        # Use spaCy's pipe for efficient batch processing
        for doc, text in zip(self.nlp.pipe(texts, batch_size=50), texts):
            entities = self._extract_entities_from_doc(doc, text)
            results.append(entities)

        return results

    def process_stream(
        self,
        texts: Generator[str, None, None],
        batch_size: int = 50
    ) -> Generator[list[ExtractedEntity], None, None]:
        """
        Process a stream of texts efficiently.

        Args:
            texts: Generator of texts to process
            batch_size: Number of documents to process at once

        Yields:
            List of entities for each input text
        """
        if not self.is_available:
            for _ in texts:
                yield []
            return

        # Collect texts into batches
        batch = []
        for text in texts:
            batch.append(text)
            if len(batch) >= batch_size:
                for entities in self.process_batch(batch):
                    yield entities
                batch = []

        # Process remaining
        if batch:
            for entities in self.process_batch(batch):
                yield entities

    def _extract_entities_from_doc(self, doc: "Doc", original_text: str) -> list[ExtractedEntity]:
        """
        Extract entities from a processed spaCy Doc.

        Args:
            doc: Processed spaCy document
            original_text: Original text for context extraction

        Returns:
            List of extracted entities
        """
        entities = []

        for ent in doc.ents:
            # Map spaCy label to our types
            entity_type = self.LABEL_MAPPING.get(ent.label_, 'other')

            # Skip 'other' types unless explicitly included
            if entity_type == 'other':
                continue

            # Calculate confidence based on entity length and context
            confidence = self._calculate_confidence(ent, doc)

            # Skip low confidence entities
            if confidence < self.config.min_confidence:
                continue

            # Extract context snippet
            context = self._extract_context(
                original_text,
                ent.start_char,
                ent.end_char,
                self.config.max_context_length
            )

            # Build extra data
            extra_data = {}

            # For PERSON entities, try to detect role
            if ent.label_ == 'PERSON':
                role = self._detect_role(context)
                if role:
                    extra_data['role'] = role

            # For ORG entities, try to detect relationship
            if ent.label_ in ('ORG', 'NORP'):
                relationship = self._detect_org_relationship(context)
                if relationship:
                    extra_data['relationship'] = relationship

            entity = ExtractedEntity(
                text=ent.text,
                label=ent.label_,
                start_char=ent.start_char,
                end_char=ent.end_char,
                confidence=confidence,
                context_snippet=context,
                extra_data=extra_data,
            )
            entities.append(entity)

        return entities

    def _calculate_confidence(self, ent: "Span", doc: "Doc") -> float:
        """
        Calculate confidence score for an entity.

        This uses heuristics based on:
        - Entity length (too short entities are less reliable)
        - Capitalization (proper nouns have higher confidence)
        - Context (entities in complete sentences are more reliable)

        Args:
            ent: The spaCy entity span
            doc: The full document

        Returns:
            Confidence score between 0 and 1
        """
        base_confidence = 0.7  # spaCy's NER is generally reliable

        # Penalty for very short entities (< 2 characters)
        if len(ent.text.strip()) < 2:
            base_confidence -= 0.3

        # Bonus for proper capitalization (first letter uppercase)
        if ent.text and ent.text[0].isupper():
            base_confidence += 0.1

        # Bonus for multi-word entities (generally more specific)
        word_count = len(ent.text.split())
        if word_count > 1:
            base_confidence += 0.05 * min(word_count - 1, 3)

        # Penalty for all-uppercase (might be acronym or header)
        if ent.text.isupper() and len(ent.text) > 3:
            base_confidence -= 0.1

        # Clamp to [0, 1]
        return max(0.0, min(1.0, base_confidence))

    def _extract_context(
        self,
        text: str,
        start: int,
        end: int,
        max_length: int
    ) -> str:
        """
        Extract context around an entity.

        Args:
            text: Full text
            start: Entity start position
            end: Entity end position
            max_length: Maximum context length

        Returns:
            Context string with entity highlighted
        """
        # Calculate context boundaries
        context_start = max(0, start - max_length // 2)
        context_end = min(len(text), end + max_length // 2)

        # Adjust to word boundaries
        if context_start > 0:
            # Find the start of the word
            while context_start > 0 and text[context_start - 1] not in ' \n\t':
                context_start -= 1

        if context_end < len(text):
            # Find the end of the word
            while context_end < len(text) and text[context_end] not in ' \n\t':
                context_end += 1

        # Extract context
        context = text[context_start:context_end]

        # Add ellipsis if truncated
        if context_start > 0:
            context = '...' + context
        if context_end < len(text):
            context = context + '...'

        return context.strip()

    def _detect_role(self, context: str) -> str | None:
        """
        Detect a person's role from surrounding context.

        Args:
            context: Text context around the person's name

        Returns:
            Detected role or None
        """
        for pattern, role in self._role_patterns:
            if pattern.search(context):
                return role
        return None

    def _detect_org_relationship(self, context: str) -> str | None:
        """
        Detect an organization's relationship from context.

        Args:
            context: Text context around the organization

        Returns:
            Relationship type (partner, client, investor, competitor) or None
        """
        context_lower = context.lower()

        # Check for relationship indicators
        if any(word in context_lower for word in ['partner', 'partnership', 'partnered']):
            return 'partner'
        if any(word in context_lower for word in ['client', 'customer', 'serve', 'serving']):
            return 'client'
        if any(word in context_lower for word in ['investor', 'invested', 'funding', 'backed by', 'funded by']):
            return 'investor'
        if any(word in context_lower for word in ['competitor', 'competing', 'versus', 'vs.']):
            return 'competitor'
        if any(word in context_lower for word in ['acquired', 'acquisition', 'merger']):
            return 'acquisition'

        return None

    def get_model_info(self) -> dict[str, Any]:
        """
        Get information about the loaded model.

        Returns:
            Dictionary with model metadata
        """
        if not self.is_available:
            return {
                'available': False,
                'error': 'spaCy not installed'
            }

        if not self._is_initialized:
            self._load_model()

        if self._nlp is None:
            return {
                'available': True,
                'initialized': False,
                'error': 'Model not loaded'
            }

        return {
            'available': True,
            'initialized': True,
            'model_name': self._nlp.meta.get('name', 'unknown'),
            'model_version': self._nlp.meta.get('version', 'unknown'),
            'pipeline': list(self._nlp.pipe_names),
            'labels': list(self._nlp.get_pipe('ner').labels) if 'ner' in self._nlp.pipe_names else [],
        }

    def get_stats(self) -> dict[str, Any]:
        """
        Get pipeline statistics.

        Returns:
            Dictionary with processing statistics
        """
        return {
            'is_available': self.is_available,
            'is_initialized': self.is_initialized,
            'min_confidence': self.config.min_confidence,
            'max_context_length': self.config.max_context_length,
            'batch_size': self.config.batch_size,
        }


# Global pipeline instance
nlp_pipeline = NLPPipeline()
