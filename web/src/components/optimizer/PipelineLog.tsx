import { useEffect, useRef, useState, useCallback } from 'react';
import type { LogLine, JobStatus } from '../../types';

interface Props {
  lines:    LogLine[];
  status:   JobStatus | null;
  onClear?: () => void;
}

/** Classify a log line to determine its color / icon. */
function classifyLine(text: string): 'success' | 'error' | 'warn' | 'step' | 'section' | 'info' | 'dim' {
  const t = text.trim();
  if (t.startsWith('✓') || t.startsWith('[green]') || t.includes('✓')) return 'success';
  if (t.startsWith('✗') || t.startsWith('[red]'))  return 'error';
  if (t.includes('⚠') || t.includes('⚡'))         return 'warn';
  if (/^▶\s+Step \d+\/\d+/.test(t))                return 'step';
  if (t.startsWith('━') || t.startsWith('─'))       return 'section';
  if (t.startsWith('→') || t.startsWith('[cyan]'))  return 'info';
  if (t.startsWith('[dim]') || t.startsWith('  '))  return 'dim';
  return 'info';
}

const classMap: Record<string, string> = {
  success: 'log-success',
  error:   'log-error',
  warn:    'log-warn',
  step:    'log-step',
  section: 'log-section',
  info:    'log-info',
  dim:     'log-dim',
};

export function PipelineLog({ lines, status, onClear }: Props) {
  const scrollRef    = useRef<HTMLDivElement>(null);
  const [pinned, setPinned] = useState(true);

  // Auto-scroll when pinned
  useEffect(() => {
    if (pinned && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [lines, pinned]);

  // Re-pin when job starts
  useEffect(() => {
    if (status === 'running' || status === 'queued') {
      setPinned(true);
    }
  }, [status]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    setPinned(atBottom);
  }, []);

  const scrollToBottom = useCallback(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      setPinned(true);
    }
  }, []);

  const isEmpty = lines.length === 0;

  return (
    <div className="pipeline-log">
      {/* Toolbar */}
      <div className="pl-toolbar">
        <span className="pl-title">
          {status === 'running' && <span className="pl-running-dot" />}
          Pipeline Output
          {lines.length > 0 && <span className="pl-count">{lines.length} lines</span>}
        </span>
        <div className="pl-actions">
          {!pinned && (
            <button className="pl-action-btn" onClick={scrollToBottom} title="Scroll to bottom">
              ↓
            </button>
          )}
          {lines.length > 0 && onClear && (
            <button className="pl-action-btn" onClick={onClear}>Clear</button>
          )}
        </div>
      </div>

      {/* Log body */}
      <div className="pl-body" ref={scrollRef} onScroll={handleScroll}>
        {isEmpty ? (
          <div className="pl-empty">
            <span>Output will stream here when pipeline runs</span>
          </div>
        ) : (
          <div className="pl-lines">
            {lines.map((l, i) => {
              const cls = l.kind === 'error' ? 'log-error'
                        : l.kind === 'step'  ? 'log-step'
                        : classMap[classifyLine(l.line)];
              return (
                <div key={i} className={`pl-line ${cls}`}>
                  <span className="pl-ts">{l.ts}</span>
                  <span className="pl-text">{l.line}</span>
                </div>
              );
            })}

            {/* Blinking cursor while running */}
            {(status === 'running' || status === 'queued') && (
              <div className="pl-cursor">
                <span className="pl-ts">&nbsp;</span>
                <span className="pl-caret">▋</span>
              </div>
            )}
          </div>
        )}
      </div>

      <style>{`
        .pipeline-log {
          display: flex;
          flex-direction: column;
          height: 100%;
          background: #0f1117;
          border-radius: 10px;
          overflow: hidden;
          border: 1px solid #1e2230;
        }
        .pl-toolbar {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 8px 12px;
          background: #161b27;
          border-bottom: 1px solid #1e2230;
          flex-shrink: 0;
        }
        .pl-title {
          display: flex;
          align-items: center;
          gap: 7px;
          font-size: 11px;
          font-weight: 600;
          color: #8892a4;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }
        .pl-running-dot {
          width: 7px; height: 7px;
          border-radius: 50%;
          background: #22c55e;
          animation: blink 1s ease-in-out infinite;
          flex-shrink: 0;
        }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.25} }
        .pl-count {
          font-weight: 400;
          font-size: 10px;
          color: #4b5563;
          background: #1e2230;
          padding: 1px 6px;
          border-radius: 10px;
        }
        .pl-actions { display: flex; gap: 6px; }
        .pl-action-btn {
          background: #1e2230;
          border: none;
          color: #8892a4;
          font-size: 11px;
          padding: 3px 8px;
          border-radius: 4px;
          cursor: pointer;
          transition: background 0.15s;
        }
        .pl-action-btn:hover { background: #2d3748; }
        .pl-body {
          flex: 1;
          overflow-y: auto;
          padding: 8px 0;
          font-family: 'JetBrains Mono', monospace;
          font-size: 11.5px;
          line-height: 1.6;
          scrollbar-width: thin;
          scrollbar-color: #2d3748 transparent;
        }
        .pl-body::-webkit-scrollbar { width: 6px; }
        .pl-body::-webkit-scrollbar-thumb { background: #2d3748; border-radius: 3px; }
        .pl-empty {
          display: flex;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: #4b5563;
          font-size: 12px;
          font-family: inherit;
        }
        .pl-lines { padding: 0; }
        .pl-line {
          display: flex;
          gap: 10px;
          padding: 1px 12px;
          transition: background 0.1s;
        }
        .pl-line:hover { background: rgba(255,255,255,0.02); }
        .pl-ts {
          flex-shrink: 0;
          width: 54px;
          color: #3d4a5c;
          user-select: none;
          font-size: 10px;
          padding-top: 1px;
        }
        .pl-text { flex: 1; white-space: pre-wrap; word-break: break-all; color: #cdd4e0; }
        /* Line type colors */
        .log-success .pl-text { color: #4ade80; }
        .log-error   .pl-text { color: #f87171; }
        .log-warn    .pl-text { color: #fbbf24; }
        .log-step    .pl-text { color: #60a5fa; font-weight: 600; }
        .log-section .pl-text { color: #475569; }
        .log-info    .pl-text { color: #67e8f9; }
        .log-dim     .pl-text { color: #4b5563; }
        /* Blinking cursor */
        .pl-cursor { display: flex; gap: 10px; padding: 1px 12px; }
        .pl-caret {
          color: #60a5fa;
          animation: blink 0.8s step-end infinite;
          font-size: 13px;
        }
      `}</style>
    </div>
  );
}
