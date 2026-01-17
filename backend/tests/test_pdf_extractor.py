"""Tests for PDF text extraction."""

import pytest
from unittest.mock import MagicMock, patch

from app.crawlers.pdf_extractor import (
    PDFContent,
    PDFExtractor,
    pdf_extractor,
)


class TestPDFContent:
    """Tests for PDFContent dataclass."""

    def test_basic_creation(self):
        """Test creating a PDFContent."""
        content = PDFContent(
            text='Sample PDF text',
            page_count=5,
            has_text_layer=True,
            metadata={'title': 'Test PDF'},
        )

        assert content.text == 'Sample PDF text'
        assert content.page_count == 5
        assert content.has_text_layer is True
        assert content.metadata['title'] == 'Test PDF'
        assert content.error is None

    def test_is_valid_success(self):
        """Test is_valid property for valid PDF."""
        content = PDFContent(
            text='This is valid text content with many words.',
            page_count=1,
            has_text_layer=True,
            metadata={},
        )

        assert content.is_valid is True

    def test_is_valid_no_text_layer(self):
        """Test is_valid property when no text layer."""
        content = PDFContent(
            text='',
            page_count=1,
            has_text_layer=False,
            metadata={},
        )

        assert content.is_valid is False

    def test_is_valid_empty_text(self):
        """Test is_valid property when text is empty."""
        content = PDFContent(
            text='',
            page_count=1,
            has_text_layer=True,
            metadata={},
        )

        assert content.is_valid is False

    def test_is_valid_with_error(self):
        """Test is_valid property when error occurred."""
        content = PDFContent(
            text='Some text',
            page_count=1,
            has_text_layer=True,
            metadata={},
            error='Failed to parse',
        )

        assert content.is_valid is False

    def test_error_message(self):
        """Test error field."""
        content = PDFContent(
            text='',
            page_count=0,
            has_text_layer=False,
            metadata={},
            error='PDF is corrupted',
        )

        assert content.error == 'PDF is corrupted'


class TestPDFExtractorConstants:
    """Tests for PDFExtractor constants."""

    def test_pdf_signature(self):
        """Test PDF signature constant."""
        assert PDFExtractor.PDF_SIGNATURE == b'%PDF'

    def test_max_pdf_size(self):
        """Test max PDF size constant."""
        assert PDFExtractor.MAX_PDF_SIZE == 50 * 1024 * 1024  # 50MB

    def test_max_pages(self):
        """Test max pages constant."""
        assert PDFExtractor.MAX_PAGES == 200


class TestPDFExtractorIsPDF:
    """Tests for is_pdf method."""

    @pytest.fixture
    def extractor(self):
        """Create a PDFExtractor instance."""
        return PDFExtractor()

    def test_is_pdf_valid(self, extractor):
        """Test is_pdf with valid PDF content."""
        content = b'%PDF-1.4 some content'
        assert extractor.is_pdf(content) is True

    def test_is_pdf_invalid(self, extractor):
        """Test is_pdf with non-PDF content."""
        content = b'<html><body>Hello</body></html>'
        assert extractor.is_pdf(content) is False

    def test_is_pdf_empty(self, extractor):
        """Test is_pdf with empty content."""
        content = b''
        assert extractor.is_pdf(content) is False


class TestPDFExtractorIsPDFURL:
    """Tests for is_pdf_url method."""

    @pytest.fixture
    def extractor(self):
        """Create a PDFExtractor instance."""
        return PDFExtractor()

    def test_pdf_extension(self, extractor):
        """Test URL with .pdf extension."""
        assert extractor.is_pdf_url('https://example.com/doc.pdf')
        assert extractor.is_pdf_url('https://example.com/DOC.PDF')
        assert extractor.is_pdf_url('https://example.com/path/to/file.pdf')

    def test_pdf_query_param(self, extractor):
        """Test URL with PDF in query params."""
        assert extractor.is_pdf_url('https://example.com/download?format=pdf')
        assert extractor.is_pdf_url('https://example.com/file?type=pdf')

    def test_non_pdf_url(self, extractor):
        """Test URL that is not a PDF."""
        assert not extractor.is_pdf_url('https://example.com/page.html')
        assert not extractor.is_pdf_url('https://example.com/doc.docx')


