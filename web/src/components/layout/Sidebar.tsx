// src/components/layout/Sidebar.tsx
import { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import clsx from "clsx";
import { useSystemStore } from "@/store/systemStore";
import { useClientStore } from "@/store/clientStore";
import { schemaApi } from "@/api/schema";
import type { SchemaAll } from "@/types/schema";

// ── Nav icon helpers ──────────────────────────────────────────────────────────
function DashIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="1" y="1" width="5" height="5" rx="1.2" fill="currentColor" />
      <rect x="8" y="1" width="5" height="5" rx="1.2" fill="currentColor" />
      <rect x="1" y="8" width="5" height="5" rx="1.2" fill="currentColor" />
      <rect x="8" y="8" width="5" height="5" rx="1.2" fill="currentColor" />
    </svg>
  );
}
function OptimizerIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M2 3.5h10M4.5 7h7M7 10.5h5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="3" cy="7" r="1.2" fill="currentColor" />
    </svg>
  );
}
function PlanIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="5.5" y="1" width="3" height="2.5" rx="0.8" fill="currentColor" />
      <rect x="1" y="10.5" width="3" height="2.5" rx="0.8" fill="currentColor" />
      <rect x="10" y="10.5" width="3" height="2.5" rx="0.8" fill="currentColor" />
      <path d="M7 3.5v3.5M7 7l-4.5 3M7 7l4.5 3" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  );
}
function DeployIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <path d="M7 1L1.5 4v4c0 3 2.3 5 5.5 5.5C10.2 13 12.5 11 12.5 8V4L7 1Z"
        stroke="currentColor" strokeWidth="1.3" />
      <path d="M4.5 7l2 2 3-3" stroke="currentColor" strokeWidth="1.2"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
function HistoryIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M7 4v3.5l2.5 1.5" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}
function ModelIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <rect x="1" y="4.5" width="12" height="5" rx="1.5" stroke="currentColor" strokeWidth="1.3" />
      <path d="M4 7h6" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
      <circle cx="10" cy="7" r="1" fill="currentColor" />
    </svg>
  );
}
function ClientIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="5" r="2.2" stroke="currentColor" strokeWidth="1.3" />
      <path d="M2 13c0-2.5 2.2-4.5 5-4.5s5 2 5 4.5"
        stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}
function SettingsIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
      <circle cx="7" cy="7" r="2" stroke="currentColor" strokeWidth="1.3" />
      <path d="M7 1v1.5M7 11.5V13M1 7h1.5M11.5 7H13M2.9 2.9l1 1M10.1 10.1l1 1M2.9 11.1l1-1M10.1 3.9l1-1"
        stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}
function ChevronIcon({ open }: { open: boolean }) {
  return (
    <svg
      width="10" height="10" viewBox="0 0 10 10" fill="none"
      style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 0.15s" }}
    >
      <path d="M2 3.5l3 3 3-3" stroke="currentColor" strokeWidth="1.3"
        strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

// ── NavItem ───────────────────────────────────────────────────────────────────
interface NavItemProps {
  to: string;
  icon: React.ReactNode;
  label: string;
  badge?: React.ReactNode;
}

function NavItem({ to, icon, label, badge }: NavItemProps) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) => clsx("nav-item", isActive && "active")}
    >
      {icon}
      <span style={{ flex: 1 }}>{label}</span>
      {badge}
    </NavLink>
  );
}

// ── Schema tree ───────────────────────────────────────────────────────────────
interface SchemaTreeProps {
  schema: SchemaAll | null;
  loading: boolean;
}

