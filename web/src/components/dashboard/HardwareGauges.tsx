// src/components/dashboard/HardwareGauges.tsx
import { RadialBarChart, RadialBar, ResponsiveContainer } from "recharts";
import { useSystemStore } from "@/store/systemStore";
import { LoadingSpinner } from "@/components/shared/LoadingSpinner";

// ── Single gauge card ─────────────────────────────────────────────────────────
interface GaugeProps {
  label: string;
  value: number;       // display value (e.g. 45.2)
  unit: string;        // e.g. "%" or " GB"
  subtitle: string;    // e.g. "Normal" or "of 32 GB"
  pct: number;         // 0–100 percentage for fill
  color: string;
  critical?: boolean;  // triggers pulsing red border
  footer?: { label: string; value: string }[];
}

function GaugeCard({ label, value, unit, subtitle, pct, color, critical, footer }: GaugeProps) {
  const fillPct = Math.min(100, Math.max(0, pct));
  const data = [{ value: fillPct, fill: color }];

  return (
    <div
      className={critical ? "card animate-pulse-danger" : "card"}
      style={{
        padding: "18px 16px",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        border: critical ? "1.5px solid var(--danger)" : undefined,
      }}
    >
      {/* Label row */}
      <div style={{
        display: "flex", alignItems: "center", gap: 7, marginBottom: 14,
      }}>
        {critical && (
          <span className="badge badge-danger" style={{ fontSize: 10 }}>
            {Math.round(pct)}% — critical
          </span>
        )}
        {!critical && (
          <div style={{
            fontSize: 10, fontWeight: 500,
            color: critical ? "var(--danger)" : "var(--text-muted)",
            textTransform: "uppercase", letterSpacing: "0.07em",
          }}>
            {label}
          </div>
        )}
      </div>

      {critical && (
        <div style={{
          fontSize: 10, fontWeight: 500,
          color: "var(--danger)",
          textTransform: "uppercase", letterSpacing: "0.07em",
          marginBottom: 10,
        }}>
          {label}
        </div>
      )}

      {/* Gauge */}
      <div style={{ position: "relative", width: 130, height: 130 }}>
        <ResponsiveContainer width="100%" height="100%">
          <RadialBarChart
            cx="50%"
            cy="50%"
            innerRadius="75%"
            outerRadius="100%"
            startAngle={210}
            endAngle={-30}
            data={data}
            barSize={10}
          >
            {/* Track */}
            <RadialBar
              background={{ fill: critical ? "#FEE2E2" : "#E2E8F0" }}
              dataKey="value"
              cornerRadius={5}
            />
          </RadialBarChart>
        </ResponsiveContainer>

        {/* Center text */}
        <div style={{
          position: "absolute", inset: 0,
          display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center",
          pointerEvents: "none",
        }}>
          <span style={{
            fontSize: 22, fontWeight: 500, lineHeight: 1,
            color: critical ? "var(--danger)" : "var(--text-primary)",
          }}>
            {typeof value === "number" ? value.toFixed(value >= 10 ? 1 : 1) : value}
            <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 400 }}>{unit}</span>
          </span>
          <span style={{ fontSize: 10, color: "var(--text-muted)", marginTop: 3 }}>{subtitle}</span>
        </div>
      </div>

      {/* Footer stats */}
      {footer && (
        <div style={{ display: "flex", gap: 14, marginTop: 10 }}>
          {footer.map(f => (
            <div key={f.label} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 10, color: "var(--text-muted)" }}>{f.label}</div>
              <div style={{
                fontSize: 12, fontWeight: 500,
                color: critical && f.label === "Status" ? "var(--danger)" : "var(--text-primary)",
              }}>
                {f.value}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* VRAM warning message */}
      {critical && (
        <div style={{
          fontSize: 11, color: "var(--danger)", textAlign: "center",
          marginTop: 10, lineHeight: 1.4,
        }}>
          VRAM nearly full — optimization<br />may slow or switch to CPU
        </div>
      )}
    </div>
  );
}

// ── VRAM unavailable placeholder ──────────────────────────────────────────────
function GpuUnavailable() {
  return (
    <div className="card" style={{
      padding: "18px 16px",
      display: "flex", flexDirection: "column", alignItems: "center",
      justifyContent: "center", minHeight: 240,
    }}>
      <div style={{ fontSize: 10, fontWeight: 500, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.07em", marginBottom: 12 }}>
        VRAM
      </div>
      <div style={{ fontSize: 12, color: "var(--text-muted)", textAlign: "center", lineHeight: 1.5 }}>
        GPU stats unavailable<br />
        <span style={{ fontSize: 11 }}>pynvml and nvidia-smi both failed</span>
      </div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────────
export function HardwareGauges() {
  const stats = useSystemStore(s => s.stats);

  if (!stats) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 14 }}>
        {[0, 1, 2].map(i => (
          <div key={i} className="card" style={{
            minHeight: 240, display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <LoadingSpinner />
          </div>
        ))}
      </div>
    );
  }

  const ramUsedGb  = +(stats.ram_usage_mb / 1024).toFixed(1);
  const ramTotalGb = +(stats.ram_total_mb / 1024).toFixed(0);
  const vramCrit   = stats.gpu ? stats.gpu.vram_pct > 90 : false;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, minmax(0, 1fr))", gap: 14 }}>

      {/* CPU */}
      <GaugeCard
        label="CPU Usage"
        value={stats.cpu_usage}
        unit="%"
        subtitle={stats.cpu_usage > 80 ? "High" : stats.cpu_usage > 50 ? "Moderate" : "Normal"}
        pct={stats.cpu_usage}
        color="#2563EB"
        footer={[
          { label: "Usage", value: `${stats.cpu_usage.toFixed(1)}%` },
          { label: "RAM free", value: `${((stats.ram_total_mb - stats.ram_usage_mb) / 1024).toFixed(1)} GB` },
          { label: "Status", value: stats.cpu_usage > 95 ? "Critical" : "OK" },
        ]}
      />

      {/* RAM */}
      <GaugeCard
        label="System RAM"
        value={ramUsedGb}
        unit=" GB"
        subtitle={`of ${ramTotalGb} GB`}
        pct={stats.ram_pct}
        color="#2563EB"
        footer={[
          { label: "Used", value: `${stats.ram_pct.toFixed(1)}%` },
          { label: "Free", value: `${((stats.ram_total_mb - stats.ram_usage_mb) / 1024).toFixed(1)} GB` },
          { label: "Status", value: stats.ram_pct > 90 ? "High" : "OK" },
        ]}
      />

      {/* VRAM */}
      {stats.gpu ? (
        <GaugeCard
          label="VRAM"
          value={+(stats.gpu.vram_usage_mb / 1024).toFixed(1)}
          unit=" GB"
          subtitle={`of ${(stats.gpu.vram_total_mb / 1024).toFixed(0)} GB`}
          pct={stats.gpu.vram_pct}
          color={vramCrit ? "#DC2626" : "#2563EB"}
          critical={vramCrit}
          footer={vramCrit ? undefined : [
            { label: "Used", value: `${stats.gpu.vram_pct.toFixed(1)}%` },
            { label: "GPU", value: `${stats.gpu.utilization_pct}%` },
            { label: "Source", value: stats.gpu.source === "pynvml" ? "nvml" : "smi" },
          ]}
        />
      ) : (
        <GpuUnavailable />
      )}
    </div>
  );
}
