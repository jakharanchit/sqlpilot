# ============================================================
# tools/schema.py
# Tool 1: get_schema    — pulls DDL + indexes for a table
# Tool 2: get_view_definition — fetches a view's full SQL
# ============================================================

import pyodbc
from config import DB_CONFIG
from rich.console import Console

console = Console()


def _get_connection():
    """
    Build a connection string from config.py and return a pyodbc connection.
    Supports both Windows Auth and SQL Server login.
    """
    cfg = DB_CONFIG

    if cfg.get("trusted_connection", "no").lower() == "yes":
        conn_str = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={cfg['database']};"
            f"Trusted_Connection=yes;"
        )
    else:
        conn_str = (
            f"DRIVER={{{cfg['driver']}}};"
            f"SERVER={cfg['server']};"
            f"DATABASE={cfg['database']};"
            f"UID={cfg['username']};"
            f"PWD={cfg['password']};"
        )

    return pyodbc.connect(conn_str)


def get_schema(table_name: str) -> dict:
    """
    Pulls the full schema context for a table:
    - Column names, data types, nullability
    - Primary keys
    - All existing indexes (name, columns, type)
    - Row count estimate

    Returns a dict the agent passes to Ollama for context.

    Usage:
        schema = get_schema("measurements")
    """
    console.print(f"[cyan]→ Fetching schema for:[/cyan] {table_name}")

    conn   = _get_connection()
    cursor = conn.cursor()
    result = {}

    # --- Columns ---
    cursor.execute("""
        SELECT
            c.COLUMN_NAME,
            c.DATA_TYPE,
            c.CHARACTER_MAXIMUM_LENGTH,
            c.IS_NULLABLE,
            CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 'YES' ELSE 'NO' END AS IS_PRIMARY_KEY
        FROM INFORMATION_SCHEMA.COLUMNS c
        LEFT JOIN (
            SELECT ku.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
            WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
              AND tc.TABLE_NAME = ?
        ) pk ON c.COLUMN_NAME = pk.COLUMN_NAME
        WHERE c.TABLE_NAME = ?
        ORDER BY c.ORDINAL_POSITION
    """, table_name, table_name)

    columns = []
    for row in cursor.fetchall():
        col = {
            "name":        row.COLUMN_NAME,
            "type":        row.DATA_TYPE,
            "max_length":  row.CHARACTER_MAXIMUM_LENGTH,
            "nullable":    row.IS_NULLABLE,
            "primary_key": row.IS_PRIMARY_KEY,
        }
        columns.append(col)

    result["columns"] = columns

    # --- Indexes ---
    cursor.execute("""
        SELECT
            i.name                          AS index_name,
            i.type_desc                     AS index_type,
            i.is_unique,
            STRING_AGG(c.name, ', ')
                WITHIN GROUP (ORDER BY ic.key_ordinal) AS key_columns,
            STRING_AGG(
                CASE WHEN ic.is_included_column = 1 THEN c.name END, ', '
            ) AS included_columns
        FROM sys.indexes i
        JOIN sys.index_columns ic
            ON i.object_id = ic.object_id AND i.index_id = ic.index_id
        JOIN sys.columns c
            ON ic.object_id = c.object_id AND ic.column_id = c.column_id
        JOIN sys.tables t
            ON i.object_id = t.object_id
        WHERE t.name = ?
          AND i.type > 0
        GROUP BY i.name, i.type_desc, i.is_unique
        ORDER BY i.name
    """, table_name)

    indexes = []
    for row in cursor.fetchall():
        indexes.append({
            "name":             row.index_name,
            "type":             row.index_type,
            "unique":           row.is_unique,
            "key_columns":      row.key_columns,
            "included_columns": row.included_columns,
        })

    result["indexes"] = indexes

    # --- Row count estimate ---
    cursor.execute("""
        SELECT SUM(p.rows) AS row_count
        FROM sys.tables t
        JOIN sys.partitions p
            ON t.object_id = p.object_id
        WHERE t.name = ?
          AND p.index_id IN (0, 1)
    """, table_name)

    row = cursor.fetchone()
    result["estimated_row_count"] = row.row_count if row else "unknown"
    result["table_name"] = table_name

    conn.close()

    console.print(
        f"[green]✓[/green] Schema fetched — "
        f"{len(columns)} columns, {len(indexes)} indexes, "
        f"~{result['estimated_row_count']:,} rows"
        if isinstance(result['estimated_row_count'], int)
        else f"[green]✓[/green] Schema fetched — {len(columns)} columns, {len(indexes)} indexes"
    )

    return result


def get_view_definition(view_name: str) -> dict:
    """
    Fetches the full SQL definition of a view plus the list
    of underlying tables it references.

    Usage:
        view = get_view_definition("vw_dashboard")
    """
    console.print(f"[cyan]→ Fetching view definition:[/cyan] {view_name}")

    conn   = _get_connection()
    cursor = conn.cursor()

    # --- View SQL definition ---
    cursor.execute("""
        SELECT definition
        FROM sys.sql_modules sm
        JOIN sys.objects o ON sm.object_id = o.object_id
        WHERE o.type = 'V'
          AND o.name = ?
    """, view_name)

    row = cursor.fetchone()
    if not row:
        conn.close()
        console.print(f"[red]✗ View '{view_name}' not found in database[/red]")
        return {"error": f"View '{view_name}' not found"}

    definition = row.definition

    # --- Tables the view references ---
    cursor.execute("""
        SELECT DISTINCT OBJECT_NAME(referenced_id) AS referenced_table
        FROM sys.sql_expression_dependencies
        WHERE referencing_id = OBJECT_ID(?)
          AND referenced_id IS NOT NULL
    """, view_name)

    referenced_tables = [r.referenced_table for r in cursor.fetchall()]

    conn.close()

    console.print(
        f"[green]✓[/green] View fetched — "
        f"references {len(referenced_tables)} table(s): "
        f"{', '.join(referenced_tables)}"
    )

    return {
        "view_name":          view_name,
        "definition":         definition,
        "referenced_tables":  referenced_tables,
    }


def list_all_tables() -> list:
    """
    Returns a list of all user tables in the database.
    Useful for getting an overview of the whole schema.

    Usage:
        tables = list_all_tables()
    """
    conn   = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)

    tables = [row.TABLE_NAME for row in cursor.fetchall()]
    conn.close()

    return tables


def list_all_views() -> list:
    """
    Returns a list of all views in the database.

    Usage:
        views = list_all_views()
    """
    conn   = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT TABLE_NAME
        FROM INFORMATION_SCHEMA.VIEWS
        ORDER BY TABLE_NAME
    """)

    views = [row.TABLE_NAME for row in cursor.fetchall()]
    conn.close()

    return views


def test_connection() -> bool:
    """
    Quick connectivity check. Run this first to confirm
    your config.py connection string works.

    Usage:
        python -c "from tools.schema import test_connection; test_connection()"
    """
    try:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0].split('\n')[0]
        conn.close()
        console.print(f"[green]✓ Connected:[/green] {version}")
        return True
    except Exception as e:
        console.print(f"[red]✗ Connection failed:[/red] {e}")
        console.print("\n[yellow]Check your config.py:[/yellow]")
        console.print("  - Is SQL Server running?")
        console.print("  - Is the server name correct? (try 'localhost\\SQLEXPRESS')")
        console.print("  - Is the database name correct?")
        console.print("  - Is ODBC Driver 17 installed?")
        return False
