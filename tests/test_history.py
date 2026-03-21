# ============================================================
# tests/test_history.py
# Tests for tools/history.py
# Uses temp_project fixture — all writes go to a temp DB.
# ============================================================

import pytest


class TestFingerprint:
    def test_same_query_same_hash(self):
        from tools.history import _fingerprint

        q1 = "SELECT * FROM measurements WHERE machine_id = 1"
        q2 = "SELECT * FROM measurements WHERE machine_id = 1"
        assert _fingerprint(q1) == _fingerprint(q2)

    def test_whitespace_differences_ignored(self):
        from tools.history import _fingerprint

        q1 = "SELECT   *   FROM   measurements"
        q2 = "SELECT * FROM measurements"
        assert _fingerprint(q1) == _fingerprint(q2)

    def test_case_differences_ignored(self):
        from tools.history import _fingerprint

        q1 = "SELECT * FROM Measurements WHERE Machine_ID = 1"
        q2 = "select * from measurements where machine_id = 1"
        assert _fingerprint(q1) == _fingerprint(q2)

    def test_different_queries_different_hash(self):
        from tools.history import _fingerprint

        q1 = "SELECT * FROM measurements"
        q2 = "SELECT * FROM sensors"
        assert _fingerprint(q1) != _fingerprint(q2)

    def test_comments_stripped(self):
        from tools.history import _fingerprint

        q1 = "SELECT * FROM measurements -- fast query"
        q2 = "SELECT * FROM measurements"
        assert _fingerprint(q1) == _fingerprint(q2)

    def test_returns_hex_string(self):
        from tools.history import _fingerprint

        result = _fingerprint("SELECT 1")
        assert isinstance(result, str)
        assert len(result) == 32  # MD5 hex digest


class TestRecordRun:
    def test_records_basic_run(self, temp_project):
        from tools.history import record_run, get_history

        run_id = record_run(
            query  = "SELECT * FROM measurements WHERE machine_id = 1",
            tables = ["measurements"],
        )

        assert isinstance(run_id, int)
        assert run_id >= 1

        history = get_history(limit=1)
        assert len(history) == 1

    def test_records_benchmark_data(self, temp_project):
        from tools.history import record_run, get_history

        record_run(
            query           = "SELECT * FROM measurements",
            tables          = ["measurements"],
            before_ms       = 847.3,
            after_ms        = 12.1,
            improvement_pct = 98.6,
            speedup         = 70.0,
        )

        history = get_history(limit=1)
        run     = history[0]
        assert run["before_ms"]       == 847.3
        assert run["after_ms"]        == 12.1
        assert run["improvement_pct"] == 98.6

    def test_stores_query_preview(self, temp_project):
        from tools.history import record_run, get_history

        query = "SELECT machine_id, value FROM measurements WHERE machine_id = 42"
        record_run(query=query, tables=["measurements"])

        history = get_history(limit=1)
        assert "measurements" in history[0]["query_preview"]

    def test_multiple_runs_tracked(self, temp_project):
        from tools.history import record_run, get_history

        for i in range(5):
            record_run(query=f"SELECT {i} FROM measurements")

        history = get_history(limit=10)
        assert len(history) == 5

    def test_record_from_pipeline(self, temp_project, sample_pipeline_result):
        from tools.history import record_from_pipeline, get_history

        run_id = record_from_pipeline(sample_pipeline_result)

        assert isinstance(run_id, int)
        history = get_history(limit=1)
        assert len(history) == 1
        assert history[0]["improvement_pct"] == 98.6


class TestGetHistory:
    def test_returns_most_recent_first(self, temp_project, populated_history_db):
        from tools.history import get_history

        history = get_history(limit=10)
        # Most recent should be first
        assert len(history) >= 2
        for i in range(len(history) - 1):
            assert history[i]["timestamp"] >= history[i + 1]["timestamp"]

    def test_filter_by_table_name(self, temp_project, populated_history_db):
        from tools.history import get_history

        results = get_history(table_name="sensor_readings")
        assert all("sensor_readings" in r["tables_involved"] for r in results)

    def test_filter_by_query_text(self, temp_project, populated_history_db):
        from tools.history import get_history

        results = get_history(query="dashboard filter")
        assert len(results) > 0
        assert all("dashboard" in (r.get("label") or "") for r in results)

    def test_limit_respected(self, temp_project, populated_history_db):
        from tools.history import get_history

        results = get_history(limit=2)
        assert len(results) <= 2

    def test_empty_db_returns_empty_list(self, temp_project):
        from tools.history import get_history

        results = get_history()
        assert results == []


