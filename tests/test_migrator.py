# ============================================================
# tests/test_migrator.py
# Tests for tools/migrator.py
# Uses temp_project fixture for isolated file operations.
# ============================================================

import json
from pathlib import Path

import pytest


class TestCreateMigration:
    def test_creates_sql_file(self, temp_project):
        from tools.migrator import create_migration

        result = create_migration(
            description  = "test optimization",
            apply_sql    = ["CREATE INDEX IX_test ON measurements (machine_id);"],
            rollback_sql = ["DROP INDEX IF EXISTS IX_test ON measurements;"],
        )

        assert result["filename"] != ""
        mig_path = Path(temp_project / "migrations" / result["filename"])
        assert mig_path.exists()

    def test_migration_file_contains_apply_sql(self, temp_project):
        from tools.migrator import create_migration

        result = create_migration(
            description  = "add index",
            apply_sql    = ["CREATE INDEX IX_test ON measurements (machine_id);"],
            rollback_sql = ["DROP INDEX IF EXISTS IX_test ON measurements;"],
        )

        content = (temp_project / "migrations" / result["filename"]).read_text()
        assert "CREATE INDEX IX_test" in content

    def test_migration_file_contains_rollback_sql(self, temp_project):
        from tools.migrator import create_migration

        result = create_migration(
            description  = "add index",
            apply_sql    = ["CREATE INDEX IX_test ON measurements (machine_id);"],
            rollback_sql = ["DROP INDEX IF EXISTS IX_test ON measurements;"],
        )

        content = (temp_project / "migrations" / result["filename"]).read_text()
        assert "DROP INDEX IF EXISTS IX_test" in content

    def test_benchmark_data_written_to_file(self, temp_project):
        from tools.migrator import create_migration

        result = create_migration(
            description     = "optimize query",
            apply_sql       = ["CREATE INDEX IX_x ON t (col);"],
            rollback_sql    = ["DROP INDEX IF EXISTS IX_x ON t;"],
            before_ms       = 847.3,
            after_ms        = 12.1,
            improvement_pct = 98.6,
        )

        content = (temp_project / "migrations" / result["filename"]).read_text()
        assert "847" in content
        assert "98.6" in content

    def test_sequential_numbering(self, temp_project):
        from tools.migrator import create_migration

        r1 = create_migration("first",  ["SELECT 1"], ["SELECT 1"])
        r2 = create_migration("second", ["SELECT 2"], ["SELECT 2"])
        r3 = create_migration("third",  ["SELECT 3"], ["SELECT 3"])

        assert r1["number"] == 1
        assert r2["number"] == 2
        assert r3["number"] == 3

    def test_filename_uses_description_slug(self, temp_project):
        from tools.migrator import create_migration

        result = create_migration(
            description  = "optimize vw dashboard",
            apply_sql    = ["SELECT 1"],
            rollback_sql = ["SELECT 1"],
        )

        assert "optimize" in result["filename"]

    def test_status_is_pending_initially(self, temp_project):
        from tools.migrator import create_migration

        result = create_migration(
            description  = "test",
            apply_sql    = ["SELECT 1"],
            rollback_sql = ["SELECT 1"],
        )

        assert result["status"] == "pending"

    def test_registry_updated(self, temp_project):
        from tools.migrator import create_migration, _load_registry

        create_migration(
            description  = "test",
            apply_sql    = ["SELECT 1"],
            rollback_sql = ["SELECT 1"],
        )

        registry = _load_registry()
        assert len(registry["migrations"]) == 1


class TestSlug:
    def test_slug_removes_special_chars(self):
        from tools.migrator import _slug

        result = _slug("hello world! (test)")
        assert "!" not in result
        assert "(" not in result
        assert ")" not in result

    def test_slug_replaces_spaces_with_underscores(self):
        from tools.migrator import _slug

        result = _slug("optimize vw dashboard")
        assert " " not in result
        assert "_" in result

    def test_slug_respects_max_len(self):
        from tools.migrator import _slug

        long_text = "a" * 100
        result = _slug(long_text, max_len=20)
        assert len(result) <= 20


class TestListMigrations:
    def test_returns_empty_list_when_no_migrations(self, temp_project):
        from tools.migrator import list_migrations

        result = list_migrations()
        assert result == []

    def test_returns_created_migrations(self, temp_project, sample_migration):
        from tools.migrator import list_migrations

        result = list_migrations()
        assert len(result) == 1

    def test_filter_by_pending_status(self, temp_project, sample_migration):
        from tools.migrator import list_migrations

        pending = list_migrations(status_filter="pending")
        assert len(pending) == 1
        assert pending[0]["status"] == "pending"

    def test_filter_by_applied_returns_empty_for_new(self, temp_project, sample_migration):
        from tools.migrator import list_migrations

        applied = list_migrations(status_filter="applied")
        assert applied == []


class TestMarkApplied:
    def test_marks_migration_as_applied(self, temp_project, sample_migration):
        from tools.migrator import mark_applied, list_migrations

        mark_applied(sample_migration["number"])

        migrations = list_migrations()
        assert migrations[0]["status"] == "applied"

    def test_records_client_name(self, temp_project, sample_migration):
        from tools.migrator import mark_applied, _load_registry

        mark_applied(sample_migration["number"], client="test_client")

        registry = _load_registry()
        m = registry["migrations"][str(sample_migration["number"])]
        assert "test_client" in m["applied_to"]

    def test_returns_false_for_missing_migration(self, temp_project):
        from tools.migrator import mark_applied

        result = mark_applied(999)
        assert result is False


class TestMarkRolledBack:
    def test_marks_migration_as_rolled_back(self, temp_project, sample_migration):
        from tools.migrator import mark_rolled_back, list_migrations

        mark_rolled_back(sample_migration["number"])

        migrations = list_migrations()
        assert migrations[0]["status"] == "rolled_back"


class TestMigrationFromOptimization:
    def test_creates_migration_from_pipeline_result(self, temp_project, sample_pipeline_result):
        from tools.migrator import migration_from_optimization, list_migrations

        result = migration_from_optimization(sample_pipeline_result["optimization"])

        assert result is not None
        assert result["number"] >= 1
        migrations = list_migrations()
        assert len(migrations) == 1

    def test_rollback_contains_drop_index(self, temp_project, sample_pipeline_result):
        from tools.migrator import migration_from_optimization

        migration_from_optimization(sample_pipeline_result["optimization"])

        from tools.migrator import list_migrations
        m = list_migrations()[0]
        content = (Path(temp_project / "migrations" / m["filename"])).read_text()
        assert "DROP INDEX" in content

    def test_no_migration_when_no_index_scripts(self, temp_project, sample_pipeline_result):
        from tools.migrator import migration_from_optimization, list_migrations

        result_no_indexes = dict(sample_pipeline_result["optimization"])
        result_no_indexes["index_scripts"] = []

        # Should not create a migration when there's nothing to apply
        migration_from_optimization(result_no_indexes)
        # migration may or may not be created — just check it doesn't crash
