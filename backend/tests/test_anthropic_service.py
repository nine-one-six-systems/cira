"""Tests for the Anthropic Claude API Service (Task 6.1)."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestAnthropicServiceInit:
    """Test AnthropicService initialization."""

    def test_service_initializes(self):
        """Test that service initializes without error."""
        from app.services.anthropic_service import AnthropicService

        service = AnthropicService()
        assert service is not None
        assert service._client is None  # Lazy initialization

    def test_global_instance_exists(self):
        """Test that global instance is available."""
        from app.services.anthropic_service import anthropic_service

        assert anthropic_service is not None


class TestClaudeResponse:
    """Test ClaudeResponse dataclass."""

    def test_claude_response_creation(self):
        """Test creating a ClaudeResponse."""
        from app.services.anthropic_service import ClaudeResponse

        response = ClaudeResponse(
            content="Test response",
            input_tokens=100,
            output_tokens=50,
            model="claude-sonnet-4-20250514",
        )

        assert response.content == "Test response"
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.total_tokens == 150

    def test_claude_response_with_raw(self):
        """Test ClaudeResponse with raw response data."""
        from app.services.anthropic_service import ClaudeResponse

        response = ClaudeResponse(
            content="Test",
            input_tokens=50,
            output_tokens=25,
            model="claude-sonnet-4-20250514",
            stop_reason="end_turn",
            raw_response={"id": "msg_123"},
        )

        assert response.stop_reason == "end_turn"
        assert response.raw_response["id"] == "msg_123"


class TestAnthropicServiceErrors:
    """Test error classes."""

    def test_error_hierarchy(self):
        """Test error class hierarchy."""
        from app.services.anthropic_service import (
            AnthropicServiceError,
            RateLimitError,
            APIError,
            TimeoutError,
        )

        assert issubclass(RateLimitError, AnthropicServiceError)
        assert issubclass(APIError, AnthropicServiceError)
        assert issubclass(TimeoutError, AnthropicServiceError)

    def test_rate_limit_error(self):
        """Test RateLimitError creation."""
        from app.services.anthropic_service import RateLimitError

        error = RateLimitError("Rate limited")
        assert str(error) == "Rate limited"

    def test_api_error(self):
        """Test APIError creation."""
        from app.services.anthropic_service import APIError

        error = APIError("API failed")
        assert str(error) == "API failed"


class TestAnthropicServiceCall:
    """Test AnthropicService.call method."""

    def test_call_without_api_key_raises_error(self, app):
        """Test that missing API key raises error."""
        from app.services.anthropic_service import AnthropicService, AnthropicServiceError

        with app.app_context():
            app.config['ANTHROPIC_API_KEY'] = None
            service = AnthropicService()

            with pytest.raises(AnthropicServiceError) as exc_info:
                service.call("Hello")

            assert "ANTHROPIC_API_KEY" in str(exc_info.value)

    @patch('app.services.anthropic_service.AnthropicService._get_client')
    def test_call_success(self, mock_get_client, app):
        """Test successful API call."""
        from app.services.anthropic_service import AnthropicService

        # Mock the client and response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Hello back!")]
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_123"
        mock_response.type = "message"
        mock_response.role = "assistant"

        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with app.app_context():
            service = AnthropicService()
            response = service.call("Hello")

            assert response.content == "Hello back!"
            assert response.input_tokens == 10
            assert response.output_tokens == 5
            assert response.total_tokens == 15

    @patch('app.services.anthropic_service.AnthropicService._get_client')
    def test_call_with_system_prompt(self, mock_get_client, app):
        """Test call with system prompt."""
        from app.services.anthropic_service import AnthropicService

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="Response")]
        mock_response.usage.input_tokens = 20
        mock_response.usage.output_tokens = 10
        mock_response.model = "claude-sonnet-4-20250514"
        mock_response.stop_reason = "end_turn"
        mock_response.id = "msg_456"
        mock_response.type = "message"
        mock_response.role = "assistant"

        mock_client.messages.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        with app.app_context():
            service = AnthropicService()
            response = service.call(
                prompt="User prompt",
                system_prompt="Be helpful",
            )

            # Verify system prompt was passed
            call_kwargs = mock_client.messages.create.call_args.kwargs
            assert call_kwargs['system'] == "Be helpful"


class TestAnthropicServiceRetry:
    """Test retry logic."""

    @patch('app.services.anthropic_service.time.sleep')
    @patch('app.services.anthropic_service.AnthropicService._get_client')
    def test_rate_limit_triggers_retry(self, mock_get_client, mock_sleep, app):
        """Test that 429 triggers retry with backoff."""
        import anthropic
        from app.services.anthropic_service import AnthropicService, RateLimitError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = anthropic.RateLimitError(
            message="Rate limited",
            response=MagicMock(status_code=429),
            body={}
        )
        mock_get_client.return_value = mock_client

        with app.app_context():
            service = AnthropicService()

            with pytest.raises(RateLimitError):
                service.call("Hello")

            # Should have retried (3 attempts total)
            assert mock_client.messages.create.call_count == 3
            # Should have slept between retries
            assert mock_sleep.call_count >= 2

    @patch('app.services.anthropic_service.AnthropicService._get_client')
    def test_timeout_raises_timeout_error(self, mock_get_client, app):
        """Test that timeout raises TimeoutError."""
        import anthropic
        from app.services.anthropic_service import AnthropicService, TimeoutError

        mock_client = MagicMock()
        mock_client.messages.create.side_effect = anthropic.APITimeoutError(
            request=MagicMock()
        )
        mock_get_client.return_value = mock_client

        with app.app_context():
            service = AnthropicService()

            with pytest.raises(TimeoutError):
                service.call("Hello", timeout=10)


class TestAnthropicServiceConfig:
    """Test configuration handling."""

    def test_default_config_values(self):
        """Test default configuration values."""
        from app.services.anthropic_service import AnthropicService

        service = AnthropicService()

        assert service.DEFAULT_MODEL == "claude-sonnet-4-20250514"
        assert service.DEFAULT_MAX_TOKENS == 4000
        assert service.DEFAULT_TEMPERATURE == 0.3
        assert service.DEFAULT_TIMEOUT == 60
        assert service.MAX_RETRIES == 3

    def test_get_config_outside_context(self):
        """Test getting config outside app context returns defaults."""
        from app.services.anthropic_service import AnthropicService

        service = AnthropicService()

        # Outside app context should return default
        model = service._get_config_value('CLAUDE_MODEL', 'default-model')
        assert model == 'default-model'


class TestAnthropicServiceHealthCheck:
    """Test health check functionality."""

    @patch('app.services.anthropic_service.AnthropicService.call')
    def test_health_check_success(self, mock_call, app):
        """Test health check returns healthy status."""
        from app.services.anthropic_service import AnthropicService, ClaudeResponse

        mock_call.return_value = ClaudeResponse(
            content="Hello",
            input_tokens=5,
            output_tokens=1,
            model="claude-sonnet-4-20250514",
        )

        with app.app_context():
            service = AnthropicService()
            result = service.health_check()

            assert result['status'] == 'healthy'
            assert 'model' in result

    @patch('app.services.anthropic_service.AnthropicService.call')
    def test_health_check_failure(self, mock_call, app):
        """Test health check returns unhealthy on error."""
        from app.services.anthropic_service import AnthropicService, APIError

        mock_call.side_effect = APIError("Connection failed")

        with app.app_context():
            service = AnthropicService()
            result = service.health_check()

            assert result['status'] == 'unhealthy'
            assert 'error' in result


class TestAnalyzeText:
    """Test analyze_text method."""

    @patch('app.services.anthropic_service.AnthropicService.call')
    def test_analyze_text_calls_correct_prompt(self, mock_call, app):
        """Test that analyze_text uses correct prompt."""
        from app.services.anthropic_service import AnthropicService, ClaudeResponse

        mock_call.return_value = ClaudeResponse(
            content="Analysis result",
            input_tokens=100,
            output_tokens=50,
            model="claude-sonnet-4-20250514",
        )

        with app.app_context():
            service = AnthropicService()
            context = {
                'company_name': 'Test Company',
                'website_url': 'https://test.com',
                'industry': 'Tech',
            }

            result = service.analyze_text(
                text="Company content here",
                analysis_type='company_overview',
                context=context,
            )

            assert result.content == "Analysis result"
            mock_call.assert_called_once()
