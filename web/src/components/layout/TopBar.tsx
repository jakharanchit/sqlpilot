// src/components/layout/TopBar.tsx
import { useSystemStore } from "@/store/systemStore";

interface Props {
  title: string;
  actions?: React.ReactNode;
}

export default function TopBar({ title, actions }: Props) {
  const lastUpdated = useSystemStore(s => s.lastUpdated);

  const timeStr = lastUpdated
    ? lastUpdated.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })
    : null;

  return (
    <header style={{
      height: "var(--topbar-height)",
      background: "var(--bg-surface)",
      borderBottom: "0.5px solid var(--border)",
      display: "flex",
      alignItems: "center",
      padding: "0 24px",
      gap: 12,
      flexShrink: 0,
      position: "sticky",
      top: 0,
      zIndex: 10,
    }}>
      <h1 style={{ fontSize: 15, fontWeight: 500, color: "var(--text-primary)", flex: 1, margin: 0 }}>
        {title}
      </h1>

      {actions}

      {timeStr && (
        <div style={{
          display: "flex", alignItems: "center", gap: 5,
          padding: "5px 12px",
          background: "var(--bg-elevated)",
          border: "0.5px solid var(--border)",
          borderRadius: 6,
        }}>
          <span style={{ fontSize: 11, color: "var(--text-muted)" }}>Refreshed</span>
          <span style={{ fontSize: 11, fontWeight: 500, color: "var(--text-secondary)" }}>{timeStr}</span>
        </div>
      )}
    </header>
  );
}
