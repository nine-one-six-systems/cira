"""Extraction integration test fixtures.

This module provides realistic company page content fixtures for testing
the entity extraction pipeline.

Requirements covered: NER-01 to NER-07
"""

import pytest
from typing import Any


# ============================================================================
# TEXT FIXTURES
# ============================================================================

ABOUT_PAGE_TEXT = """
About TechInnovate Solutions

TechInnovate Solutions is a leading enterprise software company founded in 2018 by
John Smith, CEO and Co-founder, along with Sarah Johnson, CTO and Co-founder.
Headquartered in San Francisco, California, we have grown to over 200 employees
across three offices globally.

Our mission is to transform how businesses leverage data through our flagship product,
DataStream Analytics, which provides real-time insights for Fortune 500 companies.
We also offer CloudSync Platform for seamless cloud migration and DataGuard for
enterprise security solutions.

Since our founding, TechInnovate has been backed by Sequoia Capital and Andreessen
Horowitz, having raised over $75 million in Series B funding in 2022. Our strategic
partners include Microsoft, Google Cloud, and Amazon Web Services, enabling us to
provide best-in-class cloud integrations.

Our client roster includes industry leaders such as Bank of America, Delta Airlines,
and Walmart. In 2023, we were recognized by Gartner as a "Cool Vendor" in the
enterprise analytics space.

For inquiries, please contact us at info@techinnovate.com or call (415) 555-7890.
Visit our offices at 100 Market Street, Suite 500, San Francisco, CA 94105.

Follow us on LinkedIn at linkedin.com/company/techinnovate and Twitter @techinnovate.
"""


TEAM_PAGE_TEXT = """
Our Leadership Team

John Smith - Chief Executive Officer and Co-Founder
John Smith leads TechInnovate with over 20 years of experience in enterprise software.
Before founding TechInnovate, John was VP of Engineering at Oracle. J. Smith holds
an MBA from Stanford Business School and a BS in Computer Science from MIT.

Sarah Johnson - Chief Technology Officer and Co-Founder
Sarah Johnson drives our technical vision and product architecture. Sarah was
previously a Principal Engineer at Google. Sarah Johnson is a recognized expert in
distributed systems and has authored multiple patents. S. Johnson speaks regularly
at tech conferences worldwide.

Michael Chen - Vice President of Engineering
Michael Chen oversees our engineering teams across all product lines. Michael joined
from Amazon where he led the AWS CloudFormation team. Mike Chen has built
engineering organizations from 10 to over 100 engineers.

Dr. Emily Williams - Chief Data Scientist
Emily Williams leads our data science and machine learning initiatives. Dr. Williams
previously served as a research scientist at DeepMind. Emily holds a Ph.D. in
Machine Learning from Stanford University.

David Martinez - VP of Sales
David Martinez heads our global sales organization. Martinez has 15 years of
enterprise sales experience at companies including Salesforce and SAP.

Jennifer Lee - Director of Product Management
Jennifer Lee manages product strategy and roadmap. Lee previously worked at
Microsoft on Azure services. Jen Lee is passionate about customer-centric design.

Robert Taylor - Head of Customer Success
Robert Taylor ensures our customers achieve their goals with our products. Taylor
has led customer success teams at multiple SaaS companies.

Lisa Brown - Chief Marketing Officer
Lisa Brown drives brand awareness and demand generation. L. Brown previously held
marketing leadership roles at HubSpot and Marketo.
"""


CONTACT_PAGE_TEXT = """
Contact TechInnovate Solutions

Get in Touch
We'd love to hear from you! Reach out through any of the following channels.

General Inquiries
Email: info@techinnovate.com
Phone: (415) 555-7890

Sales Team
For sales and partnership opportunities:
Email: sales@techinnovate.com
Phone: 415.555.7891

Support
For product support and technical assistance:
Email: support@techinnovate.com
Phone: +1-415-555-7892
Support Portal: support.techinnovate.com

Media and Press
For press inquiries and media requests:
Email: press@techinnovate.com

Headquarters
100 Market Street
Suite 500
San Francisco, CA 94105
United States

New York Office
350 Fifth Avenue
Floor 45
New York, NY 10118

London Office
25 Old Broad Street
London EC2N 1HN
United Kingdom

Connect With Us
LinkedIn: linkedin.com/company/techinnovate
Twitter: twitter.com/techinnovate
Facebook: facebook.com/techinnovatesolutions
GitHub: github.com/techinnovate
YouTube: youtube.com/c/techinnovate
Instagram: instagram.com/techinnovate

Office Hours
Monday - Friday: 9:00 AM - 6:00 PM PST
Saturday - Sunday: Closed
"""


