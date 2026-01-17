"""Tests for database migrations."""

import pytest
from flask import Flask
from app import create_app, db


class TestMigrations:
    """Tests for database migration infrastructure."""

    def test_db_upgrade_creates_tables(self, app):
        """Test that database tables are created."""
        with app.app_context():
            # Check that all expected tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            expected_tables = [
                'companies',
                'crawl_sessions',
                'pages',
                'entities',
                'analyses',
                'token_usages'
            ]

            for table in expected_tables:
                assert table in tables, f"Table {table} not found"

    def test_companies_table_has_expected_columns(self, app):
        """Test that companies table has expected columns."""
        with app.app_context():
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('companies')]

            expected_columns = [
                'id',
                'company_name',
                'website_url',
                'industry',
                'analysis_mode',
                'config',
                'status',
                'processing_phase',
                'total_tokens_used',
                'estimated_cost',
                'created_at',
                'updated_at',
                'started_at',
                'completed_at',
                'paused_at',
                'total_paused_duration_ms'
            ]

            for column in expected_columns:
                assert column in columns, f"Column {column} not found in companies"

    def test_companies_table_has_indexes(self, app):
        """Test that companies table has expected indexes."""
        with app.app_context():
            inspector = db.inspect(db.engine)
            indexes = inspector.get_indexes('companies')
            index_names = [idx['name'] for idx in indexes]

            # Check for composite index
            assert any('status' in str(idx.get('column_names', [])) for idx in indexes)

    def test_pages_table_has_expected_columns(self, app):
        """Test that pages table has expected columns."""
        with app.app_context():
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('pages')]

            expected_columns = [
                'id',
                'company_id',
                'url',
                'page_type',
                'content_hash',
                'raw_html',
                'extracted_text',
                'crawled_at',
                'is_external'
            ]

            for column in expected_columns:
                assert column in columns, f"Column {column} not found in pages"

    def test_entities_table_has_expected_columns(self, app):
        """Test that entities table has expected columns."""
        with app.app_context():
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('entities')]

            expected_columns = [
                'id',
                'company_id',
                'entity_type',
                'entity_value',
                'context_snippet',
                'source_url',
                'confidence_score',
                'extra_data',
                'created_at'
            ]

            for column in expected_columns:
                assert column in columns, f"Column {column} not found in entities"

    def test_fresh_database_via_create_all(self, app):
        """Test fresh database creation via db.create_all()."""
        with app.app_context():
            # Drop all and recreate
            db.drop_all()
            db.create_all()

            # Verify tables exist
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

            assert 'companies' in tables
            assert 'pages' in tables
            assert 'entities' in tables
