"""Health check endpoint."""

from flask import jsonify, current_app
from app.api import api_bp
from app import db
from app.services import redis_service


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

    # Check Redis connection using the service
    redis_health = redis_service.health_check()
    if redis_health['connected']:
        health_status['redis'] = 'connected'
        if redis_health.get('latency_ms'):
            health_status['redis_latency_ms'] = redis_health['latency_ms']
    else:
        current_app.logger.warning(
            f'Redis health check failed: {redis_health.get("error", "unknown")}'
        )
        health_status['redis'] = 'disconnected'
        # Redis being down doesn't make the service unhealthy for basic operations
        if health_status['status'] == 'healthy':
            health_status['status'] = 'degraded'

    return jsonify({
        'success': True,
        'data': health_status
    }), 200
