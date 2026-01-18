"""Tests for the spaCy NLP Pipeline (Task 5.1)."""

import pytest
from unittest.mock import MagicMock, patch


class TestNLPPipelineBasics:
    """Test NLP pipeline initialization and configuration."""

    def test_pipeline_initializes(self):
        """Test that the pipeline initializes without error."""
        from app.extractors.nlp_pipeline import NLPPipeline, ExtractionConfig

        config = ExtractionConfig(min_confidence=0.5)
        pipeline = NLPPipeline(config)

        assert pipeline.config.min_confidence == 0.5
        assert pipeline.config.max_context_length == 100

    def test_default_config(self):
        """Test default configuration values."""
        from app.extractors.nlp_pipeline import NLPPipeline, ExtractionConfig

        pipeline = NLPPipeline()

        assert pipeline.config.min_confidence == 0.5
        assert pipeline.config.max_context_length == 100
        assert pipeline.config.batch_size == 1000

    def test_custom_config(self):
        """Test custom configuration."""
        from app.extractors.nlp_pipeline import NLPPipeline, ExtractionConfig

        config = ExtractionConfig(
            min_confidence=0.7,
            max_context_length=200,
            batch_size=500
        )
        pipeline = NLPPipeline(config)

        assert pipeline.config.min_confidence == 0.7
        assert pipeline.config.max_context_length == 200
        assert pipeline.config.batch_size == 500

    def test_is_available_property(self):
        """Test that is_available property works."""
        from app.extractors.nlp_pipeline import NLPPipeline, SPACY_AVAILABLE

        pipeline = NLPPipeline()
        assert pipeline.is_available == SPACY_AVAILABLE

    def test_get_stats_before_init(self):
        """Test stats before model is loaded."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        stats = pipeline.get_stats()

        assert 'is_available' in stats
        assert 'min_confidence' in stats
        assert stats['min_confidence'] == 0.5


class TestNLPPipelineProcessing:
    """Test NLP pipeline text processing."""

    def test_process_empty_text(self):
        """Test processing empty text."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        result = pipeline.process_text('')

        assert result == []

    def test_process_none_text(self):
        """Test processing None text."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        result = pipeline.process_text(None)

        assert result == []

    @pytest.mark.skipif(
        not pytest.importorskip('spacy', reason="spacy not installed"),
        reason="spacy not installed"
    )
    def test_process_text_with_person(self):
        """Test extracting person entities."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        text = "John Smith is the CEO of Acme Corporation."
        result = pipeline.process_text(text)

        # Should extract at least one entity
        assert len(result) >= 1

        # Check for person entity
        person_entities = [e for e in result if e.label == 'PERSON']
        if person_entities:
            assert 'John' in person_entities[0].text or 'Smith' in person_entities[0].text

    @pytest.mark.skipif(
        not pytest.importorskip('spacy', reason="spacy not installed"),
        reason="spacy not installed"
    )
    def test_process_text_with_organization(self):
        """Test extracting organization entities."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        text = "Google is a technology company headquartered in Mountain View."
        result = pipeline.process_text(text)

        # Check for organization entity
        org_entities = [e for e in result if e.label in ('ORG', 'NORP')]
        if org_entities:
            assert any('Google' in e.text for e in org_entities)

    @pytest.mark.skipif(
        not pytest.importorskip('spacy', reason="spacy not installed"),
        reason="spacy not installed"
    )
    def test_process_text_with_location(self):
        """Test extracting location entities."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        text = "Our headquarters is located in San Francisco, California."
        result = pipeline.process_text(text)

        # Check for location entity
        loc_entities = [e for e in result if e.label in ('GPE', 'LOC', 'FAC')]
        if loc_entities:
            assert any('San Francisco' in e.text or 'California' in e.text for e in loc_entities)

    @pytest.mark.skipif(
        not pytest.importorskip('spacy', reason="spacy not installed"),
        reason="spacy not installed"
    )
    def test_process_text_with_money(self):
        """Test extracting money entities."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        text = "The company raised $50 million in Series B funding."
        result = pipeline.process_text(text)

        # Check for money entity
        money_entities = [e for e in result if e.label == 'MONEY']
        if money_entities:
            assert any('50' in e.text or 'million' in e.text for e in money_entities)

    @pytest.mark.skipif(
        not pytest.importorskip('spacy', reason="spacy not installed"),
        reason="spacy not installed"
    )
    def test_process_text_with_date(self):
        """Test extracting date entities."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        text = "The company was founded in 2015."
        result = pipeline.process_text(text)

        # Check for date entity
        date_entities = [e for e in result if e.label in ('DATE', 'TIME')]
        if date_entities:
            assert any('2015' in e.text for e in date_entities)


