# Safety & State Management for SQL Deployments

## 1. The Sandbox Lifecycle State Machine
The Web UI must represent the `sandbox-test` command as a **Linear Pipeline** with terminal state persistence.

### Lifecycle Stages
| Step | UI State | Internal Operation | Visual Indicator |
| :--- | :--- | :--- | :--- |
| **1. Provision** | "Creating Shadow..." | `sandbox-create` | Pulsing cloud icon |
| **2. Ingest** | "Restoring Backup..." | RESTORE HEADERONLY/DATABASE | Loading bar (MB/s) |
| **3. Mutate** | "Applying Migrations..." | `migrator.py` apply logic | SQL line-by-line tick |
| **4. Validate** | "Running Benchmarks..." | `benchmarker.py` (Before vs After) | Speedup Gauge (+X%) |
| **5. Cleanup** | "Wiping Shadow..." | `sandbox-destroy` | Shredder animation |

### Rule: The "Sandbox Lock"
*   **Constraint:** The "Deploy to Production" button is **globally disabled** until a successful `completed` status is received for a `full-run` or `sandbox-test` job.
*   **Persistence:** If the sandbox fails, the UI must transition to **"Emergency Halt"** mode, preventing further actions until the error is acknowledged.

## 2. The 'Red Button' Component (Safety Gate)
Before any SQL hits the production server, the user must pass through the **Human-in-the-loop Gate**.

### Component: `DeploymentConfirmModal`
1.  **SQL Diff Viewer:** A Monaco-based editor showing the `original.sql` vs the `optimized.sql` with syntax highlighting.
2.  **Impact Summary:**
    *   Estimated Cost Delta: (e.g., `-45.2%`)
    *   Affected Rows: (e.g., `1,000,000+`)
    *   Index Count: `+2 new indexes`
3.  **The "Manual Type" Validation:**
    *   The "Apply to Production" button remains greyed out.
    *   Input Field: `Type "APPLY_TO_PROD" to proceed`.
    *   User must manually type the string to enable the `POST /api/deploy` trigger.

## 3. The Failure & Rollback UI
If `sandbox-run` or a migration fails, the UI must treat it as a **Forensic Site**.

### Error Presentation
*   **The Error Card:** Large Red header with the specific SQL State and Exception from `error_handler.py`.
*   **Log Injection:** Directly pipe the last 20 lines of `agent.log` into a scrollable terminal window within the error view.
*   **Rollback Preview:** Automatically load and display the contents of `rollback.sql`.
    *   Action: `Download Rollback Script` (for manual execution via SSMS if things are dire).

### The "Keep for Inspection" Flag
Matching the `--keep` flag in the CLI, the UI should offer a toggle:
*   `[ ] Keep Shadow DB on Failure`: If checked, the `sandbox-destroy` command is skipped, and the UI provides the connection string to the shadow database for manual debugging.

## 4. API & History Integration
Every transition in the state machine must be logged to the `jobs` table in `query_history.db`.

*   **Pending:** Job created, UI shows "In Queue".
*   **Running:** UI polls `started_at`, displays live SSE log stream.
*   **Failed:** UI displays the `error` column content and enables the "Forensic" view.
*   **Completed:** UI displays the `result` JSON (Speedup metrics, report paths).
