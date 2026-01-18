"""Batch queue management API routes."""

from flask import request

from app.api import api_bp
from app.api.routes.companies import make_error_response, make_success_response
from app.services.batch_queue_service import batch_queue_service
from app.models.enums import BatchStatus, CompanyStatus


@api_bp.route('/batches', methods=['POST'])
def create_batch():
    """
    Create a new batch job from existing companies.

    Request body:
    {
        "companyIds": ["uuid1", "uuid2", ...],
        "name": "Optional batch name",
        "description": "Optional description",
        "config": {...},  // Optional shared config
        "priority": 100,  // Optional (lower = higher priority)
        "maxConcurrent": 3,  // Optional concurrent limit
        "startImmediately": true  // Optional (default: true)
    }

    Returns:
        201: Batch created successfully
        400: Validation error
    """
    data = request.get_json()

    if not data:
        return make_error_response(
            'VALIDATION_ERROR',
            'Request body is required'
        )

    company_ids = data.get('companyIds', [])
    if not company_ids or not isinstance(company_ids, list):
        return make_error_response(
            'VALIDATION_ERROR',
            'companyIds is required and must be a non-empty array'
        )

    result = batch_queue_service.create_batch(
        company_ids=company_ids,
        name=data.get('name'),
        description=data.get('description'),
        config=data.get('config'),
        priority=data.get('priority', 100),
        max_concurrent=data.get('maxConcurrent'),
        start_immediately=data.get('startImmediately', True),
    )

    if result.get('success'):
        return make_success_response(result, status=201)
    else:
        return make_error_response(
            'BATCH_CREATE_ERROR',
            result.get('error', 'Failed to create batch')
        )


@api_bp.route('/batches', methods=['GET'])
def list_batches():
    """
    List all batches with optional filtering.

    Query params:
    - status: Filter by status (pending, processing, completed, cancelled, paused)
    - limit: Max results (default: 100)
    - offset: Pagination offset (default: 0)

    Returns:
        200: List of batches
    """
    status_param = request.args.get('status')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    status = None
    if status_param:
        try:
            status = BatchStatus(status_param)
        except ValueError:
            return make_error_response(
                'VALIDATION_ERROR',
                f'Invalid status: {status_param}'
            )

    result = batch_queue_service.list_batches(
        status=status,
        limit=limit,
        offset=offset,
    )

    return make_success_response(result)


@api_bp.route('/batches/<batch_id>', methods=['GET'])
def get_batch(batch_id: str):
    """
    Get a specific batch by ID.

    Returns:
        200: Batch details
        404: Batch not found
    """
    batch = batch_queue_service.get_batch(batch_id)

    if not batch:
        return make_error_response(
            'NOT_FOUND',
            f'Batch {batch_id} not found',
            status=404
        )

    return make_success_response(batch)


@api_bp.route('/batches/<batch_id>/progress', methods=['GET'])
def get_batch_progress(batch_id: str):
    """
    Get batch progress for polling.

    Returns real-time progress information from Redis (with DB fallback).

    Returns:
        200: Batch progress
        404: Batch not found
    """
    progress = batch_queue_service.get_batch_progress(batch_id)

    if not progress:
        return make_error_response(
            'NOT_FOUND',
            f'Batch {batch_id} not found',
            status=404
        )

    return make_success_response(progress)


@api_bp.route('/batches/<batch_id>/companies', methods=['GET'])
def get_batch_companies(batch_id: str):
    """
    Get companies in a batch.

    Query params:
    - status: Filter by status (pending, in_progress, completed, failed, paused)
    - limit: Max results (default: 100)
    - offset: Pagination offset (default: 0)

    Returns:
        200: List of companies
        404: Batch not found
    """
    # Verify batch exists
    batch = batch_queue_service.get_batch(batch_id)
    if not batch:
        return make_error_response(
            'NOT_FOUND',
            f'Batch {batch_id} not found',
            status=404
        )

    status_param = request.args.get('status')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    status = None
    if status_param:
        try:
            status = CompanyStatus(status_param)
        except ValueError:
            return make_error_response(
                'VALIDATION_ERROR',
                f'Invalid status: {status_param}'
            )

    result = batch_queue_service.get_batch_companies(
        batch_id=batch_id,
        status=status,
        limit=limit,
        offset=offset,
    )

    return make_success_response(result)


@api_bp.route('/batches/<batch_id>/start', methods=['POST'])
def start_batch(batch_id: str):
    """
    Start processing a batch.

    Returns:
        200: Batch started
        404: Batch not found
        422: Cannot start batch (invalid state)
    """
    result = batch_queue_service.start_batch(batch_id)

    if result.get('success'):
        return make_success_response(result)
    elif 'not found' in result.get('error', '').lower():
        return make_error_response(
            'NOT_FOUND',
            result['error'],
            status=404
        )
    else:
        return make_error_response(
            'INVALID_STATE',
            result.get('error', 'Cannot start batch'),
            status=422
        )


@api_bp.route('/batches/<batch_id>/pause', methods=['POST'])
def pause_batch(batch_id: str):
    """
    Pause a batch and all its in-progress companies.

    Returns:
        200: Batch paused
        404: Batch not found
        422: Cannot pause batch (invalid state)
    """
    result = batch_queue_service.pause_batch(batch_id)

    if result.get('success'):
        return make_success_response(result)
    elif 'not found' in result.get('error', '').lower():
        return make_error_response(
            'NOT_FOUND',
            result['error'],
            status=404
        )
    else:
        return make_error_response(
            'INVALID_STATE',
            result.get('error', 'Cannot pause batch'),
            status=422
        )


@api_bp.route('/batches/<batch_id>/resume', methods=['POST'])
def resume_batch(batch_id: str):
    """
    Resume a paused batch.

    Returns:
        200: Batch resumed
        404: Batch not found
        422: Cannot resume batch (invalid state)
    """
    result = batch_queue_service.resume_batch(batch_id)

    if result.get('success'):
        return make_success_response(result)
    elif 'not found' in result.get('error', '').lower():
        return make_error_response(
            'NOT_FOUND',
            result['error'],
            status=404
        )
    else:
        return make_error_response(
            'INVALID_STATE',
            result.get('error', 'Cannot resume batch'),
            status=422
        )


@api_bp.route('/batches/<batch_id>/cancel', methods=['POST'])
def cancel_batch(batch_id: str):
    """
    Cancel a batch and all its pending/in-progress companies.

    Returns:
        200: Batch cancelled
        404: Batch not found
        422: Cannot cancel batch (invalid state)
    """
    result = batch_queue_service.cancel_batch(batch_id)

    if result.get('success'):
        return make_success_response(result)
    elif 'not found' in result.get('error', '').lower():
        return make_error_response(
            'NOT_FOUND',
            result['error'],
            status=404
        )
    else:
        return make_error_response(
            'INVALID_STATE',
            result.get('error', 'Cannot cancel batch'),
            status=422
        )


@api_bp.route('/batches/schedule', methods=['POST'])
def schedule_batches():
    """
    Trigger fair scheduling across all active batches.

    This endpoint can be called periodically or by a Celery beat task
    to ensure companies are being scheduled fairly.

    Returns:
        200: Scheduling result with count of companies scheduled
    """
    scheduled = batch_queue_service.schedule_next_from_all_batches()
    return make_success_response({
        'success': True,
        'companies_scheduled': scheduled,
    })
