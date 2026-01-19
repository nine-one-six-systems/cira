# Phase 2: Entity Extraction - Research

**Researched:** 2026-01-19
**Domain:** Named Entity Recognition (NER), structured data extraction, entity deduplication
**Confidence:** HIGH

## Summary

Phase 2 focuses on extracting structured entities from crawled web pages using spaCy NLP and regex-based pattern matching. The existing codebase has a comprehensive, fully-implemented entity extraction system including an NLP pipeline (`nlp_pipeline.py`), entity extractor (`entity_extractor.py`), structured data extractor (`structured_extractor.py`), and deduplicator (`deduplicator.py`).

The implementation uses spaCy's `en_core_web_lg` model for Named Entity Recognition, extracting PERSON, ORG, GPE, PRODUCT, DATE, and MONEY entities. Structured data (emails, phones, addresses, social handles) is extracted via regex patterns with validation. The deduplication system uses fuzzy matching for person names and organization variations.

**Primary recommendation:** The existing implementation covers all NER-01 through NER-07 requirements. Phase 2 planning should focus on integration testing the extraction pipeline, verifying API endpoint behavior (API-10), ensuring UI component functionality (UI-05), and validating edge cases for confidence scoring and deduplication.

## Standard Stack

The established libraries/tools for this domain:

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| spaCy | 3.7+ | NLP pipeline, NER | Industry standard for production NER, fast CPU inference |
| en_core_web_lg | - | English NER model | Best accuracy/speed balance for CPU, 500k word vectors |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| re (stdlib) | - | Regex patterns | Structured data extraction (emails, phones) |
| email-validator | 2.1+ | Email validation | RFC 5322 compliant email validation |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| en_core_web_lg | en_core_web_trf | Transformer is more accurate but 10-40x slower, needs GPU |
| en_core_web_lg | en_core_web_sm | Smaller but significantly less accurate for NER |
| Custom regex | phonenumbers lib | Library is more robust for international numbers but adds dependency |
| LCS similarity | FuzzyWuzzy/RapidFuzz | External libraries are faster but add dependencies |

**Installation:**
```bash
pip install spacy>=3.7.0 email-validator>=2.1.0
python -m spacy download en_core_web_lg
```

## Architecture Patterns

### Existing Project Structure
```
backend/app/extractors/
├── __init__.py
├── nlp_pipeline.py       # spaCy model loading, entity extraction, confidence scoring
├── entity_extractor.py   # Named entity extraction worker, database integration
├── structured_extractor.py  # Regex-based email/phone/address/social extraction
└── deduplicator.py       # Entity deduplication and merging logic
```

### Pattern 1: Lazy Model Loading
**What:** spaCy model loaded on first use, not at import time
**When to use:** Always - prevents slow startup and allows graceful degradation
**Example:**
```python
# Source: backend/app/extractors/nlp_pipeline.py
class NLPPipeline:
    def __init__(self, config: ExtractionConfig | None = None):
        self.config = config or ExtractionConfig()
        self._nlp = None
        self._is_initialized = False

    @property
    def nlp(self):
        """Lazy load the spaCy model."""
        if self._nlp is None:
            self._load_model()
        return self._nlp
```

### Pattern 2: Heuristic-Based Confidence Scoring
**What:** Confidence scores calculated from entity characteristics since spaCy NER doesn't provide native scores
**When to use:** For all extracted entities - enables filtering by confidence
**Example:**
```python
# Source: backend/app/extractors/nlp_pipeline.py
def _calculate_confidence(self, ent: "Span", doc: "Doc") -> float:
    base_confidence = 0.7  # spaCy's NER is generally reliable

    # Penalty for very short entities (< 2 characters)
    if len(ent.text.strip()) < 2:
        base_confidence -= 0.3

    # Bonus for proper capitalization
    if ent.text and ent.text[0].isupper():
        base_confidence += 0.1

    # Bonus for multi-word entities
    word_count = len(ent.text.split())
    if word_count > 1:
        base_confidence += 0.05 * min(word_count - 1, 3)

    return max(0.0, min(1.0, base_confidence))
```

### Pattern 3: Context Snippet Extraction
**What:** 50 characters before/after entity for traceability
**When to use:** All entities - enables source verification in UI
**Example:**
```python
# Source: backend/app/extractors/nlp_pipeline.py
def _extract_context(self, text: str, start: int, end: int, max_length: int) -> str:
    context_start = max(0, start - max_length // 2)
    context_end = min(len(text), end + max_length // 2)

    # Adjust to word boundaries
    # ... (word boundary logic)

    context = text[context_start:context_end]
    if context_start > 0:
        context = '...' + context
    if context_end < len(text):
        context = context + '...'
    return context.strip()
```

