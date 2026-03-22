// src/components/dashboard/RecentRunsPanel.tsx
// Phase 1: static placeholder rows.
// Phase 3: replace with useEffect → historyApi.getHistory({ limit: 5 })

interface RunRow {
  id: number;
  time: string;
  label: string;
  tables: string;
  before_ms: number | null;
  after_ms: number | null;
  improvement_pct: number | null;
  migration: string | null;
  regression?: boolean;
}

const MOCK_RUNS: RunRow[] = [
  { id: 47, time: "14:10", label: "vw_dashboard machine filter",  tables: "measurements · sensors", before_ms: 847,  after_ms: 12,  improvement_pct: 98.6, migration: "#004" },
  { id: 46, time: "13:45", label: "sensor_readings aggregation",  tables: "sensor_readings",         before_ms: 1240, after_ms: 91,  improvement_pct: 92.7, migration: "#003" },
  { id: 45, time: "12:20", label: "machine_log date range",       tables: "machine_log",             before_ms: 320,  after_ms: 44,  improvement_pct: 86.3, migration: "#003" },
  { id: 44, time: "Yesterday", label: "vw_sensor_summary view",   tables: "vw_sensor_summary",       before_ms: 210,  after_ms: 248, improvement_pct: -18.1, migration: null, regression: true },
  { id: 43, time: "Yesterday", label: "measurements bulk read",   tables: "measurements",            before_ms: 550,  after_ms: 62,  improvement_pct: 88.7, migration: "#002" },
];

function ImpBadge({ pct }: { pct: number }) {
  const good = pct > 0;
  return (
    <span style={{
      background: good ? "var(--success-light)" : "var(--danger-light)",
      color: good ? "#166534" : "#991B1B",
      fontSize: 11, fontWeight: 500,
      padding: "2px 8px", borderRadius: 20,
    }}>
      {pct > 0 ? "+" : ""}{pct.toFixed(1)}%
    </span>
  );
}

export function RecentRunsPanel() {
  const successful  = MOCK_RUNS.filter(r => !r.regression && r.improvement_pct !== null && r.improvement_pct > 0);
  const avgImp      = successful.length
    ? (successful.reduce((s, r) => s + (r.improvement_pct ?? 0), 0) / successful.length).toFixed(1)
    : "—";
  const bestImp     = successful.length
    ? Math.max(...successful.map(r => r.improvement_pct ?? 0)).toFixed(1)
    : "—";
  const regressions = MOCK_RUNS.filter(r => r.regression).length;

  return (
    <div className="card" style={{ overflow: "hidden" }}>
      {/* Header */}
      <div style={{
        padding: "14px 18px",
        borderBottom: "0.5px solid var(--border)",
        display: "flex", alignItems: "center", justifyContent: "space-between",
      }}>
        <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)" }}>Recent Runs</span>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>
            {MOCK_RUNS.length} shown · avg{" "}
            <span style={{ color: "var(--success)", fontWeight: 500 }}>+{avgImp}%</span>
          </span>
          <span style={{ fontSize: 11, color: "var(--accent)", cursor: "pointer" }}>View all →</span>
        </div>
      </div>

      {/* Table */}
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "var(--bg-elevated)" }}>
            {["Time", "Label / Tables", "Before", "After", "Δ", "Mig"].map((h, i) => (
              <th key={h} style={{
                padding: "8px 12px",
                paddingLeft: i === 0 ? 18 : 12,
                paddingRight: i === 5 ? 18 : 12,
                textAlign: i >= 2 ? "right" : "left",
                fontSize: 10, fontWeight: 500,
                color: "var(--text-muted)",
                textTransform: "uppercase", letterSpacing: "0.06em",
                borderBottom: "0.5px solid var(--border)",
                whiteSpace: "nowrap",
              }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {MOCK_RUNS.map((run, idx) => (
            <tr
              key={run.id}
              style={{
                borderBottom: idx < MOCK_RUNS.length - 1 ? "0.5px solid var(--bg-elevated)" : "none",
                background: run.regression ? "#FFFDF5" : "transparent",
              }}
            >
              <td style={{ padding: "11px 12px 11px 18px", color: "var(--text-muted)", fontSize: 11, whiteSpace: "nowrap" }}>
                {run.time}
              </td>
              <td style={{ padding: "11px 12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 7, marginBottom: 1 }}>
                  <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)" }}>{run.label}</span>
                  {run.regression && (
                    <span style={{ background: "var(--warning-light)", color: "#B45309", fontSize: 9, fontWeight: 500, padding: "1px 6px", borderRadius: 4 }}>
                      regression
                    </span>
                  )}
                </div>
                <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1 }}>{run.tables}</div>
              </td>
              <td style={{ padding: "11px 12px", textAlign: "right" }}>
                <span className="font-mono" style={{ fontSize: 11, color: "var(--danger)" }}>
                  {run.before_ms !== null ? `${run.before_ms.toLocaleString()}ms` : "—"}
                </span>
              </td>
              <td style={{ padding: "11px 12px", textAlign: "right" }}>
                <span className="font-mono" style={{
                  fontSize: 11,
                  color: run.regression ? "var(--danger)" : "var(--success)",
                }}>
                  {run.after_ms !== null ? `${run.after_ms.toLocaleString()}ms` : "—"}
                </span>
              </td>
              <td style={{ padding: "11px 12px", textAlign: "right" }}>
                {run.improvement_pct !== null ? <ImpBadge pct={run.improvement_pct} /> : <span style={{ color: "var(--text-muted)" }}>—</span>}
              </td>
              <td style={{ padding: "11px 18px 11px 12px", textAlign: "center" }}>
                <span className="font-mono" style={{ fontSize: 10, color: run.migration ? "var(--accent)" : "var(--border-strong)" }}>
                  {run.migration ?? "—"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Footer stats */}
      <div style={{
        padding: "11px 18px",
        background: "var(--bg-elevated)",
        borderTop: "0.5px solid var(--border)",
        display: "flex", gap: 22, flexWrap: "wrap",
      }}>
        {[
          { label: "Avg improvement", value: `+${avgImp}%`, color: "var(--success)" },
          { label: "Best ever",       value: `${bestImp}%`, color: "var(--text-primary)" },
          { label: "Regressions",     value: String(regressions), color: regressions > 0 ? "var(--warning)" : "var(--text-primary)" },
          { label: "Migrations total",value: "12",          color: "var(--text-primary)" },
          { label: "Pending deploy",  value: "3",           color: "var(--danger)" },
        ].map(s => (
          <div key={s.label}>
            <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{s.label} </span>
            <span style={{ fontSize: 12, fontWeight: 500, color: s.color }}>{s.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
