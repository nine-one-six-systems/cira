"""Tests for application factory."""

import pytest
from app import create_app


def test_app_creates_without_errors():
    """Test that app creates without errors."""
    app = create_app('testing')
    assert app is not None


def test_app_has_testing_config():
    """Test that testing app has correct config."""
    app = create_app('testing')
    assert app.config['TESTING'] is True


def test_app_registers_api_blueprint():
    """Test that app registers API blueprint."""
    app = create_app('testing')
    assert 'api' in app.blueprints


def test_app_health_endpoint_accessible():
    """Test that health endpoint is accessible."""
    app = create_app('testing')
    with app.test_client() as client:
        response = client.get('/api/v1/health')
        assert response.status_code == 200
