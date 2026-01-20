"""Application configuration management."""

import os
from typing import Type


class Config:
    """Base configuration class."""

    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

    # Database - use absolute path to avoid working directory issues
    @staticmethod
    def _get_db_path(db_name: str = 'cira.db') -> str:
        """Get absolute database path."""
        db_url = os.environ.get('DATABASE_URL')
        if db_url:
            return db_url
        # Default to instance folder for Flask apps
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        instance_path = os.path.join(backend_dir, 'instance')
        os.makedirs(instance_path, exist_ok=True)
        return f'sqlite:///{os.path.join(instance_path, db_name)}'
    
    SQLALCHEMY_DATABASE_URI = _get_db_path('cira.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # SQLAlchemy Connection Options
    # For SQLite: Use NullPool and configure for concurrent access
    # For PostgreSQL/Supabase: Use connection pooling
    @staticmethod
    def _get_engine_options() -> dict:
        """Get SQLAlchemy engine options based on database type."""
        db_url = os.environ.get('DATABASE_URL', '')
        
        if db_url.startswith('postgresql'):
            # PostgreSQL connection pooling
            return {
                'pool_size': int(os.environ.get('DB_POOL_SIZE', '10')),
                'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '3600')),
                'pool_pre_ping': True,
                'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', '30')),
                'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '20')),
            }
        else:
            # SQLite: Use StaticPool and WAL mode for concurrent access
            from sqlalchemy.pool import StaticPool
            return {
                'connect_args': {
                    'timeout': 30,  # Wait up to 30s for locks
                    'check_same_thread': False,  # Allow multi-threaded access
                },
                'poolclass': StaticPool,  # Single connection pool for SQLite
            }
    
    SQLALCHEMY_ENGINE_OPTIONS = _get_engine_options()

    # Redis
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # Celery
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/1')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

    # CORS
    CORS_ORIGINS = os.environ.get('FRONTEND_URL', 'http://localhost:5173').split(',')

    # Anthropic
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY', '')

    # Crawl defaults
    CRAWL_DEFAULT_MAX_PAGES = int(os.environ.get('CRAWL_DEFAULT_MAX_PAGES', '100'))
    CRAWL_DEFAULT_MAX_DEPTH = int(os.environ.get('CRAWL_DEFAULT_MAX_DEPTH', '3'))
    CRAWL_DEFAULT_TIME_LIMIT_MINUTES = int(os.environ.get('CRAWL_DEFAULT_TIME_LIMIT_MINUTES', '30'))
    CRAWL_DEFAULT_RATE_LIMIT = float(os.environ.get('CRAWL_DEFAULT_RATE_LIMIT', '1'))

    # Analysis defaults
    ANALYSIS_DEFAULT_MODE = os.environ.get('ANALYSIS_DEFAULT_MODE', 'thorough')
    ANALYSIS_MAX_RETRIES = int(os.environ.get('ANALYSIS_MAX_RETRIES', '3'))
    ANALYSIS_TIMEOUT_SECONDS = int(os.environ.get('ANALYSIS_TIMEOUT_SECONDS', '60'))

    # Token pricing (per 1M tokens)
    CLAUDE_INPUT_TOKEN_PRICE = float(os.environ.get('CLAUDE_INPUT_TOKEN_PRICE', '3.00'))
    CLAUDE_OUTPUT_TOKEN_PRICE = float(os.environ.get('CLAUDE_OUTPUT_TOKEN_PRICE', '15.00'))

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True
    # Use same database as base config for consistency
    # In development, we'll use cira.db to match production behavior
    SQLALCHEMY_DATABASE_URI = Config._get_db_path('cira.db')


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

    # Use NullPool for SQLite in-memory testing (SQLite doesn't support multi-connection pooling)
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
    }


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False

    @classmethod
    def init_app(cls, app):
        """Production-specific initialization."""
        # Ensure required environment variables are set
        required_vars = ['SECRET_KEY', 'ANTHROPIC_API_KEY']
        missing = [var for var in required_vars if not os.environ.get(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


# Configuration mapping
config_map: dict[str, Type[Config]] = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: str | None = None) -> Config:
    """
    Get configuration instance based on environment.

    Args:
        config_name: Configuration name or None to use FLASK_ENV

    Returns:
        Configuration instance
    """
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    config_class = config_map.get(config_name, DevelopmentConfig)
    return config_class()