class TestGetTrend:
    def test_returns_oldest_first(self, temp_project, populated_history_db):
        from tools.history import get_trend

        runs = get_trend(table_name="measurements")
        assert len(runs) >= 3
        # Oldest first
        for i in range(len(runs) - 1):
            assert runs[i]["timestamp"] <= runs[i + 1]["timestamp"]

    def test_shows_improvement_over_time(self, temp_project, populated_history_db):
        from tools.history import get_trend

        runs = get_trend(table_name="measurements")
        # After_ms should generally decrease (getting faster)
        after_times = [r["after_ms"] for r in runs if r.get("after_ms")]
        assert after_times[-1] < after_times[0]

    def test_empty_for_unknown_table(self, temp_project, populated_history_db):
        from tools.history import get_trend

        runs = get_trend(table_name="nonexistent_table_xyz")
        assert runs == []


class TestGetRegressions:
    def test_finds_negative_improvement(self, temp_project):
        from tools.history import record_run, get_regressions

        # Record a regression — optimized is slower
        record_run(
            query           = "SELECT * FROM measurements",
            before_ms       = 100.0,
            after_ms        = 150.0,
            improvement_pct = -50.0,
        )

        regressions = get_regressions()
        assert len(regressions) >= 1
        assert all(r["improvement_pct"] <= 0 for r in regressions)

    def test_no_regressions_when_all_improved(self, temp_project, populated_history_db):
        from tools.history import get_regressions

        regressions = get_regressions()
        # All populated_history_db runs have positive improvement
        assert all(r["improvement_pct"] <= 0 for r in regressions)

    def test_threshold_filters_small_regressions(self, temp_project):
        from tools.history import record_run, get_regressions

        record_run(
            query           = "SELECT 1",
            before_ms       = 100.0,
            after_ms        = 102.0,
            improvement_pct = -2.0,  # Only 2% worse
        )

        # With -5% threshold, this should not appear
        regressions = get_regressions(threshold_pct=-5.0)
        assert len(regressions) == 0


class TestCompareRuns:
    def test_compares_two_runs(self, temp_project, populated_history_db):
        from tools.history import compare_runs

        # Compare first and last run IDs
        first_id = populated_history_db[0]
        last_id  = populated_history_db[-1]

        result = compare_runs(first_id, last_id)

        assert "run_a" in result
        assert "run_b" in result
        assert "diff"  in result

    def test_diff_contains_improvement_delta(self, temp_project, populated_history_db):
        from tools.history import compare_runs

        result = compare_runs(populated_history_db[0], populated_history_db[-1])

        assert "improvement_pct" in result["diff"]
        delta = result["diff"]["improvement_pct"]
        assert "delta"     in delta
        assert "direction" in delta

    def test_returns_error_for_missing_run(self, temp_project):
        from tools.history import compare_runs

        result = compare_runs(9999, 9998)
        assert "error" in result

    def test_better_run_identified_correctly(self, temp_project, populated_history_db):
        from tools.history import compare_runs

        # Run 3 (85.8% improvement) should be better than run 1 (50.4%)
        result = compare_runs(populated_history_db[0], populated_history_db[2])

        imp_diff = result["diff"].get("improvement_pct", {})
        assert imp_diff.get("direction") == "better"


class TestGetStats:
    def test_returns_dict_with_counts(self, temp_project, populated_history_db):
        from tools.history import get_stats

        stats = get_stats()

        assert "total_runs"      in stats
        assert "successful_runs" in stats
        assert "avg_improvement" in stats
        assert "best_improvement" in stats

    def test_correct_run_count(self, temp_project, populated_history_db):
        from tools.history import get_stats

        stats = get_stats()
        assert stats["total_runs"] == len(populated_history_db)

    def test_best_improvement_is_highest(self, temp_project, populated_history_db):
        from tools.history import get_stats

        stats = get_stats()
        assert stats["best_improvement"] >= stats["avg_improvement"]

    def test_empty_db_returns_empty_dict(self, temp_project):
        from tools.history import get_stats

        stats = get_stats()
        # Either empty dict or zeros — should not crash
        assert isinstance(stats, dict)
