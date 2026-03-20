# ============================================================
# tools/executor.py
# Fetches execution plan XML directly from SQL Server.
# No manual SSMS export needed — runs the query, captures
# both the estimated plan and actual execution statistics.
#
# HOW SQL SERVER PLAN CAPTURE WORKS:
#   SET SHOWPLAN_XML ON  → estimated plan (doesn't run query)
#   SET STATISTICS XML ON → actual plan  (runs query, captures real stats)
#
# We use STATISTICS XML (actual) by default because:
#   - Shows real row counts vs estimates (reveals cardinality issues)
#   - Captures actual operator costs based on real data
#   - DeepSeek-R1 gets much better signal from actual vs estimated
# ============================================================

import re
import time
import xml.etree.ElementTree as ET

import pyodbc
from rich.console import Console
from rich.live import Live
from rich.spinner import Spinner
from rich.text import Text

from config import DB_CONFIG

console = Console()


def _get_connection():
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


# ============================================================
# MAIN: fetch_execution_plan
# ============================================================

def fetch_execution_plan(query: str, actual: bool = True) -> dict:
    """
    Executes the query against SQL Server and captures the
    execution plan XML automatically.

    Args:
        query:  the SQL query to analyze
        actual: True  = actual execution plan (runs query, real stats)
                False = estimated plan only   (doesn't run query)

    Returns:
        dict with keys:
            xml          — raw plan XML string
            plan_type    — "actual" or "estimated"
            elapsed_ms   — how long the query took to run (actual only)
            row_count    — rows returned
            operators    — list of parsed operator summaries
            warnings     — list of warnings found in plan
            missing_indexes — missing index hints from SQL Server
            summary      — plain-text summary for terminal display
            error        — set if something went wrong

    Usage:
        plan = fetch_execution_plan("SELECT * FROM vw_dashboard WHERE machine_id=1")
        plan = fetch_execution_plan("SELECT ...", actual=False)  # estimated only
    """
    plan_type   = "actual" if actual else "estimated"
    set_command = "SET STATISTICS XML ON" if actual else "SET SHOWPLAN_XML ON"
    off_command = "SET STATISTICS XML OFF" if actual else "SET SHOWPLAN_XML OFF"

    console.print(f"  [dim]→ Fetching {plan_type} execution plan from SQL Server...[/dim]")

    conn   = None
    xml_plan = ""
    elapsed_ms = 0
    row_count  = 0

    try:
        conn   = _get_connection()
        cursor = conn.cursor()

        # Turn on plan capture
        cursor.execute(set_command)

        # Run the query and time it
        start = time.perf_counter()
        cursor.execute(query)

        # Collect ALL result sets — SQL Server returns:
        #   Result set 1: the actual query results
        #   Result set 2+: the XML plan(s)
        xml_parts = []

        while True:
            try:
                rows = cursor.fetchall()
                if rows:
                    # Check if this looks like XML plan data
                    first_val = str(rows[0][0]) if rows[0] else ""
                    if first_val.strip().startswith("<"):
                        for row in rows:
                            xml_parts.append(str(row[0]))
                    else:
                        # This is the actual query result set
                        row_count = len(rows)

                if not cursor.nextset():
                    break
            except Exception:
                break

        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        # Turn off plan capture
        cursor.execute(off_command)
        conn.close()

        xml_plan = "\n".join(xml_parts)

        if not xml_plan:
            return {
                "error": "No execution plan XML returned. "
                         "Try running the query manually in SSMS first to confirm it works.",
                "plan_type": plan_type,
            }

    except pyodbc.ProgrammingError as e:
        if conn:
            conn.close()
        return {
            "error": f"Query syntax error: {e}",
            "plan_type": plan_type,
        }
    except Exception as e:
        if conn:
            conn.close()
        return {
            "error": f"Failed to fetch execution plan: {e}",
            "plan_type": plan_type,
        }

    # Parse the XML for key insights
    parsed = _parse_plan_xml(xml_plan)

    console.print(
        f"  [green]✓[/green] Execution plan captured "
        f"[dim]({elapsed_ms}ms · {row_count} rows · "
        f"{len(parsed['operators'])} operators · "
        f"{len(parsed['flagged'])} flagged)[/dim]"
    )

    return {
        "xml":             xml_plan,
        "plan_type":       plan_type,
        "elapsed_ms":      elapsed_ms,
        "row_count":       row_count,
        "operators":       parsed["operators"],
        "flagged":         parsed["flagged"],
        "warnings":        parsed["warnings"],
        "missing_indexes": parsed["missing_indexes"],
        "summary":         parsed["summary"],
    }