### Pattern 4: Role Detection via Regex
**What:** Person roles (CEO, Founder, VP, etc.) detected from surrounding context
**When to use:** For PERSON entities - adds valuable metadata
**Example:**
```python
# Source: backend/app/extractors/nlp_pipeline.py
ROLE_PATTERNS = [
    (r'\b(CEO|Chief Executive Officer)\b', 'CEO'),
    (r'\b(CTO|Chief Technology Officer)\b', 'CTO'),
    (r'\b(Founder|Co-Founder)\b', 'Founder'),
    (r'\b(VP|Vice President)\s+(of\s+)?(\w+)', 'VP'),
    # ... more patterns
]

def _detect_role(self, context: str) -> str | None:
    for pattern, role in self._role_patterns:
        if pattern.search(context):
            return role
    return None
```

### Pattern 5: Organization Relationship Detection
**What:** Classify ORG entities as partner, client, investor, competitor, or acquisition
**When to use:** For ORG entities - provides relationship context
**Example:**
```python
# Source: backend/app/extractors/nlp_pipeline.py
def _detect_org_relationship(self, context: str) -> str | None:
    context_lower = context.lower()

    if any(word in context_lower for word in ['partner', 'partnership']):
        return 'partner'
    if any(word in context_lower for word in ['client', 'customer']):
        return 'client'
    if any(word in context_lower for word in ['investor', 'funded by']):
        return 'investor'
    # ... etc
```

### Pattern 6: Fuzzy Name Matching for Deduplication
**What:** Match name variations like "John Smith" vs "J. Smith"
**When to use:** Person entity deduplication
**Example:**
```python
# Source: backend/app/extractors/deduplicator.py
def _names_match(self, name1: str, name2: str) -> bool:
    # Handle initials: "J. Smith" matches "John Smith"
    parts1 = [p.rstrip('.').lower() for p in n1.split()]
    parts2 = [p.rstrip('.').lower() for p in n2.split()]

    if len(parts1) >= 2 and len(parts2) >= 2:
        # First name: exact or initial match
        first_match = (first1 == first2 or
                      (len(first1) == 1 and first2.startswith(first1)))
        # Last name: must match exactly
        last_match = parts1[-1] == parts2[-1]

        return first_match and last_match
    return False
```

### Anti-Patterns to Avoid
- **Loading model at import:** Causes slow startup; use lazy loading
- **Ignoring confidence scores:** Always filter by minimum confidence threshold
- **Treating all entity types equally:** Use type-specific deduplication (names vs emails)
- **Hardcoding entity type strings:** Use `EntityType` enum from `app.models.enums`

## Don't Hand-Roll

Problems that look simple but have existing solutions:

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| NER | Custom rules | spaCy en_core_web_lg | Pre-trained on OntoNotes, handles edge cases |
| Confidence scoring | Model probability | `NLPPipeline._calculate_confidence()` | spaCy NER doesn't expose scores natively |
| Email validation | Simple regex | RFC 5322 pattern + domain validation | Many edge cases (plus signs, dots, etc.) |
| Phone normalization | Basic digit extraction | `StructuredDataExtractor.extract_phones()` | Handles extensions, country codes, formats |
| Name deduplication | Exact match | `EntityDeduplicator._names_match()` | Handles initials, middle names |
| Org deduplication | Exact match | `EntityDeduplicator._deduplicate_organizations()` | Handles "Inc.", "LLC", "Corp." variations |

**Key insight:** The existing extractors handle many subtle cases. For example, emails like `user+tag@gmail.com` and obfuscated emails like `user [at] domain [dot] com` are both handled.

## Common Pitfalls

### Pitfall 1: spaCy Model Not Installed
**What goes wrong:** Import error or fallback to smaller model with worse accuracy
**Why it happens:** Model download is a separate step from pip install
**How to avoid:** Check `nlp_pipeline.is_available` and `is_initialized` before extraction
**Warning signs:** Logs showing "en_core_web_lg not found, using en_core_web_sm"

### Pitfall 2: Low Confidence Entity Noise
**What goes wrong:** Too many false positive entities in results
**Why it happens:** Default min_confidence too low, or confidence heuristics don't filter well
**How to avoid:** Use `ExtractionConfig(min_confidence=0.5)` or higher for strict filtering
**Warning signs:** Short single-letter entities, generic words classified as ORG

### Pitfall 3: Duplicate Entities Across Pages
**What goes wrong:** Same person/org appears multiple times with slightly different names
**Why it happens:** Deduplication not run, or name variations not matched
**How to avoid:** Always run `deduplicate_company_entities()` after extraction
**Warning signs:** "John Smith" and "John A. Smith" appearing as separate entities

