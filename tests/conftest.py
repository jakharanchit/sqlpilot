# ============================================================
# tests/conftest.py
# Shared pytest fixtures for the SQL Optimization Agent test suite.
#
# DESIGN PRINCIPLE:
#   All tests run without a live SQL Server or Ollama instance.
#   Mock objects simulate exact real responses so tests are:
#     - Fast (no network / DB calls)
#     - Reliable (no external dependencies)
#     - Portable (run on any machine)
#     - Safe (no real DB modified)
#
# KEY FIXTURES:
#   mock_db_connection  — pyodbc.connect returns a mock cursor
#   mock_ollama         — requests.post returns realistic AI response
#   temp_dirs           — isolated temp directories per test
#   sample_schema       — realistic schema dict for measurements table
#   sample_migration    — a fully-populated migration dict
#   sample_pipeline_result — what pipeline.run_single() returns
# ============================================================

import json
import os
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest


# ============================================================
# TEMP DIRECTORY FIXTURES
# ============================================================

@pytest.fixture
def temp_dir(tmp_path):
    """Isolated temporary directory for each test."""
    return tmp_path


@pytest.fixture
def temp_project(tmp_path, monkeypatch):
    """
    Full isolated project directory structure.
    Patches config.py paths so tools write to temp dirs.
    """
    dirs = {
        "BASE_DIR":        str(tmp_path),
        "MIGRATIONS_DIR":  str(tmp_path / "migrations"),
        "REPORTS_DIR":     str(tmp_path / "reports"),
        "DEPLOYMENTS_DIR": str(tmp_path / "deployments"),
        "SNAPSHOTS_DIR":   str(tmp_path / "snapshots"),
        "HISTORY_DB":      str(tmp_path / "history.db"),
        "PLANS_DIR":       str(tmp_path / "plans"),
    }

    for d in dirs.values():
        Path(d).mkdir(parents=True, exist_ok=True)

    # Patch config module paths
    import config as cfg
    for attr, val in dirs.items():
        monkeypatch.setattr(cfg, attr, val)

    # Also patch runs/ dir references in logger
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    return tmp_path


# ============================================================
# DATABASE MOCK FIXTURES
# ============================================================

