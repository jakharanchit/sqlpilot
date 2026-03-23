"""
bridge/routers/plan.py
Phase 6 — Execution plan analysis and tree extraction.

Calls tools/executor.py to fetch the plan XML from SQL Server,
then builds a nested operator tree for the D3 visualizer.
"""
import uuid
import re
import xml.etree.ElementTree as ET
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/plan", tags=["plan"])

# ── Expensive operator catalogue ──────────────────────────────────────────────
EXPENSIVE_OPERATORS = {
    "Table Scan":           ("HIGH",   "Entire table read — no index used"),
    "Clustered Index Scan": ("HIGH",   "Full clustered index scan — filter may not be sargable"),
    "Index Scan":           ("MEDIUM", "Full non-clustered index scan — consider more selective index"),
    "Key Lookup":           ("HIGH",   "Extra heap read — index is missing INCLUDE columns"),
    "RID Lookup":           ("HIGH",   "Heap lookup — table has no clustered index"),
    "Hash Match":           ("MEDIUM", "Large dataset join — index on join columns may help"),
    "Sort":                 ("MEDIUM", "Explicit sort in memory — index could eliminate this"),
    "Parallelism":          ("INFO",   "Query went parallel — may indicate a large table scan"),
    "Lazy Spool":           ("MEDIUM", "Data spooled to tempdb — may indicate nested loop issue"),
    "Eager Spool":          ("MEDIUM", "Data spooled to tempdb eagerly"),
}


class PlanRequest(BaseModel):
    query:  str
    actual: bool = True


@router.post("/from-query")
def plan_from_query(body: PlanRequest):
    """
    Run the query against SQL Server, capture the execution plan XML,
    extract the operator tree, and return a StructuredPlan dict.
    Runs synchronously — plan capture is typically fast (< 5s).
    """
    if not body.query.strip():
        raise HTTPException(400, "Query cannot be empty")

    from tools.executor import fetch_execution_plan

    raw = fetch_execution_plan(body.query.strip(), actual=body.actual)

    if "error" in raw:
        raise HTTPException(422, f"Plan capture failed: {raw['error']}")

    xml_str = raw.get("xml", "")
    if not xml_str:
        raise HTTPException(422, "SQL Server returned no plan XML")

    # Build the operator tree from raw XML
    tree, total_cost, operator_count = _build_tree(xml_str)

    # Re-compute cost_pct for all nodes now that we know total_cost
    if total_cost > 0:
        _annotate_pct(tree, total_cost)

    # Collect flat flagged list (any node with severity set)
    flagged: list = []
    _collect_flagged(tree, flagged)

    return {
        "plan_type":       raw.get("plan_type", "estimated"),
        "elapsed_ms":      raw.get("elapsed_ms"),
        "row_count":       raw.get("row_count"),
        "total_cost":      round(total_cost, 6),
        "operator_count":  operator_count,
        "tree":            tree,
        "warnings":        raw.get("warnings", []),
        "missing_indexes": raw.get("missing_indexes", []),
        "flagged":         flagged,
        "query":           body.query.strip(),
    }


@router.get("/operators")
def operator_catalogue():
    """Returns the known expensive operator types for the UI legend."""
    return [
        {"name": name, "severity": sev, "reason": reason}
        for name, (sev, reason) in EXPENSIVE_OPERATORS.items()
    ]


# ── Tree extraction from XML ───────────────────────────────────────────────────

_NS_RE = re.compile(r'\{[^}]*\}')   # strips XML namespace prefix


def _tag(elem) -> str:
    return _NS_RE.sub('', elem.tag)


def _build_tree(xml_str: str):
    """
    Parse plan XML and return (root_node, total_cost, operator_count).

    SQL Server plan XML structure:
        <ShowPlanXML>
          <BatchSequence>
            <Batch>
              <Statements>
                <StmtSimple>
                  <QueryPlan>
                    <RelOp PhysicalOp="..." EstimatedTotalSubtreeCost="...">
                      <RelOp ...>          ← children
                        ...
                      </RelOp>
                    </RelOp>
                  </QueryPlan>
                </StmtSimple>
              </Statements>
            </Batch>
          </BatchSequence>
        </ShowPlanXML>

    We find the outermost RelOp (highest subtree cost = root) and walk recursively.
    """
    # Wrap in a root element so multiple XML docs in the string parse safely
    try:
        wrapped = ET.fromstring(f"<Root>{xml_str}</Root>")
    except ET.ParseError as e:
        raise HTTPException(422, f"Could not parse plan XML: {e}")

    # Find all RelOp elements
    all_elems = list(wrapped.iter())
    relops = [e for e in all_elems if _tag(e) == "RelOp"]

    if not relops:
        raise HTTPException(422, "No operator nodes found in plan XML")

    # The root RelOp has the highest EstimatedTotalSubtreeCost
    root_relop = max(relops, key=lambda e: float(e.get("EstimatedTotalSubtreeCost", 0)))
    total_cost = float(root_relop.get("EstimatedTotalSubtreeCost", 0))

    counter = {"n": 0}
    root_node = _parse_relop(root_relop, counter)

    return root_node, total_cost, counter["n"]