# ============================================================
# XML PARSING
# ============================================================

# Operators that always indicate a problem
EXPENSIVE_OPERATORS = {
    "Table Scan":           ("HIGH",   "Entire table read — no index used"),
    "Clustered Index Scan": ("HIGH",   "Full index scan — filter may not be sargable"),
    "Index Scan":           ("MEDIUM", "Full index scan — consider more selective index"),
    "Key Lookup":           ("HIGH",   "Extra heap read — index missing INCLUDE columns"),
    "Hash Match":           ("MEDIUM", "Large data join — index on join columns may help"),
    "Sort":                 ("MEDIUM", "Explicit sort — index could eliminate this"),
    "Parallelism":          ("INFO",   "Query went parallel — may indicate large table scan"),
    "RID Lookup":           ("HIGH",   "Heap lookup — table has no clustered index"),
    "Lazy Spool":           ("MEDIUM", "Data spooled to tempdb — may indicate nested loop issue"),
}


def _parse_plan_xml(xml_str: str) -> dict:
    """
    Extracts key performance signals from execution plan XML.
    Returns structured data instead of raw XML for cleaner AI prompts.
    """
    operators      = []
    warnings       = []
    missing_indexes = []
    flagged        = []

    try:
        # Handle multiple XML documents in one string
        # Wrap in root element to parse safely
        wrapped = f"<Root>{xml_str}</Root>"
        root    = ET.fromstring(wrapped)

        # Walk all elements
        for elem in root.iter():
            tag = elem.tag.split("}")[-1]  # strip namespace

            # RelOp = individual operator nodes
            if tag == "RelOp":
                op_name  = elem.get("PhysicalOp", elem.get("LogicalOp", "Unknown"))
                cost     = float(elem.get("EstimatedTotalSubtreeCost", 0))
                est_rows = float(elem.get("EstimateRows", 0))
                act_rows_elem = elem.find(".//{http://schemas.microsoft.com/sqlserver/2004/07/showplan}ActualRows")
                act_rows = float(act_rows_elem.text) if act_rows_elem is not None else None

                op_data = {
                    "name":      op_name,
                    "cost":      cost,
                    "est_rows":  round(est_rows),
                    "act_rows":  round(act_rows) if act_rows is not None else None,
                }

                # Flag if this is an expensive operator type
                if op_name in EXPENSIVE_OPERATORS:
                    severity, reason = EXPENSIVE_OPERATORS[op_name]
                    flagged.append({**op_data, "severity": severity, "reason": reason})

                operators.append(op_data)

            # Warnings block
            if tag == "Warnings":
                for child in elem:
                    child_tag = child.tag.split("}")[-1]
                    if child_tag == "PlanAffectingConvert":
                        warnings.append({
                            "type":   "ImplicitConversion",
                            "column": child.get("Column", "?"),
                            "issue":  child.get("ConvertIssue", "?"),
                            "expr":   child.get("Expression", "?"),
                        })
                    elif child_tag == "NoJoinPredicate":
                        warnings.append({
                            "type":  "NoJoinPredicate",
                            "issue": "Missing JOIN predicate — potential cross join",
                        })
                    elif child_tag == "SpillToTempDb":
                        warnings.append({
                            "type":  "TempDbSpill",
                            "issue": "Sort or hash spilled to tempdb — memory pressure",
                        })

            # Missing index hints from SQL Server itself
            if tag == "MissingIndex":
                cols = []
                for cg in elem.findall(".//{http://schemas.microsoft.com/sqlserver/2004/07/showplan}ColumnGroup"):
                    usage     = cg.get("Usage", "")
                    col_names = [c.get("Name", "") for c in cg]
                    cols.append(f"{usage}({', '.join(col_names)})")
                missing_indexes.append({
                    "impact":  elem.get("Impact", "?"),
                    "columns": cols,
                })

    except ET.ParseError as e:
        # XML parse failed — return what we have with a note
        warnings.append({"type": "ParseWarning", "issue": f"Could not fully parse plan XML: {e}"})

    # Sort operators by cost
    operators.sort(key=lambda x: x["cost"], reverse=True)

    # Build a text summary for terminal output
    summary_lines = []
    if flagged:
        summary_lines.append(f"Flagged operators: {len(flagged)}")
        for f in flagged[:5]:
            summary_lines.append(f"  [{f['severity']}] {f['name']} — {f['reason']}")
    if warnings:
        summary_lines.append(f"Warnings: {len(warnings)}")
        for w in warnings:
            if w["type"] == "ImplicitConversion":
                summary_lines.append(f"  ⚠ Implicit conversion on column: {w['column']}")
            else:
                summary_lines.append(f"  ⚠ {w['type']}: {w['issue']}")
    if missing_indexes:
        summary_lines.append(f"Missing index hints: {len(missing_indexes)}")
        for mi in missing_indexes:
            summary_lines.append(f"  → Impact {mi['impact']}%: {'; '.join(mi['columns'])}")

    return {
        "operators":       operators,
        "flagged":         flagged,
        "warnings":        warnings,
        "missing_indexes": missing_indexes,
        "summary":         "\n".join(summary_lines),
    }