@pytest.fixture
def mock_cursor():
    """
    Mock pyodbc cursor with realistic SQL Server responses.
    Handles different queries by inspecting the SQL text.
    """
    cursor = MagicMock()

    # Default fetchall — empty
    cursor.fetchall.return_value = []
    cursor.fetchone.return_value = None

    def execute_side_effect(sql, *args):
        sql_upper = sql.strip().upper()

        # @@VERSION
        if "@@VERSION" in sql_upper:
            cursor.fetchone.return_value = (
                "Microsoft SQL Server 2022 (RTM) - 16.0.1000.6",
            )
        # DB_NAME
        elif "DB_NAME()" in sql_upper:
            cursor.fetchone.return_value = ("AcmeDev",)
        # INFORMATION_SCHEMA.COLUMNS
        elif "INFORMATION_SCHEMA.COLUMNS" in sql_upper:
            # Return realistic column data
            Row = MagicMock()
            col1 = MagicMock()
            col1.COLUMN_NAME = "id"
            col1.DATA_TYPE   = "int"
            col1.CHARACTER_MAXIMUM_LENGTH = None
            col1.IS_NULLABLE = "NO"
            col1.IS_PRIMARY_KEY = "YES"

            col2 = MagicMock()
            col2.COLUMN_NAME = "machine_id"
            col2.DATA_TYPE   = "int"
            col2.CHARACTER_MAXIMUM_LENGTH = None
            col2.IS_NULLABLE = "NO"
            col2.IS_PRIMARY_KEY = "NO"

            col3 = MagicMock()
            col3.COLUMN_NAME = "value"
            col3.DATA_TYPE   = "float"
            col3.CHARACTER_MAXIMUM_LENGTH = None
            col3.IS_NULLABLE = "YES"
            col3.IS_PRIMARY_KEY = "NO"

            col4 = MagicMock()
            col4.COLUMN_NAME = "timestamp"
            col4.DATA_TYPE   = "datetime"
            col4.CHARACTER_MAXIMUM_LENGTH = None
            col4.IS_NULLABLE = "NO"
            col4.IS_PRIMARY_KEY = "NO"

            cursor.fetchall.return_value = [col1, col2, col3, col4]

        # Indexes
        elif "SYS.INDEXES" in sql_upper:
            idx = MagicMock()
            idx.index_name       = "IX_measurements_machine"
            idx.index_type       = "NONCLUSTERED"
            idx.is_unique        = False
            idx.key_columns      = "machine_id, timestamp"
            idx.included_columns = "value"
            cursor.fetchall.return_value = [idx]

        # Row count
        elif "SYS.PARTITIONS" in sql_upper:
            rc = MagicMock()
            rc.row_count = 250000
            cursor.fetchone.return_value = rc

        # INFORMATION_SCHEMA.TABLES
        elif "INFORMATION_SCHEMA.TABLES" in sql_upper and "BASE TABLE" in sql_upper:
            t1 = MagicMock(); t1.__getitem__ = lambda s, i: "measurements"
            t2 = MagicMock(); t2.__getitem__ = lambda s, i: "sensors"
            row1 = MagicMock()
            row1[0] = "measurements"
            row2 = MagicMock()
            row2[0] = "sensors"
            cursor.fetchall.return_value = [row1, row2]

        # INFORMATION_SCHEMA.VIEWS
        elif "INFORMATION_SCHEMA.VIEWS" in sql_upper:
            v1 = MagicMock()
            v1[0] = "vw_dashboard"
            cursor.fetchall.return_value = [v1]

        # View definition
        elif "SYS.SQL_MODULES" in sql_upper:
            row = MagicMock()
            row.definition = (
                "CREATE VIEW vw_dashboard AS\n"
                "SELECT m.machine_id, m.value, m.timestamp\n"
                "FROM measurements m\n"
                "WHERE m.value IS NOT NULL"
            )
            cursor.fetchone.return_value = row

        # HAS_PERMS_BY_NAME
        elif "HAS_PERMS_BY_NAME" in sql_upper:
            cursor.fetchone.return_value = (1,)

        # COUNT for tables
        elif "COUNT(*)" in sql_upper and "INFORMATION_SCHEMA" in sql_upper:
            cursor.fetchone.return_value = (12,)

        return cursor

    cursor.execute.side_effect = execute_side_effect
    return cursor


@pytest.fixture
def mock_db_connection(mock_cursor):
    """
    Patches pyodbc.connect to return a mock connection
    with our mock cursor.
    """
    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor

    with patch("pyodbc.connect", return_value=mock_conn):
        yield mock_conn


# ============================================================
# OLLAMA MOCK FIXTURES
# ============================================================

MOCK_DIAGNOSIS = """
The main performance issue is a Table Scan on the measurements table.

1. **Non-sargable filter**: The WHERE clause on machine_id uses an implicit 
   INT to VARCHAR conversion, preventing index use.

2. **Missing covering index**: No index exists on (machine_id, timestamp) 
   which are the primary filter columns.

3. **SELECT ***: Pulling all 12 columns when only 3 are needed adds 
   unnecessary I/O.
""".strip()

MOCK_OPTIMIZED_QUERY = """
SELECT m.machine_id, m.value, m.timestamp
FROM measurements m WITH (NOLOCK)
WHERE m.machine_id = 1
  AND m.timestamp >= '2026-01-01'
""".strip()

MOCK_INDEX_SCRIPT = """
-- Covering index for machine_id + timestamp filter pattern
-- Targets: vw_dashboard filter queries from LabVIEW
CREATE NONCLUSTERED INDEX IX_measurements_machine_ts
ON measurements (machine_id, timestamp)
INCLUDE (value);
""".strip()

MOCK_OLLAMA_RESPONSE = f"""
Here is the optimized query:

```sql
{MOCK_OPTIMIZED_QUERY}
```

**What changed:**
- Replaced SELECT * with specific columns (removes 9 unused columns)
- Added WITH (NOLOCK) for read-only dashboard use
- Explicit column filter prevents implicit type conversion

```sql
{MOCK_INDEX_SCRIPT}
```
"""


