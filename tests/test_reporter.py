# ============================================================
# tests/test_reporter.py
# Tests for tools/reporter.py
#
# Focus: generated document content correctness.
# These are pure string generation functions — fast, no DB.
# ============================================================

from pathlib import Path

import pytest


# ============================================================
# Helper — minimal migration dict for reporter tests
# ============================================================

def make_migration(number=1, description="add test index",
                   before_ms=847.3, after_ms=12.1,
                   improvement_pct=98.6, tables=None,
                   filename=None):
    return {
        "number":          number,
        "filename":        filename or f"{number:03d}_{description.replace(' ', '_')}.sql",
        "description":     description,
        "date":            "2026-03-21 14:32:01",
        "client":          "client_acme",
        "tables_affected": tables or ["measurements"],
        "reason":          "Table Scan on measurements (847ms avg)",
        "before_ms":       before_ms,
        "after_ms":        after_ms,
        "improvement_pct": improvement_pct,
        "status":          "pending",
        "applied_to":      [],
    }


# ============================================================
# _build_deploy_sql
# ============================================================

class TestBuildDeploySql:
    def test_contains_safety_check(self, temp_project):
        from tools.reporter import _build_deploy_sql

        migrations = [make_migration()]
        sql = _build_deploy_sql(migrations, "client_acme")

        assert "DB_NAME()" in sql
        assert "RAISERROR" in sql

    def test_contains_migration_description(self, temp_project):
        from tools.reporter import _build_deploy_sql

        migrations = [make_migration(description="add covering index")]
        sql = _build_deploy_sql(migrations, "client_acme")

        assert "add covering index" in sql

    def test_contains_print_statements(self, temp_project):
        from tools.reporter import _build_deploy_sql

        migrations = [make_migration()]
        sql = _build_deploy_sql(migrations, "client_acme")

        assert "PRINT" in sql

    def test_multiple_migrations_in_order(self, temp_project):
        from tools.reporter import _build_deploy_sql

        migrations = [
            make_migration(1, "first change"),
            make_migration(2, "second change"),
            make_migration(3, "third change"),
        ]
        sql = _build_deploy_sql(migrations, "client_acme")

        pos1 = sql.find("first change")
        pos2 = sql.find("second change")
        pos3 = sql.find("third change")
        assert pos1 < pos2 < pos3  # correct order

    def test_contains_benchmark_numbers(self, temp_project):
        from tools.reporter import _build_deploy_sql

        migrations = [make_migration(before_ms=847.3, after_ms=12.1, improvement_pct=98.6)]
        sql = _build_deploy_sql(migrations, "client_acme")

        assert "847" in sql
        assert "98.6" in sql


# ============================================================
# _build_rollback_sql
# ============================================================

class TestBuildRollbackSql:
    def test_rollback_header_present(self, temp_project):
        from tools.reporter import _build_rollback_sql

        sql = _build_rollback_sql([make_migration()], "client_acme")
        assert "ROLLBACK" in sql.upper()

    def test_rollback_has_safety_check(self, temp_project):
        from tools.reporter import _build_rollback_sql

        sql = _build_rollback_sql([make_migration()], "client_acme")
        assert "RAISERROR" in sql or "DB_NAME()" in sql

    def test_multiple_migrations_in_reverse_order(self, temp_project):
        from tools.reporter import _build_rollback_sql

        migrations = [
            make_migration(1, "first"),
            make_migration(2, "second"),
            make_migration(3, "third"),
        ]
        sql = _build_rollback_sql(migrations, "client_acme")

        # In rollback, migrations should be in reverse (3, 2, 1)
        pos1 = sql.find("001")
        pos3 = sql.find("003")
        assert pos3 < pos1  # 003 should appear before 001


# ============================================================
# _build_pre_flight
# ============================================================

class TestBuildPreFlight:
    def test_contains_backup_checkbox(self, temp_project):
        from tools.reporter import _build_pre_flight

        md = _build_pre_flight([make_migration()], "client_acme")
        assert "backup" in md.lower()
        assert "[ ]" in md

    def test_contains_database_name(self, temp_project):
        from tools.reporter import _build_pre_flight

        md = _build_pre_flight([make_migration()], "client_acme")
        # DB name from config — at least mentions database
        assert "database" in md.lower() or "db" in md.lower()

    def test_contains_sign_off_section(self, temp_project):
        from tools.reporter import _build_pre_flight

        md = _build_pre_flight([make_migration()], "client_acme")
        assert "sign" in md.lower() or "confirm" in md.lower() or "name:" in md.lower()

    def test_lists_all_migrations(self, temp_project):
        from tools.reporter import _build_pre_flight

        migrations = [
            make_migration(1, "first change"),
            make_migration(2, "second change"),
        ]
        md = _build_pre_flight(migrations, "client_acme")
        assert "first change" in md
        assert "second change" in md


