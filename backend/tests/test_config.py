"""Tests for configuration loading."""

import os
import pytest
from app.config import Config, DevelopmentConfig, TestingConfig, ProductionConfig, get_config


def test_development_config():
    """Test development configuration."""
    config = DevelopmentConfig()
    assert config.DEBUG is True


def test_testing_config():
    """Test testing configuration."""
    config = TestingConfig()
    assert config.TESTING is True
    assert config.SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:'


def test_production_config():
    """Test production configuration."""
    config = ProductionConfig()
    assert config.DEBUG is False


def test_get_config_default():
    """Test get_config returns development by default."""
    # Clear FLASK_ENV to test default behavior
    old_env = os.environ.pop('FLASK_ENV', None)
    try:
        config = get_config()
        assert isinstance(config, DevelopmentConfig)
    finally:
        if old_env:
            os.environ['FLASK_ENV'] = old_env


def test_get_config_testing():
    """Test get_config returns testing config."""
    config = get_config('testing')
    assert isinstance(config, TestingConfig)


def test_config_loads_environment_variables(monkeypatch):
    """Test that config loads from environment variables."""
    # Since class attributes are set at import time, we test by checking
    # that the config can read from os.environ when accessed dynamically
    import importlib
    import app.config as config_module

    monkeypatch.setenv('LOG_LEVEL', 'DEBUG')
    # Reload the module to pick up the new environment variable
    importlib.reload(config_module)

    config = config_module.Config()
    assert config.LOG_LEVEL == 'DEBUG'

    # Clean up by reloading with original value
    monkeypatch.setenv('LOG_LEVEL', 'INFO')
    importlib.reload(config_module)
