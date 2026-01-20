"""CIRA Backend Application Package."""

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from sqlalchemy import event

from app.config import Config, get_config
from app.services.redis_service import redis_service
from app.middleware.security import init_security_middleware

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()


def _set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable WAL mode and other optimizations for SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30 second timeout
    cursor.execute("PRAGMA synchronous=NORMAL")  # Faster writes, still safe with WAL
    cursor.close()


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

    # Enable SQLite WAL mode for better concurrent access
    if 'sqlite' in app.config.get('SQLALCHEMY_DATABASE_URI', ''):
        with app.app_context():
            event.listen(db.engine, 'connect', _set_sqlite_pragma)

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

    # Initialize security middleware (NFR-SEC-005: Secure headers)
    init_security_middleware(app)

    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()

    # Register startup tasks for job recovery
    # This runs after the first request in production, or can be triggered explicitly
    _register_startup_tasks(app)

    return app


def _register_startup_tasks(app: Flask) -> None:
    """
    Register tasks to run on application startup.

    Includes:
    - Automatic recovery of in_progress jobs (FR-STA-005)
    """
    import os
    import threading

    # Skip recovery in testing mode to avoid side effects
    if app.config.get('TESTING', False):
        return

    # Skip recovery if explicitly disabled
    if os.environ.get('SKIP_JOB_RECOVERY', '').lower() == 'true':
        app.logger.info('Job recovery skipped (SKIP_JOB_RECOVERY=true)')
        return

    def recover_jobs_async():
        """Recover jobs asynchronously in background thread."""
        with app.app_context():
            try:
                from app.services.job_service import job_service
                recovered = job_service.recover_in_progress_jobs()
                if recovered:
                    app.logger.info(
                        f'Recovered {len(recovered)} in-progress jobs on startup: {recovered}'
                    )
                else:
                    app.logger.info('No in-progress jobs to recover on startup')
            except Exception as e:
                app.logger.error(f'Error recovering jobs on startup: {e}')

    @app.before_request
    def trigger_recovery_once():
        """Trigger job recovery on first request, but don't block."""
        # Use a flag to ensure this only runs once
        if not hasattr(app, '_jobs_recovery_triggered'):
            app._jobs_recovery_triggered = True
            # Run recovery in background thread to avoid blocking requests
            thread = threading.Thread(target=recover_jobs_async, daemon=True)
            thread.start()
            app.logger.info('Job recovery started in background thread')


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
