// src/components/layout/PageShell.tsx
interface Props {
  children: React.ReactNode;
}

export function PageShell({ children }: Props) {
  return (
    <main style={{
      flex: 1,
      overflowY: "auto",
      padding: "22px",
      display: "flex",
      flexDirection: "column",
      gap: 18,
      minWidth: 0,
    }}>
      {children}
    </main>
  );
}
