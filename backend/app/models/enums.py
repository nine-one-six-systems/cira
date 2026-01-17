"""Enumeration types for database models."""

import enum


class CompanyStatus(enum.Enum):
    """Status of a company analysis."""
    PENDING = 'pending'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    FAILED = 'failed'
    PAUSED = 'paused'


class CrawlStatus(enum.Enum):
    """Status of a crawl session."""
    ACTIVE = 'active'
    PAUSED = 'paused'
    COMPLETED = 'completed'
    TIMEOUT = 'timeout'
    FAILED = 'failed'


class ProcessingPhase(enum.Enum):
    """Current phase of analysis processing."""
    QUEUED = 'queued'
    CRAWLING = 'crawling'
    EXTRACTING = 'extracting'
    ANALYZING = 'analyzing'
    GENERATING = 'generating'
    COMPLETED = 'completed'


class AnalysisMode(enum.Enum):
    """Analysis mode configuration."""
    QUICK = 'quick'
    THOROUGH = 'thorough'


class PageType(enum.Enum):
    """Type classification for crawled pages."""
    ABOUT = 'about'
    TEAM = 'team'
    PRODUCT = 'product'
    SERVICE = 'service'
    CONTACT = 'contact'
    CAREERS = 'careers'
    PRICING = 'pricing'
    BLOG = 'blog'
    NEWS = 'news'
    OTHER = 'other'


class EntityType(enum.Enum):
    """Type of extracted entity."""
    PERSON = 'person'
    ORGANIZATION = 'org'
    LOCATION = 'location'
    PRODUCT = 'product'
    DATE = 'date'
    MONEY = 'money'
    EMAIL = 'email'
    PHONE = 'phone'
    ADDRESS = 'address'
    SOCIAL_HANDLE = 'social_handle'
    TECH_STACK = 'tech_stack'


class ApiCallType(enum.Enum):
    """Type of API call for token tracking."""
    EXTRACTION = 'extraction'
    SUMMARIZATION = 'summarization'
    ANALYSIS = 'analysis'
