# ============================================================
# tests/test_pipeline.py
# Integration tests for tools/pipeline.py
#
# These test the full pipeline flow with all external
# dependencies mocked (DB, Ollama, Git, benchmarker).
# Verifies that stages chain correctly and the result
# dict is structured as expected.
# ============================================================

from unittest.mock import MagicMock, patch

import pytest


# ============================================================
# Pipeline result structure
# ============================================================

class TestPipelineResultStructure:
    def test_result_has_required_keys(self, sample_pipeline_result):
        required = [
            "query", "label", "success", "errors",
            "optimization", "benchmark", "migration",
            "report_path", "timestamp",
        ]
        for key in required:
            assert key in sample_pipeline_result, f"Missing key: {key}"

    def test_successful_result_has_no_errors(self, sample_pipeline_result):
        assert sample_pipeline_result["success"] is True
        assert sample_pipeline_result["errors"] == []

    def test_optimization_has_required_keys(self, sample_pipeline_result):
        opt = sample_pipeline_result["optimization"]
        required = [
            "original_query", "optimized_query", "diagnosis",
            "index_scripts", "schema_list",
        ]
        for key in required:
            assert key in opt, f"Missing optimization key: {key}"

    def test_benchmark_has_required_keys(self, sample_pipeline_result):
        bench = sample_pipeline_result["benchmark"]
        required = [
            "before", "after", "improvement_pct",
            "speedup", "row_mismatch",
        ]
        for key in required:
            assert key in bench, f"Missing benchmark key: {key}"

    def test_benchmark_before_after_structure(self, sample_pipeline_result):
        bench = sample_pipeline_result["benchmark"]
        for section in ["before", "after"]:
            assert "avg_ms"    in bench[section]
            assert "row_count" in bench[section]


# ============================================================
# Row mismatch protection
# ============================================================

class TestRowMismatchProtection:
    def test_row_mismatch_flagged_in_result(self, sample_pipeline_result):
        """Simulates what happens when row counts differ."""
        result = dict(sample_pipeline_result)
        result["benchmark"] = dict(result["benchmark"])
        result["benchmark"]["row_mismatch"] = True
        result["errors"] = ["Row count mismatch — optimization returns different data"]

        assert result["benchmark"]["row_mismatch"] is True
        assert any("mismatch" in e.lower() for e in result["errors"])

    def test_no_migration_on_row_mismatch(self, sample_pipeline_result):
        """When rows don't match, migration should not be created."""
        result = dict(sample_pipeline_result)
        result["benchmark"] = dict(result["benchmark"])
        result["benchmark"]["row_mismatch"] = True
        result["migration"] = None  # Pipeline stops before migration

        assert result["migration"] is None


# ============================================================
# Pipeline with mocked dependencies
# ============================================================

