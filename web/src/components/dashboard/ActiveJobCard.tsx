// src/components/dashboard/ActiveJobCard.tsx
// Phase 1: static placeholder showing the card structure.
// Phase 2: wires to jobStore — real step progress and SSE log stream.

const STEPS = [
  "Tables", "Schema", "Exec Plan", "Parse Plan",
  "Diagnose", "Rewrite", "Extract", "Save & Git", "Results",
];

interface Props {
  // Phase 2 will inject these from jobStore
  activeStep?: number;     // 1-based, 0 = no active job
  label?: string;
  query?: string;
  tables?: string;
  elapsedStr?: string;
  logLines?: string[];
}

export function ActiveJobCard({
  activeStep = 0,
  label = "",
  query = "",
  tables = "",
  elapsedStr = "",
  logLines = [],
}: Props) {

  if (activeStep === 0) {
    return (
      <div className="card" style={{
        padding: "22px 18px",
        display: "flex", alignItems: "center", gap: 16,
        color: "var(--text-muted)",
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: "var(--bg-elevated)",
          display: "flex", alignItems: "center", justifyContent: "center",
          flexShrink: 0,
        }}>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
            <circle cx="8" cy="8" r="6.5" stroke="var(--text-muted)" strokeWidth="1.3" />
            <path d="M6 8l1.5 1.5L11 6" stroke="var(--text-muted)" strokeWidth="1.3"
              strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 500, color: "var(--text-secondary)" }}>No active job</div>
          <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
            Go to Query Optimizer to start a full-run
          </div>
        </div>
        <a
          href="/optimizer"
          style={{
            marginLeft: "auto",
            fontSize: 11, color: "var(--accent)",
            textDecoration: "none",
            padding: "5px 12px",
            border: "0.5px solid var(--accent-light)",
            borderRadius: 6,
            background: "var(--accent-light)",
          }}
        >
          New optimization →
        </a>
      </div>
    );
  }

  const progressPct = Math.round((activeStep / STEPS.length) * 100);

  return (
    <div className="card" style={{ overflow: "hidden" }}>

      {/* Header */}
      <div style={{
        padding: "14px 18px",
        borderBottom: "0.5px solid var(--border)",
        display: "flex", alignItems: "flex-start", gap: 12,
      }}>
        <div
          className="animate-blink"
          style={{
            width: 8, height: 8, borderRadius: "50%",
            background: "var(--warning)", flexShrink: 0, marginTop: 3,
          }}
        />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)" }}>Active Job</span>
            <span className="badge badge-neutral" style={{ fontSize: 10 }}>full_run</span>
            {tables && (
              <span className="badge badge-neutral" style={{ fontSize: 10 }}>{tables}</span>
            )}
          </div>
          {query && (
            <div className="font-mono" style={{
              fontSize: 11, color: "var(--text-secondary)",
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
            }}>
              {query}
            </div>
          )}
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div style={{ fontSize: 12, fontWeight: 500, color: "var(--warning)" }}>
            Step {activeStep} / {STEPS.length}
          </div>
          {elapsedStr && (
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 2 }}>
              elapsed {elapsedStr}
            </div>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div style={{ height: 3, background: "var(--bg-elevated)" }}>
        <div style={{
          width: `${progressPct}%`, height: "100%",
          background: "var(--accent)",
          transition: "width 0.4s ease",
        }} />
      </div>

      {/* Step bubbles */}
      <div style={{
        padding: "14px 18px 10px",
        display: "flex", alignItems: "flex-start",
        overflowX: "auto",
      }}>
        {STEPS.map((step, i) => {
          const stepNum = i + 1;
          const done    = stepNum < activeStep;
          const active  = stepNum === activeStep;
          const pending = stepNum > activeStep;

          return (
            <div
              key={step}
              style={{
                display: "flex", alignItems: "center",
                flex: i < STEPS.length - 1 ? 1 : undefined,
                minWidth: 44,
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
                {/* Bubble */}
                <div style={{
                  width: 22, height: 22, borderRadius: "50%",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  background: done ? "var(--success-light)" : active ? "#DBEAFE" : "var(--bg-elevated)",
                  border: `${active ? 2 : 1.5}px solid ${done ? "var(--success)" : active ? "var(--accent)" : "var(--border)"}`,
                }}>
                  {done ? (
                    <svg width="10" height="10" viewBox="0 0 10 10" fill="none">
                      <path d="M2 5l2 2 4-4" stroke="var(--success)" strokeWidth="1.5"
                        strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : active ? (
                    <div
                      className="animate-blink"
                      style={{ width: 7, height: 7, borderRadius: "50%", background: "var(--accent)" }}
                    />
                  ) : (
                    <span style={{ fontSize: 9, color: "var(--border-strong)", fontWeight: 500 }}>
                      {stepNum}
                    </span>
                  )}
                </div>
                {/* Label */}
                <span style={{
                  fontSize: 9,
                  color: done ? "var(--success)" : active ? "var(--accent)" : "var(--border-strong)",
                  fontWeight: active ? 500 : 400,
                  textAlign: "center", width: 48, lineHeight: 1.2,
                }}>
                  {step}
                </span>
              </div>

              {/* Connector line */}
              {i < STEPS.length - 1 && (
                <div style={{
                  flex: 1, height: 1.5, marginBottom: 12, margin: "0 2px 12px 2px",
                  background: done ? "var(--success-light)" : stepNum === activeStep ? "#BFDBFE" : "var(--border)",
                }} />
              )}
            </div>
          );
        })}
      </div>

      {/* Live log */}
      {logLines.length > 0 && (
        <div style={{ margin: "0 18px 16px" }}>
          <div style={{
            background: "var(--bg-elevated)",
            border: "0.5px solid var(--border)",
            borderRadius: 7, overflow: "hidden",
          }}>
            <div style={{
              padding: "7px 12px",
              borderBottom: "0.5px solid var(--border)",
              display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
              <span style={{ fontSize: 10, fontWeight: 500, color: "var(--text-secondary)" }}>Live output</span>
              <span style={{ fontSize: 10, color: "var(--text-muted)" }}>auto-scroll on</span>
            </div>
            <div className="font-mono" style={{ padding: "10px 14px", fontSize: 11, lineHeight: 1.8, color: "var(--text-secondary)" }}>
              {logLines.slice(-6).map((line, i) => (
                <div key={i} dangerouslySetInnerHTML={{ __html: colorizeLogLine(line) }} />
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/** Minimal log colorization — applies span colors for known prefixes */
function colorizeLogLine(line: string): string {
  const esc = line.replace(/</g, "&lt;").replace(/>/g, "&gt;");
  if (esc.startsWith("  ✓") || esc.startsWith("✓"))
    return `<span style="color:var(--success)">${esc}</span>`;
  if (esc.includes("[HIGH]") || esc.includes("[✗]"))
    return esc.replace(/\[HIGH\]/g, `<span style="color:var(--danger)">[HIGH]</span>`);
  if (esc.startsWith("→") || esc.startsWith("  →"))
    return `<span style="color:var(--accent)">${esc}</span>`;
  if (esc.includes("model:") || esc.startsWith("  "))
    return `<span style="color:var(--text-muted)">${esc}</span>`;
  return esc;
}
