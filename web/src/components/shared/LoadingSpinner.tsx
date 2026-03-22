// src/components/shared/LoadingSpinner.tsx
import clsx from "clsx";

interface Props {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizes = { sm: "w-3 h-3", md: "w-5 h-5", lg: "w-8 h-8" };

export function LoadingSpinner({ size = "md", className }: Props) {
  return (
    <div
      className={clsx(
        "animate-spin rounded-full border-2 border-slate-200 border-t-blue-600",
        sizes[size],
        className
      )}
    />
  );
}
