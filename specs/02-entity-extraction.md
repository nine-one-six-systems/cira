# Entity Extraction Specification

## Overview

The entity extraction system uses spaCy NLP for Named Entity Recognition (NER) combined with pattern-based extraction for structured data. It processes crawled pages to identify people, organizations, locations, products, and structured data like emails and phone numbers.

## Functional Requirements

### Entity Extraction (FR-NER-001 to FR-NER-007)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-NER-001 | Extract company name variations | P0 |
| FR-NER-002 | Extract locations (headquarters, offices) | P0 |
| FR-NER-003 | Extract people names with roles (CEO, founders, executives) | P0 |
| FR-NER-004 | Extract product and service names | P0 |
| FR-NER-005 | Extract organization mentions (partners, clients, investors) | P1 |
| FR-NER-006 | Extract dates (founded, milestones) | P1 |
| FR-NER-007 | Extract monetary values (revenue, funding) | P1 |

### Structured Data Extraction (FR-STR-001 to FR-STR-005)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-STR-001 | Extract email patterns | P0 |
| FR-STR-002 | Extract phone numbers | P1 |
| FR-STR-003 | Extract physical addresses | P1 |
| FR-STR-004 | Extract social media handles | P1 |
| FR-STR-005 | Extract tech stack indicators from job postings and about pages | P2 |

## Acceptance Criteria

### Named Entity Recognition
- spaCy en_core_web_lg model loaded
- Standard entities extracted: PERSON, ORG, GPE, DATE, MONEY
- Context snippets (50 chars before/after) preserved
- Confidence scores assigned based on spaCy's scoring
- Source URL recorded for each entity

### Person Extraction
- Names extracted with surrounding context
- Roles identified (CEO, Founder, CTO, VP, Director, etc.)
- Multiple roles for same person merged
- Confidence > 0.7 for clear entities

### Organization Extraction
- Company name variations captured
- Related organizations categorized (partner, client, investor, competitor)
- Relationship context preserved

### Location Extraction
- Headquarters identified from "HQ", "headquarters", address patterns
- Office locations with city/country
- Geographic context (region, country) normalized

### Product/Service Extraction
- Product names linked to descriptions when available
- Services categorized by type
- Pricing information associated when found

### Structured Data Patterns
- Email: RFC 5322 compliant regex
- Phone: International and US formats, normalized to E.164
- Address: US and international format detection
- Social handles: @username patterns with platform detection

## Test Requirements

### Programmatic Tests

1. **spaCy NER Tests**
   - PERSON entities extracted from team pages
   - ORG entities extracted from partnership mentions
   - GPE (locations) extracted from contact pages
   - DATE entities extracted from timeline/history
   - MONEY entities extracted from funding announcements

2. **Role Detection Tests**
   - "John Smith, CEO" extracts person with CEO role
   - "Founded by Jane Doe" extracts person with Founder role
   - Multiple mentions of same person merged

3. **Email Extraction Tests**
   - Valid emails extracted: user@domain.com
   - Invalid patterns rejected: user@, @domain.com
   - Obfuscated emails detected: user [at] domain [dot] com

4. **Phone Extraction Tests**
   - US format: (555) 123-4567, 555-123-4567
   - International: +1-555-123-4567
   - Normalized to consistent format

5. **Deduplication Tests**
   - Same entity from multiple pages appears once
   - Highest confidence score retained
   - All source URLs preserved

### Performance Tests

- Process 1000+ tokens/second
- Batch processing more efficient than single-document
- Memory stable for large documents

## Data Models

### Entity

```typescript
interface Entity {
  id: string;
  companyId: string;
  entityType: EntityType;
  entityValue: string;
  contextSnippet: string;
  sourceUrl: string;
  confidenceScore: number;
  createdAt: Date;
}

enum EntityType {
  PERSON = 'person',
  ORGANIZATION = 'org',
  LOCATION = 'location',
  PRODUCT = 'product',
  DATE = 'date',
  MONEY = 'money',
  EMAIL = 'email',
  PHONE = 'phone',
  ADDRESS = 'address',
  SOCIAL_HANDLE = 'social_handle',
  TECH_STACK = 'tech_stack'
}
```

### PersonEntity (extended)

```typescript
interface PersonEntity extends Entity {
  role?: string;        // CEO, Founder, CTO, etc.
  department?: string;  // Engineering, Sales, etc.
}
```

### OrganizationEntity (extended)

```typescript
interface OrganizationEntity extends Entity {
  relationship?: string; // partner, client, investor, competitor
}
```

## Configuration

```typescript
interface ExtractionConfig {
  minConfidence: number;     // Default: 0.5
  maxContextLength: number;  // Default: 100 chars
  enableTechStack: boolean;  // Default: false (P2 feature)
  customPatterns: RegexPattern[];
}
```

## Dependencies

- spaCy 3.7+ with en_core_web_lg model
- Custom pipeline components for domain-specific entities
