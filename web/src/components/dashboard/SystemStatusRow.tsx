// src/components/dashboard/SystemStatusRow.tsx
import { useSystemStore } from "@/store/systemStore";

interface StatusPillProps {
  label: string;
  note: string;
  status: "online" | "offline" | "warning" | "info";
}

function StatusPill({ label, note, status }: StatusPillProps) {
  const borderColors = {
    online:  "var(--border)",
    offline: "var(--danger)",
    warning: "var(--warning)",
    info:    "#BFDBFE",
  };
  const noteColors = {
    online:  "var(--text-secondary)",
    offline: "var(--danger)",
    warning: "var(--warning)",
    info:    "var(--accent)",
  };
  const dotColors = {
    online:  "var(--success)",
    offline: "var(--danger)",
    warning: "var(--warning)",
    info:    "var(--accent)",
  };

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 7,
      background: "var(--bg-surface)",
      border: `0.5px solid ${borderColors[status]}`,
      borderRadius: 6,
      padding: "6px 12px",
    }}>
      <div className="status-dot" style={{ background: dotColors[status] }} />
      <span style={{ fontSize: 11, fontWeight: 500, color: "var(--text-primary)" }}>{label}</span>
      <span style={{ fontSize: 11, color: "#CBD5E1" }}>·</span>
      <span style={{ fontSize: 11, color: noteColors[status] }}>{note}</span>
    </div>
  );
}

export function SystemStatusRow() {
  const stats = useSystemStore(s => s.stats);

  const dbStatus  = stats?.db.status  === "online" ? "online"
    : stats?.db.status                             ? "offline" : "offline";
  const olStatus  = stats?.ollama.status === "online" ? "online" : "offline";

  const dbNote    = stats?.db.status === "online"
    ? `${stats.db.database} · ${stats.db.server}`
    : stats?.db.error ?? "offline";

  const olNote    = stats?.ollama.status === "online"
    ? `online · ${stats.ollama.active_models.length} model${stats.ollama.active_models.length !== 1 ? "s" : ""}`
    : "offline";

  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
      <StatusPill
        label={stats?.db.database || "Database"}
        note={stats ? dbNote : "connecting..."}
        status={stats ? (dbStatus as "online" | "offline") : "warning"}
      />
      <StatusPill
        label="Ollama"
        note={stats ? olNote : "connecting..."}
        status={stats ? (olStatus as "online" | "offline") : "warning"}
      />
      <StatusPill
        label="Git"
        note="clean · auto-commit on"
        status="online"
      />
      <StatusPill
        label="Schema snapshot"
        note="today, 07:01"
        status="info"
      />
    </div>
  );
}