@pytest.fixture
def mock_ollama_response():
    """Returns a realistic mock Ollama streaming response."""

    class MockStreamResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def iter_lines(self):
            # Simulate streaming tokens
            words = MOCK_OLLAMA_RESPONSE.split()
            for i, word in enumerate(words):
                done = (i == len(words) - 1)
                yield json.dumps({
                    "response": word + (" " if not done else ""),
                    "done":     done,
                }).encode()

    return MockStreamResponse()


@pytest.fixture
def mock_ollama(mock_ollama_response):
    """Patches requests.post to return mock Ollama streaming response."""
    with patch("requests.post", return_value=mock_ollama_response) as mock_post:
        # Also patch requests.get for /api/tags model list check
        mock_tags = MagicMock()
        mock_tags.status_code = 200
        mock_tags.json.return_value = {
            "models": [
                {"name": "qwen2.5-coder:14b"},
                {"name": "deepseek-r1:14b"},
            ]
        }
        with patch("requests.get", return_value=mock_tags):
            yield mock_post


@pytest.fixture
def mock_ollama_diagnosis():
    """Mock that returns just the diagnosis text (for Step 5)."""
    class MockDiagnosisResponse:
        status_code = 200
        def raise_for_status(self): pass
        def iter_lines(self):
            words = MOCK_DIAGNOSIS.split()
            for i, word in enumerate(words):
                done = (i == len(words) - 1)
                yield json.dumps({
                    "response": word + " ",
                    "done": done,
                }).encode()

    with patch("requests.post", return_value=MockDiagnosisResponse()):
        with patch("requests.get", return_value=MagicMock(
            status_code=200,
            json=lambda: {"models": [
                {"name": "qwen2.5-coder:14b"},
                {"name": "deepseek-r1:14b"},
            ]}
        )):
            yield


# ============================================================
# DATA FIXTURES
# ============================================================

@pytest.fixture
def sample_schema():
    """Realistic schema dict for measurements table."""
    return {
        "table_name": "measurements",
        "estimated_row_count": 250000,
        "columns": [
            {"name": "id",         "type": "int",      "nullable": "NO",  "primary_key": "YES"},
            {"name": "machine_id", "type": "int",      "nullable": "NO",  "primary_key": "NO"},
            {"name": "value",      "type": "float",    "nullable": "YES", "primary_key": "NO"},
            {"name": "timestamp",  "type": "datetime", "nullable": "NO",  "primary_key": "NO"},
        ],
        "indexes": [
            {
                "name":             "PK_measurements",
                "type":             "CLUSTERED",
                "unique":           True,
                "key_columns":      "id",
                "included_columns": None,
            }
        ],
    }


@pytest.fixture
def sample_schema_no_indexes():
    """Schema with no indexes — worst case for optimization."""
    return {
        "table_name": "sensor_readings",
        "estimated_row_count": 500000,
        "columns": [
            {"name": "id",        "type": "int",   "nullable": "NO",  "primary_key": "YES"},
            {"name": "sensor_id", "type": "int",   "nullable": "NO",  "primary_key": "NO"},
            {"name": "reading",   "type": "float", "nullable": "YES", "primary_key": "NO"},
        ],
        "indexes": [],
    }


@pytest.fixture
def sample_migration(temp_project):
    """A fully-populated migration dict as returned by create_migration()."""
    from tools.migrator import create_migration
    return create_migration(
        description     = "test optimization",
        apply_sql       = [
            "CREATE NONCLUSTERED INDEX IX_test ON measurements (machine_id) INCLUDE (value);"
        ],
        rollback_sql    = [
            "DROP INDEX IF EXISTS IX_test ON measurements;"
        ],
        reason          = "Table Scan on measurements",
        before_ms       = 847.3,
        after_ms        = 12.1,
        improvement_pct = 98.6,
        tables_affected = ["measurements"],
        source_query    = "SELECT * FROM measurements WHERE machine_id = 1",
    )


