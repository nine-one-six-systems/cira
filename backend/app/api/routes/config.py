"""Configuration API routes."""

from flask import current_app

from app.api import api_bp
from app.api.routes.companies import make_success_response
from app.models.enums import AnalysisMode
from app.schemas import AppConfigResponse, DefaultConfig, ModeConfig


@api_bp.route('/config', methods=['GET'])
def get_config():
    """Get application configuration."""
    # Default configuration values
    defaults = DefaultConfig(
        analysisMode=AnalysisMode.THOROUGH,
        timeLimitMinutes=30,
        maxPages=100,
        maxDepth=3
    )

    # Quick mode configuration
    quick_mode = ModeConfig(
        maxPages=50,
        maxDepth=2,
        followExternal=False
    )

    # Thorough mode configuration
    thorough_mode = ModeConfig(
        maxPages=200,
        maxDepth=4,
        followExternal=True
    )

    response = AppConfigResponse(
        defaults=defaults,
        quickMode=quick_mode,
        thoroughMode=thorough_mode
    )

    return make_success_response(response.model_dump(by_alias=True, mode='json'))
