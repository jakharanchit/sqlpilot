# ============================================================
# tests/test_watcher.py
# Tests for tools/watcher.py
#
# Focus: diff_snapshots() and severity classification.
# These are pure logic functions — no DB or Ollama needed.
# ============================================================

import json
from pathlib import Path

import pytest


# ============================================================
# diff_snapshots — core diff logic
# ============================================================

class TestDiffSnapshots:
    def test_no_changes_returns_empty_list(self, sample_snapshot):
        from tools.watcher import diff_snapshots

        changes = diff_snapshots(sample_snapshot, sample_snapshot)
        assert changes == []

    def test_detects_column_type_change(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        new["tables"]["measurements"]["columns"]["value"]["type"] = "varchar"

        changes = diff_snapshots(sample_snapshot, new)
        type_changes = [c for c in changes if c["change_type"] == "column_type_changed"]
        assert len(type_changes) == 1
        assert type_changes[0]["object"] == "measurements.value"

    def test_column_type_change_is_high_severity(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        new["tables"]["measurements"]["columns"]["machine_id"]["type"] = "bigint"

        changes = diff_snapshots(sample_snapshot, new)
        type_changes = [c for c in changes if c["change_type"] == "column_type_changed"]
        assert type_changes[0]["severity"] == "HIGH"

    def test_detects_dropped_column(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        del new["tables"]["measurements"]["columns"]["value"]

        changes = diff_snapshots(sample_snapshot, new)
        dropped = [c for c in changes if c["change_type"] == "column_dropped"]
        assert len(dropped) == 1
        assert "value" in dropped[0]["object"]

    def test_dropped_column_is_high_severity(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        del new["tables"]["measurements"]["columns"]["timestamp"]

        changes = diff_snapshots(sample_snapshot, new)
        dropped = [c for c in changes if c["change_type"] == "column_dropped"]
        assert dropped[0]["severity"] == "HIGH"

    def test_detects_new_column(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        new["tables"]["measurements"]["columns"]["batch_id"] = {
            "type": "int", "size": 0, "nullable": "YES", "pk": False
        }

        changes = diff_snapshots(sample_snapshot, new)
        added = [c for c in changes if c["change_type"] == "column_added"]
        assert len(added) == 1
        assert "batch_id" in added[0]["object"]

    def test_new_column_is_low_severity(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        new["tables"]["measurements"]["columns"]["new_col"] = {
            "type": "int", "size": 0, "nullable": "YES", "pk": False
        }

        changes = diff_snapshots(sample_snapshot, new)
        added = [c for c in changes if c["change_type"] == "column_added"]
        assert added[0]["severity"] == "LOW"

    def test_detects_dropped_index(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        del new["tables"]["measurements"]["indexes"]["IX_measurements_machine"]

        changes = diff_snapshots(sample_snapshot, new)
        dropped = [c for c in changes if c["change_type"] == "index_dropped"]
        assert len(dropped) == 1

    def test_dropped_index_is_high_severity(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        del new["tables"]["measurements"]["indexes"]["IX_measurements_machine"]

        changes = diff_snapshots(sample_snapshot, new)
        dropped = [c for c in changes if c["change_type"] == "index_dropped"]
        assert dropped[0]["severity"] == "HIGH"

    def test_detects_index_keys_changed(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        new["tables"]["measurements"]["indexes"]["IX_measurements_machine"]["keys"] = "machine_id"

        changes = diff_snapshots(sample_snapshot, new)
        key_changes = [c for c in changes if c["change_type"] == "index_keys_changed"]
        assert len(key_changes) == 1

    def test_detects_dropped_table(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        del new["tables"]["measurements"]

        changes = diff_snapshots(sample_snapshot, new)
        dropped = [c for c in changes if c["change_type"] == "table_dropped"]
        assert len(dropped) == 1
        assert dropped[0]["severity"] == "HIGH"

    def test_detects_new_table(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        new["tables"]["calibration_log"] = {
            "columns": {"id": {"type": "int", "size": 0, "nullable": "NO", "pk": True}},
            "indexes": {},
            "row_count": 0,
        }

        changes = diff_snapshots(sample_snapshot, new)
        added = [c for c in changes if c["change_type"] == "table_added"]
        assert len(added) == 1
        assert added[0]["severity"] == "INFO"

    def test_detects_view_changed(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        new["views"]["vw_dashboard"]["definition_hash"] = "completely_different_hash"

        changes = diff_snapshots(sample_snapshot, new)
        changed = [c for c in changes if c["change_type"] == "view_changed"]
        assert len(changed) == 1
        assert changed[0]["severity"] == "MEDIUM"

    def test_detects_dropped_view(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        del new["views"]["vw_dashboard"]

        changes = diff_snapshots(sample_snapshot, new)
        dropped = [c for c in changes if c["change_type"] == "view_dropped"]
        assert len(dropped) == 1
        assert dropped[0]["severity"] == "HIGH"

    def test_changes_sorted_by_severity(self, sample_snapshot):
        from tools.watcher import diff_snapshots, SEVERITY_ORDER
        import copy

        new = copy.deepcopy(sample_snapshot)
        # Mix of HIGH and LOW changes
        del new["tables"]["measurements"]["columns"]["value"]       # HIGH (dropped column)
        new["tables"]["measurements"]["columns"]["new_col"] = {     # LOW (new column)
            "type": "int", "size": 0, "nullable": "YES", "pk": False
        }

        changes = diff_snapshots(sample_snapshot, new)
        severities = [SEVERITY_ORDER[c["severity"]] for c in changes]
        assert severities == sorted(severities)  # Should be in order: HIGH < MEDIUM < LOW < INFO

    def test_empty_old_snapshot_returns_empty(self, sample_snapshot):
        from tools.watcher import diff_snapshots

        changes = diff_snapshots({}, sample_snapshot)
        assert changes == []

    def test_nullable_change_is_medium_severity(self, sample_snapshot):
        from tools.watcher import diff_snapshots
        import copy

        new = copy.deepcopy(sample_snapshot)
        new["tables"]["measurements"]["columns"]["value"]["nullable"] = "NO"

        changes = diff_snapshots(sample_snapshot, new)
        null_changes = [c for c in changes if c["change_type"] == "column_nullable_changed"]
        assert null_changes[0]["severity"] == "MEDIUM"


# ============================================================
# save_snapshot / load_snapshot
# ============================================================

class TestSnapshotIO:
    def test_save_and_load_roundtrip(self, temp_project, sample_snapshot):
        from tools.watcher import save_snapshot, load_snapshot

        paths = save_snapshot(sample_snapshot)

        loaded = load_snapshot(paths["latest"])

        assert loaded["database"]  == sample_snapshot["database"]
        assert loaded["captured_at"] == sample_snapshot["captured_at"]
        assert "measurements" in loaded["tables"]

    def test_save_creates_dated_file(self, temp_project, sample_snapshot):
        from tools.watcher import save_snapshot

        paths = save_snapshot(sample_snapshot)

        assert Path(paths["dated"]).exists()
        assert Path(paths["latest"]).exists()

    def test_load_missing_returns_empty(self, temp_project):
        from tools.watcher import load_snapshot

        result = load_snapshot(str(temp_project / "nonexistent.json"))
        assert result == {}