class TestPDFExtractorExtract:
    """Tests for extract method."""

    @pytest.fixture
    def extractor(self):
        """Create a PDFExtractor instance with mocked PyPDF2 availability."""
        with patch.object(PDFExtractor, '_check_pypdf2', return_value=True):
            return PDFExtractor()

    def test_extract_not_pdf(self, extractor):
        """Test extract with non-PDF content."""
        content = b'<html></html>'
        result = extractor.extract(content)

        assert result.is_valid is False
        assert result.error == 'Content is not a PDF'

    def test_extract_too_large(self, extractor):
        """Test extract with PDF that's too large."""
        # Create content that looks like PDF but is too big
        content = b'%PDF' + b'x' * (51 * 1024 * 1024)
        result = extractor.extract(content)

        assert result.is_valid is False
        assert 'too large' in result.error

    @patch('app.crawlers.pdf_extractor.PDFExtractor._check_pypdf2')
    def test_extract_pypdf2_not_available(self, mock_check):
        """Test extract when PyPDF2 is not installed."""
        mock_check.return_value = False
        extractor = PDFExtractor()

        content = b'%PDF-1.4 test'
        result = extractor.extract(content)

        assert result.is_valid is False
        assert 'PyPDF2 not installed' in result.error


class TestPDFExtractorWithMockedPyPDF2:
    """Tests for extract method with mocked PyPDF2."""

    @pytest.fixture
    def mock_pypdf2(self):
        """Create mock PyPDF2 module."""
        with patch.dict('sys.modules', {'PyPDF2': MagicMock()}):
            yield

    @pytest.fixture
    def extractor(self, mock_pypdf2):
        """Create a PDFExtractor with mocked PyPDF2."""
        with patch.object(PDFExtractor, '_check_pypdf2', return_value=True):
            return PDFExtractor()

    def test_extract_success(self, extractor):
        """Test successful PDF extraction."""
        # Create mock PDF reader
        mock_page = MagicMock()
        mock_page.extract_text.return_value = 'This is some extracted text from the PDF document.'

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader.metadata = {'/Title': 'Test Document'}

        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            content = b'%PDF-1.4 valid content'
            result = extractor.extract(content)

            assert result.error is None
            assert result.page_count == 1
            assert 'extracted text' in result.text

    def test_extract_multiple_pages(self, extractor):
        """Test PDF extraction with multiple pages."""
        pages = []
        for i in range(3):
            mock_page = MagicMock()
            mock_page.extract_text.return_value = f'Page {i + 1} content with enough words.'
            pages.append(mock_page)

        mock_reader = MagicMock()
        mock_reader.pages = pages
        mock_reader.metadata = {}

        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            content = b'%PDF-1.4 content'
            result = extractor.extract(content)

            assert result.page_count == 3
            assert 'Page 1' in result.text
            assert 'Page 2' in result.text
            assert 'Page 3' in result.text

    def test_extract_with_metadata(self, extractor):
        """Test PDF extraction with metadata."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = 'Document content here with many words.'

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page]
        mock_reader.metadata = {
            '/Title': 'Test Title',
            '/Author': 'Test Author',
            '/Subject': 'Test Subject',
            '/Creator': 'Test Creator',
        }

        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            content = b'%PDF-1.4 content'
            result = extractor.extract(content)

            assert result.metadata['title'] == 'Test Title'
            assert result.metadata['author'] == 'Test Author'
            assert result.metadata['subject'] == 'Test Subject'
            assert result.metadata['creator'] == 'Test Creator'

    def test_extract_page_error_handling(self, extractor):
        """Test extraction continues despite page errors."""
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = 'Valid page content with enough words.'

        mock_page2 = MagicMock()
        mock_page2.extract_text.side_effect = Exception('Page error')

        mock_page3 = MagicMock()
        mock_page3.extract_text.return_value = 'Another valid page content here.'

        mock_reader = MagicMock()
        mock_reader.pages = [mock_page1, mock_page2, mock_page3]
        mock_reader.metadata = {}

        with patch('PyPDF2.PdfReader', return_value=mock_reader):
            content = b'%PDF-1.4 content'
            result = extractor.extract(content)

            # Should have extracted from pages 1 and 3
            assert 'Valid page' in result.text
            assert 'Another valid' in result.text


class TestPDFExtractorCleanText:
    """Tests for _clean_text method."""

    @pytest.fixture
    def extractor(self):
        """Create a PDFExtractor instance."""
        return PDFExtractor()

    def test_removes_excessive_whitespace(self, extractor):
        """Test that excessive whitespace is cleaned."""
        text = 'Hello    world\t\t\ttest'
        result = extractor._clean_text(text)
        assert '    ' not in result
        assert '\t\t' not in result

    def test_removes_control_characters(self, extractor):
        """Test that control characters are removed."""
        text = 'Hello\x00\x01\x02world'
        result = extractor._clean_text(text)
        assert '\x00' not in result
        assert 'Helloworld' in result.replace(' ', '').replace('\n', '')

    def test_strips_text(self, extractor):
        """Test that text is stripped."""
        text = '   Hello world   '
        result = extractor._clean_text(text)
        assert not result.startswith(' ')
        assert not result.endswith(' ')


class TestPDFExtractorMeaningfulText:
    """Tests for _has_meaningful_text method."""

    @pytest.fixture
    def extractor(self):
        """Create a PDFExtractor instance."""
        return PDFExtractor()

    def test_meaningful_text(self, extractor):
        """Test text with meaningful content."""
        # Need at least 20 words of 3+ characters by default
        text = ('This document contains many words that form meaningful sentences. '
                'It has enough content to pass the meaningful text threshold. '
                'Additional words are added here to ensure we have enough.')
        assert extractor._has_meaningful_text(text) is True

    def test_not_meaningful_numbers_only(self, extractor):
        """Test text with only numbers."""
        text = '123 456 789 012 345 678 901'
        assert extractor._has_meaningful_text(text) is False

    def test_not_meaningful_short_words(self, extractor):
        """Test text with very short words."""
        text = 'a b c d e f g h i j k l m n o p'
        assert extractor._has_meaningful_text(text) is False

    def test_empty_text(self, extractor):
        """Test empty text."""
        assert extractor._has_meaningful_text('') is False
        assert extractor._has_meaningful_text(None) is False

    def test_custom_min_words(self, extractor):
        """Test with custom minimum word count."""
        text = 'This has five words here'
        assert extractor._has_meaningful_text(text, min_words=5) is True
        assert extractor._has_meaningful_text(text, min_words=10) is False


class TestPDFExtractorFromURL:
    """Tests for extract_from_url method."""

    @pytest.fixture
    def extractor(self):
        """Create a PDFExtractor instance with mocked PyPDF2 availability."""
        with patch.object(PDFExtractor, '_check_pypdf2', return_value=True):
            return PDFExtractor()

    def test_extract_from_url_with_custom_fetch(self, extractor):
        """Test extract_from_url with custom fetch function."""
        mock_fetch = MagicMock(return_value=b'<html></html>')

        result = extractor.extract_from_url(
            'https://example.com/doc.pdf',
            fetch_func=mock_fetch
        )

        mock_fetch.assert_called_once_with('https://example.com/doc.pdf')
        assert result.error == 'Content is not a PDF'

    @patch('requests.get')
    def test_extract_from_url_http_error(self, mock_get, extractor):
        """Test extract_from_url with HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        result = extractor.extract_from_url('https://example.com/doc.pdf')

        assert result.is_valid is False
        assert 'HTTP 404' in result.error

    @patch('requests.get')
    def test_extract_from_url_connection_error(self, mock_get, extractor):
        """Test extract_from_url with connection error."""
        mock_get.side_effect = Exception('Connection failed')

        result = extractor.extract_from_url('https://example.com/doc.pdf')

        assert result.is_valid is False
        assert 'Connection failed' in result.error


class TestGlobalInstance:
    """Tests for global pdf_extractor instance."""

    def test_global_instance_exists(self):
        """Test that global instance exists."""
        assert pdf_extractor is not None
        assert isinstance(pdf_extractor, PDFExtractor)

    def test_global_instance_can_check_pdf(self):
        """Test that global instance can check if content is PDF."""
        assert pdf_extractor.is_pdf(b'%PDF-1.4') is True
        assert pdf_extractor.is_pdf(b'<html>') is False

    def test_global_instance_can_check_url(self):
        """Test that global instance can check PDF URLs."""
        assert pdf_extractor.is_pdf_url('https://example.com/doc.pdf') is True
        assert pdf_extractor.is_pdf_url('https://example.com/page.html') is False