function SchemaTree({ schema, loading }: SchemaTreeProps) {
  const [tablesOpen, setTablesOpen] = useState(true);
  const [viewsOpen, setViewsOpen]   = useState(false);
  const navigate = useNavigate();

  if (loading) {
    return (
      <div style={{ padding: "8px 4px" }}>
        {[...Array(4)].map((_, i) => (
          <div key={i} style={{
            height: 14, borderRadius: 4,
            background: "var(--bg-elevated)",
            marginBottom: 8,
            width: `${60 + Math.random() * 30}%`,
            opacity: 0.6,
          }} />
        ))}
      </div>
    );
  }

  if (!schema) return null;

  return (
    <div style={{ fontSize: 11 }}>
      {/* Tables */}
      <button
        onClick={() => setTablesOpen(v => !v)}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          width: "100%", background: "none", border: "none",
          padding: "5px 4px", cursor: "pointer",
          color: "var(--text-muted)", fontSize: 10,
          textTransform: "uppercase", letterSpacing: "0.07em",
          fontWeight: 500,
        }}
      >
        <ChevronIcon open={tablesOpen} />
        Tables ({schema.table_count})
      </button>
      {tablesOpen && (
        <div style={{ paddingLeft: 8, marginBottom: 4 }}>
          {schema.tables.slice(0, 20).map(t => (
            <div
              key={t}
              onClick={() => navigate(`/optimizer?table=${t}`)}
              style={{
                padding: "3px 6px", borderRadius: 4,
                cursor: "pointer", color: "var(--text-secondary)",
                display: "flex", alignItems: "center", gap: 6,
                whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-elevated)")}
              onMouseLeave={e => (e.currentTarget.style.background = "none")}
            >
              <span style={{ color: "var(--success)", fontSize: 9 }}>▶</span>
              {t}
            </div>
          ))}
          {schema.table_count > 20 && (
            <div style={{ padding: "3px 6px", color: "var(--text-muted)", fontSize: 10 }}>
              +{schema.table_count - 20} more
            </div>
          )}
        </div>
      )}

      {/* Views */}
      <button
        onClick={() => setViewsOpen(v => !v)}
        style={{
          display: "flex", alignItems: "center", gap: 6,
          width: "100%", background: "none", border: "none",
          padding: "5px 4px", cursor: "pointer",
          color: "var(--text-muted)", fontSize: 10,
          textTransform: "uppercase", letterSpacing: "0.07em",
          fontWeight: 500,
        }}
      >
        <ChevronIcon open={viewsOpen} />
        Views ({schema.view_count})
      </button>
      {viewsOpen && (
        <div style={{ paddingLeft: 8, marginBottom: 4 }}>
          {schema.views.slice(0, 12).map(v => (
            <div
              key={v}
              onClick={() => navigate(`/optimizer?view=${v}`)}
              style={{
                padding: "3px 6px", borderRadius: 4,
                cursor: "pointer", color: "var(--text-secondary)",
                display: "flex", alignItems: "center", gap: 6,
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-elevated)")}
              onMouseLeave={e => (e.currentTarget.style.background = "none")}
            >
              <span style={{ color: "var(--accent)", fontSize: 9 }}>▶</span>
              {v}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Mini system status at sidebar bottom ─────────────────────────────────────
function SidebarSystemStatus() {
  const stats = useSystemStore(s => s.stats);

  const dbStatus  = stats?.db.status     ?? "unknown";
  const olStatus  = stats?.ollama.status ?? "unknown";

  return (
    <div style={{ padding: "12px 16px", borderTop: "0.5px solid var(--border)" }}>
      <div style={{
        fontSize: 10, color: "var(--text-muted)",
        textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8,
      }}>
        System
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {[
          { label: stats?.db.database || "Database", note: "SQL Server", dotClass: dbStatus === "online" ? "online" : "offline" },
          { label: "Ollama",
            note: stats?.ollama.active_models.length
              ? `${stats.ollama.active_models.length} loaded`
              : "offline",
            dotClass: olStatus === "online" ? "online" : "offline",
          },
          { label: "Git", note: "tracked", dotClass: "online" },
        ].map(row => (
          <div key={row.label} style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <div className={`status-dot ${row.dotClass}`} />
            <span style={{ fontSize: 11, color: "var(--text-secondary)", flex: 1 }}>{row.label}</span>
            <span style={{ fontSize: 10, color: "var(--text-muted)" }}>{row.note}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main Sidebar ──────────────────────────────────────────────────────────────
export function Sidebar() {
  const [schema, setSchema]   = useState<SchemaAll | null>(null);
  const [loading, setLoading] = useState(true);
  const { activeClient }      = useClientStore();

  useEffect(() => {
    schemaApi.getAll()
      .then(setSchema)
      .catch(() => setSchema({ tables: [], views: [], table_count: 0, view_count: 0 }))
      .finally(() => setLoading(false));
  }, [activeClient]);

  return (
    <aside style={{
      width: "var(--sidebar-width)",
      flexShrink: 0,
      background: "var(--bg-surface)",
      borderRight: "0.5px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      height: "100vh",
      position: "sticky",
      top: 0,
      overflow: "hidden",
    }}>

      {/* Logo + client switcher */}
      <div style={{ padding: "18px 16px 14px", borderBottom: "0.5px solid var(--border)" }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 9, marginBottom: 14 }}>
          <div style={{
            width: 30, height: 30, background: "var(--accent)",
            borderRadius: 7, display: "flex", alignItems: "center",
            justifyContent: "center", flexShrink: 0,
          }}>
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <ellipse cx="8" cy="4" rx="5.5" ry="2.2" stroke="white" strokeWidth="1.3" />
              <path d="M2.5 4v8c0 1.2 2.5 2.2 5.5 2.2s5.5-1 5.5-2.2V4" stroke="white" strokeWidth="1.3" />
              <path d="M2.5 8c0 1.2 2.5 2.2 5.5 2.2s5.5-1 5.5-2.2" stroke="white" strokeWidth="1.3" />
            </svg>
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)" }}>SQL Agent</div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 1 }}>v4.0 · localhost:8000</div>
          </div>
        </div>

        {/* Client switcher */}
        <div style={{
          background: "var(--bg-elevated)",
          border: "0.5px solid var(--border-strong)",
          borderRadius: 7, padding: "7px 11px",
          display: "flex", alignItems: "center",
          justifyContent: "space-between", cursor: "pointer",
        }}>
          <div>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", lineHeight: 1.2 }}>
              Active client
            </div>
            <div style={{ fontSize: 12, fontWeight: 500, color: "var(--text-primary)", marginTop: 1 }}>
              {activeClient || "—"}
            </div>
          </div>
          <ChevronIcon open={false} />
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "10px 8px", display: "flex", flexDirection: "column", gap: 1 }}>
        <div style={{ fontSize: 10, color: "#CBD5E1", textTransform: "uppercase", letterSpacing: "0.08em", padding: "4px 8px 6px" }}>
          Main
        </div>
        <NavItem to="/dashboard"   icon={<DashIcon />}      label="Dashboard" />
        <NavItem to="/optimizer"   icon={<OptimizerIcon />} label="Query Optimizer" />
        <NavItem to="/visualizer"  icon={<PlanIcon />}      label="Plan Visualizer" />
        <NavItem to="/deploy"      icon={<DeployIcon />}    label="Deployment Gate"
          badge={<span className="badge badge-danger" style={{ fontSize: 10, padding: "1px 6px" }}>3</span>}
        />
        <NavItem to="/history"     icon={<HistoryIcon />}   label="History & Trends" />

        <div style={{ height: "0.5px", background: "var(--bg-elevated)", margin: "6px 4px" }} />
        <div style={{ fontSize: 10, color: "#CBD5E1", textTransform: "uppercase", letterSpacing: "0.08em", padding: "4px 8px 6px" }}>
          Config
        </div>
        <NavItem to="/models"   icon={<ModelIcon />}   label="Model Manager" />
        <NavItem to="/clients"  icon={<ClientIcon />}  label="Client Manager" />
        <NavItem to="/settings" icon={<SettingsIcon />} label="Settings" />
      </nav>

      {/* Schema tree */}
      <div style={{ flex: 1, overflowY: "auto", padding: "8px 12px", borderTop: "0.5px solid var(--border)" }}>
        <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
          Schema
        </div>
        <SchemaTree schema={schema} loading={loading} />
      </div>

      {/* System status */}
      <SidebarSystemStatus />
    </aside>
  );
}
