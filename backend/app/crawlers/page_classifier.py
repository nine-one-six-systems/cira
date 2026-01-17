"""Page type classification based on URL and content."""

import logging
import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class PageClassification:
    """Classification result for a page."""

    page_type: str
    confidence: float  # 0.0 to 1.0
    match_source: str  # 'url', 'content', 'combined'
    matched_patterns: list[str]


# Page types and their priorities
PAGE_TYPES = [
    'about',
    'team',
    'product',
    'service',
    'contact',
    'careers',
    'pricing',
    'blog',
    'news',
    'other',
]

# URL patterns for page type detection (compiled regexes)
URL_PATTERNS: dict[str, list[tuple[re.Pattern, float]]] = {
    'about': [
        (re.compile(r'/about[-_]?us/?$', re.I), 1.0),
        (re.compile(r'/about/?$', re.I), 1.0),
        (re.compile(r'/company/?$', re.I), 0.9),
        (re.compile(r'/who[-_]?we[-_]?are/?$', re.I), 0.9),
        (re.compile(r'/our[-_]?story/?$', re.I), 0.9),
        (re.compile(r'/mission/?$', re.I), 0.8),
        (re.compile(r'/vision/?$', re.I), 0.8),
        (re.compile(r'/values/?$', re.I), 0.8),
        (re.compile(r'/history/?$', re.I), 0.8),
    ],
    'team': [
        (re.compile(r'/team/?$', re.I), 1.0),
        (re.compile(r'/our[-_]?team/?$', re.I), 1.0),
        (re.compile(r'/people/?$', re.I), 0.9),
        (re.compile(r'/leadership/?$', re.I), 0.9),
        (re.compile(r'/management/?$', re.I), 0.9),
        (re.compile(r'/founders/?$', re.I), 0.9),
        (re.compile(r'/executives/?$', re.I), 0.9),
        (re.compile(r'/board/?$', re.I), 0.8),
        (re.compile(r'/advisors/?$', re.I), 0.8),
        (re.compile(r'/team/', re.I), 0.7),  # Team subpages
    ],
    'product': [
        (re.compile(r'/products?/?$', re.I), 1.0),
        (re.compile(r'/solutions?/?$', re.I), 0.9),
        (re.compile(r'/platform/?$', re.I), 0.9),
        (re.compile(r'/features?/?$', re.I), 0.9),
        (re.compile(r'/offerings?/?$', re.I), 0.9),
        (re.compile(r'/tools?/?$', re.I), 0.8),
        (re.compile(r'/software/?$', re.I), 0.8),
        (re.compile(r'/products?/', re.I), 0.7),  # Product subpages
    ],
    'service': [
        (re.compile(r'/services?/?$', re.I), 1.0),
        (re.compile(r'/what[-_]?we[-_]?do/?$', re.I), 0.9),
        (re.compile(r'/capabilities/?$', re.I), 0.9),
        (re.compile(r'/consulting/?$', re.I), 0.9),
        (re.compile(r'/expertise/?$', re.I), 0.8),
        (re.compile(r'/services?/', re.I), 0.7),  # Service subpages
    ],
    'contact': [
        (re.compile(r'/contact[-_]?us/?$', re.I), 1.0),
        (re.compile(r'/contact/?$', re.I), 1.0),
        (re.compile(r'/get[-_]?in[-_]?touch/?$', re.I), 0.9),
        (re.compile(r'/reach[-_]?us/?$', re.I), 0.9),
        (re.compile(r'/locations?/?$', re.I), 0.8),
        (re.compile(r'/offices?/?$', re.I), 0.8),
        (re.compile(r'/support/?$', re.I), 0.7),
    ],
    'careers': [
        (re.compile(r'/careers?/?$', re.I), 1.0),
        (re.compile(r'/jobs?/?$', re.I), 1.0),
        (re.compile(r'/join[-_]?us/?$', re.I), 0.9),
        (re.compile(r'/hiring/?$', re.I), 0.9),
        (re.compile(r'/opportunities?/?$', re.I), 0.9),
        (re.compile(r'/work[-_]?with[-_]?us/?$', re.I), 0.9),
        (re.compile(r'/openings?/?$', re.I), 0.8),
        (re.compile(r'/careers?/', re.I), 0.7),  # Career subpages
    ],
    'pricing': [
        (re.compile(r'/pricing/?$', re.I), 1.0),
        (re.compile(r'/plans?/?$', re.I), 0.9),
        (re.compile(r'/packages?/?$', re.I), 0.9),
        (re.compile(r'/cost/?$', re.I), 0.8),
        (re.compile(r'/subscription/?$', re.I), 0.8),
    ],
    'blog': [
        (re.compile(r'/blog/?$', re.I), 1.0),
        (re.compile(r'/articles?/?$', re.I), 0.9),
        (re.compile(r'/insights?/?$', re.I), 0.9),
        (re.compile(r'/resources?/?$', re.I), 0.8),
        (re.compile(r'/learn/?$', re.I), 0.8),
        (re.compile(r'/blog/', re.I), 0.7),  # Blog posts
    ],
    'news': [
        (re.compile(r'/news/?$', re.I), 1.0),
        (re.compile(r'/press/?$', re.I), 1.0),
        (re.compile(r'/press[-_]?releases?/?$', re.I), 1.0),
        (re.compile(r'/media/?$', re.I), 0.9),
        (re.compile(r'/announcements?/?$', re.I), 0.9),
        (re.compile(r'/newsroom/?$', re.I), 0.9),
        (re.compile(r'/news/', re.I), 0.7),  # News articles
    ],
}

