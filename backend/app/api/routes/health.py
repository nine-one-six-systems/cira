"""Health check endpoint."""

from flask import jsonify, current_app
from app.api import api_bp
from app import db


@api_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.

    Returns service health status including database and Redis connectivity.

    Returns:
        JSON response with health status
    """
    health_status = {
        'status': 'healthy',
        'version': '1.0.0',
        'database': 'unknown',
        'redis': 'unknown'
    }

    # Check database connection
    try:
        db.session.execute(db.text('SELECT 1'))
        health_status['database'] = 'connected'
    except Exception as e:
        current_app.logger.error(f'Database health check failed: {e}')
        health_status['database'] = 'disconnected'
        health_status['status'] = 'degraded'

    # Check Redis connection
    try:
        import redis
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        r = redis.from_url(redis_url)
        r.ping()
        health_status['redis'] = 'connected'
    except Exception as e:
        current_app.logger.warning(f'Redis health check failed: {e}')
        health_status['redis'] = 'disconnected'
        # Redis being down doesn't make the service unhealthy for basic operations
        if health_status['status'] == 'healthy':
            health_status['status'] = 'degraded'

    return jsonify({
        'success': True,
        'data': health_status
    }), 200