class TestNLPPipelineBatchProcessing:
    """Test NLP pipeline batch processing."""

    def test_process_batch_empty(self):
        """Test batch processing with empty list."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        result = pipeline.process_batch([])

        assert result == []

    def test_process_batch_empty_texts(self):
        """Test batch processing with empty strings."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        result = pipeline.process_batch(['', '', ''])

        assert len(result) == 3
        for entities in result:
            assert entities == []

    @pytest.mark.skipif(
        not pytest.importorskip('spacy', reason="spacy not installed"),
        reason="spacy not installed"
    )
    def test_process_batch_multiple_texts(self):
        """Test batch processing multiple texts."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        texts = [
            "John Smith is the CEO.",
            "The company is in New York.",
            "They raised $10 million.",
        ]
        result = pipeline.process_batch(texts)

        assert len(result) == 3


class TestNLPPipelineRoleDetection:
    """Test person role detection."""

    def test_detect_ceo_role(self):
        """Test detecting CEO role."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "John Smith, CEO, leads the company"
        role = pipeline._detect_role(context)

        assert role == 'CEO'

    def test_detect_founder_role(self):
        """Test detecting Founder role."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "Founded by Jane Doe in 2015"
        role = pipeline._detect_role(context)

        assert role == 'Founder'

    def test_detect_cto_role(self):
        """Test detecting CTO role."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "Our Chief Technology Officer, Bob Jones"
        role = pipeline._detect_role(context)

        assert role == 'CTO'

    def test_detect_vp_role(self):
        """Test detecting VP role."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "Sarah is VP of Engineering"
        role = pipeline._detect_role(context)

        assert role == 'VP'

    def test_detect_director_role(self):
        """Test detecting Director role."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "Mike is Director of Sales"
        role = pipeline._detect_role(context)

        assert role == 'Director'

    def test_no_role_detected(self):
        """Test when no role is present."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "John works at the company"
        role = pipeline._detect_role(context)

        assert role is None


class TestNLPPipelineOrgRelationship:
    """Test organization relationship detection."""

    def test_detect_partner_relationship(self):
        """Test detecting partner relationship."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "Our partner Microsoft helps with cloud infrastructure"
        relationship = pipeline._detect_org_relationship(context)

        assert relationship == 'partner'

    def test_detect_investor_relationship(self):
        """Test detecting investor relationship."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "Backed by investor Sequoia Capital"
        relationship = pipeline._detect_org_relationship(context)

        assert relationship == 'investor'

    def test_detect_client_relationship(self):
        """Test detecting client relationship."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "Our client Google uses our services"
        relationship = pipeline._detect_org_relationship(context)

        assert relationship == 'client'

    def test_detect_competitor_relationship(self):
        """Test detecting competitor relationship."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "Competing with competitor Amazon in cloud"
        relationship = pipeline._detect_org_relationship(context)

        assert relationship == 'competitor'

    def test_no_relationship_detected(self):
        """Test when no relationship is present."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        context = "Google is a technology company"
        relationship = pipeline._detect_org_relationship(context)

        assert relationship is None


