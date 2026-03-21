# ============================================================
# tests/test_sandbox.py
# Tests for tools/sandbox.py
#
# All SQL Server calls are mocked — no real DB needed.
# Tests cover: shadow naming, apply logic, regression
# detection, destroy, and the full pipeline flow.
# ============================================================

import time
from unittest.mock import MagicMock, patch, call

import pytest


# ============================================================
# Shadow name
# ============================================================

class TestShadowName:
    def test_shadow_name_contains_original_db(self):
        from tools.sandbox import _shadow_name
        from config import DB_CONFIG

        name = _shadow_name()
        assert DB_CONFIG["database"] in name

    def test_shadow_name_contains_today_date(self):
        from tools.sandbox import _shadow_name
        from datetime import date

        name  = _shadow_name()
        today = date.today().strftime("%Y%m%d")
        assert today in name

    def test_shadow_name_contains_shadow_keyword(self):
        from tools.sandbox import _shadow_name

        name = _shadow_name()
        assert "Shadow" in name


# ============================================================
# _shadow_exists
# ============================================================

class TestShadowExists:
    def test_returns_true_when_shadow_found(self):
        from tools.sandbox import _shadow_exists

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (1,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("pyodbc.connect", return_value=mock_conn):
            result = _shadow_exists("AcmeDev_Shadow_20260321")

        assert result is True

    def test_returns_false_when_not_found(self):
        from tools.sandbox import _shadow_exists

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (0,)
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("pyodbc.connect", return_value=mock_conn):
            result = _shadow_exists("AcmeDev_Shadow_Nonexistent")

        assert result is False

    def test_returns_false_on_connection_error(self):
        from tools.sandbox import _shadow_exists
        import pyodbc

        with patch("pyodbc.connect", side_effect=pyodbc.Error("08001", "failed")):
            result = _shadow_exists("AcmeDev_Shadow_20260321")

        assert result is False


# ============================================================
# apply()
# ============================================================

class TestApply:
    def test_applies_single_statement(self):
        from tools.sandbox import apply

        mock_cursor = MagicMock()
        mock_conn   = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("pyodbc.connect", return_value=mock_conn):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = apply(
                    ["CREATE INDEX IX_test ON measurements (machine_id)"],
                    shadow_name="AcmeDev_Shadow_20260321",
                )

        assert result["success"] is True
        assert result["statements"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is True

    def test_applies_multiple_statements(self):
        from tools.sandbox import apply

        mock_cursor = MagicMock()
        mock_conn   = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        statements = [
            "CREATE INDEX IX_a ON measurements (machine_id)",
            "CREATE INDEX IX_b ON sensors (sensor_id)",
            "CREATE INDEX IX_c ON sensor_readings (sensor_id, timestamp)",
        ]

        with patch("pyodbc.connect", return_value=mock_conn):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = apply(statements, shadow_name="AcmeDev_Shadow_20260321")

        assert result["statements"] == 3
        assert result["success"] is True
        assert all(r["success"] for r in result["results"])

    def test_records_failure_on_sql_error(self):
        from tools.sandbox import apply
        import pyodbc

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = pyodbc.Error("42S01", "table already exists")
        mock_conn   = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("pyodbc.connect", return_value=mock_conn):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = apply(
                    ["CREATE INDEX IX_existing ON measurements (id)"],
                    shadow_name="AcmeDev_Shadow_20260321",
                )

        assert result["success"] is False
        assert result["failed_count"] == 1
        assert result["results"][0]["success"] is False
        assert result["results"][0]["error"] != ""

    def test_raises_sandbox_error_when_shadow_not_found(self):
        from tools.sandbox import apply
        from tools.error_handler import SandboxError

        with patch("tools.sandbox._shadow_exists", return_value=False):
            with pytest.raises(SandboxError):
                apply(["SELECT 1"], shadow_name="nonexistent")

    def test_continues_after_one_failure(self):
        from tools.sandbox import apply
        import pyodbc

        call_count = [0]

        def execute_side_effect(sql, *args):
            call_count[0] += 1
            if call_count[0] == 1:
                raise pyodbc.Error("42S01", "first fails")

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = execute_side_effect
        mock_conn   = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("pyodbc.connect", return_value=mock_conn):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = apply(
                    ["FAIL THIS", "CREATE INDEX IX_ok ON t (col)"],
                    shadow_name="AcmeDev_Shadow_20260321",
                )

        assert result["statements"] == 2
        assert result["failed_count"] == 1
        assert result["results"][0]["success"] is False
        assert result["results"][1]["success"] is True


# ============================================================
# benchmark()
# ============================================================

class TestBenchmark:
    def test_returns_timing_for_each_query(self):
        from tools.sandbox import benchmark

        mock_cursor = MagicMock()
        mock_conn   = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        queries = [
            {"label": "q1", "sql": "SELECT 1"},
            {"label": "q2", "sql": "SELECT 2"},
        ]

        with patch("pyodbc.connect", return_value=mock_conn):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = benchmark(queries, shadow_name="AcmeDev_Shadow_20260321", runs=3)

        assert result["queries"] == 2
        assert len(result["results"]) == 2
        for r in result["results"]:
            assert "avg_ms" in r
            assert r["success"] is True

    def test_avg_ms_is_non_negative(self):
        from tools.sandbox import benchmark

        mock_cursor = MagicMock()
        mock_conn   = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("pyodbc.connect", return_value=mock_conn):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = benchmark(
                    [{"label": "test", "sql": "SELECT COUNT(*) FROM measurements"}],
                    shadow_name="AcmeDev_Shadow_20260321",
                    runs=5,
                )

        assert result["results"][0]["avg_ms"] >= 0

    def test_records_correct_run_count(self):
        from tools.sandbox import benchmark

        mock_cursor = MagicMock()
        mock_conn   = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("pyodbc.connect", return_value=mock_conn):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = benchmark(
                    [{"label": "t", "sql": "SELECT 1"}],
                    shadow_name="AcmeDev_Shadow_20260321",
                    runs=7,
                )

        assert result["results"][0]["runs"] == 7
        assert len(result["results"][0]["times"]) == 7


# ============================================================
# regression_check()
# ============================================================

class TestRegressionCheck:
    def test_passes_when_no_regression(self):
        from tools.sandbox import regression_check

        # Benchmark returns fast times — well within threshold
        mock_bench = {
            "queries": 1,
            "results": [{"label": "q", "sql": "SELECT 1", "success": True,
                         "avg_ms": 12.0, "min_ms": 10.0, "max_ms": 15.0,
                         "times": [12.0], "runs": 3}],
            "success": True,
        }

        with patch("tools.sandbox.benchmark", return_value=mock_bench):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = regression_check(
                    [{"label": "q", "sql": "SELECT 1", "baseline_ms": 12.1}],
                    shadow_name   = "AcmeDev_Shadow_20260321",
                    threshold_pct = 30.0,
                )

        assert result["passed"] is True
        assert result["regressions"] == []

    def test_fails_when_query_is_much_slower(self):
        from tools.sandbox import regression_check

        # Shadow returns 500ms vs 12ms baseline — regression!
        mock_bench = {
            "queries": 1,
            "results": [{"label": "dashboard", "sql": "SELECT * FROM vw_dashboard",
                         "success": True, "avg_ms": 500.0, "min_ms": 480.0,
                         "max_ms": 520.0, "times": [500.0], "runs": 3}],
            "success": True,
        }

        with patch("tools.sandbox.benchmark", return_value=mock_bench):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = regression_check(
                    [{"label": "dashboard",
                      "sql": "SELECT * FROM vw_dashboard",
                      "baseline_ms": 12.1}],
                    shadow_name   = "AcmeDev_Shadow_20260321",
                    threshold_pct = 30.0,
                )

        assert result["passed"] is False
        assert len(result["regressions"]) == 1
        assert result["regressions"][0]["slowdown_pct"] > 30.0

    def test_threshold_respected(self):
        from tools.sandbox import regression_check

        # 25% slower — below 30% threshold, should pass
        mock_bench = {
            "queries": 1,
            "results": [{"label": "q", "sql": "SELECT 1", "success": True,
                         "avg_ms": 15.0, "min_ms": 14.0, "max_ms": 16.0,
                         "times": [15.0], "runs": 3}],
            "success": True,
        }

        with patch("tools.sandbox.benchmark", return_value=mock_bench):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = regression_check(
                    [{"label": "q", "sql": "SELECT 1", "baseline_ms": 12.0}],
                    shadow_name   = "AcmeDev_Shadow_20260321",
                    threshold_pct = 30.0,  # 25% < 30% threshold
                )

        assert result["passed"] is True

    def test_passes_when_no_queries(self):
        from tools.sandbox import regression_check

        result = regression_check(
            [], shadow_name="AcmeDev_Shadow_20260321"
        )
        assert result["passed"] is True
        assert result["regressions"] == []

    def test_fails_when_query_errors_in_shadow(self):
        from tools.sandbox import regression_check

        mock_bench = {
            "queries": 1,
            "results": [{"label": "q", "sql": "SELECT 1",
                         "success": False, "error": "table does not exist"}],
            "success": False,
        }

        with patch("tools.sandbox.benchmark", return_value=mock_bench):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = regression_check(
                    [{"label": "q", "sql": "SELECT 1", "baseline_ms": 12.0}],
                    shadow_name="AcmeDev_Shadow_20260321",
                )

        assert result["passed"] is False
        assert len(result["regressions"]) == 1


# ============================================================
# destroy()
# ============================================================

class TestDestroy:
    def test_drops_shadow_db(self):
        from tools.sandbox import destroy

        mock_cursor = MagicMock()
        mock_conn   = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("pyodbc.connect", return_value=mock_conn):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = destroy("AcmeDev_Shadow_20260321")

        assert result is True
        # Should have called ALTER DATABASE (set single user) and DROP DATABASE
        calls = [str(c) for c in mock_cursor.execute.call_args_list]
        assert any("DROP DATABASE" in c or "SINGLE_USER" in c for c in calls)

    def test_returns_true_when_shadow_not_found(self):
        from tools.sandbox import destroy

        with patch("tools.sandbox._shadow_exists", return_value=False):
            result = destroy("AcmeDev_Shadow_Nonexistent")

        assert result is True  # Nothing to do, that's fine

    def test_returns_false_on_error(self):
        from tools.sandbox import destroy
        import pyodbc

        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = pyodbc.Error("42000", "permission denied")
        mock_conn   = MagicMock()
        mock_conn.cursor.return_value = mock_cursor

        with patch("pyodbc.connect", return_value=mock_conn):
            with patch("tools.sandbox._shadow_exists", return_value=True):
                result = destroy("AcmeDev_Shadow_20260321")

        assert result is False


# ============================================================
# run_sandbox_test() — full pipeline
# ============================================================

class TestRunSandboxTest:
    def _mock_all(self):
        """Returns a context manager that mocks the full sandbox pipeline."""
        from contextlib import ExitStack

        stack = ExitStack()

        # Mock create
        stack.enter_context(patch("tools.sandbox.create", return_value={
            "shadow_name": "AcmeDev_Shadow_20260321",
            "success": True, "elapsed_s": 45.2,
        }))

        # Mock apply
        stack.enter_context(patch("tools.sandbox.apply", return_value={
            "shadow_name": "AcmeDev_Shadow_20260321",
            "statements": 1,
            "results": [{"sql": "CREATE INDEX...", "success": True, "elapsed_ms": 120}],
            "success": True,
            "failed_count": 0,
        }))

        # Mock benchmark
        stack.enter_context(patch("tools.sandbox.benchmark", return_value={
            "shadow_name": "AcmeDev_Shadow_20260321",
            "queries": 1,
            "results": [{"label": "q", "sql": "SELECT 1", "success": True,
                         "avg_ms": 11.0, "min_ms": 10.0, "max_ms": 13.0,
                         "times": [11.0]*3, "runs": 3}],
            "success": True,
        }))

        # Mock regression_check
        stack.enter_context(patch("tools.sandbox.regression_check", return_value={
            "passed": True, "regressions": [], "results": [],
            "threshold_pct": 30.0,
        }))

        # Mock destroy
        stack.enter_context(patch("tools.sandbox.destroy", return_value=True))

        return stack

    def test_returns_safe_to_deploy_on_success(self):
        from tools.sandbox import run_sandbox_test

        with self._mock_all():
            result = run_sandbox_test(
                sql_statements = ["CREATE INDEX IX_test ON measurements (machine_id)"],
                regression_queries = [{"label": "q", "sql": "SELECT 1", "baseline_ms": 12.0}],
            )

        assert result["safe_to_deploy"] is True
        assert result["passed"] is True
        assert result["errors"] == []

    def test_returns_not_safe_when_apply_fails(self):
        from tools.sandbox import run_sandbox_test

        with patch("tools.sandbox.create", return_value={"success": True,
                   "shadow_name": "AcmeDev_Shadow_20260321", "elapsed_s": 45}):
            with patch("tools.sandbox.apply", return_value={
                "success": False, "failed_count": 1,
                "statements": 1,
                "results": [{"sql": "BAD SQL", "success": False,
                             "error": "syntax error"}],
            }):
                with patch("tools.sandbox.destroy", return_value=True):
                    result = run_sandbox_test(
                        sql_statements=["BAD SQL"],
                        regression_queries=[],
                    )

        assert result["safe_to_deploy"] is False
        assert result["passed"] is False
        assert len(result["errors"]) > 0

    def test_returns_not_safe_when_regression_detected(self):
        from tools.sandbox import run_sandbox_test

        with patch("tools.sandbox.create", return_value={"success": True,
                   "shadow_name": "AcmeDev_Shadow_20260321", "elapsed_s": 45}):
            with patch("tools.sandbox.apply", return_value={
                "success": True, "failed_count": 0, "statements": 1,
                "results": [{"sql": "CREATE INDEX...", "success": True, "elapsed_ms": 120}],
            }):
                with patch("tools.sandbox.benchmark", return_value={
                    "queries": 1, "success": True,
                    "results": [{"label": "q", "sql": "SELECT 1", "success": True,
                                 "avg_ms": 500.0, "min_ms": 480.0, "max_ms": 520.0,
                                 "times": [500.0]*3, "runs": 3}],
                }):
                    with patch("tools.sandbox.regression_check", return_value={
                        "passed": False,
                        "regressions": [{"label": "q", "reason": "500% slower",
                                         "baseline_ms": 12.0, "shadow_ms": 500.0,
                                         "slowdown_pct": 4066.0, "severity": "HIGH"}],
                        "results": [],
                    }):
                        with patch("tools.sandbox.destroy", return_value=True):
                            result = run_sandbox_test(
                                sql_statements=["CREATE INDEX..."],
                                regression_queries=[{
                                    "label": "q", "sql": "SELECT 1", "baseline_ms": 12.0
                                }],
                            )

        assert result["safe_to_deploy"] is False
        assert result["passed"] is False
        assert any("Regression" in e for e in result["errors"])

    def test_destroy_called_even_on_failure(self):
        from tools.sandbox import run_sandbox_test

        mock_destroy = MagicMock(return_value=True)

        with patch("tools.sandbox.create", return_value={"success": True,
                   "shadow_name": "AcmeDev_Shadow_20260321", "elapsed_s": 45}):
            with patch("tools.sandbox.apply", return_value={
                "success": False, "failed_count": 1, "statements": 1,
                "results": [{"sql": "BAD", "success": False, "error": "err"}],
            }):
                with patch("tools.sandbox.destroy", mock_destroy):
                    run_sandbox_test(
                        sql_statements=["BAD"],
                        keep_on_failure=False,
                    )

        mock_destroy.assert_called_once()