def _parse_relop(elem, counter: dict) -> dict:
    """
    Recursively convert a RelOp XML element into a PlanOperator dict.
    Only includes direct RelOp children (not grandchildren via double-descent).
    """
    counter["n"] += 1
    op_id    = str(uuid.uuid4())[:8]
    name     = elem.get("PhysicalOp", elem.get("LogicalOp", "Unknown"))
    cost     = float(elem.get("EstimatedTotalSubtreeCost", 0))
    est_rows = round(float(elem.get("EstimateRows", 0)))

    # Actual rows — lives inside <RunTimeInformation><RunTimeCountersPerThread>
    act_rows = None
    for rt in elem.iter():
        if _tag(rt) == "RunTimeCountersPerThread":
            try:
                act_rows = round(float(rt.get("ActualRows", 0)))
            except (TypeError, ValueError):
                pass
            break

    # Object info (table/index name) from the first <IndexScan> or <TableScan> child
    obj_name  = None
    seek_pred = None
    for child in elem:
        child_tag = _tag(child)
        if child_tag in ("IndexScan", "TableScan"):
            obj_elem = child.find(".//{*}Object")
            if obj_elem is not None:
                parts = [
                    obj_elem.get("Table", ""),
                    obj_elem.get("Index", ""),
                ]
                obj_name = ".".join(p.strip("[]") for p in parts if p)
            # Seek predicates
            sp_elems = child.findall(".//{*}SeekPredicates//{*}ScalarOperator")
            if sp_elems:
                seek_pred = ", ".join(
                    e.get("ScalarString", "") for e in sp_elems[:3]
                    if e.get("ScalarString")
                )
            break

    # Severity
    severity = None
    reason   = ""
    if name in EXPENSIVE_OPERATORS:
        sev, rsn = EXPENSIVE_OPERATORS[name]
        severity = sev
        reason   = rsn

    # Collect direct child RelOps.
    # RelOps are nested inside operator-specific wrappers like <NestedLoops>,
    # <Hash>, <IndexScan> etc. We go one level deep to find them.
    child_relops_seen: set = set()
    children_nodes = []

    for child in elem:
        # Direct RelOp child (unusual but possible)
        if _tag(child) == "RelOp":
            cid = id(child)
            if cid not in child_relops_seen:
                child_relops_seen.add(cid)
                children_nodes.append(_parse_relop(child, counter))
        else:
            # One level down — operator wrapper elements contain child RelOps
            for grandchild in child:
                if _tag(grandchild) == "RelOp":
                    cid = id(grandchild)
                    if cid not in child_relops_seen:
                        child_relops_seen.add(cid)
                        children_nodes.append(_parse_relop(grandchild, counter))

    return {
        "id":        op_id,
        "name":      name,
        "cost":      round(cost, 6),
        "cost_pct":  0.0,          # filled in by _annotate_pct
        "est_rows":  est_rows,
        "act_rows":  act_rows,
        "severity":  severity,
        "reason":    reason,
        "object":    obj_name,
        "seek_pred": seek_pred,
        "children":  children_nodes,
    }


def _annotate_pct(node: dict, total_cost: float):
    """Walk tree and set cost_pct on every node."""
    node["cost_pct"] = round((node["cost"] / total_cost) * 100, 1) if total_cost > 0 else 0.0
    for child in node.get("children", []):
        _annotate_pct(child, total_cost)


def _collect_flagged(node: dict, out: list):
    """Collect all nodes with severity into a flat list."""
    if node.get("severity"):
        out.append(node)
    for child in node.get("children", []):
        _collect_flagged(child, out)