def format_plan_for_prompt(plan: dict) -> str:
    """
    Converts parsed plan data into a compact, focused text block
    for inclusion in AI prompts. Avoids sending raw XML (too large).
    """
    if "error" in plan:
        return f"[Execution plan unavailable: {plan['error']}]"

    lines = [
        f"EXECUTION PLAN ({plan['plan_type'].upper()}) — {plan.get('elapsed_ms', '?')}ms · {plan.get('row_count', '?')} rows",
        "",
    ]

    if plan["flagged"]:
        lines.append("FLAGGED OPERATORS (problems found):")
        for op in plan["flagged"]:
            act = f" | actual rows: {op['act_rows']}" if op.get("act_rows") is not None else ""
            lines.append(
                f"  [{op['severity']}] {op['name']} "
                f"(est rows: {op['est_rows']}{act}) — {op['reason']}"
            )
        lines.append("")

    if plan["warnings"]:
        lines.append("WARNINGS:")
        for w in plan["warnings"]:
            if w["type"] == "ImplicitConversion":
                lines.append(
                    f"  ⚠ IMPLICIT CONVERSION on '{w['column']}' "
                    f"({w['issue']}) — prevents index use"
                )
            else:
                lines.append(f"  ⚠ {w['type']}: {w['issue']}")
        lines.append("")

    if plan["missing_indexes"]:
        lines.append("SQL SERVER MISSING INDEX HINTS:")
        for mi in plan["missing_indexes"]:
            lines.append(f"  Impact {mi['impact']}%: {'; '.join(mi['columns'])}")
        lines.append("")

    if plan["operators"]:
        lines.append("TOP OPERATORS BY COST:")
        for op in plan["operators"][:6]:
            act = f" | actual: {op['act_rows']}" if op.get("act_rows") is not None else ""
            lines.append(f"  {op['name']} — est rows: {op['est_rows']}{act} | cost: {op['cost']:.4f}")

    return "\n".join(lines)