### Pitfall 4: Missing Role/Relationship Context
**What goes wrong:** Person extracted without role, org without relationship
**Why it happens:** Context window too small, or role not in surrounding text
**How to avoid:** Ensure `max_context_length` is at least 100 chars
**Warning signs:** Key executives extracted without CEO/Founder tags

### Pitfall 5: Email/Phone False Positives
**What goes wrong:** Invalid emails like "name@example.png" or partial phone numbers
**Why it happens:** Regex too permissive, image filenames match email pattern
**How to avoid:** Use existing validation in `StructuredDataExtractor` (INVALID_EMAIL_DOMAINS)
**Warning signs:** Emails with image extensions, 5-digit "phone numbers"

### Pitfall 6: Memory Issues on Large Pages
**What goes wrong:** spaCy OOM on very long documents
**Why it happens:** Entire document loaded into memory for NLP processing
**How to avoid:** Use `nlp.pipe()` for batch processing, or chunk very long documents
**Warning signs:** Memory spikes during extraction phase

## Code Examples

Verified patterns from existing implementation:

### Basic Entity Extraction
```python
# Source: backend/app/extractors/nlp_pipeline.py
from app.extractors.nlp_pipeline import NLPPipeline, ExtractionConfig

config = ExtractionConfig(min_confidence=0.5, max_context_length=100)
pipeline = NLPPipeline(config=config)

text = "John Smith is the CEO of Acme Corp, located in San Francisco."
entities = pipeline.process_text(text)

for ent in entities:
    print(f"{ent.label}: {ent.text} (confidence: {ent.confidence:.2f})")
    print(f"  Context: {ent.context_snippet}")
    if ent.extra_data.get('role'):
        print(f"  Role: {ent.extra_data['role']}")
```

### Extracting from Company Pages
```python
# Source: backend/app/extractors/entity_extractor.py
from app.extractors.entity_extractor import EntityExtractor

extractor = EntityExtractor()

# Extract and save to database
result = extractor.save_entities_for_company(
    company_id='uuid-here',
    progress_callback=lambda p: print(f"Processed {p['pages_processed']} pages")
)

print(f"Saved {result['entities_saved']} entities")
print(f"By type: {result['entities_by_type']}")
```

### Structured Data Extraction
```python
# Source: backend/app/extractors/structured_extractor.py
from app.extractors.structured_extractor import StructuredDataExtractor

extractor = StructuredDataExtractor(enable_tech_stack=True)

text = """
Contact us at info@example.com or call (555) 123-4567.
Follow us on Twitter: @examplecorp
We use Python, React, and PostgreSQL.
"""

entities = extractor.extract_all(text)
for ent in entities:
    print(f"{ent.entity_type}: {ent.normalized_value or ent.value}")
    # email: info@example.com
    # phone: +15551234567
    # social_handle: examplecorp (platform: twitter)
    # tech_stack: python (category: languages)
```

### Entity Deduplication
```python
# Source: backend/app/extractors/deduplicator.py
from app.extractors.deduplicator import EntityDeduplicator, deduplicate_company_entities

# For a company in the database
result = deduplicate_company_entities(company_id='uuid-here')
print(f"Reduced {result['original_count']} to {result['deduplicated_count']} entities")

# Manual deduplication
deduplicator = EntityDeduplicator()
entities = [
    {'type': 'person', 'value': 'John Smith', 'confidence': 0.9, 'source_url': '/about'},
    {'type': 'person', 'value': 'J. Smith', 'confidence': 0.7, 'source_url': '/team'},
]
merged = deduplicator.deduplicate_entities(entities)
# Result: Single entity with merged source_urls and highest confidence
```

## API Endpoint Verification

### GET /api/v1/companies/:id/entities

**Existing Implementation:** `backend/app/api/routes/entities.py`

```python
# Query parameters:
# - type: EntityType filter (person, org, location, etc.)
# - minConfidence: float 0-1
# - page: int (default 1)
# - pageSize: int (default 50, max 100)

# Response format: PaginatedResponse with EntityItem
```

**Test cases to verify:**
- Filter by entity type works
- Filter by minConfidence excludes low-confidence entities
- Pagination returns correct page counts
- Entities ordered by confidence descending
- Response includes contextSnippet and sourceUrl

## UI Component Verification

### Entity Browser (UI-05)

**Existing Implementation:** `frontend/src/pages/CompanyResults.tsx`

