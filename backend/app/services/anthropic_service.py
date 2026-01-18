"""Anthropic Claude API Client Service.

Task 6.1: Anthropic Claude API Client
- API key from ANTHROPIC_API_KEY env
- Exponential backoff on 429
- Max 3 retries
- Timeout handling
- Response parsing with token counts
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from flask import current_app

logger = logging.getLogger(__name__)


@dataclass
class ClaudeResponse:
    """Response from Claude API call."""
    content: str
    input_tokens: int
    output_tokens: int
    model: str
    stop_reason: str | None = None
    raw_response: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        """Total tokens used in this call."""
        return self.input_tokens + self.output_tokens


class AnthropicServiceError(Exception):
    """Base exception for Anthropic service errors."""
    pass


class RateLimitError(AnthropicServiceError):
    """Rate limit exceeded (429)."""
    pass


class APIError(AnthropicServiceError):
    """General API error."""
    pass


class TimeoutError(AnthropicServiceError):
    """Request timeout."""
    pass


class AnthropicService:
    """
    Claude API client with error handling and retry logic.

    Features:
    - Exponential backoff on rate limits (429)
    - Configurable max retries (default 3)
    - Timeout handling
    - Token usage tracking
    """

    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    DEFAULT_MAX_TOKENS = 4000
    DEFAULT_TEMPERATURE = 0.3
    DEFAULT_TIMEOUT = 60
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 1.0  # seconds

    def __init__(self):
        """Initialize the Anthropic service."""
        self._client = None

    def _get_client(self):
        """Get or create the Anthropic client (lazy initialization)."""
        if self._client is None:
            try:
                import anthropic
            except ImportError:
                logger.error("anthropic package not installed")
                raise AnthropicServiceError(
                    "anthropic package is required. Install with: pip install anthropic"
                )

            api_key = current_app.config.get('ANTHROPIC_API_KEY')
            if not api_key:
                logger.error("ANTHROPIC_API_KEY not configured")
                raise AnthropicServiceError(
                    "ANTHROPIC_API_KEY environment variable not set"
                )

            self._client = anthropic.Anthropic(api_key=api_key)

        return self._client

    def _get_config_value(self, key: str, default: Any) -> Any:
        """Get config value with fallback to default."""
        try:
            return current_app.config.get(key, default)
        except RuntimeError:
            # Outside of app context
            return default

    def call(
        self,
        prompt: str,
        system_prompt: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        timeout: int | None = None,
    ) -> ClaudeResponse:
        """
        Make a call to Claude API with retry logic.

        Args:
            prompt: The user prompt/message
            system_prompt: Optional system prompt for context
            model: Model to use (default: claude-sonnet-4-20250514)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)
            timeout: Request timeout in seconds

        Returns:
            ClaudeResponse with content and token usage

        Raises:
            RateLimitError: If rate limited after all retries
            APIError: For other API errors
            TimeoutError: If request times out
        """
        # Get configuration values
        model = model or self._get_config_value('CLAUDE_MODEL', self.DEFAULT_MODEL)
        max_tokens = max_tokens or self._get_config_value(
            'ANALYSIS_MAX_TOKENS', self.DEFAULT_MAX_TOKENS
        )
        temperature = temperature if temperature is not None else self._get_config_value(
            'ANALYSIS_TEMPERATURE', self.DEFAULT_TEMPERATURE
        )
        timeout = timeout or self._get_config_value(
            'ANALYSIS_TIMEOUT_SECONDS', self.DEFAULT_TIMEOUT
        )
        max_retries = self._get_config_value('ANALYSIS_MAX_RETRIES', self.MAX_RETRIES)

        client = self._get_client()

        # Build messages
        messages = [{"role": "user", "content": prompt}]

        # Retry loop with exponential backoff
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.debug(
                    f"Claude API call attempt {attempt + 1}/{max_retries}, "
                    f"model={model}, max_tokens={max_tokens}"
                )

                # Make the API call
                response = client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt or "",
                    messages=messages,
                    timeout=timeout,
                )

                # Parse response
                content = ""
                for block in response.content:
                    if block.type == "text":
                        content += block.text

                result = ClaudeResponse(
                    content=content,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    model=response.model,
                    stop_reason=response.stop_reason,
                    raw_response={
                        "id": response.id,
                        "type": response.type,
                        "role": response.role,
                    }
                )

                logger.info(
                    f"Claude API call successful: {result.total_tokens} tokens "
                    f"({result.input_tokens} in, {result.output_tokens} out)"
                )

                return result

            except Exception as e:
                import anthropic

                last_error = e
                error_type = type(e).__name__

                # Handle rate limiting with exponential backoff
                if isinstance(e, anthropic.RateLimitError):
                    if attempt < max_retries - 1:
                        delay = self.BASE_RETRY_DELAY * (2 ** attempt)
                        logger.warning(
                            f"Rate limited (429), retrying in {delay:.1f}s "
                            f"(attempt {attempt + 1}/{max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    else:
                        logger.error("Rate limit exceeded after all retries")
                        raise RateLimitError("Rate limit exceeded") from e

                # Handle timeout
                elif isinstance(e, anthropic.APITimeoutError):
                    logger.error(f"Request timed out after {timeout}s")
                    raise TimeoutError(f"Request timed out after {timeout}s") from e

                # Handle other API errors
                elif isinstance(e, anthropic.APIStatusError):
                    logger.error(f"API error: {error_type} - {str(e)}")
                    if attempt < max_retries - 1:
                        delay = self.BASE_RETRY_DELAY * (2 ** attempt)
                        logger.warning(f"Retrying in {delay:.1f}s")
                        time.sleep(delay)
                        continue
                    raise APIError(f"API error: {str(e)}") from e

                # Handle connection errors
                elif isinstance(e, anthropic.APIConnectionError):
                    logger.error(f"Connection error: {str(e)}")
                    if attempt < max_retries - 1:
                        delay = self.BASE_RETRY_DELAY * (2 ** attempt)
                        logger.warning(f"Retrying in {delay:.1f}s")
                        time.sleep(delay)
                        continue
                    raise APIError(f"Connection error: {str(e)}") from e

                # Other unexpected errors
                else:
                    logger.error(f"Unexpected error: {error_type} - {str(e)}")
                    raise AnthropicServiceError(f"Unexpected error: {str(e)}") from e

        # Should not reach here, but just in case
        raise AnthropicServiceError(f"All retries failed: {last_error}")

    def analyze_text(
        self,
        text: str,
        analysis_type: str,
        context: dict[str, Any] | None = None,
    ) -> ClaudeResponse:
        """
        Analyze text using Claude with a specific analysis prompt.

        Args:
            text: Text to analyze
            analysis_type: Type of analysis (e.g., 'summary', 'entities', 'sentiment')
            context: Additional context for the analysis

        Returns:
            ClaudeResponse with analysis results
        """
        from app.analysis.prompts import get_analysis_prompt

        prompt, system_prompt = get_analysis_prompt(analysis_type, text, context)
        return self.call(prompt, system_prompt=system_prompt)

    def health_check(self) -> dict[str, Any]:
        """
        Check if the Anthropic API is accessible.

        Returns:
            Dict with status and any error message
        """
        try:
            # Make a minimal API call
            response = self.call(
                prompt="Hello",
                max_tokens=10,
                timeout=10,
            )
            return {
                "status": "healthy",
                "model": response.model,
                "tokens_used": response.total_tokens,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# Global service instance (lazy initialized)
anthropic_service = AnthropicService()
