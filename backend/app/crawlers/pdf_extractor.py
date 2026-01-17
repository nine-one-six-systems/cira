"""PDF text extraction for crawled documents."""

import io
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PDFContent:
    """Extracted content from a PDF."""

    text: str
    page_count: int
    has_text_layer: bool
    metadata: dict[str, Any]
    error: str | None = None

    @property
    def is_valid(self) -> bool:
        """Check if extraction was successful."""
        return self.error is None and self.has_text_layer and len(self.text) > 0


class PDFExtractor:
    """
    Extracts text from PDF files.

    Features:
    - Detects PDF links (FR-CRL-008)
    - Extracts text from PDFs with text layers
    - Skips image-only PDFs
    - Stores text in Page table
    - Handles large PDFs gracefully
    """

    # PDF signature
    PDF_SIGNATURE = b'%PDF'

    # Maximum PDF size to process (50MB)
    MAX_PDF_SIZE = 50 * 1024 * 1024

    # Maximum pages to process
    MAX_PAGES = 200

    def __init__(self):
        """Initialize PDF extractor."""
        self._pypdf2_available = self._check_pypdf2()

    def _check_pypdf2(self) -> bool:
        """Check if PyPDF2 is available."""
        try:
            import PyPDF2  # noqa: F401
            return True
        except ImportError:
            logger.warning(
                "PyPDF2 not installed. PDF extraction will be disabled. "
                "Install with: pip install PyPDF2"
            )
            return False

    def is_pdf(self, content: bytes) -> bool:
        """
        Check if content is a PDF file.

        Args:
            content: Raw bytes

        Returns:
            True if content is a PDF
        """
        return content[:4] == self.PDF_SIGNATURE

    def is_pdf_url(self, url: str) -> bool:
        """
        Check if URL points to a PDF file.

        Args:
            url: URL to check

        Returns:
            True if URL appears to be a PDF
        """
        url_lower = url.lower()
        # Check extension
        if url_lower.endswith('.pdf'):
            return True
        # Check query parameters
        if 'format=pdf' in url_lower or 'type=pdf' in url_lower:
            return True
        return False

    def extract(self, content: bytes) -> PDFContent:
        """
        Extract text from PDF content.

        Args:
            content: Raw PDF bytes

        Returns:
            PDFContent with extracted text and metadata
        """
        if not self._pypdf2_available:
            return PDFContent(
                text='',
                page_count=0,
                has_text_layer=False,
                metadata={},
                error='PyPDF2 not installed',
            )

        if not self.is_pdf(content):
            return PDFContent(
                text='',
                page_count=0,
                has_text_layer=False,
                metadata={},
                error='Content is not a PDF',
            )

        if len(content) > self.MAX_PDF_SIZE:
            return PDFContent(
                text='',
                page_count=0,
                has_text_layer=False,
                metadata={},
                error=f'PDF too large: {len(content)} bytes (max: {self.MAX_PDF_SIZE})',
            )

        try:
            import PyPDF2

            reader = PyPDF2.PdfReader(io.BytesIO(content))

            # Get metadata
            metadata = {}
            if reader.metadata:
                metadata = {
                    'title': reader.metadata.get('/Title', ''),
                    'author': reader.metadata.get('/Author', ''),
                    'subject': reader.metadata.get('/Subject', ''),
                    'creator': reader.metadata.get('/Creator', ''),
                }

            page_count = len(reader.pages)

            # Limit pages to process
            pages_to_process = min(page_count, self.MAX_PAGES)

            # Extract text from each page
            text_parts = []
            total_text_length = 0

            for i in range(pages_to_process):
                try:
                    page = reader.pages[i]
                    page_text = page.extract_text() or ''
                    text_parts.append(page_text.strip())
                    total_text_length += len(page_text)
                except Exception as e:
                    logger.warning(f"Error extracting page {i}: {e}")
                    continue

            # Combine text
            full_text = '\n\n'.join(text_parts)

            # Clean up text
            full_text = self._clean_text(full_text)

            # Check if we have meaningful text (not just whitespace/numbers)
            has_text = self._has_meaningful_text(full_text)

            return PDFContent(
                text=full_text,
                page_count=page_count,
                has_text_layer=has_text,
                metadata=metadata,
            )

        except Exception as e:
            error_msg = str(e)
            logger.warning(f"PDF extraction error: {error_msg}")
            return PDFContent(
                text='',
                page_count=0,
                has_text_layer=False,
                metadata={},
                error=error_msg,
            )

    def extract_from_url(
        self,
        url: str,
        fetch_func=None
    ) -> PDFContent:
        """
        Extract text from a PDF URL.

        Args:
            url: URL of the PDF
            fetch_func: Optional function to fetch URL content

        Returns:
            PDFContent with extracted text and metadata
        """
        if fetch_func is None:
            # Use requests as default
            import requests
            try:
                response = requests.get(
                    url,
                    timeout=30,
                    headers={'User-Agent': 'CIRA Bot/1.0'},
                )
                if response.status_code != 200:
                    return PDFContent(
                        text='',
                        page_count=0,
                        has_text_layer=False,
                        metadata={},
                        error=f'HTTP {response.status_code}',
                    )
                content = response.content
            except Exception as e:
                return PDFContent(
                    text='',
                    page_count=0,
                    has_text_layer=False,
                    metadata={},
                    error=str(e),
                )
        else:
            content = fetch_func(url)

        return self.extract(content)

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        import re

        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove control characters
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)

        # Normalize line breaks
        text = re.sub(r' {2,}', '\n', text)

        return text.strip()

    def _has_meaningful_text(self, text: str, min_words: int = 20) -> bool:
        """
        Check if text contains meaningful content.

        Image-only PDFs often produce just numbers or single characters.

        Args:
            text: Extracted text
            min_words: Minimum word count to consider meaningful

        Returns:
            True if text appears meaningful
        """
        if not text:
            return False

        # Count words (sequences of letters)
        import re
        words = re.findall(r'[a-zA-Z]{3,}', text)

        return len(words) >= min_words


# Global instance
pdf_extractor = PDFExtractor()