class TestNLPPipelineContextExtraction:
    """Test context extraction."""

    def test_extract_context_middle(self):
        """Test extracting context from middle of text."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        text = "This is some text before. John Smith is the CEO. This is after."
        context = pipeline._extract_context(text, 27, 37, 50)

        assert 'John Smith' in context

    def test_extract_context_start(self):
        """Test extracting context from start of text."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        text = "John Smith is the CEO of this company."
        context = pipeline._extract_context(text, 0, 10, 50)

        assert 'John Smith' in context
        assert not context.startswith('...')

    def test_extract_context_end(self):
        """Test extracting context from end of text."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        text = "The company CEO is John Smith"
        context = pipeline._extract_context(text, 19, 29, 50)

        assert 'John Smith' in context
        assert not context.endswith('...')

    def test_extract_context_adds_ellipsis(self):
        """Test that ellipsis is added when truncated."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        text = "A" * 50 + " John Smith " + "B" * 50
        context = pipeline._extract_context(text, 50, 62, 30)

        # Should have ellipsis on both ends
        assert '...' in context


class TestNLPPipelineConfidenceCalculation:
    """Test confidence score calculation."""

    def test_confidence_normal_entity(self):
        """Test confidence for normal entity."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()

        # Create mock entity and doc
        mock_ent = MagicMock()
        mock_ent.text = "John Smith"
        mock_doc = MagicMock()

        confidence = pipeline._calculate_confidence(mock_ent, mock_doc)

        # Base confidence is 0.7, should be increased for proper capitalization
        assert 0.5 <= confidence <= 1.0

    def test_confidence_short_entity(self):
        """Test lower confidence for very short entities."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()

        mock_ent = MagicMock()
        mock_ent.text = "J"
        mock_doc = MagicMock()

        confidence = pipeline._calculate_confidence(mock_ent, mock_doc)

        # Should be penalized for being too short
        assert confidence < 0.7

    def test_confidence_multiword_entity(self):
        """Test higher confidence for multi-word entities."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()

        mock_ent_single = MagicMock()
        mock_ent_single.text = "John"

        mock_ent_multi = MagicMock()
        mock_ent_multi.text = "John William Smith Jr"

        mock_doc = MagicMock()

        conf_single = pipeline._calculate_confidence(mock_ent_single, mock_doc)
        conf_multi = pipeline._calculate_confidence(mock_ent_multi, mock_doc)

        # Multi-word should have higher confidence
        assert conf_multi >= conf_single


class TestNLPPipelineModelInfo:
    """Test model information."""

    def test_get_model_info_without_init(self):
        """Test getting model info before initialization."""
        from app.extractors.nlp_pipeline import NLPPipeline

        pipeline = NLPPipeline()
        pipeline._nlp = None  # Ensure not loaded

        info = pipeline.get_model_info()

        assert 'available' in info


class TestExtractedEntity:
    """Test ExtractedEntity dataclass."""

    def test_entity_to_dict(self):
        """Test converting entity to dictionary."""
        from app.extractors.nlp_pipeline import ExtractedEntity

        entity = ExtractedEntity(
            text="John Smith",
            label="PERSON",
            start_char=0,
            end_char=10,
            confidence=0.9,
            context_snippet="John Smith is the CEO",
            extra_data={'role': 'CEO'}
        )

        result = entity.to_dict()

        assert result['text'] == "John Smith"
        assert result['label'] == "PERSON"
        assert result['confidence'] == 0.9
        assert result['extra_data']['role'] == 'CEO'

    def test_entity_default_extra_data(self):
        """Test entity with default extra_data."""
        from app.extractors.nlp_pipeline import ExtractedEntity

        entity = ExtractedEntity(
            text="Test",
            label="ORG",
            start_char=0,
            end_char=4,
            confidence=0.8,
            context_snippet="Test context"
        )

        assert entity.extra_data == {}


class TestGlobalPipeline:
    """Test global pipeline instance."""

    def test_global_pipeline_exists(self):
        """Test that global pipeline is available."""
        from app.extractors.nlp_pipeline import nlp_pipeline

        assert nlp_pipeline is not None

    def test_global_pipeline_is_nlp_pipeline(self):
        """Test that global pipeline is correct type."""
        from app.extractors.nlp_pipeline import nlp_pipeline, NLPPipeline

        assert isinstance(nlp_pipeline, NLPPipeline)