# Content patterns for page type detection
CONTENT_PATTERNS: dict[str, list[tuple[re.Pattern, float]]] = {
    'about': [
        (re.compile(r'\bour\s+mission\b', re.I), 0.8),
        (re.compile(r'\bour\s+vision\b', re.I), 0.8),
        (re.compile(r'\bfounded\s+in\b', re.I), 0.7),
        (re.compile(r'\bwho\s+we\s+are\b', re.I), 0.8),
        (re.compile(r'\bour\s+story\b', re.I), 0.8),
        (re.compile(r'\bcompany\s+overview\b', re.I), 0.8),
    ],
    'team': [
        (re.compile(r'\bour\s+team\b', re.I), 0.8),
        (re.compile(r'\bleadership\s+team\b', re.I), 0.9),
        (re.compile(r'\bexecutive\s+team\b', re.I), 0.9),
        (re.compile(r'\bfounder[s]?\s+&?\s*ceo\b', re.I), 0.8),
        (re.compile(r'\bboard\s+of\s+directors\b', re.I), 0.8),
    ],
    'product': [
        (re.compile(r'\bour\s+products?\b', re.I), 0.8),
        (re.compile(r'\bkey\s+features?\b', re.I), 0.7),
        (re.compile(r'\bproduct\s+overview\b', re.I), 0.8),
    ],
    'service': [
        (re.compile(r'\bour\s+services?\b', re.I), 0.8),
        (re.compile(r'\bwhat\s+we\s+offer\b', re.I), 0.7),
    ],
    'contact': [
        (re.compile(r'\bcontact\s+us\b', re.I), 0.9),
        (re.compile(r'\bget\s+in\s+touch\b', re.I), 0.9),
        (re.compile(r'\bsend\s+us\s+a\s+message\b', re.I), 0.8),
        (re.compile(r'\brequest\s+a\s+demo\b', re.I), 0.7),
    ],
    'careers': [
        (re.compile(r'\bjob\s+openings?\b', re.I), 0.9),
        (re.compile(r'\bopen\s+positions?\b', re.I), 0.9),
        (re.compile(r'\bwe\'?re\s+hiring\b', re.I), 0.9),
        (re.compile(r'\bjoin\s+our\s+team\b', re.I), 0.9),
        (re.compile(r'\bcareer\s+opportunities\b', re.I), 0.9),
    ],
    'pricing': [
        (re.compile(r'\bpricing\s+plans?\b', re.I), 0.9),
        (re.compile(r'\bmonthly\s+plan\b', re.I), 0.8),
        (re.compile(r'\bannual\s+plan\b', re.I), 0.8),
        (re.compile(r'\bfree\s+trial\b', re.I), 0.7),
        (re.compile(r'\bper\s+month\b', re.I), 0.6),
    ],
    'blog': [
        (re.compile(r'\blatest\s+posts?\b', re.I), 0.8),
        (re.compile(r'\bblog\s+posts?\b', re.I), 0.9),
        (re.compile(r'\bpublished\s+on\b', re.I), 0.6),
    ],
    'news': [
        (re.compile(r'\bpress\s+release\b', re.I), 0.9),
        (re.compile(r'\bnews\s+&\s+events?\b', re.I), 0.8),
        (re.compile(r'\bin\s+the\s+news\b', re.I), 0.8),
    ],
}


