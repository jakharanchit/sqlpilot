// src/components/shared/EmptyState.tsx
interface Props {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 text-center">
      <div
        style={{
          width: 40, height: 40,
          borderRadius: 10,
          background: "var(--bg-elevated)",
          display: "flex", alignItems: "center", justifyContent: "center",
          marginBottom: 12,
        }}
      >
        <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
          <circle cx="9" cy="9" r="7.5" stroke="var(--text-muted)" strokeWidth="1.3" />
          <path d="M9 6v4M9 12v.5" stroke="var(--text-muted)" strokeWidth="1.4" strokeLinecap="round" />
        </svg>
      </div>
      <p style={{ fontSize: 13, fontWeight: 500, color: "var(--text-primary)", margin: 0 }}>
        {title}
      </p>
      {description && (
        <p style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 4, maxWidth: 280 }}>
          {description}
        </p>
      )}
      {action && <div style={{ marginTop: 14 }}>{action}</div>}
    </div>
  );
}