@pytest.fixture
def sample_pipeline_result(sample_schema):
    """Realistic result dict from pipeline.run_single()."""
    return {
        "query":   "SELECT * FROM measurements WHERE machine_id = 1",
        "label":   "test run",
        "success": True,
        "errors":  [],
        "optimization": {
            "original_query":   "SELECT * FROM measurements WHERE machine_id = 1",
            "optimized_query":  MOCK_OPTIMIZED_QUERY,
            "diagnosis":        MOCK_DIAGNOSIS,
            "index_scripts":    [MOCK_INDEX_SCRIPT],
            "schema_list":      [sample_schema],
            "log_path":         "runs/test_run.md",
            "plan":             {},
            "full_ai_response": MOCK_OLLAMA_RESPONSE,
            "timestamp":        "2026-03-21 14:32:01",
            "migration":        None,
        },
        "benchmark": {
            "label":           "test run",
            "before":          {"avg_ms": 847.3, "min_ms": 820.1, "max_ms": 890.2, "p50_ms": 845.0, "std_ms": 18.2, "row_count": 1500, "times": [847.3]*10},
            "after":           {"avg_ms": 12.1,  "min_ms": 10.5,  "max_ms": 15.2,  "p50_ms": 12.0,  "std_ms": 1.8,  "row_count": 1500, "times": [12.1]*10},
            "improvement_pct": 98.6,
            "speedup":         70.0,
            "row_mismatch":    False,
            "original_query":  "SELECT * FROM measurements WHERE machine_id = 1",
            "optimized_query": MOCK_OPTIMIZED_QUERY,
            "timestamp":       "2026-03-21 14:33:00",
            "runs":            10,
        },
        "migration":          None,
        "report_path":        "reports/",
        "deployment_package": None,
        "timestamp":          "2026-03-21 14:32:01",
    }


@pytest.fixture
def sample_snapshot():
    """Realistic schema snapshot dict."""
    return {
        "captured_at": "2026-03-21 07:00:00",
        "database":    "AcmeDev",
        "client":      "client_acme",
        "tables": {
            "measurements": {
                "columns": {
                    "id":         {"type": "int",      "size": 0,   "nullable": "NO",  "pk": True},
                    "machine_id": {"type": "int",      "size": 0,   "nullable": "NO",  "pk": False},
                    "value":      {"type": "float",    "size": 0,   "nullable": "YES", "pk": False},
                    "timestamp":  {"type": "datetime", "size": 0,   "nullable": "NO",  "pk": False},
                },
                "indexes": {
                    "IX_measurements_machine": {
                        "type": "NONCLUSTERED", "unique": False,
                        "keys": "machine_id, timestamp", "includes": "value"
                    }
                },
                "row_count": 250000,
            }
        },
        "views": {
            "vw_dashboard": {
                "definition_hash": "abc123def456",
                "definition":      "CREATE VIEW vw_dashboard AS SELECT ...",
            }
        },
    }


# ============================================================
# HISTORY DB FIXTURE
# ============================================================

@pytest.fixture
def populated_history_db(temp_project):
    """
    Creates a history.db with sample run records for testing
    history queries, trends, and comparisons.
    """
    from tools.history import record_run, _get_conn

    # Record a series of runs showing improvement over time
    runs = [
        dict(query="SELECT * FROM measurements WHERE machine_id=1",
             label="dashboard filter", tables=["measurements"],
             before_ms=847.3, after_ms=420.1, improvement_pct=50.4, speedup=2.0),
        dict(query="SELECT * FROM measurements WHERE machine_id=1",
             label="dashboard filter", tables=["measurements"],
             before_ms=420.1, after_ms=85.2, improvement_pct=79.7, speedup=4.9),
        dict(query="SELECT * FROM measurements WHERE machine_id=1",
             label="dashboard filter", tables=["measurements"],
             before_ms=85.2, after_ms=12.1, improvement_pct=85.8, speedup=7.0),
        dict(query="SELECT COUNT(*) FROM sensor_readings",
             label="sensor count", tables=["sensor_readings"],
             before_ms=340.5, after_ms=45.2, improvement_pct=86.7, speedup=7.5),
    ]

    run_ids = []
    for r in runs:
        run_id = record_run(**r, run_type="query", success=True)
        run_ids.append(run_id)

    return run_ids
