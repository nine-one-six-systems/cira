"""Tests for health check endpoint."""

import pytest


def test_health_endpoint_returns_200(client):
    """Test that health endpoint returns 200 OK."""
    response = client.get('/api/v1/health')
    assert response.status_code == 200


def test_health_endpoint_returns_healthy_status(client):
    """Test that health endpoint returns healthy status."""
    response = client.get('/api/v1/health')
    data = response.get_json()

    assert data['success'] is True
    assert 'data' in data
    assert data['data']['status'] in ['healthy', 'degraded']


def test_health_endpoint_returns_version(client):
    """Test that health endpoint returns version."""
    response = client.get('/api/v1/health')
    data = response.get_json()

    assert 'version' in data['data']
    assert data['data']['version'] == '1.0.0'


def test_health_endpoint_returns_database_status(client):
    """Test that health endpoint returns database status."""
    response = client.get('/api/v1/health')
    data = response.get_json()

    assert 'database' in data['data']
    assert data['data']['database'] == 'connected'


def test_health_endpoint_returns_redis_status(client):
    """Test that health endpoint returns redis status."""
    response = client.get('/api/v1/health')
    data = response.get_json()

    assert 'redis' in data['data']
    # Redis may or may not be connected in test environment
    assert data['data']['redis'] in ['connected', 'disconnected']