CAREERS_PAGE_TEXT = """
Careers at TechInnovate Solutions

Join Our Team
We're building the future of enterprise analytics. Join a team of innovators,
problem-solvers, and builders.

Our Technology Stack
We use cutting-edge technologies to build world-class products:

Backend: Python, Go, Java
Frontend: React, TypeScript, JavaScript
Databases: PostgreSQL, MongoDB, Redis, Elasticsearch
Infrastructure: AWS, Kubernetes, Docker, Terraform
Data Processing: Apache Kafka, Apache Spark, Apache Flink
ML/AI: PyTorch, TensorFlow, scikit-learn

Open Positions

Engineering
- Senior Backend Engineer (Python/Go)
- Staff Frontend Engineer (React/TypeScript)
- Machine Learning Engineer
- DevOps Engineer (Kubernetes/AWS)
- Data Engineer (Spark/Kafka)

Product
- Senior Product Manager - Analytics
- Product Designer - Enterprise UX
- Technical Product Manager

Sales & Marketing
- Enterprise Account Executive
- Marketing Manager - Demand Gen
- Customer Success Manager

Benefits
- Competitive salary and equity
- Health, dental, and vision insurance
- 401(k) with company match
- Unlimited PTO
- Remote-friendly culture
- Learning and development budget
- Home office stipend

Equal Opportunity Employer
TechInnovate Solutions is an equal opportunity employer. We celebrate diversity
and are committed to creating an inclusive environment for all employees.
"""


DUPLICATE_ENTITY_TEXT = """
Executive Spotlight: John Smith

John Smith is the CEO and Co-founder of TechInnovate Solutions. Mr. Smith has led
the company since its founding in 2018. According to John, the company's mission
is to democratize data analytics for enterprises.

In a recent interview, John Smith discussed the company's growth trajectory. "We've
grown from 5 to over 200 employees," Smith said. J. Smith also mentioned plans for
international expansion.

John Smith can be reached at john@techinnovate.com for speaking engagements.
For general inquiries, contact info@techinnovate.com or john@techinnovate.com.

TechInnovate Solutions has partnered with Google to enhance its cloud offerings.
Google Cloud is a strategic partner for TechInnovate. The partnership with Google
enables advanced AI capabilities.

TechInnovate Inc. was recently valued at $500 million. TechInnovate Solutions
continues to grow rapidly. TechInnovate's products are used by Fortune 500 companies.
"""


# Text with minimal content for edge case testing
MINIMAL_PAGE_TEXT = """
Contact us for more information.
"""


# Non-English text for graceful handling test
NON_ENGLISH_TEXT = """
Willkommen bei TechInnovate Losungen

Wir bieten innovative Softwarelosungen fur Unternehmen.
Unser Team besteht aus erfahrenen Ingenieuren und Entwicklern.
Hans Muller ist der Geschaftsfuhrer unserer deutschen Niederlassung.
Kontaktieren Sie uns unter info@techinnovate.de.
"""


# Empty text for edge case testing
EMPTY_PAGE_TEXT = ""


# Text with products and services
PRODUCTS_PAGE_TEXT = """
Our Products and Services

DataStream Analytics
DataStream Analytics is our flagship real-time analytics platform. Built for
enterprise-scale data processing, DataStream can handle millions of events
per second with sub-millisecond latency.

CloudSync Platform
CloudSync Platform simplifies cloud migration and multi-cloud management.
Supports AWS, Azure, and Google Cloud Platform.

DataGuard Security
DataGuard provides comprehensive data security and compliance monitoring.
SOC 2 Type II and HIPAA certified.

AI Insights Engine
Our newest product, AI Insights Engine, uses advanced machine learning to
surface actionable insights from your data automatically.

Professional Services
We offer implementation, training, and consulting services to ensure your
success with our products.
"""


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================