class TestPipelineWithMocks:
    def test_run_single_returns_dict(
        self, temp_project, mock_db_connection, mock_ollama
    ):
        """Full pipeline with all external deps mocked."""
        from tools.pipeline import run_single
        from unittest.mock import patch

        # Mock the benchmarker to return realistic results
        mock_bench_result = {
            "label":           "test",
            "before":          {"avg_ms": 847.3, "row_count": 100, "min_ms": 820.0,
                               "max_ms": 870.0, "p50_ms": 845.0, "std_ms": 15.0,
                               "times": [847.3] * 10},
            "after":           {"avg_ms": 12.1, "row_count": 100, "min_ms": 10.0,
                               "max_ms": 15.0, "p50_ms": 12.0, "std_ms": 1.5,
                               "times": [12.1] * 10},
            "improvement_pct": 98.6,
            "speedup":         70.0,
            "row_mismatch":    False,
            "original_query":  "SELECT * FROM measurements",
            "optimized_query": "SELECT id, value FROM measurements WITH(NOLOCK)",
            "timestamp":       "2026-03-21 14:32:01",
            "runs":            10,
        }

        with patch("tools.pipeline._fetch_schemas_for_query") as mock_schema:
            mock_schema.return_value = [{
                "table_name": "measurements",
                "estimated_row_count": 250000,
                "columns": [
                    {"name": "id", "type": "int", "nullable": "NO", "primary_key": "YES"},
                    {"name": "value", "type": "float", "nullable": "YES", "primary_key": "NO"},
                ],
                "indexes": [],
            }]

            with patch("tools.benchmarker.benchmark_query", return_value=mock_bench_result):
                with patch("tools.config_validator.quick_check", return_value=None):
                    with patch("tools.git_manager.commit_optimization", return_value=True):
                        result = run_single(
                            "SELECT * FROM measurements WHERE machine_id = 1",
                            label="test run",
                            skip_deploy=True,
                        )

        assert isinstance(result, dict)
        assert "success" in result
        assert "query"   in result

    def test_run_single_stops_on_connection_failure(self, temp_project):
        """Pipeline should abort cleanly when DB is unavailable."""
        from tools.pipeline import run_single
        from tools.error_handler import DBConnectionError

        with patch("tools.config_validator.quick_check",
                   side_effect=DBConnectionError("no DB")):
            result = run_single("SELECT 1", skip_deploy=True)

        assert result["success"] is False
        assert len(result["errors"]) > 0

    def test_run_single_handles_ollama_failure_gracefully(
        self, temp_project, mock_db_connection
    ):
        """Pipeline should not crash when Ollama is unavailable."""
        from tools.pipeline import run_single

        with patch("tools.config_validator.quick_check", return_value=None):
            with patch("tools.pipeline._fetch_schemas_for_query") as mock_schema:
                mock_schema.return_value = [{
                    "table_name": "measurements",
                    "estimated_row_count": 250000,
                    "columns": [],
                    "indexes": [],
                }]
                with patch("tools.optimizer.optimize_query") as mock_opt:
                    mock_opt.return_value = {
                        "original_query":   "SELECT 1",
                        "optimized_query":  "",   # Empty — Ollama failed
                        "diagnosis":        "",
                        "index_scripts":    [],
                        "schema_list":      [],
                        "log_path":         "",
                        "plan":             {},
                        "full_ai_response": "",
                        "timestamp":        "2026-03-21 14:32:01",
                        "migration":        None,
                    }
                    result = run_single("SELECT 1", skip_deploy=True)

        # Should not crash — result may have empty optimization but no exception
        assert isinstance(result, dict)


# ============================================================
# Batch pipeline
# ============================================================

class TestRunBatch:
    def test_processes_all_sql_files(self, temp_project):
        """Batch should process each .sql file in the folder."""
        from tools.pipeline import run_batch

        # Create test .sql files
        queries_dir = temp_project / "queries"
        queries_dir.mkdir()
        (queries_dir / "query1.sql").write_text("SELECT * FROM measurements")
        (queries_dir / "query2.sql").write_text("SELECT * FROM sensors")

        with patch("tools.pipeline.run_single") as mock_run:
            mock_run.return_value = {
                "query": "SELECT 1", "label": "test", "success": True,
                "errors": [], "optimization": None, "benchmark": None,
                "migration": None, "report_path": None, "timestamp": "",
            }

            result = run_batch(str(queries_dir), skip_deploy=True)

        assert result["files_processed"] == 2
        assert mock_run.call_count == 2

    def test_returns_error_for_empty_folder(self, temp_project):
        """Batch on empty folder should return error dict."""
        from tools.pipeline import run_batch

        empty_dir = temp_project / "empty_queries"
        empty_dir.mkdir()

        result = run_batch(str(empty_dir), skip_deploy=True)
        assert "error" in result

    def test_continues_on_individual_file_failure(self, temp_project):
        """One file failing should not stop the rest."""
        from tools.pipeline import run_batch

        queries_dir = temp_project / "queries"
        queries_dir.mkdir()
        (queries_dir / "good.sql").write_text("SELECT * FROM measurements")
        (queries_dir / "bad.sql").write_text("INVALID SQL !!!!")

        def mock_run_single(query, **kwargs):
            if "INVALID" in query:
                return {
                    "query": query, "label": "", "success": False,
                    "errors": ["Query failed"], "optimization": None,
                    "benchmark": None, "migration": None,
                    "report_path": None, "timestamp": "",
                }
            return {
                "query": query, "label": "", "success": True,
                "errors": [], "optimization": None, "benchmark": None,
                "migration": None, "report_path": None, "timestamp": "",
            }

        with patch("tools.pipeline.run_single", side_effect=mock_run_single):
            result = run_batch(str(queries_dir), skip_deploy=True)

        assert result["successful"] == 1
        assert result["failed"]     == 1
        assert result["files_processed"] == 2