class PageClassifier:
    """
    Classifies web pages into types based on URL and content.

    Features:
    - URL pattern matching for quick classification
    - Content-based classification as fallback
    - Combined scoring for improved accuracy
    - Confidence scores for each classification
    """

    def __init__(self):
        """Initialize page classifier."""
        self._url_patterns = URL_PATTERNS
        self._content_patterns = CONTENT_PATTERNS

    def classify(
        self,
        url: str,
        content: str | None = None
    ) -> PageClassification:
        """
        Classify a page based on URL and optionally content.

        Args:
            url: Page URL
            content: Optional page text content

        Returns:
            PageClassification with type, confidence, and metadata
        """
        parsed = urlparse(url)
        path = parsed.path.lower()

        # First try URL-based classification
        url_result = self._classify_by_url(path)

        if content:
            # Try content-based classification
            content_result = self._classify_by_content(content)

            # Combine results
            if url_result and content_result:
                # Both have results - combine
                return self._combine_classifications(url_result, content_result)
            elif content_result and not url_result:
                return content_result
            elif url_result:
                return url_result
        elif url_result:
            return url_result

        # Default to 'other'
        return PageClassification(
            page_type='other',
            confidence=0.5,
            match_source='default',
            matched_patterns=[],
        )

    def _classify_by_url(self, path: str) -> PageClassification | None:
        """Classify based on URL path patterns."""
        best_type = None
        best_confidence = 0.0
        matched_patterns = []

        for page_type, patterns in self._url_patterns.items():
            for pattern, confidence in patterns:
                if pattern.search(path):
                    matched_patterns.append(pattern.pattern)
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_type = page_type

        if best_type:
            return PageClassification(
                page_type=best_type,
                confidence=best_confidence,
                match_source='url',
                matched_patterns=matched_patterns,
            )

        return None

    def _classify_by_content(self, content: str) -> PageClassification | None:
        """Classify based on page content."""
        scores: dict[str, tuple[float, list[str]]] = {}

        for page_type, patterns in self._content_patterns.items():
            type_score = 0.0
            type_patterns = []

            for pattern, weight in patterns:
                matches = pattern.findall(content)
                if matches:
                    # Score based on number of matches and weight
                    match_score = min(len(matches) * weight * 0.3, weight)
                    type_score += match_score
                    type_patterns.append(pattern.pattern)

            if type_score > 0:
                # Normalize score to 0-1 range
                normalized_score = min(type_score / 2.0, 1.0)
                scores[page_type] = (normalized_score, type_patterns)

        if scores:
            # Get best type
            best_type = max(scores.keys(), key=lambda t: scores[t][0])
            confidence, patterns = scores[best_type]

            return PageClassification(
                page_type=best_type,
                confidence=confidence,
                match_source='content',
                matched_patterns=patterns,
            )

        return None

    def _combine_classifications(
        self,
        url_result: PageClassification,
        content_result: PageClassification
    ) -> PageClassification:
        """Combine URL and content classifications."""
        # If they agree, boost confidence
        if url_result.page_type == content_result.page_type:
            combined_confidence = min(
                (url_result.confidence + content_result.confidence) / 1.5,
                1.0
            )
            return PageClassification(
                page_type=url_result.page_type,
                confidence=combined_confidence,
                match_source='combined',
                matched_patterns=url_result.matched_patterns + content_result.matched_patterns,
            )

        # Prefer URL classification with higher base confidence
        # but reduce if content strongly disagrees
        if url_result.confidence >= content_result.confidence * 1.2:
            return url_result
        elif content_result.confidence >= url_result.confidence * 1.2:
            return content_result
        else:
            # Similar confidence - prefer URL
            url_result.confidence *= 0.9  # Slight penalty for ambiguity
            return url_result

    def classify_url_only(self, url: str) -> str:
        """
        Quick classification based on URL only.

        Args:
            url: Page URL

        Returns:
            Page type string
        """
        result = self.classify(url)
        return result.page_type

    def get_all_patterns(self) -> dict[str, Any]:
        """Get all classification patterns for debugging."""
        return {
            'url_patterns': {
                ptype: [p.pattern for p, _ in patterns]
                for ptype, patterns in self._url_patterns.items()
            },
            'content_patterns': {
                ptype: [p.pattern for p, _ in patterns]
                for ptype, patterns in self._content_patterns.items()
            },
        }


# Global instance
page_classifier = PageClassifier()