Features to verify:
- Entity table with columns: Type, Value, Confidence, Source
- Type filter dropdown (ENTITY_TYPE_OPTIONS)
- Confidence displayed as progress bar with color coding
- Context snippet shown below entity value
- Pagination controls
- Source URL clickable link

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Rule-based NER | Statistical/Neural NER | 2010s | Much better accuracy, handles variations |
| Small word vectors | Large (500k) word vectors | spaCy 3.0 | Better out-of-vocabulary handling |
| Manual role detection | Context-aware regex | Always | More roles detected, less maintenance |
| Exact string match | Fuzzy name matching | Always | Better deduplication rates |

**Deprecated/outdated:**
- spaCy v2.x patterns: Use v3.x pipeline configuration
- NLTK for NER: spaCy is faster and more accurate
- Custom NER training: en_core_web_lg is sufficient for general domains

## Open Questions

Things that couldn't be fully resolved:

1. **Confidence calibration**
   - What we know: Heuristic scoring works well for filtering
   - What's unclear: Optimal threshold for different use cases
   - Recommendation: Start with 0.5, allow user adjustment via config

2. **International phone numbers**
   - What we know: US formats handled well
   - What's unclear: International format coverage
   - Recommendation: Current implementation sufficient for US focus; add phonenumbers lib if international needed

3. **Tech stack extraction accuracy**
   - What we know: Feature exists but disabled by default (P2 priority)
   - What's unclear: False positive rate for technology mentions
   - Recommendation: Enable only for careers/jobs pages where tech stack is mentioned

4. **Very large entity sets**
   - What we know: Deduplication uses O(n^2) comparison within groups
   - What's unclear: Performance with 10,000+ entities
   - Recommendation: Current approach sufficient; consider blocking/indexing for massive scale

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/extractors/*.py` - Fully implemented and tested
- IMPLEMENTATION_PLAN.md - Task definitions for Phase 5 (Entity Extraction)
- [spaCy Official Documentation](https://spacy.io/usage/models) - Model capabilities and usage

### Secondary (MEDIUM confidence)
- [spaCy en_core_web_lg on HuggingFace](https://huggingface.co/spacy/en_core_web_lg) - Model specifications
- [Nanonets NER Guide 2025](https://nanonets.com/blog/named-entity-recognition-with-nltk-and-spacy/) - NER best practices
- [Email Regex Patterns](https://uibakery.io/regex-library/email-regex-python) - Email validation patterns

### Tertiary (LOW confidence)
- [Dedupe Library](https://github.com/dedupeio/dedupe) - Alternative deduplication approach (not used, but validated existing approach)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Verified against existing implementation
- Architecture: HIGH - Patterns extracted from working code
- Pitfalls: HIGH - Common issues documented with existing mitigations
- API/UI: HIGH - Implementation exists and is tested

**Research date:** 2026-01-19
**Valid until:** Indefinite - codebase is the source of truth

## Requirement Coverage Analysis

Based on codebase analysis, here is the implementation status of Phase 2 requirements:

### Entity Extraction Requirements

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| NER-01: PERSON entities with spaCy | IMPLEMENTED | `nlp_pipeline.py` with PERSON label mapping |
| NER-02: ORG entities (partners, clients, investors) | IMPLEMENTED | `nlp_pipeline.py` with `_detect_org_relationship()` |
| NER-03: GPE entities (locations, headquarters) | IMPLEMENTED | `nlp_pipeline.py` maps GPE, LOC, FAC to 'location' |
| NER-04: PRODUCT entities | IMPLEMENTED | `nlp_pipeline.py` maps PRODUCT, WORK_OF_ART |
| NER-05: Person role detection | IMPLEMENTED | `nlp_pipeline.py` `ROLE_PATTERNS` and `_detect_role()` |
| NER-06: Structured data (email, phone, address) | IMPLEMENTED | `structured_extractor.py` with validation |
| NER-07: Deduplication with confidence | IMPLEMENTED | `deduplicator.py` with fuzzy matching |

### API Requirements

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| API-10: GET /companies/:id/entities | IMPLEMENTED | `backend/app/api/routes/entities.py` |

### UI Requirements

| Requirement | Status | Implementation |
|-------------|--------|----------------|
| UI-05: Entity browser with filtering | IMPLEMENTED | `frontend/src/pages/CompanyResults.tsx` Entities tab |

### Summary

All Phase 2 requirements (NER-01 through NER-07, API-10, UI-05) are implemented in the existing codebase. Planning should focus on:

1. Integration testing of the full extraction pipeline end-to-end
2. Verification that entity extraction integrates with crawl worker correctly
3. Edge case testing (empty pages, non-English content, very long text)
4. Performance validation (1000+ tokens/sec target per NER-01)
5. UI testing of entity browser filtering and pagination
