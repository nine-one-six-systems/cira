"""Tests for Pydantic schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.enums import (
    AnalysisMode,
    ApiCallType,
    CompanyStatus,
    EntityType,
    PageType,
    ProcessingPhase,
)
from app.schemas import (
    ApiError,
    ApiErrorResponse,
    ApiResponse,
    AnalysisSummary,
    BatchCompanyResult,
    BatchUploadResponse,
    CompanyConfig,
    CompanyDetail,
    CompanyDetailResponse,
    CompanyListItem,
    CreateCompanyRequest,
    CreateCompanyResponse,
    DeletedRecords,
    DeleteResponse,
    EntityItem,
    EntityQueryParams,
    HealthResponse,
    PageItem,
    PageQueryParams,
    PaginatedResponse,
    PaginationMeta,
    PauseResponse,
    ProgressResponse,
    RescanResponse,
    ResumeFromData,
    ResumeResponse,
    TokenUsageItem,
    TokenUsageResponse,
    VersionChange,
    VersionChanges,
    VersionItem,
    CompareVersionsResponse,
    CompareQueryParams,
)


class TestBaseSchemas:
    """Tests for base schema classes."""

    def test_api_response_wrapper(self):
        """Test ApiResponse wraps data correctly."""
        response = ApiResponse[dict](data={'key': 'value'})
        assert response.success is True
        assert response.data == {'key': 'value'}

    def test_api_error_response(self):
        """Test ApiErrorResponse structure."""
        error = ApiError(code='NOT_FOUND', message='Resource not found')
        response = ApiErrorResponse(error=error)
        assert response.success is False
        assert response.error.code == 'NOT_FOUND'
        assert response.error.message == 'Resource not found'

    def test_api_error_with_details(self):
        """Test ApiError with additional details."""
        error = ApiError(
            code='VALIDATION_ERROR',
            message='Invalid input',
            details={'field': 'websiteUrl', 'reason': 'Invalid URL format'}
        )
        assert error.details['field'] == 'websiteUrl'

    def test_pagination_meta(self):
        """Test PaginationMeta calculations."""
        meta = PaginationMeta(total=100, page=2, page_size=20, total_pages=5)
        assert meta.total == 100
        assert meta.page == 2
        assert meta.page_size == 20
        assert meta.total_pages == 5

    def test_paginated_response(self):
        """Test PaginatedResponse structure."""
        meta = PaginationMeta(total=50, page=1, page_size=20, total_pages=3)
        response = PaginatedResponse[str](data=['item1', 'item2'], meta=meta)
        assert response.success is True
        assert len(response.data) == 2
        assert response.meta.total == 50


class TestCompanySchemas:
    """Tests for company-related schemas."""

    def test_create_company_request_valid(self):
        """Test valid company creation request."""
        request = CreateCompanyRequest(
            companyName='Acme Corp',
            websiteUrl='https://acme.com',
            industry='Technology'
        )
        assert request.company_name == 'Acme Corp'
        assert str(request.website_url) == 'https://acme.com/'
        assert request.industry == 'Technology'

    def test_create_company_request_url_normalization(self):
        """Test URL normalization without protocol."""
        request = CreateCompanyRequest(
            companyName='Acme Corp',
            websiteUrl='acme.com'
        )
        assert str(request.website_url).startswith('https://')

    def test_create_company_request_company_name_too_long(self):
        """Test validation fails for name exceeding 200 characters."""
        with pytest.raises(ValidationError):
            CreateCompanyRequest(
                companyName='x' * 201,
                websiteUrl='https://acme.com'
            )

    def test_create_company_request_missing_required(self):
        """Test validation fails for missing required fields."""
        with pytest.raises(ValidationError):
            CreateCompanyRequest(companyName='Acme')  # Missing websiteUrl

    def test_company_config_defaults(self):
        """Test CompanyConfig has sensible defaults."""
        config = CompanyConfig()
        assert config.analysis_mode == AnalysisMode.THOROUGH
        assert config.time_limit_minutes == 30
        assert config.max_pages == 100
        assert config.max_depth == 3
        assert config.follow_linkedin is True
        assert config.follow_twitter is True
        assert config.follow_facebook is False

    def test_company_config_validation(self):
        """Test CompanyConfig validation boundaries."""
        with pytest.raises(ValidationError):
            CompanyConfig(timeLimitMinutes=2)  # Below minimum

        with pytest.raises(ValidationError):
            CompanyConfig(maxPages=600)  # Above maximum

    def test_create_company_response(self):
        """Test CreateCompanyResponse structure."""
        now = datetime.now(timezone.utc)
        response = CreateCompanyResponse(
            companyId='cmp_123',
            status='pending',
            createdAt=now
        )
        assert response.company_id == 'cmp_123'
        assert response.status == 'pending'

    def test_company_list_item(self):
        """Test CompanyListItem structure."""
        now = datetime.now(timezone.utc)
        item = CompanyListItem(
            id='cmp_123',
            companyName='Acme Corp',
            websiteUrl='https://acme.com',
            status=CompanyStatus.COMPLETED,
            totalTokensUsed=5000,
            estimatedCost=0.50,
            createdAt=now,
            completedAt=now
        )
        assert item.company_name == 'Acme Corp'
        assert item.status == CompanyStatus.COMPLETED

    def test_company_detail(self):
        """Test CompanyDetail structure."""
        now = datetime.now(timezone.utc)
        detail = CompanyDetail(
            id='cmp_123',
            companyName='Acme Corp',
            websiteUrl='https://acme.com',
            industry='Technology',
            analysisMode=AnalysisMode.THOROUGH,
            status=CompanyStatus.IN_PROGRESS,
            totalTokensUsed=3000,
            estimatedCost=0.30,
            createdAt=now
        )
        assert detail.industry == 'Technology'
        assert detail.analysis_mode == AnalysisMode.THOROUGH

    def test_progress_response(self):
        """Test ProgressResponse structure."""
        response = ProgressResponse(
            companyId='cmp_123',
            status=CompanyStatus.IN_PROGRESS,
            phase=ProcessingPhase.CRAWLING,
            pagesCrawled=25,
            pagesTotal=100,
            entitiesExtracted=50,
            tokensUsed=1500,
            timeElapsed=300,
            estimatedTimeRemaining=600,
            currentActivity='Crawling https://acme.com/about'
        )
        assert response.pages_crawled == 25
        assert response.phase == ProcessingPhase.CRAWLING

    def test_pause_response(self):
        """Test PauseResponse structure."""
        now = datetime.now(timezone.utc)
        response = PauseResponse(
            status='paused',
            checkpointSaved=True,
            pausedAt=now
        )
        assert response.checkpoint_saved is True

    def test_resume_response(self):
        """Test ResumeResponse structure."""
        resumed_from = ResumeFromData(
            pagesCrawled=25,
            entitiesExtracted=50,
            phase=ProcessingPhase.CRAWLING
        )
        response = ResumeResponse(
            status='in_progress',
            resumedFrom=resumed_from
        )
        assert response.resumed_from.pages_crawled == 25

    def test_rescan_response(self):
        """Test RescanResponse structure."""
        response = RescanResponse(
            newAnalysisId='ana_456',
            versionNumber=3,
            status='pending'
        )
        assert response.new_analysis_id == 'ana_456'
        assert response.version_number == 3

    def test_delete_response(self):
        """Test DeleteResponse structure."""
        records = DeletedRecords(pages=50, entities=100, analyses=2)
        response = DeleteResponse(deleted=True, deletedRecords=records)
        assert response.deleted is True
        assert response.deleted_records.pages == 50

    def test_batch_upload_response(self):
        """Test BatchUploadResponse structure."""
        results = [
            BatchCompanyResult(companyName='Acme', companyId='cmp_1'),
            BatchCompanyResult(companyName='Bad Corp', error='Invalid URL')
        ]
        response = BatchUploadResponse(
            totalCount=2,
            successful=1,
            failed=1,
            companies=results
        )
        assert response.total_count == 2
        assert response.companies[1].error == 'Invalid URL'


class TestEntitySchemas:
    """Tests for entity-related schemas."""

    def test_entity_item(self):
        """Test EntityItem structure."""
        item = EntityItem(
            id='ent_123',
            entityType=EntityType.PERSON,
            entityValue='John Smith',
            contextSnippet='CEO and founder',
            sourceUrl='https://acme.com/team',
            confidenceScore=0.95
        )
        assert item.entity_type == EntityType.PERSON
        assert item.confidence_score == 0.95

    def test_entity_query_params_defaults(self):
        """Test EntityQueryParams defaults."""
        params = EntityQueryParams()
        assert params.type is None
        assert params.min_confidence == 0.0
        assert params.page == 1
        assert params.page_size == 50

    def test_entity_query_params_validation(self):
        """Test EntityQueryParams validation."""
        with pytest.raises(ValidationError):
            EntityQueryParams(minConfidence=1.5)  # Above 1.0

        with pytest.raises(ValidationError):
            EntityQueryParams(pageSize=150)  # Above max


class TestPageSchemas:
    """Tests for page-related schemas."""

    def test_page_item(self):
        """Test PageItem structure."""
        now = datetime.now(timezone.utc)
        item = PageItem(
            id='pag_123',
            url='https://acme.com/about',
            pageType=PageType.ABOUT,
            crawledAt=now,
            isExternal=False
        )
        assert item.page_type == PageType.ABOUT
        assert item.is_external is False

    def test_page_query_params_defaults(self):
        """Test PageQueryParams defaults."""
        params = PageQueryParams()
        assert params.page_type is None
        assert params.page == 1
        assert params.page_size == 50


class TestTokenSchemas:
    """Tests for token usage schemas."""

    def test_token_usage_item(self):
        """Test TokenUsageItem structure."""
        now = datetime.now(timezone.utc)
        item = TokenUsageItem(
            callType=ApiCallType.ANALYSIS,
            section='executive_summary',
            inputTokens=5000,
            outputTokens=1000,
            timestamp=now
        )
        assert item.call_type == ApiCallType.ANALYSIS
        assert item.input_tokens == 5000

    def test_token_usage_response(self):
        """Test TokenUsageResponse structure."""
        now = datetime.now(timezone.utc)
        usage = TokenUsageItem(
            callType=ApiCallType.EXTRACTION,
            inputTokens=3000,
            outputTokens=500,
            timestamp=now
        )
        response = TokenUsageResponse(
            totalTokens=10000,
            totalInputTokens=8000,
            totalOutputTokens=2000,
            estimatedCost=1.00,
            byApiCall=[usage]
        )
        assert response.total_tokens == 10000
        assert len(response.by_api_call) == 1


class TestVersionSchemas:
    """Tests for version-related schemas."""

    def test_version_item(self):
        """Test VersionItem structure."""
        now = datetime.now(timezone.utc)
        item = VersionItem(
            analysisId='ana_123',
            versionNumber=2,
            createdAt=now,
            tokensUsed=8000
        )
        assert item.analysis_id == 'ana_123'
        assert item.version_number == 2

    def test_version_change(self):
        """Test VersionChange structure."""
        change = VersionChange(
            field='CTO',
            previousValue='Jane Doe',
            currentValue='Bob Wilson',
            changeType='modified'
        )
        assert change.change_type == 'modified'

    def test_version_changes(self):
        """Test VersionChanges grouping."""
        change = VersionChange(
            field='CTO',
            previousValue=None,
            currentValue='Bob Wilson',
            changeType='added'
        )
        changes = VersionChanges(team=[change])
        assert len(changes.team) == 1
        assert len(changes.products) == 0

    def test_compare_versions_response(self):
        """Test CompareVersionsResponse structure."""
        changes = VersionChanges()
        response = CompareVersionsResponse(
            companyId='cmp_123',
            previousVersion=1,
            currentVersion=2,
            changes=changes,
            significantChanges=False
        )
        assert response.previous_version == 1
        assert response.current_version == 2

    def test_compare_query_params(self):
        """Test CompareQueryParams validation."""
        params = CompareQueryParams(version1=1, version2=2)
        assert params.version1 == 1

        with pytest.raises(ValidationError):
            CompareQueryParams(version1=0, version2=2)  # Below min


class TestHealthSchemas:
    """Tests for health check schemas."""

    def test_health_response(self):
        """Test HealthResponse structure."""
        response = HealthResponse(
            status='healthy',
            version='1.0.0',
            database='connected',
            redis='connected'
        )
        assert response.status == 'healthy'
        assert response.database == 'connected'

    def test_health_response_degraded(self):
        """Test HealthResponse with degraded status."""
        response = HealthResponse(
            status='degraded',
            version='1.0.0',
            database='connected',
            redis='disconnected'
        )
        assert response.status == 'degraded'
        assert response.redis == 'disconnected'


class TestCamelCaseSerialization:
    """Tests for camelCase serialization."""

    def test_company_config_camel_case_alias(self):
        """Test that CompanyConfig serializes to camelCase."""
        config = CompanyConfig(
            analysisMode=AnalysisMode.QUICK,
            timeLimitMinutes=15
        )
        data = config.model_dump(by_alias=True)
        assert 'analysisMode' in data
        assert 'timeLimitMinutes' in data
        assert 'analysis_mode' not in data

    def test_create_company_request_accepts_camel_case(self):
        """Test that request accepts camelCase input."""
        request = CreateCompanyRequest.model_validate({
            'companyName': 'Acme Corp',
            'websiteUrl': 'https://acme.com'
        })
        assert request.company_name == 'Acme Corp'

    def test_response_serialization(self):
        """Test that responses serialize with camelCase."""
        now = datetime.now(timezone.utc)
        response = CreateCompanyResponse(
            companyId='cmp_123',
            status='pending',
            createdAt=now
        )
        data = response.model_dump(by_alias=True)
        assert 'companyId' in data
        assert 'createdAt' in data
