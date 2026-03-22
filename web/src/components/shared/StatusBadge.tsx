// src/components/shared/StatusBadge.tsx
import clsx from "clsx";

type Variant = "success" | "warning" | "danger" | "info" | "neutral";

interface Props {
  variant: Variant;
  children: React.ReactNode;
  className?: string;
}

export function StatusBadge({ variant, children, className }: Props) {
  return (
    <span className={clsx("badge", `badge-${variant}`, className)}>
      {children}
    </span>
  );
}