# ============================================================
# _build_technical_report
# ============================================================

class TestBuildTechnicalReport:
    def test_contains_summary_table(self, temp_project):
        from tools.reporter import _build_technical_report

        md = _build_technical_report([make_migration()], "client_acme")
        # Should have a markdown table
        assert "|" in md

    def test_contains_benchmark_results(self, temp_project):
        from tools.reporter import _build_technical_report

        md = _build_technical_report(
            [make_migration(before_ms=847.3, after_ms=12.1, improvement_pct=98.6)],
            "client_acme"
        )
        assert "847" in md
        assert "12.1" in md
        assert "98.6" in md

    def test_contains_all_migration_descriptions(self, temp_project):
        from tools.reporter import _build_technical_report

        migrations = [
            make_migration(1, "optimize dashboard view"),
            make_migration(2, "add covering index"),
        ]
        md = _build_technical_report(migrations, "client_acme")
        assert "optimize dashboard view" in md
        assert "add covering index" in md

    def test_contains_apply_instructions(self, temp_project):
        from tools.reporter import _build_technical_report

        md = _build_technical_report([make_migration()], "client_acme")
        assert "deploy.sql" in md or "SSMS" in md


# ============================================================
# _build_walkthrough
# ============================================================

class TestBuildWalkthrough:
    def test_contains_numbered_steps(self, temp_project):
        from tools.reporter import _build_walkthrough

        md = _build_walkthrough([make_migration()], "client_acme", "client_acme_2026_03_21")
        assert "Step 1" in md
        assert "Step 2" in md

    def test_contains_rollback_instruction(self, temp_project):
        from tools.reporter import _build_walkthrough

        md = _build_walkthrough([make_migration()], "client_acme", "client_acme_2026_03_21")
        assert "rollback" in md.lower()

    def test_contains_improvement_numbers(self, temp_project):
        from tools.reporter import _build_walkthrough

        md = _build_walkthrough(
            [make_migration(before_ms=847.3, after_ms=12.1, improvement_pct=98.6)],
            "client_acme",
            "client_acme_2026_03_21"
        )
        assert "847" in md or "12" in md

    def test_plain_english_not_sql_heavy(self, temp_project):
        from tools.reporter import _build_walkthrough

        md = _build_walkthrough([make_migration()], "client_acme", "client_acme_2026_03_21")
        # Should be a walkthrough guide, not a SQL dump
        assert "F5" in md or "SSMS" in md
        assert "Step" in md


# ============================================================
# _extract_apply_section / _extract_rollback_section
# ============================================================

class TestExtractSections:
    SAMPLE_MIGRATION = """
-- Migration: 001
-- ============================================================
-- ROLLBACK — run this section to undo this migration
-- ============================================================

DROP INDEX IF EXISTS IX_test ON measurements;


-- ============================================================
-- APPLY — run this section to apply this migration
-- ============================================================

CREATE NONCLUSTERED INDEX IX_test
ON measurements (machine_id, timestamp)
INCLUDE (value);


-- ============================================================
-- VERIFY
-- ============================================================
SELECT name FROM sys.indexes WHERE name = 'IX_test';
"""

    def test_extracts_apply_section(self, temp_project):
        from tools.reporter import _extract_apply_section

        result = _extract_apply_section(self.SAMPLE_MIGRATION)
        assert "CREATE NONCLUSTERED INDEX" in result
        assert "DROP INDEX" not in result

    def test_extracts_rollback_section(self, temp_project):
        from tools.reporter import _extract_rollback_section

        result = _extract_rollback_section(self.SAMPLE_MIGRATION)
        assert "DROP INDEX IF EXISTS IX_test" in result
        assert "CREATE" not in result


# ============================================================
# quick_report
# ============================================================

class TestQuickReport:
    def test_generates_markdown_string(self, temp_project, sample_pipeline_result):
        from tools.reporter import quick_report

        result = quick_report(
            sample_pipeline_result["optimization"],
            sample_pipeline_result["benchmark"],
        )

        assert isinstance(result, str)
        assert "#" in result  # has markdown headers
        assert "```sql" in result  # has SQL code blocks

    def test_contains_original_query(self, temp_project, sample_pipeline_result):
        from tools.reporter import quick_report

        result = quick_report(sample_pipeline_result["optimization"])
        assert "measurements" in result

    def test_contains_improvement_when_benchmark_provided(self, temp_project, sample_pipeline_result):
        from tools.reporter import quick_report

        result = quick_report(
            sample_pipeline_result["optimization"],
            sample_pipeline_result["benchmark"],
        )
        assert "98.6" in result

    def test_saves_to_reports_dir(self, temp_project, sample_pipeline_result):
        from tools.reporter import quick_report

        quick_report(sample_pipeline_result["optimization"])

        reports_dir = Path(temp_project / "reports")
        md_files    = list(reports_dir.glob("*.md"))
        assert len(md_files) == 1
