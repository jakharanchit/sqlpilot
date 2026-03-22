import { useEffect, useRef } from 'react';
import type { SSEEvent } from '../types';

interface SSEHandlers {
  onMessage?:  (event: SSEEvent) => void;
  onComplete?: (result: any) => void;
  onError?:    (message: string) => void;
}

export function useSSE(url: string | null, handlers: SSEHandlers) {
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;

  useEffect(() => {
    if (!url) return;

    const es = new EventSource(url);

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as SSEEvent;

        // Route to appropriate handler
        handlersRef.current.onMessage?.(data);

        if (data.type === 'complete') {
          handlersRef.current.onComplete?.((data as any).result);
          es.close();
        } else if (data.type === 'error') {
          handlersRef.current.onError?.((data as any).message ?? 'Unknown error');
          es.close();
        }
        // pings are silently ignored
      } catch {
        // malformed JSON — ignore
      }
    };

    es.onerror = () => {
      // Only report if still connected — browser may fire onerror when stream ends
      if (es.readyState === EventSource.CLOSED) return;
      handlersRef.current.onError?.('Connection lost');
      es.close();
    };

    return () => es.close();
  }, [url]);
}
