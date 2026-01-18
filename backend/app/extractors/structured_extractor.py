"""Structured Data Extraction using regex patterns.

Task 5.3: Structured Data Extraction (Regex)
- Emails with validation (FR-STR-001)
- Phone numbers normalized (FR-STR-002)
- Physical addresses (FR-STR-003)
- Social handles (FR-STR-004)

Task 5.4: Tech Stack Detection (FR-STR-005)
- Detect languages, frameworks, tools
- Source from job postings
- Categorize by type
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class StructuredEntity:
    """A structured entity extracted via pattern matching."""
    entity_type: str
    value: str
    normalized_value: str | None = None
    confidence: float = 0.9  # Pattern matching is generally reliable
    context: str = ''
    extra_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            'type': self.entity_type,
            'value': self.value,
            'normalized': self.normalized_value or self.value,
            'confidence': self.confidence,
            'context': self.context,
            'extra_data': self.extra_data,
        }


class StructuredDataExtractor:
    """
    Pattern-based extraction for structured data.

    Extracts:
    - Email addresses (RFC 5322 compliant)
    - Phone numbers (US and international formats)
    - Physical addresses
    - Social media handles
    - Tech stack indicators

    All extracted data includes confidence scores and context.
    """

    # Email pattern (RFC 5322 simplified)
    EMAIL_PATTERN = re.compile(
        r'''(?:[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-zA-Z0-9!#$%&'*+/=?^_`{|}~-]+)*'''
        r'''|"(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]'''
        r'''|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")'''
        r'''@(?:(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?\.)+[a-zA-Z0-9](?:[a-zA-Z0-9-]*[a-zA-Z0-9])?'''
        r'''|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?|[a-zA-Z0-9-]*[a-zA-Z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])+)\])''',
        re.VERBOSE | re.IGNORECASE
    )

    # Simpler email pattern for common cases
    EMAIL_SIMPLE_PATTERN = re.compile(
        r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        re.IGNORECASE
    )

    # Obfuscated email pattern
    EMAIL_OBFUSCATED_PATTERN = re.compile(
        r'([a-zA-Z0-9._%+-]+)\s*'  # local part
        r'(?:\[\s*at\s*\]|\(\s*at\s*\)|(?:\s+at\s+)|@)\s*'  # @ or [at] or (at) or " at "
        r'([a-zA-Z0-9.-]+)\s*'  # domain
        r'(?:\[\s*dot\s*\]|\(\s*dot\s*\)|(?:\s+dot\s+)|\.)\s*'  # . or [dot] or (dot) or " dot "
        r'([a-zA-Z]{2,})',  # TLD
        re.IGNORECASE
    )

    # Phone patterns
    PHONE_PATTERNS = [
        # International format: +1-555-123-4567 or +1 555 123 4567
        re.compile(r'\+?1?[-.\s]?\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})'),
        # US format variations
        re.compile(r'\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})'),
        # With extension
        re.compile(r'\(?(\d{3})\)?[-.\s]?(\d{3})[-.\s]?(\d{4})\s*(?:x|ext|extension)?\s*(\d+)?', re.IGNORECASE),
        # Written out
        re.compile(r'(\d{3})[-.\s](\d{3})[-.\s](\d{4})'),
    ]

    # Address patterns
    ADDRESS_PATTERNS = [
        # US street address
        re.compile(
            r'\d+\s+[\w\s]+(?:Street|St|Avenue|Ave|Boulevard|Blvd|Drive|Dr|Road|Rd|Lane|Ln|Way|Court|Ct|Place|Pl|Circle|Cir)\.?'
            r'(?:\s*,?\s*(?:Suite|Ste|Apt|Unit|#)\s*[\w\d]+)?'
            r'(?:\s*,?\s*[\w\s]+)?'
            r'(?:\s*,?\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?)?',
            re.IGNORECASE
        ),
        # City, State ZIP
        re.compile(r'[\w\s]+,\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?'),
        # International with postal code
        re.compile(r'[\w\s]+,?\s*[\w\s]+,?\s*[A-Z]{1,2}\d{1,2}\s*\d[A-Z]{2}', re.IGNORECASE),  # UK postal
    ]

    # Social media patterns
    SOCIAL_PATTERNS = {
        'twitter': [
            re.compile(r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/(@?\w+)', re.IGNORECASE),
            re.compile(r'@([a-zA-Z_][\w]{0,14})'),  # Twitter handle
        ],
        'linkedin': [
            re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/(?:in|company)/([^/?]+)', re.IGNORECASE),
        ],
        'facebook': [
            re.compile(r'(?:https?://)?(?:www\.)?facebook\.com/([^/?]+)', re.IGNORECASE),
            re.compile(r'(?:https?://)?(?:www\.)?fb\.com/([^/?]+)', re.IGNORECASE),
        ],
        'instagram': [
            re.compile(r'(?:https?://)?(?:www\.)?instagram\.com/([^/?]+)', re.IGNORECASE),
        ],
        'github': [
            re.compile(r'(?:https?://)?(?:www\.)?github\.com/([^/?]+)', re.IGNORECASE),
        ],
        'youtube': [
            re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/(?:c/|channel/|user/|@)?([^/?]+)', re.IGNORECASE),
        ],
    }

    # Tech stack patterns
    TECH_STACK_PATTERNS = {
        # Languages
        'languages': {
            'python': re.compile(r'\bPython\b', re.IGNORECASE),
            'javascript': re.compile(r'\b(?:JavaScript|JS)\b', re.IGNORECASE),
            'typescript': re.compile(r'\b(?:TypeScript|TS)\b', re.IGNORECASE),
            'java': re.compile(r'\bJava\b(?!\s*Script)', re.IGNORECASE),
            'go': re.compile(r'\b(?:Go|Golang)\b', re.IGNORECASE),
            'rust': re.compile(r'\bRust\b', re.IGNORECASE),
            'ruby': re.compile(r'\bRuby\b', re.IGNORECASE),
            'php': re.compile(r'\bPHP\b', re.IGNORECASE),
            'c++': re.compile(r'\bC\+\+\b', re.IGNORECASE),
            'c#': re.compile(r'\bC#\b', re.IGNORECASE),
            'swift': re.compile(r'\bSwift\b', re.IGNORECASE),
            'kotlin': re.compile(r'\bKotlin\b', re.IGNORECASE),
            'scala': re.compile(r'\bScala\b', re.IGNORECASE),
            'r': re.compile(r'\bR\b(?:\s+programming)?', re.IGNORECASE),
        },
        # Frameworks
        'frameworks': {
            'react': re.compile(r'\bReact(?:\.?js)?\b', re.IGNORECASE),
            'angular': re.compile(r'\bAngular(?:\.?js)?\b', re.IGNORECASE),
            'vue': re.compile(r'\bVue(?:\.?js)?\b', re.IGNORECASE),
            'django': re.compile(r'\bDjango\b', re.IGNORECASE),
            'flask': re.compile(r'\bFlask\b', re.IGNORECASE),
            'fastapi': re.compile(r'\bFastAPI\b', re.IGNORECASE),
            'rails': re.compile(r'\bRuby on Rails\b|\bRails\b', re.IGNORECASE),
            'spring': re.compile(r'\bSpring\b(?:\s+Boot)?', re.IGNORECASE),
            'express': re.compile(r'\bExpress(?:\.?js)?\b', re.IGNORECASE),
            'nextjs': re.compile(r'\bNext\.?js\b', re.IGNORECASE),
            'nodejs': re.compile(r'\bNode\.?js\b', re.IGNORECASE),
            '.net': re.compile(r'\.NET\b', re.IGNORECASE),
            'laravel': re.compile(r'\bLaravel\b', re.IGNORECASE),
            'svelte': re.compile(r'\bSvelte\b', re.IGNORECASE),
        },
        # Databases
        'databases': {
            'postgresql': re.compile(r'\b(?:PostgreSQL|Postgres)\b', re.IGNORECASE),
            'mysql': re.compile(r'\bMySQL\b', re.IGNORECASE),
            'mongodb': re.compile(r'\bMongoDB?\b', re.IGNORECASE),
            'redis': re.compile(r'\bRedis\b', re.IGNORECASE),
            'elasticsearch': re.compile(r'\bElasticsearch\b', re.IGNORECASE),
            'dynamodb': re.compile(r'\bDynamoDB\b', re.IGNORECASE),
            'sqlite': re.compile(r'\bSQLite\b', re.IGNORECASE),
            'cassandra': re.compile(r'\bCassandra\b', re.IGNORECASE),
            'oracle': re.compile(r'\bOracle\b(?:\s+Database)?', re.IGNORECASE),
            'sql server': re.compile(r'\bSQL\s+Server\b', re.IGNORECASE),
        },
        # Cloud/Infrastructure
        'infrastructure': {
            'aws': re.compile(r'\bAWS\b|\bAmazon Web Services\b', re.IGNORECASE),
            'gcp': re.compile(r'\bGCP\b|\bGoogle Cloud\b', re.IGNORECASE),
            'azure': re.compile(r'\bAzure\b', re.IGNORECASE),
            'kubernetes': re.compile(r'\bKubernetes\b|\bK8s\b', re.IGNORECASE),
            'docker': re.compile(r'\bDocker\b', re.IGNORECASE),
            'terraform': re.compile(r'\bTerraform\b', re.IGNORECASE),
            'ansible': re.compile(r'\bAnsible\b', re.IGNORECASE),
            'jenkins': re.compile(r'\bJenkins\b', re.IGNORECASE),
            'circleci': re.compile(r'\bCircleCI\b', re.IGNORECASE),
            'github actions': re.compile(r'\bGitHub Actions\b', re.IGNORECASE),
        },
        # Tools
        'tools': {
            'git': re.compile(r'\bGit\b(?!Hub)', re.IGNORECASE),
            'jira': re.compile(r'\bJira\b', re.IGNORECASE),
            'slack': re.compile(r'\bSlack\b', re.IGNORECASE),
            'figma': re.compile(r'\bFigma\b', re.IGNORECASE),
            'kafka': re.compile(r'\bKafka\b', re.IGNORECASE),
            'rabbitmq': re.compile(r'\bRabbitMQ\b', re.IGNORECASE),
            'graphql': re.compile(r'\bGraphQL\b', re.IGNORECASE),
            'rest api': re.compile(r'\bREST(?:ful)?\s+API\b', re.IGNORECASE),
            'nginx': re.compile(r'\bNginx\b', re.IGNORECASE),
            'apache': re.compile(r'\bApache\b(?:\s+HTTP)?', re.IGNORECASE),
        },
    }

    # Invalid domains for email filtering
    INVALID_EMAIL_DOMAINS = {
        'example.com', 'example.org', 'example.net',
        'test.com', 'localhost', 'domain.com',
        'email.com', 'your-email.com',
        'yourcompany.com',
    }

    def __init__(self, enable_tech_stack: bool = False):
        """
        Initialize the structured data extractor.

        Args:
            enable_tech_stack: Whether to enable tech stack detection (P2 feature)
        """
        self.enable_tech_stack = enable_tech_stack

    def extract_all(self, text: str, source_url: str = '') -> list[StructuredEntity]:
        """
        Extract all structured data from text.

        Args:
            text: Text to extract from
            source_url: Source URL for context

        Returns:
            List of extracted structured entities
        """
        entities = []

        # Extract emails
        entities.extend(self.extract_emails(text))

        # Extract phone numbers
        entities.extend(self.extract_phones(text))

        # Extract addresses
        entities.extend(self.extract_addresses(text))

        # Extract social handles
        entities.extend(self.extract_social_handles(text))

        # Extract tech stack if enabled
        if self.enable_tech_stack:
            entities.extend(self.extract_tech_stack(text))

        return entities

    def extract_emails(self, text: str) -> list[StructuredEntity]:
        """
        Extract email addresses from text.

        Args:
            text: Text to extract from

        Returns:
            List of email entities
        """
        entities = []
        seen = set()

        # Find standard emails
        for match in self.EMAIL_SIMPLE_PATTERN.finditer(text):
            email = match.group().lower()

            # Skip if already seen
            if email in seen:
                continue
            seen.add(email)

            # Validate
            if not self._is_valid_email(email):
                continue

            # Extract context
            context = self._extract_context(text, match.start(), match.end())

            entities.append(StructuredEntity(
                entity_type='email',
                value=match.group(),
                normalized_value=email,
                confidence=0.95,
                context=context,
            ))

        # Find obfuscated emails
        for match in self.EMAIL_OBFUSCATED_PATTERN.finditer(text):
            local, domain, tld = match.groups()
            email = f"{local}@{domain}.{tld}".lower()

            if email in seen:
                continue
            seen.add(email)

            if not self._is_valid_email(email):
                continue

            context = self._extract_context(text, match.start(), match.end())

            entities.append(StructuredEntity(
                entity_type='email',
                value=match.group(),
                normalized_value=email,
                confidence=0.85,  # Lower confidence for obfuscated
                context=context,
            ))

        return entities

    def _is_valid_email(self, email: str) -> bool:
        """Check if an email is valid."""
        # Check basic format
        if '@' not in email:
            return False

        local, domain = email.rsplit('@', 1)

        # Check domain validity
        if domain in self.INVALID_EMAIL_DOMAINS:
            return False

        # Check for common invalid patterns
        if domain.endswith('.png') or domain.endswith('.jpg'):
            return False

        # Check minimum length
        if len(local) < 1 or len(domain) < 3:
            return False

        # Check for dots in domain
        if '.' not in domain:
            return False

        return True

    def extract_phones(self, text: str) -> list[StructuredEntity]:
        """
        Extract phone numbers from text and normalize to E.164 format.

        Args:
            text: Text to extract from

        Returns:
            List of phone entities
        """
        entities = []
        seen = set()

        for pattern in self.PHONE_PATTERNS:
            for match in pattern.finditer(text):
                groups = match.groups()

                # Extract digits
                if len(groups) >= 3:
                    area, exchange, number = groups[:3]
                    extension = groups[3] if len(groups) > 3 else None

                    # Build raw phone
                    raw_phone = match.group()

                    # Skip if we've seen this number
                    normalized = f"+1{area}{exchange}{number}"
                    if normalized in seen:
                        continue
                    seen.add(normalized)

                    # Skip if not enough digits
                    if len(area + exchange + number) != 10:
                        continue

                    # Extract context
                    context = self._extract_context(text, match.start(), match.end())

                    extra_data = {}
                    if extension:
                        extra_data['extension'] = extension

                    entities.append(StructuredEntity(
                        entity_type='phone',
                        value=raw_phone,
                        normalized_value=normalized,
                        confidence=0.9,
                        context=context,
                        extra_data=extra_data,
                    ))

        return entities

    def extract_addresses(self, text: str) -> list[StructuredEntity]:
        """
        Extract physical addresses from text.

        Args:
            text: Text to extract from

        Returns:
            List of address entities
        """
        entities = []
        seen = set()

        for pattern in self.ADDRESS_PATTERNS:
            for match in pattern.finditer(text):
                address = match.group().strip()

                # Normalize for deduplication
                normalized = re.sub(r'\s+', ' ', address.lower())
                if normalized in seen:
                    continue
                seen.add(normalized)

                # Skip very short matches
                if len(address) < 15:
                    continue

                # Extract context
                context = self._extract_context(text, match.start(), match.end())

                entities.append(StructuredEntity(
                    entity_type='address',
                    value=address,
                    normalized_value=address.strip(),
                    confidence=0.8,  # Addresses can be ambiguous
                    context=context,
                ))

        return entities

    def extract_social_handles(self, text: str) -> list[StructuredEntity]:
        """
        Extract social media handles from text.

        Args:
            text: Text to extract from

        Returns:
            List of social handle entities
        """
        entities = []
        seen = set()

        for platform, patterns in self.SOCIAL_PATTERNS.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    handle = match.group(1) if match.lastindex else match.group()

                    # Clean handle
                    handle = handle.strip('/@')

                    # Skip generic handles
                    if handle.lower() in ('share', 'intent', 'home', 'login', 'signup', 'about'):
                        continue

                    # Create unique key
                    key = f"{platform}:{handle.lower()}"
                    if key in seen:
                        continue
                    seen.add(key)

                    # Extract context
                    context = self._extract_context(text, match.start(), match.end())

                    entities.append(StructuredEntity(
                        entity_type='social_handle',
                        value=match.group(),
                        normalized_value=handle,
                        confidence=0.9,
                        context=context,
                        extra_data={'platform': platform},
                    ))

        return entities

    def extract_tech_stack(self, text: str) -> list[StructuredEntity]:
        """
        Extract tech stack indicators from text.

        Most effective on job postings and about/technology pages.

        Args:
            text: Text to extract from

        Returns:
            List of tech stack entities (empty if enable_tech_stack is False)
        """
        # Return empty list if tech stack extraction is disabled
        if not self.enable_tech_stack:
            return []

        entities = []
        seen = set()

        for category, technologies in self.TECH_STACK_PATTERNS.items():
            for tech_name, pattern in technologies.items():
                matches = list(pattern.finditer(text))
                if matches:
                    # Take the first match for context
                    first_match = matches[0]

                    # Skip if we've seen this tech
                    if tech_name in seen:
                        continue
                    seen.add(tech_name)

                    # Extract context
                    context = self._extract_context(text, first_match.start(), first_match.end())

                    # Confidence based on number of mentions
                    confidence = min(0.9, 0.7 + len(matches) * 0.05)

                    entities.append(StructuredEntity(
                        entity_type='tech_stack',
                        value=first_match.group(),
                        normalized_value=tech_name,
                        confidence=confidence,
                        context=context,
                        extra_data={
                            'category': category,
                            'mentions': len(matches),
                        },
                    ))

        return entities

    def _extract_context(
        self,
        text: str,
        start: int,
        end: int,
        max_length: int = 100
    ) -> str:
        """
        Extract context around a match.

        Args:
            text: Full text
            start: Match start position
            end: Match end position
            max_length: Maximum context length

        Returns:
            Context string
        """
        # Calculate context boundaries
        context_start = max(0, start - max_length // 2)
        context_end = min(len(text), end + max_length // 2)

        # Adjust to word boundaries
        if context_start > 0:
            while context_start > 0 and text[context_start - 1] not in ' \n\t':
                context_start -= 1

        if context_end < len(text):
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


# Global extractor instance
structured_extractor = StructuredDataExtractor()
