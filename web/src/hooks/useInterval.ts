// src/hooks/useInterval.ts
import { useEffect, useRef } from "react";

/**
 * Calls `callback` every `delay` ms.
 * Passing `null` as delay pauses the interval.
 * Callback ref is always fresh — no stale closure issues.
 */
export function useInterval(callback: () => void, delay: number | null) {
  const savedCallback = useRef(callback);

  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  useEffect(() => {
    if (delay === null) return;
    const id = setInterval(() => savedCallback.current(), delay);
    return () => clearInterval(id);
  }, [delay]);
}
