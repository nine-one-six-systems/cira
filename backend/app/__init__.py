"""CIRA Backend Application Package."""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS

from app.config import Config, get_config
from app.services.redis_service import redis_service

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_name: str | None = None) -> Flask:
    """
    Application factory for creating Flask app instances.

    Args:
        config_name: Configuration environment name ('development', 'testing', 'production')
                    If None, uses FLASK_ENV environment variable.

    Returns:
        Configured Flask application instance.
    """
    app = Flask(__name__)

    # Load configuration
    config = get_config(config_name)
    app.config.from_object(config)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)

    # Configure CORS
    CORS(app, origins=app.config.get('CORS_ORIGINS', ['http://localhost:5173']))

    # Initialize Redis service
    redis_service.init_app(app)

    # Initialize Celery
    from app.workers.celery_app import init_celery
    init_celery(app)

    # Import models to register them with SQLAlchemy
    from app import models  # noqa: F401

    # Register blueprints
    from app.api import api_bp
    app.register_blueprint(api_bp, url_prefix='/api/v1')

    # Configure logging
    configure_logging(app)

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    return app


def configure_logging(app: Flask) -> None:
    """Configure application logging."""
    import logging
    from logging.handlers import RotatingFileHandler
    import os

    log_level = app.config.get('LOG_LEVEL', 'INFO')

    # Set up basic logging
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Add file handler in production
    if not app.debug:
        if not os.path.exists('logs'):
            os.mkdir('logs')

        file_handler = RotatingFileHandler(
            'logs/cira.log',
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

    app.logger.setLevel(getattr(logging, log_level))
    app.logger.info('CIRA application startup')