def create_company_with_pages(db, app_context=None) -> dict[str, Any]:
    """
    Create a Company with associated Pages for integration testing.

    This factory function creates a complete test company with multiple
    pages of different types, ready for extraction testing.

    Args:
        db: Flask-SQLAlchemy db instance
        app_context: Optional application context (uses current if not provided)

    Returns:
        Dictionary containing:
            - company: Company model instance
            - pages: Dict of page_type -> Page instance
            - company_id: UUID string
            - page_ids: Dict of page_type -> UUID string
    """
    from app.models import Company, Page
    from app.models.enums import CompanyStatus, PageType, ProcessingPhase

    # Create company
    company = Company(
        company_name="TechInnovate Solutions",
        website_url="https://techinnovate.com",
        industry="Enterprise Software",
        status=CompanyStatus.IN_PROGRESS,
        processing_phase=ProcessingPhase.EXTRACTING,
    )
    db.session.add(company)
    db.session.flush()  # Get the ID without committing

    # Create pages with different types and content
    pages = {}
    page_configs = [
        (PageType.ABOUT, "https://techinnovate.com/about", ABOUT_PAGE_TEXT),
        (PageType.TEAM, "https://techinnovate.com/team", TEAM_PAGE_TEXT),
        (PageType.CONTACT, "https://techinnovate.com/contact", CONTACT_PAGE_TEXT),
        (PageType.CAREERS, "https://techinnovate.com/careers", CAREERS_PAGE_TEXT),
        (PageType.PRODUCT, "https://techinnovate.com/products", PRODUCTS_PAGE_TEXT),
    ]

    for page_type, url, text in page_configs:
        page = Page(
            company_id=company.id,
            url=url,
            page_type=page_type,
            extracted_text=text,
        )
        db.session.add(page)
        db.session.flush()
        pages[page_type.value] = page

    db.session.commit()

    return {
        'company': company,
        'pages': pages,
        'company_id': company.id,
        'page_ids': {k: v.id for k, v in pages.items()},
    }


def create_empty_page_company(db) -> dict[str, Any]:
    """
    Create a Company with an empty Page for edge case testing.

    Args:
        db: Flask-SQLAlchemy db instance

    Returns:
        Dictionary containing company and page info
    """
    from app.models import Company, Page
    from app.models.enums import CompanyStatus, PageType, ProcessingPhase

    company = Company(
        company_name="Empty Test Company",
        website_url="https://empty.test",
        status=CompanyStatus.IN_PROGRESS,
        processing_phase=ProcessingPhase.EXTRACTING,
    )
    db.session.add(company)
    db.session.flush()

    page = Page(
        company_id=company.id,
        url="https://empty.test/about",
        page_type=PageType.ABOUT,
        extracted_text=EMPTY_PAGE_TEXT,
    )
    db.session.add(page)
    db.session.commit()

    return {
        'company': company,
        'page': page,
        'company_id': company.id,
        'page_id': page.id,
    }


def create_non_english_page_company(db) -> dict[str, Any]:
    """
    Create a Company with non-English Page content.

    Args:
        db: Flask-SQLAlchemy db instance

    Returns:
        Dictionary containing company and page info
    """
    from app.models import Company, Page
    from app.models.enums import CompanyStatus, PageType, ProcessingPhase

    company = Company(
        company_name="German Test Company",
        website_url="https://german.test",
        status=CompanyStatus.IN_PROGRESS,
        processing_phase=ProcessingPhase.EXTRACTING,
    )
    db.session.add(company)
    db.session.flush()

    page = Page(
        company_id=company.id,
        url="https://german.test/uber-uns",
        page_type=PageType.ABOUT,
        extracted_text=NON_ENGLISH_TEXT,
    )
    db.session.add(page)
    db.session.commit()

    return {
        'company': company,
        'page': page,
        'company_id': company.id,
        'page_id': page.id,
    }


# ============================================================================
# PYTEST FIXTURES
# ============================================================================

@pytest.fixture
def about_page_text() -> str:
    """Realistic about page content for extraction testing."""
    return ABOUT_PAGE_TEXT


@pytest.fixture
def team_page_text() -> str:
    """Team page content with multiple people and roles."""
    return TEAM_PAGE_TEXT


@pytest.fixture
def contact_page_text() -> str:
    """Contact page with emails, phones, addresses, and social links."""
    return CONTACT_PAGE_TEXT


@pytest.fixture
def careers_page_text() -> str:
    """Careers page with tech stack mentions."""
    return CAREERS_PAGE_TEXT


@pytest.fixture
def duplicate_entity_text() -> str:
    """Text with intentional duplicates for deduplication testing."""
    return DUPLICATE_ENTITY_TEXT


@pytest.fixture
def products_page_text() -> str:
    """Products page with product names."""
    return PRODUCTS_PAGE_TEXT


@pytest.fixture
def empty_page_text() -> str:
    """Empty text for edge case testing."""
    return EMPTY_PAGE_TEXT


@pytest.fixture
def non_english_text() -> str:
    """Non-English text for graceful handling testing."""
    return NON_ENGLISH_TEXT
